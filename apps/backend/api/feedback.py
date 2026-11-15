from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from repositories.FeedbackRepository import FeedbackRepository
from schemas.feedback import (
    HotspotFeedbackBatchSummaryRequest,
    HotspotFeedbackBatchSummaryResponse,
    HotspotFeedbackListResponse,
    HotspotFeedbackPublic,
    HotspotFeedbackUpsertRequest,
)
from schemas.pagination import PaginationDep
from schemas.sse import SSETargetScope
from services.AuthService import CurrentUserDep, OptionalUserDep, SessionDep
from services.SSENotificationService import SSENotifierDep

router = APIRouter(prefix="/hotspots", tags=["HotspotFeedback"])


@router.post(
    "/feedback/summary",
    response_model=HotspotFeedbackBatchSummaryResponse,
    summary="Obtener resumen de retroalimentación para múltiples hotspots",
)
async def get_feedback_batch_summary(
    payload: HotspotFeedbackBatchSummaryRequest,
    session: SessionDep,
) -> HotspotFeedbackBatchSummaryResponse:
    summaries = FeedbackRepository(session).get_batch_summaries(payload.hotspot_ids)
    return HotspotFeedbackBatchSummaryResponse(summaries=summaries)


@router.get(
    "/{hotspot_id}/feedback",
    response_model=HotspotFeedbackListResponse,
    summary="Listar retroalimentación y consenso de un hotspot",
)
async def list_hotspot_feedback(
    hotspot_id: uuid.UUID,
    session: SessionDep,
    pagination: PaginationDep,
    current_user: OptionalUserDep,
) -> HotspotFeedbackListResponse:
    return FeedbackRepository(session).get_hotspot_feedback(
        hotspot_id=hotspot_id,
        pagination=pagination,
        current_user_id=current_user.id if current_user is not None else None,
    )


@router.put(
    "/{hotspot_id}/feedback",
    response_model=HotspotFeedbackPublic,
    summary="Crear o actualizar retroalimentación de usuario sobre un hotspot",
)
async def upsert_hotspot_feedback(
    hotspot_id: uuid.UUID,
    payload: HotspotFeedbackUpsertRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
    notifier: SSENotifierDep,
) -> HotspotFeedbackPublic:
    repo = FeedbackRepository(session)
    feedback = repo.upsert_feedback(
        hotspot_id=hotspot_id,
        user=current_user,
        payload=payload,
    )
    summary = repo.get_summary(hotspot_id)
    notifier.emit_envelope(
        event_type="hotspot.feedback",
        target_scope=SSETargetScope.ALL,
        payload={
            "action": "upserted",
            "hotspot_id": str(hotspot_id),
            "feedback": feedback.model_dump(mode="json"),
            "summary": summary.model_dump(mode="json"),
        },
    )
    return feedback


@router.delete(
    "/{hotspot_id}/feedback/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar la retroalimentación propia sobre un hotspot",
)
async def delete_my_hotspot_feedback(
    hotspot_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    notifier: SSENotifierDep,
) -> None:
    repo = FeedbackRepository(session)
    repo.delete_user_feedback(hotspot_id=hotspot_id, user_id=current_user.id)
    summary = repo.get_summary(hotspot_id)
    notifier.emit_envelope(
        event_type="hotspot.feedback",
        target_scope=SSETargetScope.ALL,
        payload={
            "action": "deleted",
            "hotspot_id": str(hotspot_id),
            "user_id": str(current_user.id),
            "summary": summary.model_dump(mode="json"),
        },
    )
