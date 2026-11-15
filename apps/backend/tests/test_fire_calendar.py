from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from api.fire_calendar import get_fire_calendar
from model import FireCluster
from model.ClusterStatus import ClusterStatus


def _run_coro(coro):
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


def _seed_calendar_session() -> Session:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine, tables=[FireCluster.__table__])  # type: ignore[attr-defined]
    session = Session(engine)

    # Crea la tabla hotspots equivalente a la vista PostgreSQL `hotspots`
    session.execute(
        text(
            """
            CREATE TABLE hotspots (
                id TEXT PRIMARY KEY,
                country TEXT,
                latitude REAL,
                longitude REAL,
                bright_mir REAL,
                scan REAL,
                track REAL,
                acq_datetime DATETIME,
                satellite TEXT,
                instrument TEXT,
                confidence TEXT,
                confidence_class TEXT,
                version TEXT,
                bright_tir REAL,
                frp REAL,
                daynight TEXT,
                type INTEGER
            )
            """
        )
    )

    rows = [
        (
            str(uuid4()),
            "Nicaragua",
            12.10,
            -86.20,
            datetime(2025, 3, 1, 10, 0, 0),
            "Aqua",
            "MODIS",
            "90",
            "high",
            45.0,
            "D",
        ),
        (
            str(uuid4()),
            "Nicaragua",
            12.11,
            -86.19,
            datetime(2025, 3, 1, 22, 0, 0),
            "Suomi NPP",
            "VIIRS",
            "n",
            "nominal",
            15.0,
            "N",
        ),
        (
            str(uuid4()),
            "Nicaragua",
            12.15,
            -86.15,
            datetime(2025, 3, 10, 14, 0, 0),
            "Aqua",
            "MODIS",
            "h",
            "high",
            80.0,
            "D",
        ),
        (
            str(uuid4()),
            "Honduras",
            14.10,
            -87.20,
            datetime(2025, 4, 5, 11, 0, 0),
            "Terra",
            "MODIS",
            "30",
            "low",
            5.0,
            "D",
        ),
    ]
    for r in rows:
        session.execute(
            text(
                """
                INSERT INTO hotspots (
                    id, country, latitude, longitude, acq_datetime,
                    satellite, instrument, confidence, confidence_class, frp, daynight
                ) VALUES (
                    :id, :country, :lat, :lon, :dt,
                    :sat, :inst, :conf, :cclass, :frp, :dn
                )
                """
            ),
            {
                "id": r[0],
                "country": r[1],
                "lat": r[2],
                "lon": r[3],
                "dt": r[4],
                "sat": r[5],
                "inst": r[6],
                "conf": r[7],
                "cclass": r[8],
                "frp": r[9],
                "dn": r[10],
            },
        )

    session.add_all(
        [
            FireCluster(
                id=1,
                polygon=1.2,
                status=ClusterStatus.ACTIVO,
                datetimeStart=datetime(2025, 3, 1, 10, 0, 0, tzinfo=UTC),
                datetimeEnd=datetime(2025, 3, 3, 10, 0, 0, tzinfo=UTC),
                maxFrp=45.0,
            ),
            FireCluster(
                id=2,
                polygon=2.5,
                status=ClusterStatus.FINALIZADO,
                datetimeStart=datetime(2025, 3, 10, 14, 0, 0, tzinfo=UTC),
                datetimeEnd=datetime(2025, 3, 10, 18, 0, 0, tzinfo=UTC),
                maxFrp=80.0,
            ),
        ]
    )
    session.commit()
    return session


def _call_calendar(session: Session, **kwargs):
    defaults = {
        "year": 2025,
        "month": None,
        "start_date": None,
        "end_date": None,
        "country": None,
        "department": None,
        "municipality": None,
        "min_confidence": None,
        "confidence_class": None,
        "satellite": None,
        "instrument": None,
        "daynight": None,
        "min_frp": None,
        "max_frp": None,
        "cluster_id": None,
        "aggregation": "day",
        "session": session,
    }
    defaults.update(kwargs)
    return _run_coro(get_fire_calendar(**defaults))


