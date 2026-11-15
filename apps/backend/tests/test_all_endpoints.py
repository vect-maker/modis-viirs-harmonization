from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
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
from api.cluster_hotspots import get_cluster_hotspots
from api.clusters import get_cluster, get_clusters
from api.countries import get_countries
from api.dashboard import (
    get_annual_stats,
    get_confidence_dbscan,
    get_correlations,
    get_monthly_comparison,
    get_monthly_forecast,
    get_spatial_anomalies,
    get_spatial_density,
)
from api.environmental_records import get_environmental_records
from api.fact_hotspots import get_fact_hotspots
from api.fire_analysis import (
    ClusterMovementRequest,
    FirePredictRequest,
    WeatherCorrelationRequest,
    analyze_clusters_and_movement,
    analyze_weather_correlation,
    predict_fire_displacement,
)
from api.fire_calendar import get_fire_calendar
from api.fire_cluster_forecast import (
    ForecastCalculateRequest,
    calculate_forecast,
    get_fire_cluster_forecasts,
)
from api.hotspots import get_hotspots
from api.platforms import get_platforms
from api.weather import RequestWeather, get_weather_params
from main import root, sqlalchemy_error_handler, value_error_handler
from model import (
    Alert,
    AlertHistory,
    AlertRule,
    ClusterHotspots,
    EnvironmentalRecord,
    FireCluster,
    FireClusterForecast,
    Hotspots,
)
from model.Alert import AlertRuleStatus, AlertRuleType, AlertSeverity, AlertStatus
from model.ClusterStatus import ClusterStatus
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


