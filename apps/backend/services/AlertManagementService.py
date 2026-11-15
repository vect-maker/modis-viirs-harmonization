from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, col, select

from model.Alert import Alert, AlertHistory, AlertSeverity, AlertStatus
from schemas.alerts import AlertHistoryRead, AlertRead, AlertStatusUpdate
from services.AlertEventPublisher import AlertEventPublisher
from services.AlertEventSerializer import AlertEventSerializer


class AlertManagementService:
    """Servicio para ciclo de vida de alertas, prevención de duplicados e historial."""

    def __init__(
        self,
        session: Session,
        publisher: AlertEventPublisher | None = None,
    ):
        self.session = session
        self.publisher = publisher or AlertEventPublisher(session)

    @staticmethod
    def to_read(alert: Alert) -> AlertRead:
        if alert.id is None:
            raise ValueError("Alert sin id persistido")
        return AlertRead(
            id=alert.id,
            ruleId=alert.ruleId,
            fireClusterId=alert.fireClusterId,
            dedupKey=alert.dedupKey,
            title=alert.title,
            message=alert.message,
            severity=alert.severity,
            status=alert.status,
            region=alert.region,
            metadata=json.loads(alert.metadataJson or "{}"),
            acquisitionAt=alert.acquisitionAt,
            receivedAt=alert.receivedAt,
            processedAt=alert.processedAt,
            dataAgeSeconds=alert.dataAgeSeconds,
            source=alert.source,
            confidenceLevel=alert.confidenceLevel,
            createdAt=alert.createdAt,
            updatedAt=alert.updatedAt,
        )

    @staticmethod
    def history_to_read(entry: AlertHistory) -> AlertHistoryRead:
        if entry.id is None:
            raise ValueError("AlertHistory sin id persistido")
        return AlertHistoryRead(
            id=entry.id,
            alertId=entry.alertId,
            previousStatus=entry.previousStatus,
            newStatus=entry.newStatus,
            changedBy=entry.changedBy,
            note=entry.note,
            changedAt=entry.changedAt,
        )

    def create_alert_if_new(
        self,
        *,
        rule_id: int,
        dedup_key: str,
        title: str,
        message: str,
        severity: AlertSeverity,
        region: str | None,
        fire_cluster_id: int | None,
        metadata: dict[str, Any],
        acquisition_at: datetime | None,
        received_at: datetime,
        processed_at: datetime,
        source: str,
        confidence_level: str | None,
    ) -> Alert | None:
        existing = self.session.exec(
            select(Alert).where(col(Alert.dedupKey) == dedup_key)
        ).first()
        if existing is not None:
            return None

        age_seconds: float | None = None
        if acquisition_at is not None:
            acq_utc = (
                acquisition_at.replace(tzinfo=UTC)
                if acquisition_at.tzinfo is None
                else acquisition_at
            )
            age_seconds = round(max(0.0, (processed_at - acq_utc).total_seconds()), 2)

        alert = Alert(
            ruleId=rule_id,
            fireClusterId=fire_cluster_id,
            dedupKey=dedup_key,
            title=title,
            message=message,
            severity=severity,
            status=AlertStatus.NEW,
            region=region,
            metadataJson=json.dumps(metadata, default=str),
            acquisitionAt=acquisition_at,
            receivedAt=received_at,
            processedAt=processed_at,
            dataAgeSeconds=age_seconds,
            source=source,
            confidenceLevel=confidence_level,
            createdAt=processed_at,
            updatedAt=processed_at,
        )
        self.session.add(alert)
        self.session.commit()
        self.session.refresh(alert)

        if alert.id is not None:
            history = AlertHistory(
                alertId=alert.id,
                previousStatus=None,
                newStatus=AlertStatus.NEW,
                changedBy="system",
                note="Alerta generada por el motor de detección temprana",
                changedAt=processed_at,
            )
            self.session.add(history)
            self.session.commit()

            self.publisher.publish_alert_event(
                alert=alert,
                event_type="hotspot_alert",
                dedup_key=f"alert:{alert.id}:created",
            )

        return alert

    def list_alerts(
        self,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        rule_id: int | None = None,
        cluster_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AlertRead]:
        stmt = select(Alert)
        if status is not None:
            stmt = stmt.where(col(Alert.status) == status)
        if severity is not None:
            stmt = stmt.where(col(Alert.severity) == severity)
        if rule_id is not None:
            stmt = stmt.where(col(Alert.ruleId) == rule_id)
        if cluster_id is not None:
            stmt = stmt.where(col(Alert.fireClusterId) == cluster_id)
        stmt = stmt.order_by(col(Alert.createdAt).desc()).offset(offset).limit(limit)
        alerts = list(self.session.exec(stmt).all())
        return [self.to_read(a) for a in alerts]

    def get_alert(self, alert_id: int) -> AlertRead:
        alert = self.session.get(Alert, alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")
        return self.to_read(alert)

    def update_status(self, alert_id: int, payload: AlertStatusUpdate) -> AlertRead:
        alert = self.session.get(Alert, alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        previous = alert.status
        if previous == payload.status:
            return self.to_read(alert)

        now = datetime.now(UTC)
        alert.status = payload.status
        alert.updatedAt = now
        self.session.add(alert)

        history = AlertHistory(
            alertId=alert_id,
            previousStatus=previous,
            newStatus=payload.status,
            changedBy=payload.changed_by.strip(),
            note=payload.note,
            changedAt=now,
        )
        self.session.add(history)
        self.session.commit()
        self.session.refresh(alert)
        self.session.refresh(history)

        event_type = AlertEventSerializer.resolve_event_type_for_status(payload.status)
        self.publisher.publish_alert_event(
            alert=alert,
            event_type=event_type,
            dedup_key=f"alert:{alert.id}:history:{history.id}",
        )
        return self.to_read(alert)

    def list_history(
        self,
        alert_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AlertHistoryRead]:
        stmt = select(AlertHistory)
        if alert_id is not None:
            stmt = stmt.where(col(AlertHistory.alertId) == alert_id)
        stmt = stmt.order_by(col(AlertHistory.changedAt).desc()).offset(offset).limit(limit)
        rows = list(self.session.exec(stmt).all())
        return [self.history_to_read(r) for r in rows]
