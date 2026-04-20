from __future__ import annotations

from typing import Optional

from src.api._compat import APIRouter, Depends, File, Form, HTTPException, UploadFile
from src.api.deps import ApplicationContainer, get_container
from src.api.schemas import TemplateFieldUpdatePayload, TemplateUploadPayload
from src.api.serializers import to_primitive
from src.domain.models import TemplateFieldPatch, TemplateUploadFile
from src.preprocess.split_recto_verso import RectoVersoSplitter

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("/upload")
async def upload_template(
    template_name: str = Form(...),
    product_code: str = Form(...),
    created_by: str = Form(...),
    side1_file: Optional[UploadFile] = File(None),
    side2_file: Optional[UploadFile] = File(None),
    combined_file: Optional[UploadFile] = File(None),
    container: ApplicationContainer = Depends(get_container),
):
    try:
        # Validate input: either combined_file OR (side1_file + side2_file)
        if combined_file:
            # Auto-split combined template into side1 and side2
            combined_bytes = await combined_file.read()
            splitter = RectoVersoSplitter()
            split_result = splitter.split(
                image_bytes=combined_bytes,
                filename=combined_file.filename or "combined_template.jpg",
                media_type=combined_file.content_type or "image/jpeg",
            )
            
            side1_upload = TemplateUploadFile(
                filename=split_result.side1.filename,
                content=split_result.side1.content,
                media_type=split_result.side1.media_type,
            )
            side2_upload = TemplateUploadFile(
                filename=split_result.side2.filename,
                content=split_result.side2.content,
                media_type=split_result.side2.media_type,
            )
        elif side1_file and side2_file:
            # Traditional separate side1 + side2 upload
            side1_upload = TemplateUploadFile(
                filename=side1_file.filename,
                content=await side1_file.read(),
                media_type=side1_file.content_type or "application/octet-stream",
            )
            side2_upload = TemplateUploadFile(
                filename=side2_file.filename,
                content=await side2_file.read(),
                media_type=side2_file.content_type or "application/octet-stream",
            )
        else:
            raise ValueError(
                "Must provide either combined_file OR both side1_file and side2_file"
            )

        payload = TemplateUploadPayload(
            template_name=template_name,
            product_code=product_code,
            created_by=created_by,
            side1_file=side1_upload,
            side2_file=side2_upload,
        )
        record = container.template_service.create_draft(payload.to_command())
        return to_primitive(record)
    except Exception as exc:
        import traceback
        print(f"[ERROR] Upload template failed: {exc}")
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{template_id}")
def get_template(
    template_id: str,
    container: ApplicationContainer = Depends(get_container),
):
    try:
        return to_primitive(container.template_service.get_template(template_id))
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{template_id}/preview")
def get_template_preview(
    template_id: str,
    container: ApplicationContainer = Depends(get_container),
):
    try:
        return container.template_service.get_template_preview(template_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/{template_id}/fields")
def update_template_fields(
    template_id: str,
    payload: TemplateFieldUpdatePayload,
    container: ApplicationContainer = Depends(get_container),
):
    try:
        record = container.template_service.update_fields(
            template_id=template_id,
            patches=payload.fields,
            review_notes=payload.review_notes,
        )
        return to_primitive(record)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{template_id}/approve")
def approve_template(
    template_id: str,
    approved_by: str = Form(...),
    container: ApplicationContainer = Depends(get_container),
):
    try:
        record = container.template_service.approve_template(template_id, approved_by)
        return to_primitive(record)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
