from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from api.alerts import router as alerts_router
from database.session import get_session
from model.Alert import (
    Alert,
    AlertEvent,
    AlertHistory,
    AlertRule,
    AlertRuleStatus,
    AlertRuleType,
    AlertSeverity,
    AlertStatus,
)
from model.EnvironmentalRecord import EnvironmentalRecord
from model.FireCluster import FireCluster
from schemas.alerts import AlertStatusUpdate
from services.AlertDetectionService import AlertDetectionService
from services.AlertEventPublisher import AlertEventPublisher
from services.AlertEventSerializer import AlertEventSerializer
from services.AlertManagementService import AlertManagementService
from services.SSEConnectionService import SSEConnectionService, parse_last_event_id
from services.SSEManager import SSEManager, sse_manager


class _FakeRequest:
    def __init__(self, disconnected_after: int | None = None) -> None:
        self._checks = 0
        self._disconnected_after = disconnected_after

    async def is_disconnected(self) -> bool:
        self._checks += 1
        if self._disconnected_after is not None and self._checks > self._disconnected_after:
            return True
        return False


def _create_test_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[
            FireCluster.__table__,  # type: ignore[attr-defined]
            EnvironmentalRecord.__table__,  # type: ignore[attr-defined]
            AlertRule.__table__,  # type: ignore[attr-defined]
            Alert.__table__,  # type: ignore[attr-defined]
            AlertHistory.__table__,  # type: ignore[attr-defined]
            AlertEvent.__table__,  # type: ignore[attr-defined]
        ],
    )
    session = Session(engine)
    session.execute(
        text(
            """
            CREATE TABLE hotspots (
                id TEXT PRIMARY KEY,
                country TEXT,
                latitude REAL,
                longitude REAL,
                acq_datetime DATETIME,
                satellite TEXT,
                instrument TEXT,
                confidence TEXT,
                confidence_class TEXT,
                frp REAL,
                daynight TEXT
            )
            """
        )
    )
    session.commit()
    return session


def _seed_hotspots(session: Session, now: datetime) -> None:
    rows = [
        ("h1", "Nicaragua", 12.10, -86.20, now - timedelta(hours=1), "N20", "VIIRS", "92", "high", 95.0, "D"),
        ("h2", "Nicaragua", 12.11, -86.21, now - timedelta(hours=2), "N20", "VIIRS", "88", "high", 72.0, "D"),
        ("h3", "Nicaragua", 12.12, -86.22, now - timedelta(hours=3), "Aqua", "MODIS", "85", "nominal", 45.0, "N"),
        ("h4", "Nicaragua", 12.13, -86.23, now - timedelta(hours=4), "Aqua", "MODIS", "81", "nominal", 40.0, "D"),
        ("h5", "Nicaragua", 12.14, -86.24, now - timedelta(hours=5), "N20", "VIIRS", "90", "high", 55.0, "D"),
    ]
    for row in rows:
        session.execute(
            text(
                """
                INSERT INTO hotspots (
                    id, country, latitude, longitude, acq_datetime,
                    satellite, instrument, confidence, confidence_class, frp, daynight
                ) VALUES (
                    :id, :country, :lat, :lon, :dt,
                    :sat, :inst, :conf, :cclass, :frp, :dn
                )
                """
            ),
            {
                "id": row[0],
                "country": row[1],
                "lat": row[2],
                "lon": row[3],
                "dt": row[4].replace(tzinfo=None),
                "sat": row[5],
                "inst": row[6],
                "conf": row[7],
                "cclass": row[8],
                "frp": row[9],
                "dn": row[10],
            },
        )
    session.commit()


def _parse_sse_frames(raw_text: str) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    for block in raw_text.strip().split("\n\n"):
        if not block.strip():
            continue
        frame: dict[str, Any] = {}
        for line in block.splitlines():
            if line.startswith("retry: "):
                frame["retry"] = int(line[7:].strip())
            elif line.startswith("id: "):
                frame["id"] = line[4:].strip()
            elif line.startswith("event: "):
                frame["event"] = line[7:].strip()
            elif line.startswith("data: "):
                frame["data"] = json.loads(line[6:].strip())
        if frame:
            frames.append(frame)
    return frames


