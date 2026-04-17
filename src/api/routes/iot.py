from __future__ import annotations

from src.api._compat import APIRouter, Depends, HTTPException
from src.api.deps import ApplicationContainer, get_container

router = APIRouter(prefix="/iot", tags=["iot"])


@router.get("/events/{scan_job_id}")
def get_iot_events(
    scan_job_id: str,
    container: ApplicationContainer = Depends(get_container),
):
    """Return all IoT publish log entries for a given scan job."""
    try:
        return container.iot_event_repository.list_by_job(scan_job_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
