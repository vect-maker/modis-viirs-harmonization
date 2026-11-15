from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from model.Alert import (
    AlertRuleStatus,
    AlertRuleType,
    AlertSeverity,
    AlertStatus,
)


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str = ""
    ruleType: AlertRuleType
    conditions: dict[str, Any] = Field(default_factory=dict)
    severity: AlertSeverity = AlertSeverity.MEDIUM
    status: AlertRuleStatus = AlertRuleStatus.ACTIVE
    region: str | None = None


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    conditions: dict[str, Any] | None = None
    severity: AlertSeverity | None = None
    status: AlertRuleStatus | None = None
    region: str | None = None


class AlertRuleRead(BaseModel):
    id: int
    name: str
    description: str
    ruleType: AlertRuleType
    conditions: dict[str, Any]
    severity: AlertSeverity
    status: AlertRuleStatus
    region: str | None
    createdAt: datetime
    lastExecutedAt: datetime | None


class AlertStatusUpdate(BaseModel):
    status: AlertStatus
    changed_by: str = Field(default="operator", min_length=1, max_length=100)
    note: str | None = None


class AlertRead(BaseModel):
    id: int
    ruleId: int
    fireClusterId: int | None
    dedupKey: str
    title: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    region: str | None
    metadata: dict[str, Any]
    acquisitionAt: datetime | None
    receivedAt: datetime
    processedAt: datetime
    dataAgeSeconds: float | None
    source: str
    confidenceLevel: str | None
    createdAt: datetime
    updatedAt: datetime


class AlertHistoryRead(BaseModel):
    id: int
    alertId: int
    previousStatus: AlertStatus | None
    newStatus: AlertStatus
    changedBy: str
    note: str | None
    changedAt: datetime


class AlertEvaluateRequest(BaseModel):
    rule_ids: list[int] | None = None
    run_in_background: bool = True


class AlertEvaluateResponse(BaseModel):
    status: str
    evaluated_rules: int = 0
    created_alerts: int = 0
    skipped_duplicates: int = 0
    errors: list[str] = Field(default_factory=list)