def test_sse_stream_connection_headers_and_replay_on_endpoint():
    session = _create_test_session()
    now = datetime.now(UTC)
    rule = AlertRule(
        name="FRP Alto",
        ruleType=AlertRuleType.HIGH_FRP,
        conditionsJson='{"min_frp": 50}',
        severity=AlertSeverity.HIGH,
        status=AlertRuleStatus.ACTIVE,
        region="Nicaragua",
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    assert rule.id is not None

    mgmt = AlertManagementService(session)
    alert = mgmt.create_alert_if_new(
        rule_id=rule.id,
        dedup_key=f"test:{uuid4().hex}",
        title="FRP elevado",
        message="Actividad térmica con FRP elevado",
        severity=AlertSeverity.HIGH,
        region="Nicaragua",
        fire_cluster_id=None,
        metadata={"latitude": 12.45, "longitude": -86.87, "frp": 88.5, "hotspot_id": 42},
        acquisition_at=now,
        received_at=now,
        processed_at=now,
        source="NASA FIRMS / VIIRS",
        confidence_level="92",
    )
    assert alert is not None

    app = FastAPI()
    app.include_router(alerts_router)
    app.dependency_overrides[get_session] = lambda: session

    with TestClient(app) as client:
        with client.stream("GET", "/alerts/stream?last_event_id=0&max_events=1") as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            assert resp.headers["cache-control"] == "no-cache"
            assert resp.headers["connection"] == "keep-alive"
            body = "".join(resp.iter_text())

    frames = _parse_sse_frames(body)
    assert frames[0]["retry"] == 3000
    assert frames[1]["event"] == "hotspot_alert"
    payload = frames[1]["data"]
    assert payload["alert_id"] == alert.id
    assert payload["rule_code"] == "HIGH_FRP"
    assert payload["event_type"] == "hotspot_alert"
    assert payload["severity"] == "HIGH"
    assert payload["latitude"] == 12.45
    assert payload["longitude"] == -86.87
    assert payload["frp"] == 88.5
    assert payload["hotspot_id"] == 42
    # No inventar campos ausentes (satellite, instrument, fire_cluster_id eran None)
    assert "fire_cluster_id" not in payload
    assert "satellite" not in payload
    assert "instrument" not in payload


def test_sse_receives_multiple_rules_and_lifecycle_events():
    session = _create_test_session()
    now = datetime.now(UTC)
    _seed_hotspots(session, now)

    rules = [
        AlertRule(
            name="Nuevos hotspots",
            ruleType=AlertRuleType.NEW_HOTSPOTS,
            conditionsJson='{"min_count": 2, "lookback_hours": 24}',
            severity=AlertSeverity.MEDIUM,
            region="Nicaragua",
        ),
        AlertRule(
            name="FRP alto",
            ruleType=AlertRuleType.HIGH_FRP,
            conditionsJson='{"min_frp": 70.0, "lookback_hours": 24}',
            severity=AlertSeverity.HIGH,
            region="Nicaragua",
        ),
        AlertRule(
            name="Concentración",
            ruleType=AlertRuleType.HIGH_HOTSPOT_CONCENTRATION,
            conditionsJson='{"min_hotspots_per_cell": 3, "cell_size_deg": 0.2, "lookback_hours": 24}',
            severity=AlertSeverity.HIGH,
            region="Nicaragua",
        ),
        AlertRule(
            name="Pico actividad",
            ruleType=AlertRuleType.ACTIVITY_SPIKE,
            conditionsJson='{"spike_ratio": 2.0, "min_recent_count": 3, "lookback_hours": 24}',
            severity=AlertSeverity.CRITICAL,
            region="Nicaragua",
        ),
    ]
    for r in rules:
        session.add(r)
    session.commit()

    async def _run():
        client = sse_manager.register()
        try:
            detector = AlertDetectionService(session)
            result = await detector.evaluate_rules(now=now)
            assert result["created_alerts"] == 4

            received: list[dict[str, Any]] = []
            while not client.queue.empty():
                received.extend(_parse_sse_frames(client.queue.get_nowait()))

            assert len(received) == 4
            assert {f["event"] for f in received} == {"hotspot_alert"}
            assert {f["data"]["rule_code"] for f in received} == {
                "NEW_HOTSPOTS",
                "HIGH_FRP",
                "HIGH_HOTSPOT_CONCENTRATION",
                "ACTIVITY_SPIKE",
            }

            # Transiciones de estado: REVIEWED -> RESOLVED y otro a DISMISSED
            mgmt = AlertManagementService(session)
            first_alert_id = received[0]["data"]["alert_id"]
            second_alert_id = received[1]["data"]["alert_id"]

            mgmt.update_status(
                first_alert_id,
                AlertStatusUpdate(status=AlertStatus.REVIEWED, changed_by="op1"),
            )
            mgmt.update_status(
                first_alert_id,
                AlertStatusUpdate(status=AlertStatus.RESOLVED, changed_by="op1"),
            )
            mgmt.update_status(
                second_alert_id,
                AlertStatusUpdate(status=AlertStatus.DISMISSED, changed_by="op2"),
            )

            lifecycle_frames: list[dict[str, Any]] = []
            while not client.queue.empty():
                lifecycle_frames.extend(_parse_sse_frames(client.queue.get_nowait()))

            assert [f["event"] for f in lifecycle_frames] == [
                "hotspot_updated",
                "hotspot_resolved",
                "hotspot_dismissed",
            ]
        finally:
            sse_manager.unregister(client.client_id)

    asyncio.run(_run())


def test_sse_broadcast_to_multiple_clients_and_disconnect_cleanup():
    async def _run():
        manager = SSEManager(default_queue_size=2)
        c1 = manager.register()
        c2 = manager.register()
        c_slow = manager.register(max_queue_size=1)
        assert manager.active_connections == 3

        frame1 = AlertEventSerializer.format_sse_frame(
            event_id=1, event_type="hotspot_alert", data={"alert_id": 1}
        )
        frame2 = AlertEventSerializer.format_sse_frame(
            event_id=2, event_type="hotspot_alert", data={"alert_id": 2}
        )
        delivered = manager.broadcast(frame1)
        assert delivered == 3
        # El cliente lento con maxsize=1 descarta el viejo sin bloquear a c1 ni c2
        delivered2 = manager.broadcast(frame2)
        assert delivered2 == 3

        assert c1.queue.qsize() == 2
        assert c2.queue.qsize() == 2
        assert c_slow.queue.qsize() == 1
        assert _parse_sse_frames(c_slow.queue.get_nowait())[0]["id"] == "2"

        manager.unregister(c1.client_id)
        manager.unregister(c_slow.client_id)
        assert manager.active_connections == 1
        manager.unregister(c2.client_id)
        assert manager.active_connections == 0

    asyncio.run(_run())


def test_sse_heartbeat_and_reconnection_last_event_id_recovery():
    session = _create_test_session()
    now = datetime.now(UTC)
    rule = AlertRule(
        name="Regla Test",
        ruleType=AlertRuleType.NEW_HOTSPOTS,
        severity=AlertSeverity.LOW,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    assert rule.id is not None

    manager = SSEManager()
    publisher = AlertEventPublisher(session=session, manager=manager)
    mgmt = AlertManagementService(session=session, publisher=publisher)

    a1 = mgmt.create_alert_if_new(
        rule_id=rule.id,
        dedup_key="k1",
        title="Alerta 1",
        message="Desc 1",
        severity=AlertSeverity.LOW,
        region=None,
        fire_cluster_id=None,
        metadata={},
        acquisition_at=now,
        received_at=now,
        processed_at=now,
        source="NASA FIRMS",
        confidence_level=None,
    )
    a2 = mgmt.create_alert_if_new(
        rule_id=rule.id,
        dedup_key="k2",
        title="Alerta 2",
        message="Desc 2",
        severity=AlertSeverity.MEDIUM,
        region=None,
        fire_cluster_id=None,
        metadata={},
        acquisition_at=now,
        received_at=now,
        processed_at=now,
        source="NASA FIRMS",
        confidence_level=None,
    )
    assert a1 is not None and a2 is not None

    async def _run():
        conn_svc = SSEConnectionService(manager=manager, heartbeat_seconds=0.05, retry_ms=2500)

        # 1. Heartbeat cuando no hay eventos nuevos
        hb_chunks: list[str] = []
        async for chunk in conn_svc.event_stream(
            request=_FakeRequest(), session=session, last_event_id=None, max_events=1
        ):
            hb_chunks.append(chunk)
        hb_frames = _parse_sse_frames("".join(hb_chunks))
        assert hb_frames[0]["retry"] == 2500
        assert hb_frames[1]["event"] == "heartbeat"
        assert hb_frames[1]["id"].startswith("hb-")

        # 2. Reconexión con Last-Event-ID=1 recupera evento 2 perdido
        assert parse_last_event_id("1") == 1
        assert parse_last_event_id("hb-1234") is None

        replay_chunks: list[str] = []
        async for chunk in conn_svc.event_stream(
            request=_FakeRequest(), session=session, last_event_id=1, max_events=1
        ):
            replay_chunks.append(chunk)
        replay_frames = _parse_sse_frames("".join(replay_chunks))
        assert len(replay_frames) == 2  # retry + evento 2
        assert replay_frames[1]["id"] == "2"
        assert replay_frames[1]["data"]["alert_id"] == a2.id
        assert manager.active_connections == 0

    asyncio.run(_run())


def test_sse_prevents_duplicate_events_on_reevaluation_and_noop_status():
    session = _create_test_session()
    now = datetime.now(UTC)
    rule = AlertRule(
        name="Dedup Test",
        ruleType=AlertRuleType.HIGH_FRP,
        severity=AlertSeverity.HIGH,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    assert rule.id is not None

    manager = SSEManager()
    client = manager.register()
    publisher = AlertEventPublisher(session=session, manager=manager)
    mgmt = AlertManagementService(session=session, publisher=publisher)

    a1 = mgmt.create_alert_if_new(
        rule_id=rule.id,
        dedup_key="same-dedup",
        title="Alerta única",
        message="Mensaje",
        severity=AlertSeverity.HIGH,
        region="Guatemala",
        fire_cluster_id=None,
        metadata={"frp": 110.0},
        acquisition_at=now,
        received_at=now,
        processed_at=now,
        source="NASA FIRMS",
        confidence_level="90",
    )
    # Re-evaluación con mismo dedup_key no crea ni emite otro evento
    a_dup = mgmt.create_alert_if_new(
        rule_id=rule.id,
        dedup_key="same-dedup",
        title="Alerta única",
        message="Mensaje",
        severity=AlertSeverity.HIGH,
        region="Guatemala",
        fire_cluster_id=None,
        metadata={"frp": 110.0},
        acquisition_at=now,
        received_at=now,
        processed_at=now,
        source="NASA FIRMS",
        confidence_level="90",
    )
    assert a1 is not None and a1.id is not None
    assert a_dup is None

    # Publicación manual duplicada con mismo dedup_key tampoco emite
    dup_event = publisher.publish_alert_event(
        alert=a1, event_type="hotspot_alert", dedup_key=f"alert:{a1.id}:created"
    )
    assert dup_event is None

    # Update status al mismo estado actual (NEW -> NEW) no emite evento duplicado
    mgmt.update_status(a1.id, AlertStatusUpdate(status=AlertStatus.NEW, changed_by="op"))

    assert client.queue.qsize() == 1
    manager.unregister(client.client_id)


def test_sse_security_and_error_handling(monkeypatch: pytest.MonkeyPatch):
    session = _create_test_session()
    app = FastAPI()
    app.include_router(alerts_router)
    app.dependency_overrides[get_session] = lambda: session

    monkeypatch.setenv("ALERT_STREAM_TOKEN", "super-secret-token")
    monkeypatch.setenv("ALERT_SSE_HEARTBEAT_SECONDS", "0.05")

    with TestClient(app) as client:
        # Sin token -> 401
        resp_missing = client.get("/alerts/stream")
        assert resp_missing.status_code == 401

        # Token incorrecto -> 403
        resp_bad = client.get("/alerts/stream", headers={"Authorization": "Bearer wrong"})
        assert resp_bad.status_code == 403

        # Token válido vía query param (EventSource) -> 200
        with client.stream(
            "GET", "/alerts/stream?token=super-secret-token&max_events=1"
        ) as resp_ok:
            assert resp_ok.status_code == 200
            body = "".join(resp_ok.iter_text())
            assert "super-secret-token" not in body
