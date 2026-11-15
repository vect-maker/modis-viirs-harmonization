from __future__ import annotations

import asyncio
import json

from main import SSE_BROADCAST_SUBJECT, SSETargetScope, WorkerService


class _FakeKV:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    async def put(self, key: str, value: bytes) -> None:
        self.data[key] = value


class _FakeNatsClient:
    def __init__(self) -> None:
        self.is_connected = True
        self.published: list[tuple[str, bytes]] = []

    async def publish(self, subject: str, payload: bytes) -> None:
        self.published.append((subject, payload))

    async def flush(self, timeout: float = 1.0) -> None:
        return None


def test_worker_run_once_updates_kv_and_publishes_envelope():
    async def _run() -> None:
        worker = WorkerService(nats_url="nats://fake:4222", poll_interval_seconds=60)
        fake_nc = _FakeNatsClient()
        fake_kv = _FakeKV()
        worker._nc = fake_nc  # type: ignore[assignment]
        worker._kv = fake_kv  # type: ignore[assignment]

        envelope = await worker.run_once()

        assert envelope.emitter_service == "firms-worker"
        assert envelope.target_scope == SSETargetScope.ALL
        assert envelope.event_type == "notification"
        assert "firms.last_run" in fake_kv.data
        state = json.loads(fake_kv.data["firms.last_run"].decode("utf-8"))
        assert state["status"] == "completed"

        assert len(fake_nc.published) == 1
        subject, raw_payload = fake_nc.published[0]
        assert subject == SSE_BROADCAST_SUBJECT
        decoded = json.loads(raw_payload.decode("utf-8"))
        assert decoded["event_id"] == envelope.event_id
        assert decoded["payload"]["title"] == "Worker heartbeat"

    asyncio.run(_run())
