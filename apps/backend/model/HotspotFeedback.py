from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class FeedbackClassification(StrEnum):
    CONFIRMED_WILDFIRE = "confirmed_wildfire"
    AGRICULTURAL_BURN = "agricultural_burn"
    INDUSTRIAL_OR_FLARE = "industrial_or_flare"
    FALSE_POSITIVE = "false_positive"
    UNCERTAIN = "uncertain"


class FeedbackSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HotspotFeedback(SQLModel, table=True):
    """User-submitted ground-truth feedback for a satellite hotspot."""

    __tablename__ = "hotspot_feedback"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint(
            "hotspot_id",
            "user_id",
            name="uq_hotspot_feedback_hotspot_user",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hotspot_id: uuid.UUID = Field(foreign_key="fact_hotspots.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    classification: FeedbackClassification = Field(max_length=40)
    severity: FeedbackSeverity | None = Field(default=None, max_length=20)
    comment: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
