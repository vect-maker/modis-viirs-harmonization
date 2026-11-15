from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from api.fire_calendar import get_fire_calendar
from api.hotspots import get_hotspots
from model import FireCluster
from repositories.spatial_filter import SpatialAreaFilter, build_spatial_sql


def _run_coro(coro):
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


def test_postgis_sql_generation_uses_geom_and_postgis_functions():
    area = SpatialAreaFilter(
        min_lat=11.0,
        max_lat=13.0,
        min_lon=-87.0,
        max_lon=-85.0,
        center_lat=12.1,
        center_lon=-86.2,
        radius_km=15.0,
        polygon_wkt="POLYGON((-86.3 12.0, -86.1 12.0, -86.1 12.2, -86.3 12.2, -86.3 12.0))",
    )
    conds, params = build_spatial_sql(area, dialect="postgresql")
    joined = " AND ".join(conds)
    assert "ST_MakeEnvelope" in joined
    assert "ST_DWithin" in joined
    assert "ST_MakePoint" in joined
    assert "ST_Intersects" in joined
    assert "ST_GeomFromText" in joined
    assert params["sp_radius_m"] == 15000.0


def test_spatial_filter_validation_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        SpatialAreaFilter(min_lat=15.0, max_lat=10.0).validate()

    with pytest.raises(ValueError):
        SpatialAreaFilter(center_lat=12.1, center_lon=-86.2).validate()

    with pytest.raises(ValueError):
        SpatialAreaFilter(polygon_wkt="POINT(-86.2 12.1)").validate()


def test_hotspots_and_calendar_area_filtering():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine, tables=[FireCluster.__table__])  # type: ignore[attr-defined]
    session = Session(engine)
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
    # Punto dentro de Managua (12.1, -86.2) y punto lejano en Honduras (14.5, -87.5)
    for lat, lon, country in [
        (12.10, -86.20, "Nicaragua"),
        (14.50, -87.50, "Honduras"),
    ]:
        session.execute(
            text(
                """
                INSERT INTO hotspots (id, country, latitude, longitude, acq_datetime, frp, daynight)
                VALUES (:id, :country, :lat, :lon, :dt, 25.0, 'D')
                """
            ),
            {
                "id": str(uuid4()),
                "country": country,
                "lat": lat,
                "lon": lon,
                "dt": datetime(2025, 3, 15, 12, 0, 0),
            },
        )
    session.commit()

    # 1. GET /hotspots/ por radio
    res_hs = _run_coro(
        get_hotspots(
            limit=50,
            offset=0,
            min_lat=None,
            max_lat=None,
            min_lon=None,
            max_lon=None,
            center_lat=12.10,
            center_lon=-86.20,
            radius_km=20.0,
            polygon_wkt=None,
            session=session,
        )
    )
    assert len(res_hs["data"]) == 1
    assert res_hs["data"][0]["latitude"] == 12.10

    # 2. GET /fire-calendar por polígono WKT
    res_cal = _run_coro(
        get_fire_calendar(
            year=2025,
            month=3,
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
            polygon_wkt="POLYGON((-86.5 11.9, -85.9 11.9, -85.9 12.3, -86.5 12.3, -86.5 11.9))",
            aggregation="month",
            session=session,
        )
    )
    assert res_cal.total_hotspots == 1

    # 3. Validación HTTP 400 en /hotspots/ con radio incompleto
    with pytest.raises(HTTPException) as exc:
        _run_coro(
            get_hotspots(
                limit=50,
                offset=0,
                min_lat=None,
                max_lat=None,
                min_lon=None,
                max_lon=None,
                center_lat=12.1,
                center_lon=None,
                radius_km=10.0,
                polygon_wkt=None,
                session=session,
            )
        )
    assert exc.value.status_code == 400