def _build_test_session() -> Session:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(
        engine,
        tables=[
            Hotspots.__table__,  # type: ignore[attr-defined]
            FireCluster.__table__,  # type: ignore[attr-defined]
            ClusterHotspots.__table__,  # type: ignore[attr-defined]
            EnvironmentalRecord.__table__,  # type: ignore[attr-defined]
            FireClusterForecast.__table__,  # type: ignore[attr-defined]
            AlertRule.__table__,  # type: ignore[attr-defined]
            Alert.__table__,  # type: ignore[attr-defined]
            AlertHistory.__table__,  # type: ignore[attr-defined]
        ],
    )
    session = Session(engine)

    # Create analytical star-schema tables queried via raw SQL
    session.execute(
        text(
            """
            CREATE TABLE dim_country (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TABLE dim_platform (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                satellite TEXT NOT NULL,
                instrument TEXT NOT NULL
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TABLE fact_hotspots (
                id TEXT PRIMARY KEY,
                acq_datetime DATETIME,
                latitude REAL,
                longitude REAL,
                bright_mir REAL,
                bright_tir REAL,
                scan REAL,
                track REAL,
                frp REAL,
                confidence TEXT,
                confidence_class TEXT,
                confidence_numeric REAL,
                daynight TEXT,
                type INTEGER,
                version TEXT,
                country_id INTEGER,
                platform_id INTEGER
            )
            """
        )
    )

    session.execute(text("INSERT INTO dim_country (id, name) VALUES (1, 'Nicaragua')"))
    session.execute(
        text(
            "INSERT INTO dim_platform (id, satellite, instrument) "
            "VALUES (1, 'NOAA-20', 'VIIRS')"
        )
    )

    # Seed 24 months of Hotspots & fact_hotspots for dashboard, fire-calendar & monthly-forecast
    base_dt = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
    for m in range(24):
        dt = datetime(2024 + (m // 12), (m % 12) + 1, 15, 12, 0, tzinfo=UTC)
        for j in range(3):
            hid = uuid4()
            lat = 12.10 + (j * 0.01) + (m * 0.001)
            lon = -86.20 - (j * 0.01)
            frp = 20.0 + m + j * 5.0
            conf_num = 85.0 if j < 2 else 45.0
            conf_str = "h" if j < 2 else "n"
            session.add(
                Hotspots(
                    id=hid,
                    latitude=lat,
                    longitude=lon,
                    acq_datetime=dt,
                    satellite="N20",
                    instrument="VIIRS",
                    confidence=conf_str,
                    frp=frp,
                    bright_tir=330.0 + j,
                    bright_mir=295.0 + j,
                    daynight="D" if j % 2 == 0 else "N",
                )
            )
            session.execute(
                text(
                    """
                    INSERT INTO fact_hotspots (
                        id, acq_datetime, latitude, longitude, bright_mir, bright_tir,
                        scan, track, frp, confidence, confidence_class, confidence_numeric,
                        daynight, type, version, country_id, platform_id
                    ) VALUES (
                        :id, :dt, :lat, :lon, :bmir, :btir,
                        0.4, 0.4, :frp, :conf, :conf, :conf_num,
                        :dn, 0, '2.0NRT', 1, 1
                    )
                    """
                ),
                {
                    "id": str(hid),
                    "dt": dt,
                    "lat": lat,
                    "lon": lon,
                    "bmir": 300.0 + j,
                    "btir": 330.0 + j,
                    "frp": frp,
                    "conf": conf_str,
                    "conf_num": conf_num,
                    "dn": "D" if j % 2 == 0 else "N",
                },
            )

    # Seed ORM models: Hotspots, FireCluster, ClusterHotspots, EnvironmentalRecord, FireClusterForecast
    recent_dt = datetime.now(UTC) - timedelta(hours=1)
    h1 = Hotspots(
        id=uuid4(),
        latitude=12.10,
        longitude=-86.20,
        acq_datetime=recent_dt,
        satellite="N20",
        instrument="VIIRS",
        confidence="high",
        frp=42.5,
        bright_tir=335.0,
        bright_mir=305.0,
        daynight="D",
    )
    h2 = Hotspots(
        id=uuid4(),
        latitude=12.12,
        longitude=-86.18,
        acq_datetime=recent_dt + timedelta(minutes=30),
        satellite="N20",
        instrument="VIIRS",
        confidence="high",
        frp=55.0,
        bright_tir=342.0,
        bright_mir=310.0,
        daynight="D",
    )
    session.add(h1)
    session.add(h2)

    cluster = FireCluster(
        id=1,
        polygon=0.0,
        status=ClusterStatus.ACTIVO,
        datetimeStart=base_dt,
        datetimeEnd=base_dt + timedelta(hours=2),
        maxFrp=55.0,
    )
    session.add(cluster)
    session.add(ClusterHotspots(clusterId=1, hotspotsId=1))
    session.add(
        EnvironmentalRecord(
            datetimeStart=base_dt,
            temperature=34.5,
            windSpeed=18.2,
            windDirection=90.0,
            precipitation=0.0,
            humidity=42.0,
            fireClusterId=1,
        )
    )
    session.add(
        FireClusterForecast(
            fireClusterId=1,
            dirExpansion=45.0,
            cardinalDirection="NE",
            veloExpansion=2.5,
            distanceKm=5.0,
        )
    )
    session.commit()
    return session


def test_all_core_and_catalog_endpoints():
    session = _build_test_session()

    root_res = _run_coro(root())
    assert root_res == {"message": "Servidor funcionando"}

    countries = _run_coro(get_countries(limit=50, offset=0, session=session))
    assert len(countries["data"]) == 1
    assert countries["data"][0]["name"] == "Nicaragua"

    platforms = _run_coro(get_platforms(limit=50, offset=0, session=session))
    assert len(platforms["data"]) == 1
    assert platforms["data"][0]["satellite"] == "NOAA-20"

    env_records = _run_coro(get_environmental_records(limit=50, offset=0, session=session))
    assert len(env_records["data"]) == 1

    clusters = _run_coro(get_clusters(limit=50, offset=0, status=None, session=session))
    assert len(clusters["data"]) == 1

    cluster = _run_coro(get_cluster(cluster_id=1, limit=50, offset=0, session=session))
    assert cluster["data"]["cluster"].id == 1

    ch = _run_coro(get_cluster_hotspots(limit=50, offset=0, session=session))
    assert len(ch["data"]) == 1

    hotspots = _run_coro(
        get_hotspots(
            limit=50,
            offset=0,
            min_lat=12.0,
            max_lat=12.5,
            min_lon=-86.5,
            max_lon=-86.0,
            center_lat=None,
            center_lon=None,
            radius_km=None,
            polygon_wkt=None,
            session=session,
        )
    )
    assert len(hotspots["data"]) == 50

    fact_hotspots = _run_coro(
        get_fact_hotspots(
            limit=50,
            offset=0,
            min_lat=12.0,
            max_lat=12.5,
            min_lon=-86.5,
            max_lon=-86.0,
            center_lat=None,
            center_lon=None,
            radius_km=None,
            polygon_wkt=None,
            session=session,
        )
    )
    assert len(fact_hotspots["data"]) == 50

    forecasts = _run_coro(get_fire_cluster_forecasts(limit=50, offset=0, session=session))
    assert len(forecasts["data"]) == 1


def test_weather_and_fire_analysis_endpoints():
    mock_weather = [
        {
            "date": "2025-04-01",
            "temperature_max": 35.0,
            "temperature_min": 22.0,
            "precipitation_sum": 0.0,
            "wind_speed_max": 18.0,
            "wind_direction_dominant": 90.0,
            "humidity_mean": 40.0,
        },
        {
            "date": "2025-04-02",
            "temperature_max": 36.0,
            "temperature_min": 23.0,
            "precipitation_sum": 0.0,
            "wind_speed_max": 20.0,
            "wind_direction_dominant": 95.0,
            "humidity_mean": 38.0,
        },
    ]

    with patch(
        "api.weather.WeatherDataClient.fetch_daily_records",
        new=AsyncMock(return_value=mock_weather),
    ):
        weather_res = _run_coro(
            get_weather_params(
                data=RequestWeather(
                    latitude=12.1,
                    longitude=-86.2,
                    start=datetime(2025, 4, 1, tzinfo=UTC),
                    end=datetime(2025, 4, 2, tzinfo=UTC),
                ),
                limit=50,
                offset=0,
            )
        )
        assert len(weather_res["data"]) == 2

    t0 = datetime(2025, 4, 1, 10, 0, tzinfo=UTC)
    sample_rows = [
        {"id": "1", "latitude": 12.100, "longitude": -86.200, "acq_datetime": t0, "frp": 15.0},
        {"id": "2", "latitude": 12.102, "longitude": -86.198, "acq_datetime": t0 + timedelta(hours=1), "frp": 25.0},
        {"id": "3", "latitude": 12.108, "longitude": -86.192, "acq_datetime": t0 + timedelta(hours=7), "frp": 35.0},
    ]

    class _DummySession:
        pass

    with patch(
        "api.fire_analysis.HotspotRepository.iter_hotspots_filtered",
        return_value=iter(sample_rows),
    ):
        cm_res = _run_coro(
            analyze_clusters_and_movement(
                payload=ClusterMovementRequest(eps_km=2.0, min_samples=2, interval_hours=6.0),
                limit=50,
                offset=0,
                session=_DummySession(),  # type: ignore[arg-type]
            )
        )
        assert cm_res["summary"]["hotspots_valid"] == 3

    with (
        patch(
            "api.fire_analysis.HotspotRepository.iter_hotspots_filtered",
            return_value=iter(sample_rows),
        ),
        patch(
            "api.fire_analysis.WeatherDataClient.fetch_daily_records",
            new=AsyncMock(return_value=mock_weather),
        ),
    ):
        wc_res = _run_coro(
            analyze_weather_correlation(
                payload=WeatherCorrelationRequest(
                    latitude=12.1,
                    longitude=-86.2,
                    start_date=datetime(2025, 4, 1, tzinfo=UTC),
                    end_date=datetime(2025, 4, 2, tzinfo=UTC),
                ),
                limit=50,
                offset=0,
            )
        )
        assert "data" in wc_res

        # Build enough fires & intervals for FirePredictRequest
        many_rows = []
        fake_daily = []
        for fire_idx in range(6):
            day_base = t0 + timedelta(days=fire_idx * 3)
            lat = 12.0 + fire_idx * 0.2
            lon = -86.5 + fire_idx * 0.2
            for step in range(4):
                dt = day_base + timedelta(hours=step * 6)
                many_rows.append(
                    {
                        "id": f"{fire_idx}-{step}-a",
                        "latitude": lat + step * 0.005,
                        "longitude": lon + step * 0.005,
                        "acq_datetime": dt,
                        "frp": 25.0 + step * 5.0,
                    }
                )
                many_rows.append(
                    {
                        "id": f"{fire_idx}-{step}-b",
                        "latitude": lat + step * 0.005 + 0.001,
                        "longitude": lon + step * 0.005 + 0.001,
                        "acq_datetime": dt + timedelta(minutes=10),
                        "frp": 25.0 + step * 5.0,
                    }
                )
            fake_daily.append(
                {
                    "date": day_base.strftime("%Y%m%d"),
                    "T2M": 32.0,
                    "RH2M": 38.0,
                    "WS10M": 9.0,
                    "WD10M": 225.0,
                    "PRECTOTCORR": 0.0,
                }
            )
        with (
            patch(
                "api.fire_analysis.HotspotRepository.iter_hotspots_filtered",
                return_value=iter(many_rows),
            ),
            patch(
                "api.fire_analysis.WeatherDataClient.fetch_daily_records",
                new=AsyncMock(return_value=fake_daily),
            ),
        ):
            pred_res = _run_coro(
                predict_fire_displacement(
                    payload=FirePredictRequest(
                        start_date=t0,
                        end_date=t0 + timedelta(days=20),
                        eps_km=2.0,
                        min_samples=2,
                        interval_hours=6.0,
                        min_training_samples=5,
                        n_estimators=20,
                    ),
                    session=_DummySession(),  # type: ignore[arg-type]
                )
            )
            assert "metrics" in pred_res
            assert "latest_prediction" in pred_res


def test_dashboard_and_fire_calendar_endpoints():
    session = _build_test_session()

    dbscan_res = _run_coro(
        get_confidence_dbscan(
            eps=5.0,
            min_samples=2,
            high_value=90,
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2025, 12, 31, tzinfo=UTC),
            session=session,
        )
    )
    assert "summary" in dbscan_res
    assert "points" in dbscan_res

    corr_res = _run_coro(
        get_correlations(
            high_value=90,
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2025, 12, 31, tzinfo=UTC),
            session=session,
        )
    )
    assert "data" in corr_res

    annual_res = _run_coro(
        get_annual_stats(high_value=85, start_year=2001, end_year=2025, session=session)
    )
    assert len(annual_res["data"]) == 2

    density_res = _run_coro(
        get_spatial_density(
            cell_size_deg=0.1,
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2025, 12, 31, tzinfo=UTC),
            min_lat=None,
            max_lat=None,
            min_lon=None,
            max_lon=None,
            limit=5000,
            session=session,
        )
    )
    assert "data" in density_res

    monthly_cmp_res = _run_coro(
        get_monthly_comparison(year=2025, start_year=2024, end_year=2025, session=session)
    )
    assert monthly_cmp_res["year"] == 2025

    anom_res = _run_coro(
        get_spatial_anomalies(
            n_estimators=50,
            contamination=0.1,
            random_state=42,
            max_rows=500,
            max_points_returned=100,
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2025, 12, 31, tzinfo=UTC),
            min_lat=None,
            max_lat=None,
            min_lon=None,
            max_lon=None,
            session=session,
        )
    )
    assert "summary" in anom_res

    forecast_res = _run_coro(
        get_monthly_forecast(
            train_ratio=0.8,
            future_months=6,
            start_year=2024,
            end_year=2025,
            session=session,
        )
    )
    assert len(forecast_res["future"]) == 6

    cal_res = _run_coro(
        get_fire_calendar(
            year=2024,
            month=None,
            start_date=None,
            end_date=None,
            country=None,
            department=None,
            municipality=None,
            min_confidence=None,
            confidence_class=None,
            satellite=None,
            instrument=None,
            daynight=None,
            min_frp=None,
            max_frp=None,
            cluster_id=None,
            min_lat=None,
            max_lat=None,
            min_lon=None,
            max_lon=None,
            center_lat=None,
            center_lon=None,
            radius_km=None,
            polygon_wkt=None,
            aggregation="month",
            session=session,
        )
    )
    assert cal_res.total_hotspots >= 1


