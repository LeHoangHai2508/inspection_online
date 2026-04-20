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
    Parse Tesseract output - keep it simple, don't lose text.
    Create one block per token, let render_blocks_to_text handle grouping.
    """
    blocks: list[OCRBlock] = []
    texts = data.get("text", [])
    confidences = data.get("conf", [])
    lefts = data.get("left", [])
    tops = data.get("top", [])
    widths = data.get("width", [])
    heights = data.get("height", [])

    for index, text in enumerate(texts):
        cleaned = str(text).strip()
        if not cleaned:
            continue

        confidence = _safe_confidence(confidences[index] if index < len(confidences) else 0)
        left = int(lefts[index]) if index < len(lefts) else 0
        top = int(tops[index]) if index < len(tops) else 0
        width = int(widths[index]) if index < len(widths) else 0
        height = int(heights[index]) if index < len(heights) else 0
        
        blocks.append(
            OCRBlock(
                text=cleaned,
                bbox=BoundingBox(left, top, left + width, top + height),
                confidence=confidence,
                line_index=len(blocks) + 1,
            )
        )
    
    return blocks


def render_blocks_to_text(blocks: list[OCRBlock]) -> str:
    """
    Render blocks thành text, ghép các block trên cùng dòng lại với nhau.
    """
    if not blocks:
        return ""
    
    # Sort theo Y, X
    sorted_blocks = sorted(blocks, key=lambda b: (b.bbox.y1, b.bbox.x1))
    
    if not sorted_blocks:
        return ""
    
    lines = []
    current_line = []
    current_y = sorted_blocks[0].bbox.y1
    line_height_threshold = 10  # Nếu chênh lệch Y < 10px thì coi là cùng dòng
    
    for block in sorted_blocks:
        # Nếu block này gần với dòng hiện tại (cùng dòng)
        if abs(block.bbox.y1 - current_y) <= line_height_threshold:
            current_line.append(block.text)
        else:
            # Xuống dòng mới
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [block.text]
            current_y = block.bbox.y1
    
    # Thêm dòng cuối
    if current_line:
        lines.append(" ".join(current_line))
    
    return "\n".join(lines)


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
