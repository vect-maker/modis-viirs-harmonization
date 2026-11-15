from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlmodel import Session, col, func, select

from model.HotspotFeedback import FeedbackClassification, HotspotFeedback
from model.StarSchema import FactHotspot
from model.User import User
from schemas.feedback import (
    HotspotFeedbackListResponse,
    HotspotFeedbackPublic,
    HotspotFeedbackSummary,
    HotspotFeedbackUpsertRequest,
)
from schemas.pagination import PaginatedResponse, PaginationParams


def _empty_counts() -> dict[FeedbackClassification, int]:
    return {item: 0 for item in FeedbackClassification}


def _compute_consensus(
    counts: dict[FeedbackClassification, int],
) -> FeedbackClassification | None:
    max_votes = max(counts.values(), default=0)
    if max_votes == 0:
        return None
    leaders = [key for key, value in counts.items() if value == max_votes]
    return leaders[0] if len(leaders) == 1 else None


def _to_public(feedback: HotspotFeedback, user: User) -> HotspotFeedbackPublic:
    if feedback.id is None:
        raise RuntimeError("Persisted HotspotFeedback missing id")
    return HotspotFeedbackPublic(
        id=feedback.id,
        hotspot_id=feedback.hotspot_id,
        user_id=user.id,
        username=user.username,
        user_role=user.role,
        classification=feedback.classification,
        severity=feedback.severity,
        comment=feedback.comment,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


class FeedbackRepository:
    """Persistence and aggregation queries for hotspot ground-truth feedback."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _require_hotspot(self, hotspot_id: uuid.UUID) -> FactHotspot:
        hotspot = self.session.get(FactHotspot, hotspot_id)
        if hotspot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hotspot no encontrado",
            )
        return hotspot

    def upsert_feedback(
        self,
        *,
        hotspot_id: uuid.UUID,
        user: User,
        payload: HotspotFeedbackUpsertRequest,
    ) -> HotspotFeedbackPublic:
        self._require_hotspot(hotspot_id)
        cleaned_comment = payload.comment.strip() if payload.comment else None
        if cleaned_comment == "":
            cleaned_comment = None

        now = datetime.now(UTC)
        existing = self.session.exec(
            select(HotspotFeedback).where(
                HotspotFeedback.hotspot_id == hotspot_id,
                HotspotFeedback.user_id == user.id,
            )
        ).first()

        if existing is not None:
            existing.classification = payload.classification
            existing.severity = payload.severity
            existing.comment = cleaned_comment
            existing.updated_at = now
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return _to_public(existing, user)

        feedback = HotspotFeedback(
            hotspot_id=hotspot_id,
            user_id=user.id,
            classification=payload.classification,
            severity=payload.severity,
            comment=cleaned_comment,
            created_at=now,
            updated_at=now,
        )
        self.session.add(feedback)
        self.session.commit()
        self.session.refresh(feedback)
        return _to_public(feedback, user)

    def delete_user_feedback(
        self,
        *,
        hotspot_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        self._require_hotspot(hotspot_id)
        existing = self.session.exec(
            select(HotspotFeedback).where(
                HotspotFeedback.hotspot_id == hotspot_id,
                HotspotFeedback.user_id == user_id,
            )
        ).first()
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe retroalimentación del usuario para este hotspot",
            )
        self.session.delete(existing)
        self.session.commit()

    def get_batch_summaries(
        self, hotspot_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, HotspotFeedbackSummary]:
        unique_ids = list(dict.fromkeys(hotspot_ids))
        counts_by_hotspot: dict[uuid.UUID, dict[FeedbackClassification, int]] = {
            hid: _empty_counts() for hid in unique_ids
        }
        if not unique_ids:
            return {}

        rows = self.session.exec(
            select(
                HotspotFeedback.hotspot_id,
                HotspotFeedback.classification,
                func.count(col(HotspotFeedback.id)),
            )
            .where(col(HotspotFeedback.hotspot_id).in_(unique_ids))
            .group_by(
                col(HotspotFeedback.hotspot_id),
                col(HotspotFeedback.classification),
            )
        ).all()

        for hid, classification, count in rows:
            cls_enum = FeedbackClassification(classification)
            counts_by_hotspot[hid][cls_enum] = int(count)

        summaries: dict[uuid.UUID, HotspotFeedbackSummary] = {}
        for hid in unique_ids:
            counts = counts_by_hotspot[hid]
            summaries[hid] = HotspotFeedbackSummary(
                hotspot_id=hid,
                total_reports=sum(counts.values()),
                counts=counts,
                consensus=_compute_consensus(counts),
            )
        return summaries

    def get_summary(self, hotspot_id: uuid.UUID) -> HotspotFeedbackSummary:
        return self.get_batch_summaries([hotspot_id])[hotspot_id]

    def get_hotspot_feedback(
        self,
        *,
        hotspot_id: uuid.UUID,
        pagination: PaginationParams,
        current_user_id: uuid.UUID | None = None,
    ) -> HotspotFeedbackListResponse:
        self._require_hotspot(hotspot_id)
        summary = self.get_summary(hotspot_id)

        total = int(
            self.session.exec(
                select(func.count(col(HotspotFeedback.id))).where(
                    HotspotFeedback.hotspot_id == hotspot_id
                )
            ).one()
        )

        rows = self.session.exec(
            select(HotspotFeedback, User)
            .join(User, col(HotspotFeedback.user_id) == col(User.id))
            .where(HotspotFeedback.hotspot_id == hotspot_id)
            .order_by(col(HotspotFeedback.updated_at).desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        ).all()

        items = [_to_public(fb, usr) for fb, usr in rows]

        my_feedback: HotspotFeedbackPublic | None = None
        if current_user_id is not None:
            mine = self.session.exec(
                select(HotspotFeedback, User)
                .join(User, col(HotspotFeedback.user_id) == col(User.id))
                .where(
                    HotspotFeedback.hotspot_id == hotspot_id,
                    HotspotFeedback.user_id == current_user_id,
                )
            ).first()
            if mine is not None:
                my_feedback = _to_public(mine[0], mine[1])

        return HotspotFeedbackListResponse(
            summary=summary,
            items=PaginatedResponse(
                data=items,
                total=total,
                limit=pagination.limit,
                offset=pagination.offset,
            ),
            my_feedback=my_feedback,
        )
