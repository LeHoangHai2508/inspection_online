from __future__ import annotations

import importlib.util
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.models import CaptureInput
from src.utils.config_loader import load_yaml_config

_DEFAULT_CAMERA_CONFIG = {
    "cam1": {"index": 0, "width": 1280, "height": 720},
    "cam2": {"index": 1, "width": 1280, "height": 720},
}


@dataclass(frozen=True)
class CameraFrame:
    camera_id: str
    content: bytes
    media_type: str = "image/png"
    width: int = 0
    height: int = 0


class BaseCameraAdapter(ABC):
    """Abstract camera adapter — swap implementation without changing callers."""

    @abstractmethod
    def capture(self, camera_id: str) -> CameraFrame:
        """Capture a single frame from the given camera."""

    def to_capture_input(self, camera_id: str) -> CaptureInput:
        frame = self.capture(camera_id)
        return CaptureInput(
            filename=f"{camera_id}_frame.png",
            content=frame.content,
            media_type=frame.media_type,
            camera_id=camera_id,
        )


class OpenCVCameraAdapter(BaseCameraAdapter):
    """Live camera capture via OpenCV.

    Requires ``opencv-python`` to be installed.
    Camera indices are read from configs/camera.yaml.
    """

    def __init__(self) -> None:
        if importlib.util.find_spec("cv2") is None:
            raise RuntimeError(
                "opencv-python is not installed. "
                "Run: pip install opencv-python"
            )
        self._config = load_yaml_config(
            "configs/camera.yaml",
            default=_DEFAULT_CAMERA_CONFIG,
        )

    def capture(self, camera_id: str) -> CameraFrame:
        import cv2  # type: ignore

        cam_cfg = self._config.get(camera_id, _DEFAULT_CAMERA_CONFIG.get(camera_id, {}))
        index = int(cam_cfg.get("index", 0))
        width = int(cam_cfg.get("width", 1280))
        height = int(cam_cfg.get("height", 720))

        cap = cv2.VideoCapture(index)
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            ok, frame = cap.read()
            if not ok or frame is None:
                raise RuntimeError(
                    f"Camera '{camera_id}' (index={index}) failed to capture a frame."
                )
            ok2, buf = cv2.imencode(".png", frame)
            if not ok2:
                raise RuntimeError(f"Failed to encode frame from camera '{camera_id}'.")
            return CameraFrame(
                camera_id=camera_id,
                content=buf.tobytes(),
                media_type="image/png",
                width=frame.shape[1],
                height=frame.shape[0],
            )
        finally:
            cap.release()


class MockCameraAdapter(BaseCameraAdapter):
    """Returns a minimal valid PNG for testing without real hardware."""

    # 1×1 white PNG (smallest valid PNG)
    _BLANK_PNG = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
        b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
        b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def capture(self, camera_id: str) -> CameraFrame:
        return CameraFrame(
            camera_id=camera_id,
            content=self._BLANK_PNG,
            media_type="image/png",
            width=1,
            height=1,
        )


def build_camera_adapter(strict: bool = False) -> BaseCameraAdapter:
    """Factory: use OpenCV if available, else fall back to mock (unless strict=True)."""
    if importlib.util.find_spec("cv2") is not None:
        try:
            return OpenCVCameraAdapter()
        except Exception:
            pass

    if strict:
        raise RuntimeError(
            "Camera adapter could not be initialised in strict mode. "
            "Install opencv-python and connect cameras."
        )
    return MockCameraAdapter()
