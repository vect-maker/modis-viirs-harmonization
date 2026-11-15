from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import BackgroundTasks
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from api.alerts import (
    create_alert_rule,
    evaluate_alerts,
    get_alert,
    get_alert_history,
    list_alert_rules,
    list_alerts,
    update_alert_rule,
    update_alert_status,
)
from model.Alert import (
    Alert,
    AlertHistory,
    AlertRule,
    AlertRuleStatus,
    AlertRuleType,
    AlertSeverity,
    AlertStatus,
)
from model.ClusterStatus import ClusterStatus
from model.EnvironmentalRecord import EnvironmentalRecord
from model.FireCluster import FireCluster
from schemas.alerts import (
    AlertEvaluateRequest,
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertStatusUpdate,
)


def _run_coro(coro):
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


def _seed_alert_session() -> tuple[Session, datetime]:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(
        engine,
        tables=[
            FireCluster.__table__,  # type: ignore[attr-defined]
            EnvironmentalRecord.__table__,  # type: ignore[attr-defined]
            AlertRule.__table__,  # type: ignore[attr-defined]
            Alert.__table__,  # type: ignore[attr-defined]
            AlertHistory.__table__,  # type: ignore[attr-defined]
        ],
    )
    session = Session(engine)
    session.execute(
        text(
            """
            CREATE TABLE hotspots (
                id TEXT PRIMARY KEY,
                country TEXT,
                latitude REAL,
                longitude REAL,
                acq_datetime DATETIME,
                satellite TEXT,
                instrument TEXT,
                confidence TEXT,
                confidence_class TEXT,
                frp REAL,
                daynight TEXT
            )
            """
        )
    )

    now = datetime.now(UTC)
    recent_dt = (now - timedelta(hours=2)).replace(tzinfo=None)
    prev_dt = (now - timedelta(hours=30)).replace(tzinfo=None)

    for i in range(6):
        session.execute(
            text(
                """
                INSERT INTO hotspots (
                    id, country, latitude, longitude, acq_datetime,
                    satellite, instrument, confidence, confidence_class, frp, daynight
                ) VALUES (
                    :id, 'Nicaragua', :lat, :lon, :dt,
                    'Suomi NPP', 'VIIRS', 'h', 'high', :frp, 'D'
                )
                """
            ),
            {
                "id": str(uuid4()),
                "lat": 12.10 + i * 0.001,
                "lon": -86.20 + i * 0.001,
                "dt": recent_dt,
                "frp": 75.0 + i * 5.0,
            },
        )

    # 1 hotspot previo para probar ACTIVITY_SPIKE (6 vs 1 = 6x)
    session.execute(
        text(
            """
            INSERT INTO hotspots (
                id, country, latitude, longitude, acq_datetime,
                satellite, instrument, confidence, confidence_class, frp, daynight
            ) VALUES (
                :id, 'Nicaragua', 12.10, -86.20, :dt,
                'Aqua', 'MODIS', '60', 'nominal', 15.0, 'D'
            )
            """
        ),
        {"id": str(uuid4()), "dt": prev_dt},
    )

    cluster = FireCluster(
        id=1,
        polygon=1.5,
        status=ClusterStatus.ACTIVO,
        datetimeStart=now - timedelta(hours=4),
        datetimeEnd=now - timedelta(hours=1),
        maxFrp=100.0,
    )
    env = EnvironmentalRecord(
        id=1,
        temperature=38.0,
        humidity=22.0,
        windSpeed=18.0,
        windDirection=225.0,
        fireClusterId=1,
    )
    session.add_all([cluster, env])
    session.commit()
    return session, now


