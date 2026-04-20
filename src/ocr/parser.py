from __future__ import annotations

from typing import Any

from src.domain.models import BoundingBox, OCRBlock


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
    Parse Tesseract output và group theo line_num để ghép lại thành dòng hoàn chỉnh.
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

    # Group tokens theo (block_num, par_num, line_num)
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
        confidence = _safe_confidence(confidences[index] if index < len(confidences) else 0)

        key = (block_num, par_num, line_num)
        grouped.setdefault(key, []).append({
            "text": cleaned,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "confidence": confidence,
        })

    # Tạo OCRBlock cho mỗi dòng
    blocks: list[OCRBlock] = []
    line_index = 1
    
    for _, items in sorted(grouped.items(), key=lambda kv: min(x["top"] for x in kv[1])):
        # Sort tokens trong dòng theo left
        items = sorted(items, key=lambda x: x["left"])

        # Join text
        line_text = " ".join(item["text"] for item in items).strip()
        if not line_text:
            continue

        # Tính bounding box của cả dòng
        x1 = min(item["left"] for item in items)
        y1 = min(item["top"] for item in items)
        x2 = max(item["left"] + item["width"] for item in items)
        y2 = max(item["top"] + item["height"] for item in items)
        avg_conf = sum(item["confidence"] for item in items) / max(len(items), 1)

        blocks.append(
            OCRBlock(
                text=line_text,
                bbox=BoundingBox(x1, y1, x2, y2),
                confidence=avg_conf,
                line_index=line_index,
            )
        )
        line_index += 1

    return blocks


def render_blocks_to_text(blocks: list[OCRBlock]) -> str:
    if not blocks:
        return ""
    # Sort theo vị trí Y, X trước khi render
    sorted_blocks = sorted(blocks, key=lambda b: (b.bbox.y1, b.bbox.x1))
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
