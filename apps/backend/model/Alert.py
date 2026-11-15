from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class AlertRuleType(str, Enum):
    NEW_HOTSPOTS = "NEW_HOTSPOTS"
    ACTIVITY_SPIKE = "ACTIVITY_SPIKE"
    HIGH_HOTSPOT_CONCENTRATION = "HIGH_HOTSPOT_CONCENTRATION"
    HIGH_FRP = "HIGH_FRP"
    NEAR_COMMUNITY = "NEAR_COMMUNITY"
    NEAR_PROTECTED_AREA = "NEAR_PROTECTED_AREA"
    RISK_INDEX_INCREASE = "RISK_INDEX_INCREASE"


class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertRuleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"


class AlertStatus(str, Enum):
    NEW = "NEW"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class AlertRule(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=150)
    description: str = Field(default="", nullable=False)
    ruleType: AlertRuleType = Field(nullable=False, index=True)
    conditionsJson: str = Field(default="{}", nullable=False)
    severity: AlertSeverity = Field(default=AlertSeverity.MEDIUM, nullable=False)
    status: AlertRuleStatus = Field(default=AlertRuleStatus.ACTIVE, nullable=False, index=True)
    region: str | None = Field(default=None, nullable=True, index=True)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    lastExecutedAt: datetime | None = Field(default=None, nullable=True)


class Alert(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ruleId: int = Field(foreign_key="alertrule.id", nullable=False, index=True)
    fireClusterId: int | None = Field(
        default=None, foreign_key="firecluster.id", nullable=True, index=True
    )
    dedupKey: str = Field(nullable=False, unique=True, index=True, max_length=255)
    title: str = Field(nullable=False, max_length=200)
    message: str = Field(nullable=False)
    severity: AlertSeverity = Field(default=AlertSeverity.MEDIUM, nullable=False, index=True)
    status: AlertStatus = Field(default=AlertStatus.NEW, nullable=False, index=True)
    region: str | None = Field(default=None, nullable=True, index=True)
    metadataJson: str = Field(default="{}", nullable=False)

    # Trazabilidad y fiabilidad de la detección satelital
    acquisitionAt: datetime | None = Field(default=None, nullable=True)
    receivedAt: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    processedAt: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    dataAgeSeconds: float | None = Field(default=None, nullable=True)
    source: str = Field(default="NASA FIRMS", nullable=False, max_length=100)
    confidenceLevel: str | None = Field(default=None, nullable=True, max_length=50)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class AlertHistory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    alertId: int = Field(foreign_key="alert.id", nullable=False, index=True)
    previousStatus: AlertStatus | None = Field(default=None, nullable=True)
    newStatus: AlertStatus = Field(nullable=False)
    changedBy: str = Field(default="system", nullable=False, max_length=100)
    note: str | None = Field(default=None, nullable=True)
    changedAt: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class AlertEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    alertId: int = Field(foreign_key="alert.id", nullable=False, index=True)
    eventType: str = Field(nullable=False, max_length=50, index=True)
    dedupKey: str = Field(nullable=False, unique=True, index=True, max_length=255)
    payloadJson: str = Field(nullable=False)
    createdAt: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False, index=True
    )
