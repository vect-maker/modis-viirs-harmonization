from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from model.Alert import Alert, AlertRule, AlertStatus

SSEEventType = Literal[
    "hotspot_alert",
    "hotspot_updated",
    "hotspot_resolved",
    "hotspot_dismissed",
    "heartbeat",
]


def _iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    normalized = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    return normalized.isoformat()


class AlertEventSerializer:
    """
    Serializador desacoplado de eventos de dominio a payloads JSON y frames SSE.
    Nunca expone objetos ORM ni inventa campos ausentes.
    """

    @staticmethod
    def resolve_event_type_for_status(status: AlertStatus) -> SSEEventType:
        if status == AlertStatus.RESOLVED:
            return "hotspot_resolved"
        if status == AlertStatus.DISMISSED:
            return "hotspot_dismissed"
        return "hotspot_updated"

    @staticmethod
    def build_alert_payload(
        *,
        event_id: int,
        alert: Alert,
        event_type: SSEEventType,
        rule: AlertRule | None = None,
    ) -> dict[str, Any]:
        if alert.id is None:
            raise ValueError("No se puede serializar un evento para una alerta sin id")

        metadata: dict[str, Any] = {}
        if alert.metadataJson:
            try:
                parsed = json.loads(alert.metadataJson)
                if isinstance(parsed, dict):
                    metadata = parsed
            except json.JSONDecodeError:
                metadata = {}

        rule_code: str | None = (
            rule.ruleType.value if rule is not None else metadata.get("rule_code")
        )

        latitude = metadata.get("latitude", metadata.get("lat", metadata.get("cell_lat")))
        longitude = metadata.get("longitude", metadata.get("lon", metadata.get("cell_lon")))
        frp = metadata.get("frp", metadata.get("max_frp"))
        hotspot_id = metadata.get("hotspot_id")
        satellite = metadata.get("satellite")
        instrument = metadata.get("instrument")
        confidence = (
            alert.confidenceLevel
            if alert.confidenceLevel is not None
            else metadata.get("confidence")
        )

        candidate_fields: dict[str, Any] = {
            "event_id": event_id,
            "alert_id": alert.id,
            "rule_code": rule_code,
            "event_type": event_type,
            "title": alert.title,
            "description": alert.message,
            "severity": alert.severity.value,
            "hotspot_id": hotspot_id,
            "fire_cluster_id": alert.fireClusterId,
            "latitude": latitude,
            "longitude": longitude,
            "frp": frp,
            "confidence": confidence,
            "satellite": satellite,
            "instrument": instrument,
            "acquisition_datetime": _iso_utc(alert.acquisitionAt),
            "received_at": _iso_utc(alert.receivedAt),
            "processed_at": _iso_utc(alert.processedAt),
            "created_at": _iso_utc(alert.createdAt),
        }

        return {k: v for k, v in candidate_fields.items() if v is not None}

    @staticmethod
    def build_heartbeat_payload(
        *, event_id: str | int, timestamp: datetime | None = None
    ) -> dict[str, Any]:
        now = timestamp or datetime.now(UTC)
        return {
            "event_id": event_id,
            "event_type": "heartbeat",
            "timestamp": _iso_utc(now),
        }

    @staticmethod
    def format_sse_frame(
        *,
        event_id: str | int,
        event_type: SSEEventType | str,
        data: dict[str, Any],
        retry_ms: int | None = None,
    ) -> str:
        lines: list[str] = []
        if retry_ms is not None and retry_ms > 0:
            lines.append(f"retry: {retry_ms}")
        lines.append(f"id: {event_id}")
        lines.append(f"event: {event_type}")
        lines.append(f"data: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}")
        return "\n".join(lines) + "\n\n"