def test_rules_crud_evaluation_dedup_and_lifecycle():
    session, _ = _seed_alert_session()

    # 1. Crear reglas de distintos tipos
    r1 = _run_coro(
        create_alert_rule(
            AlertRuleCreate(
                name="FRP Alto Nicaragua",
                description="Detecta FRP >= 60 MW",
                ruleType=AlertRuleType.HIGH_FRP,
                conditions={"min_frp": 60.0, "lookback_hours": 24},
                severity=AlertSeverity.HIGH,
                region="Nicaragua",
            ),
            session=session,
        )
    )
    r2 = _run_coro(
        create_alert_rule(
            AlertRuleCreate(
                name="Pico de actividad",
                ruleType=AlertRuleType.ACTIVITY_SPIKE,
                conditions={"spike_ratio": 2.0, "min_recent_count": 3, "lookback_hours": 24},
                severity=AlertSeverity.CRITICAL,
                region="Nicaragua",
            ),
            session=session,
        )
    )
    r3 = _run_coro(
        create_alert_rule(
            AlertRuleCreate(
                name="Proximidad comunidad",
                ruleType=AlertRuleType.NEAR_COMMUNITY,
                conditions={
                    "target_lat": 12.10,
                    "target_lon": -86.20,
                    "radius_km": 5.0,
                    "target_name": "Comunidad Demo",
                },
                severity=AlertSeverity.HIGH,
                region="Nicaragua",
            ),
            session=session,
        )
    )
    r4 = _run_coro(
        create_alert_rule(
            AlertRuleCreate(
                name="Índice de riesgo",
                ruleType=AlertRuleType.RISK_INDEX_INCREASE,
                conditions={"min_risk_score": 0.5, "lookback_hours": 24},
                severity=AlertSeverity.MEDIUM,
                region="Nicaragua",
            ),
            session=session,
        )
    )

    rules_resp = _run_coro(list_alert_rules(limit=50, offset=0, session=session))
    assert len(rules_resp["data"]) == 4

    # Actualizar regla
    updated_rule = _run_coro(
        update_alert_rule(
            r4.id,
            AlertRuleUpdate(severity=AlertSeverity.HIGH),
            session=session,
        )
    )
    assert updated_rule.severity == AlertSeverity.HIGH

    # 2. Evaluar reglas (modo síncrono para inspeccionar resultados en test)
    bg = BackgroundTasks()
    eval_res = _run_coro(
        evaluate_alerts(
            AlertEvaluateRequest(rule_ids=[r1.id, r2.id, r3.id, r4.id], run_in_background=False),
            background_tasks=bg,
            session=session,
        )
    )
    assert eval_res.evaluated_rules == 4
    assert eval_res.created_alerts == 4
    assert eval_res.skipped_duplicates == 0
    assert eval_res.errors == []

    # 3. Re-evaluar inmediatamente -> debe prevenir duplicados
    eval_dup = _run_coro(
        evaluate_alerts(
            AlertEvaluateRequest(rule_ids=[r1.id, r2.id, r3.id, r4.id], run_in_background=False),
            background_tasks=bg,
            session=session,
        )
    )
    assert eval_dup.created_alerts == 0
    assert eval_dup.skipped_duplicates == 4

    # 4. Modo en segundo plano en endpoint HTTP
    bg_resp = _run_coro(
        evaluate_alerts(
            AlertEvaluateRequest(run_in_background=True),
            background_tasks=bg,
            session=session,
        )
    )
    assert bg_resp.status == "scheduled"
    assert len(bg.tasks) == 1

    # 5. Consultar alertas, fiabilidad y ciclo de vida (NEW -> REVIEWED -> RESOLVED)
    alerts_list = _run_coro(
        list_alerts(
            status=None,
            severity=None,
            rule_id=None,
            cluster_id=None,
            limit=50,
            offset=0,
            session=session,
        )
    )
    assert len(alerts_list["data"]) == 4
    first_alert = alerts_list["data"][0]
    assert first_alert.fireClusterId == 1
    assert first_alert.dataAgeSeconds is not None
    assert "confirmad" not in first_alert.title.lower()

    detail = _run_coro(get_alert(first_alert.id, session=session))
    assert detail.id == first_alert.id

    reviewed = _run_coro(
        update_alert_status(
            first_alert.id,
            AlertStatusUpdate(
                status=AlertStatus.REVIEWED,
                changed_by="analyst@firms",
                note="En revisión satelital",
            ),
            session=session,
        )
    )
    assert reviewed.status == AlertStatus.REVIEWED

    resolved = _run_coro(
        update_alert_status(
            first_alert.id,
            AlertStatusUpdate(
                status=AlertStatus.RESOLVED,
                changed_by="analyst@firms",
                note="Seguimiento completado",
            ),
            session=session,
        )
    )
    assert resolved.status == AlertStatus.RESOLVED

    history = _run_coro(get_alert_history(alert_id=first_alert.id, limit=50, offset=0, session=session))
    assert len(history["data"]) == 3  # NEW -> REVIEWED -> RESOLVED

    # Pausar regla
    paused = _run_coro(
        update_alert_rule(
            r1.id,
            AlertRuleUpdate(status=AlertRuleStatus.PAUSED),
            session=session,
        )
    )
    assert paused.status == AlertRuleStatus.PAUSED
