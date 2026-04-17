# Runbook

## Local start

1. Create virtual environment
2. Install `requirements.txt`
3. Initialize SQLite schema
4. Run API with `uvicorn`

## OCR usage

The current OCR layer is provider-based.

- `auto` tries `paddleocr`, then `tesseract`, then falls back to `mock`
- Template files can still be plain text files for local development
- Runtime camera uploads can also be plain text files in tests
- Each line using `field_name: value` is parsed into OCR blocks and fields in mock mode

## Example template side1 text

```text
product_code: SKU02
composition: 100 COTTON
```

## Example runtime side2 text

```text
country_of_origin: MADE IN VIETNAM
```

## Known gaps

- No real camera adapter yet
- Image crop/normalize uses ROI config and PIL when available
- Real OCR depends on installed backend packages or CLI tools
- No real DB repository yet
- UI is still minimal scaffold
