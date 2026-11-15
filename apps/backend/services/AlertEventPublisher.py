from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from model.Alert import Alert, AlertEvent, AlertRule
from services.AlertEventSerializer import AlertEventSerializer, SSEEventType
from services.SSEManager import SSEManager, sse_manager

logger = logging.getLogger("firms.sse.publisher")


class AlertEventPublisher:
    """
    Publicador de eventos de alertas desacoplado del motor de detección.
    Persiste cada evento en PostgreSQL antes de difundirlo por SSE, garantizando
    idempotencia (sin duplicados) y recuperación vía Last-Event-ID.
    """

    def __init__(
        self,
        session: Session,
        manager: SSEManager = sse_manager,
    ) -> None:
        self.session = session
        self.manager = manager

    def publish_alert_event(
        self,
        *,
        alert: Alert,
        event_type: SSEEventType,
        dedup_key: str,
        rule: AlertRule | None = None,
    ) -> AlertEvent | None:
        if alert.id is None:
            raise ValueError("La alerta debe estar persistida antes de publicar un evento SSE")

        existing = self.session.exec(
            select(AlertEvent).where(col(AlertEvent.dedupKey) == dedup_key)
        ).first()
        if existing is not None:
            return None

        resolved_rule = rule or self.session.get(AlertRule, alert.ruleId)

        event_record = AlertEvent(
            alertId=alert.id,
            eventType=event_type,
            dedupKey=dedup_key,
            payloadJson="{}",
            createdAt=datetime.now(UTC),
        )
        try:
            self.session.add(event_record)
            self.session.flush()
            if event_record.id is None:
                raise ValueError("No se generó event_id al persistir AlertEvent")

            payload = AlertEventSerializer.build_alert_payload(
                event_id=event_record.id,
                alert=alert,
                event_type=event_type,
                rule=resolved_rule,
            )
            event_record.payloadJson = json.dumps(payload, ensure_ascii=False)
            self.session.add(event_record)
            self.session.commit()
            self.session.refresh(event_record)
        except IntegrityError:
            self.session.rollback()
            logger.debug("Evento SSE duplicado omitido (dedup_key=%s)", dedup_key)
            return None

        frame = AlertEventSerializer.format_sse_frame(
            event_id=event_record.id,  # type: ignore[arg-type]
            event_type=event_type,
            data=payload,
        )
        self.manager.broadcast(frame)
        return event_record

    def get_events_after(
        self,
        last_event_id: int,
        limit: int = 500,
    ) -> list[AlertEvent]:
        stmt = (
            select(AlertEvent)
            .where(col(AlertEvent.id) > last_event_id)
            .order_by(col(AlertEvent.id).asc())
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())
