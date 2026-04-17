from __future__ import annotations

from src.iot.callback_client import MockIoTClient
from src.iot.event_builder import build_iot_event
from src.iot.retry_queue import RetryQueue


class IoTAckService:
    def __init__(
        self,
        client: MockIoTClient | None = None,
        retry_queue: RetryQueue | None = None,
    ) -> None:
        self._client = client or MockIoTClient()
        self._retry_queue = retry_queue or RetryQueue()

    def publish_result(self, result) -> str:
        event = build_iot_event(result)
        try:
            return self._client.publish(event)
        except Exception:
            self._retry_queue.push(event)
            raise
