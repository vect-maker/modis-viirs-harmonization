from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends

from schemas.sse import (
    NotificationSeverity,
    SSEEventEnvelope,
    SSETargetScope,
)
from services.AlertEventSerializer import AlertEventSerializer
from services.NatsService import NatsService, nats_service
from services.SSEManager import SSEManager, sse_manager


class SSENotificationService:
    """
    Publicador ligero para enviar notificaciones y envelopes SSE desde cualquier
    endpoint FastAPI hacia los clientes conectados. Cuando NATS está conectado,
    enruta por NATS + JetStream KV; de lo contrario, difunde localmente.
    """

    def __init__(
        self,
        manager: SSEManager = sse_manager,
        nats: NatsService = nats_service,
    ) -> None:
        self.manager = manager
        self.nats = nats

    def emit_envelope(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        emitter_service: str = "firms-api",
        target_scope: SSETargetScope = SSETargetScope.ALL,
        target_id: str | None = None,
        event_id: str | None = None,
    ) -> tuple[SSEEventEnvelope, int]:
        resolved_id = event_id or f"notif-{uuid4().hex[:12]}"
        envelope = SSEEventEnvelope(
            event_id=resolved_id,
            emitter_service=emitter_service,
            target_scope=target_scope,
            target_id=target_id,
            event_type=event_type,
            payload=payload,
            timestamp=datetime.now(UTC),
        )
        if self.nats.publish_envelope_sync(envelope):
            return envelope, self.manager.active_connections

        frame = AlertEventSerializer.format_sse_frame(
            event_id=envelope.event_id,
            event_type=envelope.event_type,
            data=envelope.model_dump(mode="json"),
        )
        delivered = self.manager.deliver_envelope(envelope, frame)
        return envelope, delivered

    def send_notification(
        self,
        *,
        title: str,
        message: str,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        duration_ms: int | None = 5000,
        emitter_service: str = "firms-api",
        target_scope: SSETargetScope = SSETargetScope.ALL,
        target_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[SSEEventEnvelope, int]:
        payload: dict[str, Any] = {
            "title": title,
            "message": message,
            "severity": severity.value,
            "duration_ms": duration_ms,
        }
        if metadata:
            payload["metadata"] = metadata

        return self.emit_envelope(
            event_type="notification",
            payload=payload,
            emitter_service=emitter_service,
            target_scope=target_scope,
            target_id=target_id,
        )


sse_notifier = SSENotificationService()


def get_sse_notifier() -> SSENotificationService:
    return sse_notifier


SSENotifierDep = Annotated[SSENotificationService, Depends(get_sse_notifier)]
