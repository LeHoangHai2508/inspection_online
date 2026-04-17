from __future__ import annotations

from pathlib import Path

from src.utils.json_utils import write_json
from src.utils.paths import IOT_STORAGE


class MockIoTClient:
    def publish(self, event: dict) -> str:
        path = IOT_STORAGE / f"{event['scan_job_id']}.json"
        write_json(path, event)
        return str(path)
