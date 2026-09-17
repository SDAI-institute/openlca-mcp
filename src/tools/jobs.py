"""Compatibility background-job controls for long-running openLCA tools."""

from __future__ import annotations

from typing import Optional

from ..app import current_job_owner, ro_tool, write_tool
from ..job_runtime import jobs
from ..schemas import arr


@ro_tool(
    "get_job_status",
    "Return status for one background openLCA job. terminal=true means the job is "
    "completed, failed, or cancelled and no further polling is required.",
    {"job_id": {"type": "string"}, "status": {"type": "string"},
     "terminal": {"type": "boolean"}, "connection": {"type": "string"}},
)
async def get_job_status(job_id: str) -> dict:
    return jobs.status(job_id, current_job_owner())


@ro_tool(
    "get_job_result",
    "Retrieve a completed background result. For a large top-level list field, pass "
    "field plus offset/limit to page it; limit is capped at 200.",
    {"job_id": {"type": "string"}, "ready": {"type": "boolean"}, "result": {}},
)
async def get_job_result(
    job_id: str,
    field: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
) -> dict:
    return jobs.result(
        job_id, current_job_owner(), field=field, offset=offset, limit=limit
    )


@ro_tool(
    "list_jobs",
    "List recent background jobs owned by the current API-key tenant.",
    {"jobs": arr({"type": "object"})},
)
async def list_jobs(limit: int = 20) -> dict:
    return jobs.list_jobs(current_job_owner(), limit)


@write_tool(
    "cancel_job",
    "Cancel a queued background job. A running openLCA IPC operation is not force-killed "
    "because interruption can leave a live calculation/result in an unsafe state.",
)
async def cancel_job(job_id: str) -> dict:
    return jobs.cancel(job_id, current_job_owner())


@write_tool(
    "dispose_job",
    "Remove a terminal compatibility job and its stored job payload. This does not dispose "
    "an openLCA calculation result_id returned inside the payload; call dispose_result too.",
)
async def dispose_job(job_id: str) -> dict:
    return jobs.dispose(job_id, current_job_owner())
