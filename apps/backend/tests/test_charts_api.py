from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from database.session import get_session
from main import app
from model import Hotspots


EXPECTED_CHART_ROUTES = {
    ("GET", "/charts/temporal/daily-activity"),
    ("GET", "/charts/temporal/historical-calendar"),
    ("GET", "/charts/temporal/fire-calendar"),
    ("GET", "/charts/temporal/annual-stats"),
    ("GET", "/charts/temporal/monthly-comparison"),
    ("GET", "/charts/diagnostics/correlations"),
    ("GET", "/charts/diagnostics/spatial-density"),
    ("GET", "/charts/diagnostics/spatial-anomalies"),
    ("GET", "/charts/models/weather-correlation"),
}

REMOVED_LEGACY_ROUTES = {
    "/dashboard/confidence-dbscan",
    "/dashboard/correlations",
    "/dashboard/annual-stats",
    "/dashboard/spatial-density",
    "/dashboard/monthly-comparison",
    "/dashboard/spatial-anomalies",
    "/dashboard/monthly-forecast",
    "/hotspots/daily-activity",
    "/hotspots/historical-calendar",
    "/fire-calendar",
    "/analysis/cluster-movement",
    "/analysis/weather-correlation",
    "/analysis/predict",
}


def test_charts_routes_registered_and_legacy_removed():
    paths = app.openapi()["paths"]
    registered = {
        (method.upper(), path)
        for path, ops in paths.items()
        for method in ops
        if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }
    assert EXPECTED_CHART_ROUTES.issubset(registered)
    registered_paths = set(paths.keys())
    assert REMOVED_LEGACY_ROUTES.isdisjoint(registered_paths)


def test_charts_http_envelope_and_shared_filters():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine, tables=[Hotspots.__table__])  # type: ignore[attr-defined]
    with Session(engine) as session:
        session.add(
            Hotspots(
                id=uuid4(),
                latitude=12.1,
                longitude=-86.2,
                frp=25.0,
                bright_mir=315.0,
                bright_tir=295.0,
                confidence="90",
                instrument="MODIS",
                harmonized_weight=2.0,
                acq_datetime=datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC),
            )
        )
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)

        resp = client.get(
            "/charts/temporal/annual-stats?include_distributions=false&metric=harmonized"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["chart"] == "temporal.annual-stats"
        assert body["meta"]["metric"] == "harmonized"
        assert "generated_at" in body["meta"]
        assert body["data"]["rows"][0]["year"] == 2024
        assert body["data"]["rows"][0]["harmonized_index"] == 2.0

        corr = client.get(
            "/charts/diagnostics/correlations?start_date=2024-01-01&end_date=2024-12-31"
        )
        assert corr.status_code == 200
        corr_body = corr.json()
        assert corr_body["chart"] == "diagnostics.correlations"
        assert corr_body["meta"]["filters"]["start_date"] == "2024-01-01"
        assert corr_body["meta"]["filters"]["end_date"] == "2024-12-31"
        assert isinstance(corr_body["data"], list)

        bad_dates = client.get(
            "/charts/diagnostics/correlations?start_date=2025-01-01&end_date=2024-01-01"
        )
        assert bad_dates.status_code == 400
    finally:
        app.dependency_overrides.clear()
