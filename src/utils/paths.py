from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORAGE_ROOT = PROJECT_ROOT / "storage"
TEMPLATE_STORAGE = STORAGE_ROOT / "templates"
CAPTURE_STORAGE = STORAGE_ROOT / "captures"
ANNOTATION_STORAGE = STORAGE_ROOT / "annotations"
IOT_STORAGE = STORAGE_ROOT / "iot_events"


def ensure_storage_tree() -> None:
    for folder in (
        STORAGE_ROOT,
        TEMPLATE_STORAGE,
        CAPTURE_STORAGE,
        ANNOTATION_STORAGE,
        IOT_STORAGE,
    ):
        folder.mkdir(parents=True, exist_ok=True)


def make_side_folder(base_folder: Path, identifier: str, side_name: str) -> Path:
    folder = base_folder / identifier / side_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder
