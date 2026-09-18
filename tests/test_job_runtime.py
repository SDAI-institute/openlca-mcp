"""Tests for the OpenLCA compatibility background-job runtime."""

import time

from src.job_runtime import JobManager


class MemoryPersistence:
    def __init__(self) -> None:
        self.rows = {}

    def save(self, payload):
        self.rows[payload["job_id"]] = dict(payload)
        return True

    def load_all(self):
        return [dict(row) for row in self.rows.values()]

    def delete(self, job_id):
        self.rows.pop(job_id, None)


def _wait(manager, job_id, owner="tenant", timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = manager.status(job_id, owner)
        if body.get("terminal"):
            return body
        time.sleep(0.01)
    raise AssertionError(f"job {job_id} did not finish")


def test_job_roundtrip_and_pagination():
    manager = JobManager(max_workers=1, ttl_seconds=60)
    try:
        submitted = manager.submit(
            "fake", "default", "tenant", lambda: {"rows": list(range(10))}
        )
        status = _wait(manager, submitted["job_id"])
        assert status["status"] == "completed"
        page = manager.result(
            submitted["job_id"], "tenant", field="rows", offset=2, limit=3
        )
        assert page["result"] == [2, 3, 4]
        assert page["pagination"]["next_offset"] == 5
    finally:
        manager.shutdown()


def test_job_owner_isolation():
    manager = JobManager(max_workers=1, ttl_seconds=60)
    try:
        submitted = manager.submit("fake", "default", "tenant-a", lambda: 1)
        _wait(manager, submitted["job_id"], owner="tenant-a")
        hidden = manager.status(submitted["job_id"], "tenant-b")
        assert hidden["success"] is False
    finally:
        manager.shutdown()


def test_restart_persistence_keeps_owner_isolation_and_interrupts_running():
    persistence = MemoryPersistence()
    first = JobManager(max_workers=1, ttl_seconds=60, persistence=persistence)
    try:
        submitted = first.submit("fake", "default", "tenant-a", lambda: {"rows": [1, 2]})
        assert _wait(first, submitted["job_id"], owner="tenant-a")["status"] == "completed"
        completed_id = submitted["job_id"]
    finally:
        first.shutdown()

    persistence.save({
        "success": True, "job_id": "job_running_fixture", "tool_name": "fake",
        "connection": "default", "owner": "tenant-a", "status": "running",
        "created_at": time.time() - 5, "started_at": time.time() - 4,
        "completed_at": None, "terminal": False, "result": None,
    })
    second = JobManager(max_workers=1, ttl_seconds=60, persistence=persistence)
    try:
        assert second.result(completed_id, "tenant-a")["result"] == {"rows": [1, 2]}
        assert second.status(completed_id, "tenant-b")["success"] is False
        interrupted = second.status("job_running_fixture", "tenant-a")
        assert interrupted["status"] == "interrupted"
        assert interrupted["terminal"] is True
    finally:
        second.shutdown()


def test_failed_job_surfaces_error():
    manager = JobManager(max_workers=1, ttl_seconds=60)
    try:
        def fail():
            raise RuntimeError("boom")

        submitted = manager.submit("fake", "default", "tenant", fail)
        status = _wait(manager, submitted["job_id"])
        assert status["status"] == "failed"
        assert "RuntimeError: boom" in status["error"]
    finally:
        manager.shutdown()
