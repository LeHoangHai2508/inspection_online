from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComparisonPolicy:
    """Thresholds for text matching and OCR trust."""

    low_confidence_threshold: float = 0.75
    default_fuzzy_threshold: float = 0.90


@dataclass(frozen=True)
class OrchestrationPolicy:
    """Business switches that control the side1 -> confirm -> side2 flow."""

    require_manual_confirm_between_sides: bool = True
    allow_side2_after_side1_ng: bool = True
