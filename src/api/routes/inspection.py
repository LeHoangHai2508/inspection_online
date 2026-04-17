from __future__ import annotations

import uuid

from src.api._compat import APIRouter, Depends, File, Form, HTTPException, UploadFile
from src.api.deps import ApplicationContainer, get_container
from src.api.schemas import SideInspectionPayload
from src.api.serializers import to_primitive
from src.capture.snapshot import SnapshotService
from src.domain.enums import InspectionSide
from src.domain.models import CaptureInput

router = APIRouter(prefix="/inspection", tags=["inspection"])

# Shared snapshot service — reuses the same adapter instance across requests
_snapshot_service = SnapshotService()


@router.post("/side1")
async def inspect_side1(
    scan_job_id: str = Form(...),
    template_id: str = Form(...),
    cam1_file: UploadFile = File(...),
    cam2_file: UploadFile = File(...),
    container: ApplicationContainer = Depends(get_container),
):
    try:
        container.inspection_orchestrator.start_scan_job(
            scan_job_id=scan_job_id,
            template_id=template_id,
        )
        payload = SideInspectionPayload(
            scan_job_id=scan_job_id,
            template_id=template_id,
            side=InspectionSide.SIDE1,
            captures=[
                CaptureInput(
                    filename=cam1_file.filename,
                    content=await cam1_file.read(),
                    media_type=cam1_file.content_type or "application/octet-stream",
                    camera_id="cam1",
                ),
                CaptureInput(
                    filename=cam2_file.filename,
                    content=await cam2_file.read(),
                    media_type=cam2_file.content_type or "application/octet-stream",
                    camera_id="cam2",
                ),
            ],
        )
        result = container.inspection_orchestrator.inspect_side1(
            scan_job_id,
            payload.to_command(),
        )
        return to_primitive(result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{scan_job_id}/confirm-side2")
def confirm_side2(
    scan_job_id: str,
    container: ApplicationContainer = Depends(get_container),
):
    try:
        job = container.inspection_orchestrator.confirm_side2(scan_job_id)
        return {"scan_job_id": job.scan_job_id, "state": job.state.value}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/side2")
async def inspect_side2(
    scan_job_id: str = Form(...),
    template_id: str = Form(...),
    cam1_file: UploadFile = File(...),
    cam2_file: UploadFile = File(...),
    container: ApplicationContainer = Depends(get_container),
):
    try:
        payload = SideInspectionPayload(
            scan_job_id=scan_job_id,
            template_id=template_id,
            side=InspectionSide.SIDE2,
            captures=[
                CaptureInput(
                    filename=cam1_file.filename,
                    content=await cam1_file.read(),
                    media_type=cam1_file.content_type or "application/octet-stream",
                    camera_id="cam1",
                ),
                CaptureInput(
                    filename=cam2_file.filename,
                    content=await cam2_file.read(),
                    media_type=cam2_file.content_type or "application/octet-stream",
                    camera_id="cam2",
                ),
            ],
        )
        result = container.inspection_orchestrator.inspect_side2(
            scan_job_id,
            payload.to_command(),
        )
        return to_primitive(result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{scan_job_id}/result")
def get_result(
    scan_job_id: str,
    container: ApplicationContainer = Depends(get_container),
):
    try:
        return to_primitive(container.inspection_orchestrator.get_result(scan_job_id))
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Live routes — capture directly from cameras (Mode B)
# ---------------------------------------------------------------------------

@router.post("/side1/live")
def inspect_side1_live(
    scan_job_id: str = Form(...),
    template_id: str = Form(...),
    container: ApplicationContainer = Depends(get_container),
):
    """Capture cam1+cam2 from live cameras and run side1 inspection."""
    try:
        container.inspection_orchestrator.start_scan_job(
            scan_job_id=scan_job_id,
            template_id=template_id,
        )
        snapshot = _snapshot_service.capture_side(InspectionSide.SIDE1)
        payload = SideInspectionPayload(
            scan_job_id=scan_job_id,
            template_id=template_id,
            side=InspectionSide.SIDE1,
            captures=snapshot.as_list(),
        )
        result = container.inspection_orchestrator.inspect_side1(
            scan_job_id,
            payload.to_command(),
        )
        return to_primitive(result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/side2/live")
def inspect_side2_live(
    scan_job_id: str = Form(...),
    template_id: str = Form(...),
    container: ApplicationContainer = Depends(get_container),
):
    """Capture cam1+cam2 from live cameras and run side2 inspection."""
    try:
        snapshot = _snapshot_service.capture_side(InspectionSide.SIDE2)
        payload = SideInspectionPayload(
            scan_job_id=scan_job_id,
            template_id=template_id,
            side=InspectionSide.SIDE2,
            captures=snapshot.as_list(),
        )
        result = container.inspection_orchestrator.inspect_side2(
            scan_job_id,
            payload.to_command(),
        )
        return to_primitive(result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
