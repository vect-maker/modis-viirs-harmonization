from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from api.clusters import router as clusters_router
from database.session import get_session
from model import ClusterHotspots, FireCluster, Hotspots
from model.ClusterStatus import ClusterStatus


def _create_test_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[
            FireCluster.__table__,  # type: ignore[attr-defined]
            Hotspots.__table__,  # type: ignore[attr-defined]
            ClusterHotspots.__table__,  # type: ignore[attr-defined]
        ],
    )
    session = Session(engine)

    app = FastAPI()
    app.include_router(clusters_router)

    def _override_session():
        yield session

    app.dependency_overrides[get_session] = _override_session
    return TestClient(app), session


def test_clusters_geojson_filters_by_bbox_and_min_hotspots():
    client, session = _create_test_client()

    c1 = FireCluster(
        id=1,
        polygon=2.45,
        area_km2=2.45,
        status=ClusterStatus.ACTIVO,
        datetimeStart=datetime(2025, 4, 1, 10, 0, tzinfo=timezone.utc),
        datetimeEnd=datetime(2025, 4, 1, 18, 0, tzinfo=timezone.utc),
        maxFrp=85.2,
        total_frp=210.5,
        harmonized_weight=14.2,
        centroid_lat=12.15,
        centroid_lon=-86.25,
        hotspot_count=12,
        modis_count=3,
        viirs_count=9,
    )
    c2 = FireCluster(
        id=2,
        polygon=0.12,
        area_km2=0.12,
        status=ClusterStatus.FINALIZADO,
        datetimeStart=datetime(2025, 4, 2, 8, 0, tzinfo=timezone.utc),
        datetimeEnd=datetime(2025, 4, 2, 9, 0, tzinfo=timezone.utc),
        maxFrp=12.0,
        total_frp=12.0,
        harmonized_weight=1.0,
        centroid_lat=14.60,
        centroid_lon=-87.50,
        hotspot_count=1,
        modis_count=0,
        viirs_count=1,
    )
    session.add_all([c1, c2])
    session.commit()

    # Query with bbox covering Managua (c1) only
    resp = client.get("/clusters/geojson?bbox=-86.5,11.9,-86.0,12.4&min_hotspots=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    feat = data["features"][0]
    assert feat["properties"]["id"] == 1
    assert feat["properties"]["hotspot_count"] == 12
    assert feat["properties"]["modis_count"] == 3
    assert feat["properties"]["viirs_count"] == 9
    assert feat["properties"]["area_km2"] == 2.45
    assert feat["properties"]["duration_h"] == 8.0

    # POST /clusters/geojson with min_hotspots=1 returns both
    resp_post = client.post("/clusters/geojson", json={"min_hotspots": 1})
    assert resp_post.status_code == 200
    assert len(resp_post.json()["features"]) == 2


def test_cluster_detail_returns_joined_hotspots():
    client, session = _create_test_client()

    hs_id_1 = uuid4()
    hs_id_2 = uuid4()
    c1 = FireCluster(
        id=10,
        polygon=1.5,
        area_km2=1.5,
        status=ClusterStatus.ACTIVO,
        centroid_lat=12.10,
        centroid_lon=-86.20,
        hotspot_count=2,
        modis_count=1,
        viirs_count=1,
    )
    h1 = Hotspots(
        id=hs_id_1,
        country="Nicaragua",
        latitude=12.10,
        longitude=-86.20,
        acq_datetime=datetime(2025, 4, 1, 12, 0, tzinfo=timezone.utc),
        instrument="MODIS",
        satellite="Terra",
        frp=40.0,
    )
    h2 = Hotspots(
        id=hs_id_2,
        country="Nicaragua",
        latitude=12.102,
        longitude=-86.201,
        acq_datetime=datetime(2025, 4, 1, 13, 0, tzinfo=timezone.utc),
        instrument="VIIRS",
        satellite="SNPP",
        frp=22.0,
    )
    session.add_all([c1, h1, h2])
    session.commit()
    session.add_all([
        ClusterHotspots(clusterId=10, hotspotsId=hs_id_1),
        ClusterHotspots(clusterId=10, hotspotsId=hs_id_2),
    ])
    session.commit()

    resp = client.get("/clusters/10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["data"]["cluster"]["id"] == 10
    instruments = {h["instrument"] for h in body["data"]["hotspots"]}
    assert instruments == {"MODIS", "VIIRS"}
