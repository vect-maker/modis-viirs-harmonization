from __future__ import annotations

import hmac
import os

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from database.session import get_session
from model.Alert import AlertRuleStatus, AlertSeverity, AlertStatus
from schemas.alerts import (
    AlertEvaluateRequest,
    AlertEvaluateResponse,
    AlertHistoryRead,
    AlertRead,
    AlertRuleCreate,
    AlertRuleRead,
    AlertRuleUpdate,
    AlertStatusUpdate,
)
from services.AlertDetectionService import AlertDetectionService
from services.AlertManagementService import AlertManagementService
from services.AlertRuleService import AlertRuleService
from services.AlertSchedulerService import alert_scheduler
from services.NotificationService import ws_manager
from services.SSEConnectionService import SSEConnectionService, parse_last_event_id

router = APIRouter(prefix="/alerts", tags=["EarlyWarning"])


def verify_sse_access(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    token: str | None = Query(default=None),
) -> None:
    expected = (
        os.getenv("ALERT_STREAM_TOKEN", "").strip()
        or os.getenv("API_AUTH_TOKEN", "").strip()
    )
    if not expected:
        return

    provided: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    elif x_api_key:
        provided = x_api_key.strip()
    elif token:
        provided = token.strip()

    if not provided:
        raise HTTPException(
            status_code=401,
            detail="Autenticación requerida para acceder al stream de alertas",
        )
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=403,
            detail="Credenciales inválidas para el stream de alertas",
        )


@router.get("", response_model=dict[str, object], summary="Listar alertas")
async def list_alerts(
    status: AlertStatus | None = None,
    severity: AlertSeverity | None = None,
    rule_id: int | None = Query(default=None, ge=1),
    cluster_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    service = AlertManagementService(session)
    data = service.list_alerts(
        status=status,
        severity=severity,
        rule_id=rule_id,
        cluster_id=cluster_id,
        limit=limit,
        offset=offset,
    )
    return {"data": data, "limit": limit, "offset": offset}


@router.get("/rules", response_model=dict[str, object], summary="Listar reglas de alerta")
async def list_alert_rules(
    status: AlertRuleStatus | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    service = AlertRuleService(session)
    data = service.list_rules(status=status, limit=limit, offset=offset)
    return {"data": data, "limit": limit, "offset": offset}


@router.post("/rules", response_model=AlertRuleRead, status_code=201, summary="Crear regla de alerta")
async def create_alert_rule(
    payload: AlertRuleCreate,
    session: Session = Depends(get_session),
):
    service = AlertRuleService(session)
    return service.create_rule(payload)


@router.patch("/rules/{rule_id}", response_model=AlertRuleRead, summary="Actualizar regla de alerta")
async def update_alert_rule(
    rule_id: int,
    payload: AlertRuleUpdate,
    session: Session = Depends(get_session),
):
    service = AlertRuleService(session)
    return service.update_rule(rule_id, payload)


@router.get("/history", response_model=dict[str, object], summary="Consultar historial de alertas")
async def get_alert_history(
    alert_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    service = AlertManagementService(session)
    data: list[AlertHistoryRead] = service.list_history(
        alert_id=alert_id, limit=limit, offset=offset
    )
    return {"data": data, "limit": limit, "offset": offset}


@router.post(
    "/evaluate",
    response_model=AlertEvaluateResponse,
    summary="Evaluar reglas activas (en segundo plano por defecto)",
)
async def evaluate_alerts(
    payload: AlertEvaluateRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    if payload.run_in_background:
        if alert_scheduler.is_running:
            return AlertEvaluateResponse(status="skipped_already_running")
        background_tasks.add_task(alert_scheduler.run_once_with_retries, payload.rule_ids)
        return AlertEvaluateResponse(status="scheduled")

    service = AlertDetectionService(session)
    result = await service.evaluate_rules(rule_ids=payload.rule_ids)
    return AlertEvaluateResponse(**result)


@router.get(
    "/stream",
    summary="Stream en tiempo real de alertas de hotspots mediante Server-Sent Events (SSE)",
    dependencies=[Depends(verify_sse_access)],
)
async def stream_alerts(
    request: Request,
    last_event_id_header: str | None = Header(default=None, alias="Last-Event-ID"),
    last_event_id: int | None = Query(default=None, ge=0),
    max_events: int | None = Query(default=None, ge=1, include_in_schema=False),
    session: Session = Depends(get_session),
):
    resolved_last_id = parse_last_event_id(last_event_id_header, last_event_id)
    connection_service = SSEConnectionService()
    return StreamingResponse(
        connection_service.event_stream(
            request=request,
            session=session,
            last_event_id=resolved_last_id,
            max_events=max_events,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{alert_id}", response_model=AlertRead, summary="Detalle de una alerta")
async def get_alert(
    alert_id: int,
    session: Session = Depends(get_session),
):
    service = AlertManagementService(session)
    return service.get_alert(alert_id)


@router.patch("/{alert_id}/status", response_model=AlertRead, summary="Actualizar estado de una alerta")
async def update_alert_status(
    alert_id: int,
    payload: AlertStatusUpdate,
    session: Session = Depends(get_session),
):
    service = AlertManagementService(session)
    return service.update_status(alert_id, payload)


@router.websocket("/ws")
async def alerts_websocket(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
