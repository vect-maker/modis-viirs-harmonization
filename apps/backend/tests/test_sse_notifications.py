from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.alerts import router as alerts_router
from schemas.sse import NotificationSeverity, SSETargetScope
from services.SSEManager import SSEManager, sse_manager
from services.SSENotificationService import SSENotificationService, SSENotifierDep


def _parse_frame(raw: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for line in raw.strip().splitlines():
        if line.startswith("id: "):
            parsed["id"] = line[4:]
        elif line.startswith("event: "):
            parsed["event"] = line[7:]
        elif line.startswith("data: "):
            parsed["data"] = json.loads(line[6:])
    return parsed


def test_sse_notification_service_emits_arbitrary_envelope():
    manager = SSEManager()
    client = manager.register()
    service = SSENotificationService(manager=manager)

    envelope, delivered = service.emit_envelope(
        event_type="worker.sync",
        emitter_service="firms-realtime-worker",
        target_scope=SSETargetScope.TENANT,
        target_id="nicaragua",
        payload={"custom_count": 42, "nested": {"ok": True}},
    )

    assert delivered == 1
    assert envelope.emitter_service == "firms-realtime-worker"
    assert envelope.target_scope == SSETargetScope.TENANT
    assert envelope.target_id == "nicaragua"
    assert envelope.event_type == "worker.sync"
    assert envelope.payload == {"custom_count": 42, "nested": {"ok": True}}

    frame = _parse_frame(client.queue.get_nowait())
    assert frame["id"] == envelope.event_id
    assert frame["event"] == "worker.sync"
    assert frame["data"]["emitter_service"] == "firms-realtime-worker"
    assert frame["data"]["target_scope"] == "tenant"
    assert frame["data"]["payload"]["custom_count"] == 42

    manager.unregister(client.client_id)


def test_post_alerts_notify_and_endpoint_injection_broadcasts_sse():
    app = FastAPI()
    app.include_router(alerts_router)

    @app.post("/demo/trigger")
    def demo_trigger(notifier: SSENotifierDep):
        env, delivered = notifier.send_notification(
            title="Sincronización completada",
            message="Se procesaron 12 focos de calor.",
            severity=NotificationSeverity.SUCCESS,
            duration_ms=4000,
            emitter_service="demo-endpoint",
            metadata={"count": 12},
        )
        return {"event_id": env.event_id, "delivered": delivered}

    client = sse_manager.register()
    try:
        with TestClient(app) as http:
            resp = http.post(
                "/alerts/notify",
                json={
                    "title": "Alerta de prueba",
                    "message": "Conexión SSE operativa",
                    "severity": "warning",
                    "duration_ms": 6000,
                    "metadata": {"source": "unit-test"},
                },
            )
            assert resp.status_code == 202
            body = resp.json()
            assert body["delivered_clients"] >= 1
            assert body["envelope"]["event_type"] == "notification"
            assert body["envelope"]["payload"]["severity"] == "warning"

            demo_resp = http.post("/demo/trigger")
            assert demo_resp.status_code == 200
            assert demo_resp.json()["delivered"] >= 1

        frames = []
        while not client.queue.empty():
            frames.append(_parse_frame(client.queue.get_nowait()))

        assert len(frames) == 2
        assert frames[0]["event"] == "notification"
        assert frames[0]["data"]["payload"]["title"] == "Alerta de prueba"
        assert frames[0]["data"]["payload"]["metadata"] == {"source": "unit-test"}

        assert frames[1]["event"] == "notification"
        assert frames[1]["data"]["emitter_service"] == "demo-endpoint"
        assert frames[1]["data"]["payload"]["severity"] == "success"
        assert frames[1]["data"]["payload"]["duration_ms"] == 4000
    finally:
        sse_manager.unregister(client.client_id)
