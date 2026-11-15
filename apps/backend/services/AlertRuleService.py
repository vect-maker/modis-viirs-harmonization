from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import Session, col, select

from model.Alert import AlertRule, AlertRuleStatus
from schemas.alerts import AlertRuleCreate, AlertRuleRead, AlertRuleUpdate


class AlertRuleService:
    """Servicio para administrar reglas configurables de detección temprana."""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def to_read(rule: AlertRule) -> AlertRuleRead:
        if rule.id is None:
            raise ValueError("AlertRule sin id persistido")
        return AlertRuleRead(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            ruleType=rule.ruleType,
            conditions=json.loads(rule.conditionsJson or "{}"),
            severity=rule.severity,
            status=rule.status,
            region=rule.region,
            createdAt=rule.createdAt,
            lastExecutedAt=rule.lastExecutedAt,
        )

    def create_rule(self, payload: AlertRuleCreate) -> AlertRuleRead:
        rule = AlertRule(
            name=payload.name.strip(),
            description=payload.description.strip(),
            ruleType=payload.ruleType,
            conditionsJson=json.dumps(payload.conditions),
            severity=payload.severity,
            status=payload.status,
            region=payload.region.strip() if payload.region else None,
            createdAt=datetime.now(UTC),
        )
        self.session.add(rule)
        self.session.commit()
        self.session.refresh(rule)
        return self.to_read(rule)

    def list_rules(
        self,
        status: AlertRuleStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AlertRuleRead]:
        stmt = select(AlertRule)
        if status is not None:
            stmt = stmt.where(col(AlertRule.status) == status)
        stmt = stmt.order_by(col(AlertRule.createdAt).desc()).offset(offset).limit(limit)
        rules = list(self.session.exec(stmt).all())
        return [self.to_read(r) for r in rules]

    def get_active_rules(self, rule_ids: list[int] | None = None) -> list[AlertRule]:
        stmt = select(AlertRule).where(col(AlertRule.status) == AlertRuleStatus.ACTIVE)
        if rule_ids:
            stmt = stmt.where(col(AlertRule.id).in_(rule_ids))
        return list(self.session.exec(stmt).all())

    def update_rule(self, rule_id: int, payload: AlertRuleUpdate) -> AlertRuleRead:
        rule = self.session.get(AlertRule, rule_id)
        if rule is None:
            raise HTTPException(status_code=404, detail="Regla de alerta no encontrada")

        if payload.name is not None:
            rule.name = payload.name.strip()
        if payload.description is not None:
            rule.description = payload.description.strip()
        if payload.conditions is not None:
            rule.conditionsJson = json.dumps(payload.conditions)
        if payload.severity is not None:
            rule.severity = payload.severity
        if payload.status is not None:
            rule.status = payload.status
        if payload.region is not None:
            rule.region = payload.region.strip() or None

        self.session.add(rule)
        self.session.commit()
        self.session.refresh(rule)
        return self.to_read(rule)

    def mark_executed(self, rule: AlertRule, executed_at: datetime) -> None:
        rule.lastExecutedAt = executed_at
        self.session.add(rule)
        self.session.commit()