def test_alerts_endpoints_end_to_end():
    session = _build_test_session()

    rule = _run_coro(
        create_alert_rule(
            payload=AlertRuleCreate(
                name="FRP Alto Test",
                description="Detecta hotspots con FRP >= 30",
                ruleType=AlertRuleType.HIGH_FRP,
                conditions={"min_frp": 30.0},
                severity=AlertSeverity.HIGH,
                status=AlertRuleStatus.ACTIVE,
            ),
            session=session,
        )
    )
    assert rule.id is not None

    rules = _run_coro(list_alert_rules(status=None, limit=50, offset=0, session=session))
    assert len(rules["data"]) == 1

    updated_rule = _run_coro(
        update_alert_rule(
            rule_id=rule.id,
            payload=AlertRuleUpdate(description="Descripción actualizada"),
            session=session,
        )
    )
    assert updated_rule.description == "Descripción actualizada"

    eval_res = _run_coro(
        evaluate_alerts(
            payload=AlertEvaluateRequest(rule_ids=[rule.id], run_in_background=False),
            background_tasks=BackgroundTasks(),
            session=session,
        )
    )
    assert eval_res.created_alerts >= 1

    alerts = _run_coro(
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
    assert len(alerts["data"]) >= 1
    alert_id = alerts["data"][0].id

    detail = _run_coro(get_alert(alert_id=alert_id, session=session))
    assert detail.id == alert_id

    updated_alert = _run_coro(
        update_alert_status(
            alert_id=alert_id,
            payload=AlertStatusUpdate(status=AlertStatus.REVIEWED, changed_by="qa", note="ok"),
            session=session,
        )
    )
    assert updated_alert.status == AlertStatus.REVIEWED

    history = _run_coro(get_alert_history(alert_id=alert_id, limit=50, offset=0, session=session))
    assert len(history["data"]) >= 2


def test_exception_handling_and_validation_errors():
    session = _build_test_session()

    # Global ValueError handler -> 400 JSON
    val_resp = _run_coro(value_error_handler(None, ValueError("Rango inválido")))  # type: ignore[arg-type]
    assert val_resp.status_code == 400
    assert json.loads(bytes(val_resp.body).decode()) == {
        "error_type": "validation_error",
        "detail": "Rango inválido",
    }

    # Global SQLAlchemyError handler -> 503 JSON
    db_resp = _run_coro(sqlalchemy_error_handler(None, SQLAlchemyError("connection refused")))  # type: ignore[arg-type]
    assert db_resp.status_code == 503
    body = json.loads(bytes(db_resp.body).decode())
    assert body["error_type"] == "database_error"
    assert body["detail"] == "Error al consultar la base de datos"

    # 404 on missing cluster
    with pytest.raises(HTTPException) as exc_cluster:
        _run_coro(get_cluster(cluster_id=99999, limit=50, offset=0, session=session))
    assert exc_cluster.value.status_code == 404

    # 404 on calculate_forecast missing cluster
    with pytest.raises(HTTPException) as exc_fc_404:
        _run_coro(calculate_forecast(payload=ForecastCalculateRequest(fireClusterId=99999), session=session))
    assert exc_fc_404.value.status_code == 404

    # 400 on calculate_forecast with <2 hotspots
    with pytest.raises(HTTPException) as exc_fc_400:
        _run_coro(calculate_forecast(payload=ForecastCalculateRequest(fireClusterId=1), session=session))
    assert exc_fc_400.value.status_code == 400

    # 400 on invalid spatial area filter
    with pytest.raises(HTTPException) as exc_sp_hotspots:
        _run_coro(
            get_hotspots(
                limit=10,
                offset=0,
                min_lat=20.0,
                max_lat=10.0,
                min_lon=None,
                max_lon=None,
                center_lat=None,
                center_lon=None,
                radius_km=None,
                polygon_wkt=None,
                session=session,
            )
        )
    assert exc_sp_hotspots.value.status_code == 400

    with pytest.raises(HTTPException) as exc_sp_fact:
        _run_coro(
            get_fact_hotspots(
                limit=10,
                offset=0,
                min_lat=20.0,
                max_lat=10.0,
                min_lon=None,
                max_lon=None,
                center_lat=None,
                center_lon=None,
                radius_km=None,
                polygon_wkt=None,
                session=session,
            )
        )
    assert exc_sp_fact.value.status_code == 400

    # 400 on invalid date/year ranges in dashboard endpoints
    with pytest.raises(HTTPException) as exc_db_dates:
        _run_coro(
            get_confidence_dbscan(
                eps=5.0,
                min_samples=2,
                high_value=90,
                start_date=datetime(2025, 5, 1, tzinfo=UTC),
                end_date=datetime(2025, 1, 1, tzinfo=UTC),
                session=session,
            )
        )
    assert exc_db_dates.value.status_code == 400

    with pytest.raises(HTTPException) as exc_cmp_years:
        _run_coro(
            get_monthly_comparison(year=None, start_year=2026, end_year=2024, session=session)
        )
    assert exc_cmp_years.value.status_code == 400

    with pytest.raises(HTTPException) as exc_fc_years:
        _run_coro(
            get_monthly_forecast(
                train_ratio=0.8,
                future_months=6,
                start_year=2026,
                end_year=2024,
                session=session,
            )
        )
    assert exc_fc_years.value.status_code == 400

    # 404 on missing alert
    with pytest.raises(HTTPException) as exc_alert:
        _run_coro(get_alert(alert_id=99999, session=session))
    assert exc_alert.value.status_code == 404
