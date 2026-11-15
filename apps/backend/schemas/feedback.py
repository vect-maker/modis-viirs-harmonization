from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from model.HotspotFeedback import FeedbackClassification, FeedbackSeverity
from schemas.pagination import PaginatedResponse


class HotspotFeedbackUpsertRequest(BaseModel):
    classification: FeedbackClassification
    severity: FeedbackSeverity | None = None
    comment: str | None = Field(default=None, max_length=1000)


class HotspotFeedbackPublic(BaseModel):
    id: uuid.UUID
    hotspot_id: uuid.UUID
    user_id: uuid.UUID
    username: str
    user_role: str
    classification: FeedbackClassification
    severity: FeedbackSeverity | None
    comment: str | None
    created_at: datetime
    updated_at: datetime


class HotspotFeedbackSummary(BaseModel):
    hotspot_id: uuid.UUID
    total_reports: int
    counts: dict[FeedbackClassification, int]
    consensus: FeedbackClassification | None


class HotspotFeedbackListResponse(BaseModel):
    summary: HotspotFeedbackSummary
    items: PaginatedResponse[HotspotFeedbackPublic]
    my_feedback: HotspotFeedbackPublic | None = None


class HotspotFeedbackBatchSummaryRequest(BaseModel):
    hotspot_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class HotspotFeedbackBatchSummaryResponse(BaseModel):
    summaries: dict[uuid.UUID, HotspotFeedbackSummary]
