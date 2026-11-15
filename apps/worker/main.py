from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

import nats
from dotenv import load_dotenv
from nats.aio.client import Client as NatsClient
from nats.js.api import KeyValueConfig
from nats.js.errors import BucketNotFoundError
from nats.js.kv import KeyValue
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("firms.worker")

SSE_BROADCAST_SUBJECT = "firms.sse.broadcast"
WORKER_STATE_BUCKET = "worker_state"


class SSETargetScope(StrEnum):
    ALL = "all"
    USER = "user"
    TENANT = "tenant"


class SSEEventEnvelope(BaseModel):
    event_id: str
    emitter_service: str = "firms-worker"
    target_scope: SSETargetScope = SSETargetScope.ALL
    target_id: str | None = None
    event_type: str = "notification"
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkerService:
    """
    Background worker that connects to NATS + JetStream KV, wakes up on a schedule,
    and publishes SSEEventEnvelope notifications to connected API replicas.
    """

    def __init__(
        self,
        *,
        nats_url: str | None = None,
        poll_interval_seconds: float | None = None,
    ) -> None:
        self.nats_url = (nats_url or os.getenv("NATS_URL", "nats://localhost:4222")).strip()
        self.poll_interval_seconds = (
            poll_interval_seconds
            if poll_interval_seconds is not None
            else float(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "300"))
        )
        self._nc: NatsClient | None = None
        self._kv: KeyValue | None = None
        self._stop_event = asyncio.Event()

    async def connect(self) -> None:
        if self._nc is not None and self._nc.is_connected:
            return
        self._nc = await nats.connect(servers=[self.nats_url], name="firms-worker")
        js = self._nc.jetstream()
        try:
            self._kv = await js.key_value(WORKER_STATE_BUCKET)
        except BucketNotFoundError:
            self._kv = await js.create_key_value(
                config=KeyValueConfig(bucket=WORKER_STATE_BUCKET)
            )
        logger.info("Worker connected to NATS at %s", self.nats_url)

    async def close(self) -> None:
        if self._nc is not None:
            try:
                await self._nc.drain()
            except Exception:
                try:
                    await self._nc.close()
                except Exception:
                    pass
            self._nc = None
        self._kv = None

    async def publish_notification(
        self,
        *,
        title: str,
        message: str,
        severity: str = "info",
        duration_ms: int = 5000,
        metadata: dict[str, Any] | None = None,
    ) -> SSEEventEnvelope:
        envelope = SSEEventEnvelope(
            event_id=f"worker-{uuid4().hex[:12]}",
            emitter_service="firms-worker",
            target_scope=SSETargetScope.ALL,
            event_type="notification",
            payload={
                "title": title,
                "message": message,
                "severity": severity,
                "duration_ms": duration_ms,
                **({"metadata": metadata} if metadata else {}),
            },
        )
        if self._nc is not None and self._nc.is_connected:
            await self._nc.publish(
                SSE_BROADCAST_SUBJECT,
                envelope.model_dump_json().encode("utf-8"),
            )
            await self._nc.flush(timeout=1)
        return envelope

    async def record_sync_state(
        self, status: str, details: dict[str, Any] | None = None
    ) -> None:
        if self._kv is None:
            return
        state = {
            "status": status,
            "updated_at": datetime.now(UTC).isoformat(),
            **(details or {}),
        }
        await self._kv.put("firms.last_run", json.dumps(state).encode("utf-8"))

    async def run_once(self) -> SSEEventEnvelope:
        """
        Single wake-up cycle. Future FIRMS realtime API polling and DB persistence
        plug in here before publishing the summary notification.
        """
        logger.info("Worker wake-up cycle starting")
        await self.record_sync_state("completed")
        envelope = await self.publish_notification(
            title="Worker heartbeat",
            message="Background worker cycle completed.",
            severity="info",
        )
        logger.info("Worker cycle finished (event_id=%s)", envelope.event_id)
        return envelope

    def request_stop(self) -> None:
        self._stop_event.set()

    async def run_forever(self) -> None:
        await self.connect()
        try:
            while not self._stop_event.is_set():
                try:
                    await self.run_once()
                except Exception as exc:
                    logger.exception("Worker cycle failed: %s", exc)

                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.poll_interval_seconds,
                    )
                except TimeoutError:
                    continue
        finally:
            await self.close()


async def main() -> None:
    worker = WorkerService()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.request_stop)
        except NotImplementedError:
            pass
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
