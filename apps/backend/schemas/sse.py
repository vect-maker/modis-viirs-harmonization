from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SSETargetScope(str, Enum):
    ALL = "all"
    USER = "user"
    TENANT = "tenant"


class NotificationSeverity(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class SSEEventEnvelope(BaseModel):
    """
    Envelope estándar para eventos SSE emitidos por cualquier endpoint del backend
    (y en el futuro por workers vía NATS).
    """

    event_id: str
    emitter_service: str = "firms-api"
    target_scope: SSETargetScope = SSETargetScope.ALL
    target_id: str | None = None
    event_type: str = "notification"
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    message: str = Field(min_length=1, max_length=1000)
    severity: NotificationSeverity = NotificationSeverity.INFO
    duration_ms: int | None = Field(default=5000, ge=0, le=60000)
    emitter_service: str = Field(default="firms-api", min_length=1, max_length=80)
    target_scope: SSETargetScope = SSETargetScope.ALL
    target_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationDispatchResponse(BaseModel):
    event_id: str
    delivered_clients: int
    envelope: SSEEventEnvelope
