from __future__ import annotations

from src.domain.models import TemplateFieldDefinition, TemplateUploadRequest


def validate_template_upload_request(request: TemplateUploadRequest) -> None:
    if not request.template_name.strip():
        raise ValueError("template_name is required.")
    if not request.product_code.strip():
        raise ValueError("product_code is required.")
    if not request.created_by.strip():
        raise ValueError("created_by is required.")

    has_side1_source = bool(request.side1_file or request.side1_fields)
    has_side2_source = bool(request.side2_file or request.side2_fields)

    if not has_side1_source or not has_side2_source:
        raise ValueError("Both side1 and side2 require either a file or field list.")

    if request.side1_fields:
        _validate_side_fields("side1", request.side1_fields)
    if request.side2_fields:
        _validate_side_fields("side2", request.side2_fields)


def _validate_side_fields(
    side_name: str,
    fields: list[TemplateFieldDefinition],
) -> None:
    if not fields:
        raise ValueError(f"{side_name} must contain at least one field.")

    field_names = [field.field_name for field in fields]
    if len(field_names) != len(set(field_names)):
        raise ValueError(f"{side_name} contains duplicated field names.")

    for field in fields:
        if not field.field_name.strip():
            raise ValueError(f"{side_name} has a field with empty field_name.")
        if field.required and not field.expected_value.strip():
            raise ValueError(
                f"{side_name}.{field.field_name} requires an expected_value."
            )
