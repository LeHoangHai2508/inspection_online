from __future__ import annotations

from src.domain.models import ObservedField, CaptureInput, BoundingBox
from src.symbol.detect_symbols import detect_symbol_regions
from src.symbol.classify_symbols import classify_symbol


class SymbolWorkflow:
    def run_capture_symbol(self, capture: CaptureInput) -> list[ObservedField]:
        regions = detect_symbol_regions(capture)
        labels: list[str] = []
        confidences: list[float] = []

        x1s, y1s, x2s, y2s = [], [], [], []

        for region in regions:
            label, score = classify_symbol(region.image)
            if label == "unknown" or score < 0.65:
                continue

            labels.append(label)
            confidences.append(score)

            x1s.append(region.bbox.x1)
            y1s.append(region.bbox.y1)
            x2s.append(region.bbox.x2)
            y2s.append(region.bbox.y2)

        if not labels:
            return []

        merged_bbox = BoundingBox(
            min(x1s), min(y1s), max(x2s), max(y2s)
        )

        value = "|".join(labels)
        avg_conf = sum(confidences) / len(confidences)

        return [
            ObservedField(
                field_name="care_symbols",
                value=value,
                confidence=avg_conf,
                bbox=merged_bbox,
                camera_source=capture.camera_id,
            )
        ]
