# Architecture Overview

## Main flow

1. Template upload receives `side1` and `side2` files.
2. OCR workflow reads full file content and generates `raw_text + blocks + candidate fields`.
3. Template stays in `REVIEW_REQUIRED` until fields are reviewed and approved.
4. Runtime starts with `side1`, waits for confirm, then runs `side2`.
5. Compare engine returns detailed errors with `expected/actual/severity`.
6. Overall decision maps to IoT action and writes mock event payload.

## Modules

- `src/template_service`: template lifecycle and review
- `src/ocr`: mock OCR workflow, parser and postprocess
- `src/preprocess`: fixed ROI and quality gate placeholders
- `src/compare`: compare field/required/extra/runtime OCR result
- `src/decision`: side decision, overall decision, operator action
- `src/pipeline`: side pipeline and state-machine orchestration
- `src/api`: FastAPI-compatible boundary
- `src/iot`: mock publisher and retry queue
- `src/annotator`: saves evidence summary for each camera
