from __future__ import annotations

import json
from datetime import date, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlmodel import Session, SQLModel, create_engine

from main import get_hotspot_daily_activity, get_hotspots
from model.StarSchema import DimCountry, DimPlatform, FactHotspot
from repositories.HotspotRepository import HotspotRepository
from repositories.spatial_filter import (
    SpatialAreaFilter,
    build_spatial_sql,
    parse_geojson_polygon_to_wkt,
)
from schemas.pagination import PaginationParams


def test_parse_geojson_polygon_to_wkt_valid_and_invalid():
    polygon_geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [-86.5, 11.9],
                [-85.9, 11.9],
                [-85.9, 12.3],
                [-86.5, 12.3],
                [-86.5, 11.9],
            ]
        ],
    }
    wkt = parse_geojson_polygon_to_wkt(json.dumps(polygon_geojson))
    assert wkt is not None
    assert wkt.startswith("POLYGON")

    multipolygon_geojson = {
        "type": "MultiPolygon",
        "coordinates": [polygon_geojson["coordinates"]],
    }
    mwkt = parse_geojson_polygon_to_wkt(multipolygon_geojson)
    assert mwkt is not None
    assert mwkt.startswith("MULTIPOLYGON")

    assert parse_geojson_polygon_to_wkt(None) is None
    assert parse_geojson_polygon_to_wkt("   ") is None

    with pytest.raises(ValueError):
        parse_geojson_polygon_to_wkt("{invalid json")

    with pytest.raises(ValueError):
        parse_geojson_polygon_to_wkt({"type": "Point", "coordinates": [-86.2, 12.1]})

    # Self-intersecting bowtie polygon
    with pytest.raises(ValueError):
        parse_geojson_polygon_to_wkt(
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [0.0, 0.0],
                        [2.0, 2.0],
                        [2.0, 0.0],
                        [0.0, 2.0],
                        [0.0, 0.0],
                    ]
                ],
            }
        )


def test_postgis_sql_uses_fact_hotspots_geom():
    wkt = (
        "POLYGON ((-86.5 11.9, -85.9 11.9, -85.9 12.3, "
        "-86.5 12.3, -86.5 11.9))"
    )
    conds, params = build_spatial_sql(
        SpatialAreaFilter(polygon_wkt=wkt),
        dialect="postgresql",
        geom_col="fact_hotspots.geom",
        lat_col="fact_hotspots.latitude",
        lon_col="fact_hotspots.longitude",
    )
    assert conds == [
        "ST_Intersects(fact_hotspots.geom, ST_GeomFromText(:sp_polygon_wkt, 4326))"
    ]
    assert "sp_polygon_wkt" in params


def test_hotspots_and_daily_activity_geojson_polygon_filtering():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(
        engine,
        tables=[DimCountry.__table__, DimPlatform.__table__, FactHotspot.__table__],  # type: ignore[attr-defined]
    )
    session = Session(engine)

    country_id = uuid4()
    platform_id = uuid4()
    session.add(DimCountry(id=country_id, name="Nicaragua"))
    session.add(DimPlatform(id=platform_id, satellite="Aqua", instrument="MODIS"))

    # Inside polygon (-86.5..-85.9, 11.9..12.3)
    session.add(
        FactHotspot(
            id=uuid4(),
            country_id=country_id,
            platform_id=platform_id,
            latitude=12.10,
            longitude=-86.20,
            acq_datetime=datetime(2025, 12, 10, 12, 0, 0),
            frp=10.5,
        )
    )
    # Outside polygon
    session.add(
        FactHotspot(
            id=uuid4(),
            country_id=country_id,
            platform_id=platform_id,
            latitude=14.50,
            longitude=-87.50,
            acq_datetime=datetime(2025, 12, 10, 14, 0, 0),
            frp=20.0,
        )
    )
    session.commit()

    polygon_str = json.dumps(
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [-86.5, 11.9],
                    [-85.9, 11.9],
                    [-85.9, 12.3],
                    [-86.5, 12.3],
                    [-86.5, 11.9],
                ]
            ],
        }
    )

    repo = HotspotRepository(session)
    wkt = parse_geojson_polygon_to_wkt(polygon_str)
    page = repo.get_hotspots(
        PaginationParams(limit=50, offset=0),
        start_date=date(2025, 12, 10),
        end_date=date(2025, 12, 10),
        polygon_wkt=wkt,
    )
    assert page.total == 1
    assert len(page.data) == 1
    assert page.data[0].latitude == pytest.approx(12.10)

    # Endpoint wrappers
    ep_page = get_hotspots(
        session=session,
        pagination=PaginationParams(limit=50, offset=0),
        start_date=date(2025, 12, 10),
        end_date=date(2025, 12, 10),
        polygon=polygon_str,
    )
    assert ep_page.total == 1

    daily = get_hotspot_daily_activity(
        session=session,
        start_date=date(2025, 12, 10),
        end_date=date(2025, 12, 10),
        instrument="MODIS",
        polygon=polygon_str,
    )
    assert len(daily.days) == 1
    assert daily.days[0].count == 1

    with pytest.raises(HTTPException) as exc_info:
        get_hotspots(
            session=session,
            pagination=PaginationParams(limit=50, offset=0),
            polygon='{"type":"Point","coordinates":[-86.2,12.1]}',
        )
    assert exc_info.value.status_code == 422
