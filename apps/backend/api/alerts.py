from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
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

router = APIRouter(prefix="/alerts", tags=["EarlyWarning"])


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
