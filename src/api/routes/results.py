from __future__ import annotations

import sqlite3

from src.api._compat import APIRouter, Depends, HTTPException
from src.api.deps import ApplicationContainer, get_container
from src.api.serializers import to_primitive

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/{scan_job_id}")
def get_result(
    scan_job_id: str,
    container: ApplicationContainer = Depends(get_container),
):
    """Return the final overall result for a completed scan job."""
    try:
        result = container.inspection_orchestrator.get_result(scan_job_id)
        return to_primitive(result)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/")
def list_recent(
    limit: int = 10,
    container: ApplicationContainer = Depends(get_container),
):
    """Return the most recent scan jobs with their statuses (dashboard feed)."""
    try:
        return container.counter_service.get_recent_jobs(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
