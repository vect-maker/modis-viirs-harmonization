from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from database.session import get_session
from main import app
from middleware.ChartCacheMiddleware import ChartCacheMiddleware
from model import Hotspots
from services.ChartCacheService import (
    ChartCacheService,
    build_chart_cache_key,
    chart_cache,
    resolve_chart_bucket,
)


@pytest.fixture(autouse=True)
def _clear_global_chart_cache():
    chart_cache.clear()
    yield
    chart_cache.clear()


def test_resolve_chart_bucket_and_key_canonicalization():
    assert resolve_chart_bucket("/charts/temporal/daily-activity") == "temporal"
    assert resolve_chart_bucket("/api/charts/diagnostics/correlations") is None
    assert resolve_chart_bucket("/charts/models/weather-correlation") == "models"
    assert resolve_chart_bucket("/hotspots") is None

    k1 = build_chart_cache_key(
        "/charts/temporal/annual-stats",
        [("metric", "raw"), ("country", "Guatemala")],
    )
    k2 = build_chart_cache_key(
        "/charts/temporal/annual-stats",
        [("country", "Guatemala"), ("metric", "raw")],
    )
    k3 = build_chart_cache_key(
        "/charts/temporal/annual-stats",
        [("country", "Guatemala"), ("metric", "harmonized")],
    )
    assert k1 == k2
    assert k1 != k3


def test_chart_cache_hit_miss_and_bypass_on_error():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine, tables=[Hotspots.__table__])  # type: ignore[attr-defined]

    with Session(engine) as seed_session:
        seed_session.add(
            Hotspots(
                id=uuid4(),
                latitude=15.1,
                longitude=-90.1,
                acq_datetime=datetime(2024, 4, 15, 12, 0, tzinfo=UTC),
                instrument="VIIRS",
                frp=18.5,
                bright_mir=325.0,
                bright_tir=295.0,
                confidence="90",
                harmonized_weight=1.0,
            )
        )
        seed_session.commit()

    session_calls = 0

    def override_get_session():
        nonlocal session_calls
        session_calls += 1
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)
        first = client.get(
            "/charts/temporal/annual-stats",
            params={"include_distributions": "false", "metric": "raw"},
        )
        assert first.status_code == 200
        assert first.headers["x-cache"] == "MISS"
        assert session_calls == 1

        # Reordered query params must hit the same cached entry without DB access.
        second = client.get(
            "/charts/temporal/annual-stats?metric=raw&include_distributions=false"
        )
        assert second.status_code == 200
        assert second.headers["x-cache"] == "HIT"
        assert second.json() == first.json()
        assert session_calls == 1

        # Invalid date range (400) must bypass caching.
        invalid = client.get(
            "/charts/temporal/fire-calendar",
            params={"year": "2024", "start_date": "2024-05-01", "end_date": "2024-04-01"},
        )
        assert invalid.status_code == 400
        assert invalid.headers["x-cache"] == "BYPASS"
    finally:
        app.dependency_overrides.clear()


def test_chart_cache_ttl_expiration():
    short_cache = ChartCacheService(
        max_capacity=16,
        ttls={"temporal": 0.05, "models": 0.05},
    )
    mini_app = FastAPI()
    mini_app.add_middleware(ChartCacheMiddleware, cache=short_cache)

    calls = 0

    @mini_app.get("/charts/temporal/ping")
    async def ping():
        nonlocal calls
        calls += 1
        return {"calls": calls}

    with TestClient(mini_app) as client:
        r1 = client.get("/charts/temporal/ping")
        assert r1.status_code == 200
        assert r1.headers["x-cache"] == "MISS"
        assert r1.json() == {"calls": 1}

        r2 = client.get("/charts/temporal/ping")
        assert r2.headers["x-cache"] == "HIT"
        assert r2.json() == {"calls": 1}

        time.sleep(0.1)

        r3 = client.get("/charts/temporal/ping")
        assert r3.headers["x-cache"] == "MISS"
        assert r3.json() == {"calls": 2}
