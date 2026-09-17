"""Tests for the OpenLCA compatibility background-job runtime."""

import time

from src.job_runtime import JobManager


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
