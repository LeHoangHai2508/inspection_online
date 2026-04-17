# API Contract

## `POST /templates/upload`

Form data:

- `template_name`
- `product_code`
- `created_by`
- `side1_file`
- `side2_file`

Returns template record with `REVIEW_REQUIRED`.

## `GET /templates/{template_id}`

Returns full template record.

## `GET /templates/{template_id}/preview`

Returns:

- `template_id`
- `template_version`
- `status`
- `side1_raw_text`
- `side2_raw_text`
- `side1_blocks`
- `side2_blocks`

## `PUT /templates/{template_id}/fields`

Body:

- `fields`
- `review_notes`

## `POST /templates/{template_id}/approve`

Form:

- `approved_by`

## `POST /inspection/side1`

Form:

- `scan_job_id`
- `template_id`
- `cam1_file`
- `cam2_file`

## `POST /inspection/{scan_job_id}/confirm-side2`

Moves state to `WAIT_SIDE2_CAPTURE`.

## `POST /inspection/side2`

Form:

- `scan_job_id`
- `template_id`
- `cam1_file`
- `cam2_file`

## `GET /inspection/{scan_job_id}/result`

Returns overall inspection result with side details and IoT action.
