from __future__ import annotations

import re
from typing import Any

from src.domain.models import BoundingBox, OCRBlock


def _is_arabic_token(text: str) -> bool:
    """
    Kiểm tra token có chứa ký tự Arabic hay không.
    Không dựa vào từ cụ thể, chỉ dựa vào script.
    """
    if not text:
        return False
    return bool(re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", text))


def _merge_items_preserve_script_direction(items: list[dict]) -> str:
    """
    Ghép token theo từng cụm script:
    - Cụm Arabic: phải -> trái
    - Cụm khác: trái -> phải
    
    Mục tiêu:
    - Không đảo cả dòng
    - Chỉ đảo đúng span Arabic liền nhau
    """
    if not items:
        return ""

    ordered = sorted(items, key=lambda item: item["left"])

    spans: list[list[dict]] = []
    current_span: list[dict] = [ordered[0]]
    current_is_arabic = _is_arabic_token(ordered[0]["text"])

    for item in ordered[1:]:
        item_is_arabic = _is_arabic_token(item["text"])

        if item_is_arabic == current_is_arabic:
            current_span.append(item)
        else:
            spans.append(current_span)
            current_span = [item]
            current_is_arabic = item_is_arabic

    if current_span:
        spans.append(current_span)

    merged_parts: list[str] = []

    for span in spans:
        if _is_arabic_token(span[0]["text"]):
            span = sorted(span, key=lambda item: item["left"], reverse=True)
        else:
            span = sorted(span, key=lambda item: item["left"])

        merged_parts.extend(item["text"] for item in span)

    return " ".join(merged_parts).strip()


def parse_text_to_blocks(raw_text: str, confidence: float = 0.99) -> list[OCRBlock]:
    blocks: list[OCRBlock] = []

    for line_index, line in enumerate(raw_text.splitlines(), start=1):
        cleaned = line.strip()
        if not cleaned:
            continue
        blocks.append(
            OCRBlock(
                text=cleaned,
                bbox=BoundingBox(0, line_index * 20, 400, line_index * 20 + 18),
                confidence=confidence,
                line_index=line_index,
            )
        )

    return blocks


def parse_paddle_output(result: Any) -> list[OCRBlock]:
    blocks: list[OCRBlock] = []
    if not result:
        return blocks

    line_index = 1
    for page in result:
        if not page:
            continue
        for item in page:
            if not item or len(item) < 2:
                continue
            bbox_points = item[0]
            text, confidence = item[1]
            blocks.append(
                OCRBlock(
                    text=str(text).strip(),
                    bbox=_bbox_from_points(bbox_points),
                    confidence=float(confidence),
                    line_index=line_index,
                )
            )
            line_index += 1
    return blocks


def parse_tesseract_data(data: dict[str, list[Any]]) -> list[OCRBlock]:
    """
    Parse output của Tesseract theo đúng line thực tế.
    
    Ý tưởng:
    - Tesseract trả về nhiều token rời.
    - Mỗi token có block_num, par_num, line_num.
    - Ta group token theo (block_num, par_num, line_num) để tạo ra 1 OCRBlock cho mỗi dòng thật.
    - Như vậy sẽ giảm tình trạng text bị đảo thứ tự hoặc bị xé nhỏ.
    """
    texts = data.get("text", [])
    confidences = data.get("conf", [])
    lefts = data.get("left", [])
    tops = data.get("top", [])
    widths = data.get("width", [])
    heights = data.get("height", [])

    block_nums = data.get("block_num", [])
    par_nums = data.get("par_num", [])
    line_nums = data.get("line_num", [])

    grouped: dict[tuple[int, int, int], list[dict[str, Any]]] = {}

    for index, text in enumerate(texts):
        cleaned = str(text).strip()
        if not cleaned:
            continue

        block_num = int(block_nums[index]) if index < len(block_nums) else 0
        par_num = int(par_nums[index]) if index < len(par_nums) else 0
        line_num = int(line_nums[index]) if index < len(line_nums) else 0

        left = int(lefts[index]) if index < len(lefts) else 0
        top = int(tops[index]) if index < len(tops) else 0
        width = int(widths[index]) if index < len(widths) else 0
        height = int(heights[index]) if index < len(heights) else 0
        confidence = _safe_confidence(
            confidences[index] if index < len(confidences) else 0
        )

        key = (block_num, par_num, line_num)
        grouped.setdefault(key, []).append(
            {
                "text": cleaned,
                "left": left,
                "top": top,
                "width": width,
                "height": height,
                "confidence": confidence,
            }
        )

    if not grouped:
        return []

    # Sort theo vị trí thực trên ảnh: ưu tiên top trước, rồi left
    sorted_groups = sorted(
        grouped.values(),
        key=lambda items: (
            min(item["top"] for item in items),
            min(item["left"] for item in items),
        ),
    )

    blocks: list[OCRBlock] = []

    for line_index, items in enumerate(sorted_groups, start=1):
        merged_text = _merge_items_preserve_script_direction(items)
        if not merged_text:
            continue

        x1 = min(item["left"] for item in items)
        y1 = min(item["top"] for item in items)
        x2 = max(item["left"] + item["width"] for item in items)
        y2 = max(item["top"] + item["height"] for item in items)
        avg_confidence = sum(item["confidence"] for item in items) / len(items)

        blocks.append(
            OCRBlock(
                text=merged_text,
                bbox=BoundingBox(x1, y1, x2, y2),
                confidence=avg_confidence,
                line_index=line_index,
            )
        )

    return blocks


def render_blocks_to_text(blocks: list[OCRBlock]) -> str:
    """
    Ở đây KHÔNG tự đoán lại dòng nữa.
    parse_tesseract_data đã group thành dòng rồi.
    Chỉ cần sort ổn định và render ra text.
    """
    if not blocks:
        return ""

    sorted_blocks = sorted(
        blocks,
        key=lambda block: (block.line_index, block.bbox.y1, block.bbox.x1),
    )

    return "\n".join(block.text for block in sorted_blocks)


def _bbox_from_points(points: list[list[float]]) -> BoundingBox:
    xs = [int(point[0]) for point in points]
    ys = [int(point[1]) for point in points]
    return BoundingBox(min(xs), min(ys), max(xs), max(ys))


def _safe_confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0

    if numeric > 1.0:
        return numeric / 100.0
    return numeric