def test_full_year_and_aggregations():
    session = _seed_calendar_session()
    res_month = _call_calendar(session, year=2025, aggregation="month")
    assert res_month.total_hotspots == 4
    assert res_month.total_fires == 2
    assert res_month.new_fires == 2
    assert res_month.active_fires == 1
    assert len(res_month.intervals) == 12
    assert res_month.intervals[2].hotspot_count == 3  # marzo
    assert res_month.intervals[2].new_fires == 2
    assert res_month.intervals[0].hotspot_count == 0  # enero sin detecciones

    res_week = _call_calendar(
        session,
        year=2025,
        month=3,
        aggregation="week",
    )
    assert res_week.aggregation == "week"
    assert res_week.total_hotspots == 3
    assert len(res_week.intervals) >= 5

    res_day = _call_calendar(session, year=2025, month=3, aggregation="day")
    assert len(res_day.intervals) == 31
    assert res_day.intervals[0].hotspot_count == 2
    assert res_day.intervals[0].daytime_hotspots == 1
    assert res_day.intervals[0].nighttime_hotspots == 1
    assert res_day.intervals[1].hotspot_count == 0
    assert res_day.intervals[1].active_fires == 1  # cluster 1 sigue activo el 2 de marzo


def test_specific_month_and_date_range():
    session = _seed_calendar_session()
    res = _call_calendar(
        session,
        year=2025,
        start_date=date(2025, 3, 1),
        end_date=date(2025, 3, 5),
        aggregation="day",
    )
    assert res.total_hotspots == 2
    assert len(res.intervals) == 5


def test_filters_country_department_confidence_frp_satellite_cluster():
    session = _seed_calendar_session()

    # 4. Departamento no existe en esquema actual
    with pytest.raises(HTTPException) as exc_dept:
        _call_calendar(session, year=2025, department="Managua")
    assert exc_dept.value.status_code == 400

    # Country sí existe
    res_country = _call_calendar(session, year=2025, country="Honduras", aggregation="month")
    assert res_country.total_hotspots == 1

    # 5. Confianza
    res_conf = _call_calendar(session, year=2025, min_confidence=80.0, aggregation="month")
    assert res_conf.total_hotspots == 2
    assert res_conf.high_confidence_count == 2

    # 6. FRP
    res_frp = _call_calendar(session, year=2025, min_frp=40.0, max_frp=60.0, aggregation="month")
    assert res_frp.total_hotspots == 1
    assert res_frp.frp_total == 45.0

    # 7. Satélite
    res_sat = _call_calendar(session, year=2025, satellite="Suomi NPP", aggregation="month")
    assert res_sat.total_hotspots == 1
    assert res_sat.nighttime_hotspots == 1

    # 8. Cluster específico
    res_cluster = _call_calendar(session, year=2025, cluster_id=1, aggregation="day")
    assert res_cluster.total_fires == 1
    assert res_cluster.total_hotspots == 2

    with pytest.raises(HTTPException) as exc_missing:
        _call_calendar(session, year=2025, cluster_id=999)
    assert exc_missing.value.status_code == 404


def test_empty_period_and_invalid_parameters():
    session = _seed_calendar_session()

    # 10. Período sin detecciones
    res_empty = _call_calendar(session, year=2020, month=2, aggregation="day")
    assert res_empty.total_hotspots == 0
    assert res_empty.total_fires == 0
    assert len(res_empty.intervals) == 29  # 2020 bisiesto
    assert all(i.hotspot_count == 0 for i in res_empty.intervals)

    # 11. Parámetros inválidos
    with pytest.raises(HTTPException) as exc_dates:
        _call_calendar(
            session,
            year=2025,
            start_date=date(2025, 3, 10),
            end_date=date(2025, 3, 1),
        )
    assert exc_dates.value.status_code == 422

    with pytest.raises(HTTPException) as exc_frp:
        _call_calendar(session, year=2025, min_frp=100.0, max_frp=10.0)
    assert exc_frp.value.status_code == 422

    with pytest.raises(HTTPException) as exc_month:
        _call_calendar(
            session,
            year=2025,
            month=3,
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 2),
        )
    assert exc_month.value.status_code == 422

    with pytest.raises(HTTPException) as exc_dn:
        _call_calendar(session, year=2025, daynight="X")
    assert exc_dn.value.status_code == 422
