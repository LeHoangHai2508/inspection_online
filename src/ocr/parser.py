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
    Parse Tesseract output và group các token thành dòng.
    Thay vì mỗi token một block, group theo vị trí Y gần nhau.
    """
    texts = data.get("text", [])
    confidences = data.get("conf", [])
    lefts = data.get("left", [])
    tops = data.get("top", [])
    widths = data.get("width", [])
    heights = data.get("height", [])

    # Bước 1: Thu thập tất cả tokens hợp lệ
    tokens = []
    for index, text in enumerate(texts):
        cleaned = str(text).strip()
        if not cleaned:
            continue

        confidence = _safe_confidence(confidences[index] if index < len(confidences) else 0)
        left = int(lefts[index]) if index < len(lefts) else 0
        top = int(tops[index]) if index < len(tops) else 0
        width = int(widths[index]) if index < len(widths) else 0
        height = int(heights[index]) if index < len(heights) else 0
        
        tokens.append({
            "text": cleaned,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "confidence": confidence,
        })
    
    if not tokens:
        return []
    
    # Bước 2: Group tokens thành lines theo Y position
    # Sort theo top trước
    tokens.sort(key=lambda t: (t["top"], t["left"]))
    
    lines = []
    current_line = [tokens[0]]
    current_top = tokens[0]["top"]
    line_height_threshold = tokens[0]["height"] * 0.5  # Nếu chênh lệch Y < 50% height thì cùng dòng
    
    for token in tokens[1:]:
        if abs(token["top"] - current_top) <= line_height_threshold:
            # Cùng dòng
            current_line.append(token)
        else:
            # Dòng mới
            lines.append(current_line)
            current_line = [token]
            current_top = token["top"]
            line_height_threshold = token["height"] * 0.5
    
    # Thêm dòng cuối
    if current_line:
        lines.append(current_line)
    
    # Bước 3: Tạo OCRBlock cho mỗi dòng
    blocks = []
    for line_index, line_tokens in enumerate(lines, start=1):
        # Sort tokens trong dòng theo left
        line_tokens.sort(key=lambda t: t["left"])
        
        # Join text
        line_text = " ".join(t["text"] for t in line_tokens)
        
        # Tính bounding box của cả dòng
        min_left = min(t["left"] for t in line_tokens)
        max_right = max(t["left"] + t["width"] for t in line_tokens)
        min_top = min(t["top"] for t in line_tokens)
        max_bottom = max(t["top"] + t["height"] for t in line_tokens)
        
        # Confidence trung bình
        avg_confidence = sum(t["confidence"] for t in line_tokens) / len(line_tokens)
        
        blocks.append(
            OCRBlock(
                text=line_text,
                bbox=BoundingBox(min_left, min_top, max_right, max_bottom),
                confidence=avg_confidence,
                line_index=line_index,
            )
        )
    
    return blocks


def render_blocks_to_text(blocks: list[OCRBlock]) -> str:
    return "\n".join(block.text for block in blocks)


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
