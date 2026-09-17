"""Bounded background jobs for long-running openLCA MCP operations.

The compatibility layer returns a ``job_id`` immediately for clients that do not
yet negotiate MCP Tasks. Jobs retain the authorized connection profile and tenant
that submitted them. Execution is serialized per openLCA connection so live IPC
results and profile-scoped state cannot race, while different profiles may run in
parallel when ``OPENLCA_JOB_WORKERS`` is greater than one.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

_TERMINAL = {"completed", "failed", "cancelled"}
_CONNECTION_LOCKS: dict[str, threading.RLock] = {}
_CONNECTION_LOCKS_GUARD = threading.RLock()


def connection_lock(connection_id: str) -> threading.RLock:
    """Return the process-wide lock for one openLCA connection profile."""
    with _CONNECTION_LOCKS_GUARD:
        lock = _CONNECTION_LOCKS.get(connection_id)
        if lock is None:
            lock = threading.RLock()
            _CONNECTION_LOCKS[connection_id] = lock
        return lock


@dataclass
class JobRecord:
    job_id: str
    tool_name: str
    connection_id: str
    owner: str
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    future: Optional[Future] = field(default=None, repr=False)

    def public(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "success": True,
            "job_id": self.job_id,
            "tool_name": self.tool_name,
            "connection": self.connection_id,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "terminal": self.status in _TERMINAL,
        }
        if self.error is not None:
            body["error"] = self.error
        return body


class JobManager:
    """Thread-backed job registry with tenant ownership and per-profile locking."""

    def __init__(self, max_workers: int = 2, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = max(60, int(ttl_seconds))
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)), thread_name_prefix="openlca-mcp-job"
        )
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.RLock()

    def _cleanup(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        with self._lock:
            expired = [
                job_id for job_id, rec in self._jobs.items()
                if rec.status in _TERMINAL
                and rec.completed_at is not None
                and rec.completed_at < cutoff
            ]
            for job_id in expired:
                self._jobs.pop(job_id, None)

    def submit(
        self,
        tool_name: str,
        connection_id: str,
        owner: str,
        fn: Callable[[], Any],
    ) -> dict[str, Any]:
        self._cleanup()
        rec = JobRecord(
            job_id=f"job_{uuid.uuid4().hex[:16]}",
            tool_name=tool_name,
            connection_id=connection_id,
            owner=owner,
        )
        with self._lock:
            self._jobs[rec.job_id] = rec
            rec.future = self._executor.submit(self._run, rec.job_id, fn)
        return rec.public()

    def _run(self, job_id: str, fn: Callable[[], Any]) -> None:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None or rec.status == "cancelled":
                return
            rec.status = "running"
            rec.started_at = time.time()
            connection_id = rec.connection_id
        try:
            with connection_lock(connection_id):
                result = fn()
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                rec = self._jobs.get(job_id)
                if rec is not None:
                    rec.status = "failed"
                    rec.error = f"{type(exc).__name__}: {exc}"
                    rec.completed_at = time.time()
            return
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is not None:
                rec.result = result
                rec.status = "completed"
                rec.completed_at = time.time()

    def _owned(self, job_id: str, owner: str) -> Optional[JobRecord]:
        self._cleanup()
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None or rec.owner != owner:
                return None
            return rec

    def status(self, job_id: str, owner: str) -> dict[str, Any]:
        rec = self._owned(job_id, owner)
        return rec.public() if rec else {"success": False, "error": f"unknown job_id '{job_id}'"}

    def result(
        self,
        job_id: str,
        owner: str,
        *,
        field: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        rec = self._owned(job_id, owner)
        if rec is None:
            return {"success": False, "error": f"unknown job_id '{job_id}'"}
        body = rec.public()
        if rec.status != "completed":
            body["ready"] = False
            return body
        body["ready"] = True
        value = rec.result
        if field is None:
            body["result"] = value
            return body
        if not isinstance(value, dict) or field not in value:
            return {"success": False, "job_id": job_id, "error": f"result field '{field}' not found"}
        selected = value[field]
        if not isinstance(selected, list):
            body.update({"field": field, "result": selected})
            return body
        offset = max(0, int(offset))
        limit = min(200, max(1, int(limit)))
        page = selected[offset: offset + limit]
        body.update({
            "field": field,
            "result": page,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": len(selected),
                "next_offset": offset + len(page) if offset + len(page) < len(selected) else None,
            },
        })
        return body

    def list_jobs(self, owner: str, limit: int = 20) -> dict[str, Any]:
        self._cleanup()
        limit = min(100, max(1, int(limit)))
        with self._lock:
            rows = sorted(
                (rec for rec in self._jobs.values() if rec.owner == owner),
                key=lambda rec: rec.created_at,
                reverse=True,
            )[:limit]
        return {"success": True, "jobs": [rec.public() for rec in rows]}

    def cancel(self, job_id: str, owner: str) -> dict[str, Any]:
        rec = self._owned(job_id, owner)
        if rec is None:
            return {"success": False, "error": f"unknown job_id '{job_id}'"}
        with self._lock:
            if rec.status in _TERMINAL:
                body = rec.public()
                body["cancelled"] = rec.status == "cancelled"
                return body
            if rec.status == "running":
                body = rec.public()
                body.update({
                    "cancelled": False,
                    "cancel_supported": False,
                    "message": "running openLCA IPC jobs cannot be interrupted safely",
                })
                return body
            cancelled = bool(rec.future and rec.future.cancel())
            if cancelled:
                rec.status = "cancelled"
                rec.completed_at = time.time()
            body = rec.public()
            body.update({"cancelled": cancelled, "cancel_supported": True})
            return body

    def dispose(self, job_id: str, owner: str) -> dict[str, Any]:
        rec = self._owned(job_id, owner)
        if rec is None:
            return {"success": False, "error": f"unknown job_id '{job_id}'"}
        if rec.status not in _TERMINAL:
            return {"success": False, "job_id": job_id, "error": "cannot dispose a non-terminal job"}
        with self._lock:
            self._jobs.pop(job_id, None)
        return {"success": True, "job_id": job_id, "disposed": True}

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)


jobs = JobManager(
    max_workers=int(os.getenv("OPENLCA_JOB_WORKERS", "2")),
    ttl_seconds=int(os.getenv("OPENLCA_JOB_TTL_SECONDS", "3600")),
)
