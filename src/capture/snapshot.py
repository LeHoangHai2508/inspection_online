from __future__ import annotations

from dataclasses import dataclass

from src.capture.camera_adapter import BaseCameraAdapter, build_camera_adapter
from src.domain.enums import InspectionSide
from src.domain.models import CaptureInput


@dataclass(frozen=True)
class SideSnapshot:
    """Raw captures from both cameras for one inspection side."""

    side: InspectionSide
    cam1: CaptureInput
    cam2: CaptureInput

    def as_list(self) -> list[CaptureInput]:
        return [self.cam1, self.cam2]


class SnapshotService:
    """Captures both cameras for a given inspection side.

    Inject a custom ``BaseCameraAdapter`` for testing or alternative hardware.
    """

    def __init__(self, adapter: BaseCameraAdapter | None = None) -> None:
        self._adapter = adapter or build_camera_adapter()

    def capture_side(self, side: InspectionSide) -> SideSnapshot:
        cam1 = self._adapter.to_capture_input("cam1")
        cam2 = self._adapter.to_capture_input("cam2")
        return SideSnapshot(side=side, cam1=cam1, cam2=cam2)
