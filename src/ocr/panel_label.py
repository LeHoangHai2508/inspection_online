from __future__ import annotations

import re
from typing import Literal

from src.domain.models import OCRBlock

PanelLabel = Literal["RECTO", "VERSO", "UNKNOWN"]


def detect_panel_label_from_text(text: str) -> PanelLabel:
    """Detect RECTO/VERSO từ raw text"""
    cleaned = re.sub(r"\s+", " ", text or "").strip().upper()

    if re.search(r"\bRECT[O0]\b", cleaned):
        return "RECTO"
    if re.search(r"\bVERS[O0]\b", cleaned):
        return "VERSO"
    return "UNKNOWN"


def detect_panel_label_from_blocks(blocks: list[OCRBlock]) -> PanelLabel:
    """
    Detect RECTO/VERSO từ OCR blocks.
    Chỉ nhìn blocks gần mép trên/dưới vì RECTO/VERSO thường nằm ở đó.
    """
    if not blocks:
        return "UNKNOWN"

    # Chỉ nhìn block gần mép trên / dưới vì RECTO/VERSO thường nằm ở đó
    min_y = min(block.bbox.y1 for block in blocks)
    max_y = max(block.bbox.y2 for block in blocks)
    total_height = max(1, max_y - min_y)

    candidate_texts: list[str] = []
    for block in blocks:
        top_ratio = (block.bbox.y1 - min_y) / total_height
        bottom_ratio = (max_y - block.bbox.y2) / total_height

        if top_ratio <= 0.18 or bottom_ratio <= 0.20:
            candidate_texts.append(block.text)

    return detect_panel_label_from_text(" ".join(candidate_texts))
