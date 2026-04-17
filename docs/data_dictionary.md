# Data Dictionary

## templates

- `template_id`
- `template_name`
- `product_code`
- `status`
- `created_by`

## template_versions

- `template_id`
- `version`
- `side`
- `raw_text`
- `source_file_path`

## template_fields

- `field_name`
- `field_type`
- `required`
- `compare_type`
- `priority`
- `expected_value`
- `side`
- `bbox_json`

## scan_jobs

- `scan_job_id`
- `template_id`
- `current_stage`
- `line_id`
- `station_id`

## side_results

- `scan_job_id`
- `side`
- `status`
- `raw_text`
- `processing_time_ms`

## overall_results

- `scan_job_id`
- `side1_status`
- `side2_status`
- `overall_status`
- `operator_action_required`
- `highest_severity`
