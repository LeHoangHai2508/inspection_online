from __future__ import annotations

from src.api._compat import APIRouter, Depends, HTTPException
from src.api.deps import ApplicationContainer, get_container

router = APIRouter(prefix="/counter", tags=["counter"])


@router.get("/summary")
def get_summary(container: ApplicationContainer = Depends(get_container)):
    """Return aggregated KPI counts: total / OK / NG / UNCERTAIN / error_rate."""
    try:
        return container.counter_service.get_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/recent")
def get_recent(
    limit: int = 10,
    container: ApplicationContainer = Depends(get_container),
):
    """Return the N most recent scan jobs for the dashboard history table."""
    try:
        return container.counter_service.get_recent_jobs(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
