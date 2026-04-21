from __future__ import annotations

from pathlib import Path
from typing import Tuple

import cv2
import numpy as np


TEMPLATE_ROOT = Path("assets/symbol_templates")


def _normalize_symbol_image(img: np.ndarray) -> np.ndarray:
    img = cv2.resize(img, (64, 64), interpolation=cv2.INTER_AREA)
    _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return img


def classify_symbol(img: np.ndarray) -> Tuple[str, float]:
    if not TEMPLATE_ROOT.exists():
        return "unknown", 0.0

    query = _normalize_symbol_image(img)

    best_label = "unknown"
    best_score = -1.0

    for class_dir in TEMPLATE_ROOT.iterdir():
        if not class_dir.is_dir():
            continue

        for p in class_dir.glob("*.*"):
            ref = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if ref is None:
                continue
            ref = _normalize_symbol_image(ref)

            score = cv2.matchTemplate(
                query,
                ref,
                cv2.TM_CCOEFF_NORMED,
            )[0][0]

            if score > best_score:
                best_score = float(score)
                best_label = class_dir.name

    return best_label, best_score
