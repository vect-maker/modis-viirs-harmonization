from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import Session, SQLModel, create_engine

from api.dashboard import (
    get_annual_stats,
    get_confidence_dbscan,
    get_correlations,
    get_monthly_comparison,
    get_monthly_forecast,
    get_spatial_anomalies,
    get_spatial_density,
)
from model import Hotspots


def _run_coro(coro):
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


def _seed_session() -> Session:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine, tables=[Hotspots.__table__])  # type: ignore[attr-defined]
    session = Session(engine)

    # 24 meses de datos (2023-2024) con tendencia y estacionalidad + algunos valores atípicos
    records: list[Hotspots] = []
    for yr in (2023, 2024):
        for mo in range(1, 13):
            count = 2 + (mo % 4) + (1 if yr == 2024 else 0)
            for k in range(count):
                conf = "l" if k == 0 and mo == 1 else ("h" if k % 2 == 0 else "n")
                if yr == 2024 and mo == 12 and k == 0:
                    conf = "5"  # valor aislado para DBSCAN
                lat = 12.10 + (k * 0.01)
                lon = -86.20 + (k * 0.01)
                if yr == 2024 and mo == 6 and k == 0:
                    lat, lon = 14.95, -83.10  # anomalía espacial
                records.append(
                    Hotspots(
                        id=uuid4(),
                        latitude=lat,
                        longitude=lon,
                        bright_mir=310.0 + k * 5.0 + mo,
                        bright_tir=290.0 + k * 2.0 + (mo * 0.5),
                        frp=10.0 + k * 8.0 + mo,
                        confidence=conf,
                        acq_datetime=datetime(
                            yr, mo, min(28, 1 + k * 3), 10, 0, 0, tzinfo=UTC
                        ),
                    )
                )
    session.add_all(records)
    session.commit()
    return session


def test_dashboard_confidence_dbscan_and_correlations():
    session = _seed_session()
    dbscan_res = _run_coro(
        get_confidence_dbscan(
            eps=5.0,
            min_samples=2,
            high_value=90,
            start_date=None,
            end_date=None,
            session=session,
        )
    )
    assert dbscan_res["summary"]["total_rows"] > 0
    assert dbscan_res["summary"]["anomaly_rows"] >= 1
    assert any(p["confidence"] == 5 and p["is_anomaly"] for p in dbscan_res["points"])

    corr_res = _run_coro(
        get_correlations(
            high_value=90,
            start_date=None,
            end_date=None,
            session=session,
        )
    )
    assert len(corr_res["data"]) == 6
    frp_tir = next(
        p for p in corr_res["data"] if p["x"] == "frp" and p["y"] == "bright_tir"
    )
    assert frp_tir["n"] > 0
    assert frp_tir["pearson_r"] is not None
    assert frp_tir["r2"] is not None


def test_dashboard_annual_stats_and_spatial_density():
    session = _seed_session()
    annual = _run_coro(
        get_annual_stats(
            high_value=85,
            start_year=2023,
            end_year=2024,
            session=session,
        )
    )
    assert len(annual["data"]) == 2
    assert annual["data"][0]["year"] == 2023
    assert annual["data"][0]["frp"]["p50"] if "p50" in annual["data"][0]["frp"] else True
    assert annual["data"][0]["frp"]["median"] is not None
    assert annual["data"][0]["frp"]["iqr"] is not None
    assert annual["data"][0]["frp"]["p90"] is not None

    density = _run_coro(
        get_spatial_density(
            cell_size_deg=0.1,
            start_date=None,
            end_date=None,
            min_lat=None,
            max_lat=None,
            min_lon=None,
            max_lon=None,
            limit=5000,
            session=session,
        )
    )
    assert density["summary"]["total_cells"] >= 1
    assert density["summary"]["total_hotspots"] > 0
    assert density["data"][0]["count"] >= 1


def test_dashboard_monthly_comparison_anomalies_and_forecast():
    session = _seed_session()
    comp = _run_coro(
        get_monthly_comparison(
            year=2024,
            start_year=2023,
            end_year=2024,
            session=session,
        )
    )
    assert comp["year"] == 2024
    assert len(comp["months"]) == 12
    assert comp["months"][0]["historic"]["mean"] is not None

    anom = _run_coro(
        get_spatial_anomalies(
            n_estimators=100,
            contamination=None,
            random_state=42,
            max_rows=5000,
            max_points_returned=500,
            start_date=None,
            end_date=None,
            min_lat=None,
            max_lat=None,
            min_lon=None,
            max_lon=None,
            session=session,
        )
    )
    assert anom["summary"]["total_points"] > 0
    assert anom["summary"]["anomaly_count"] >= 1
    assert "score_stats" in anom["summary"]

    forecast = _run_coro(
        get_monthly_forecast(
            train_ratio=0.8,
            future_months=3,
            start_year=2023,
            end_year=2024,
            session=session,
        )
    )
    assert "metrics" in forecast
    assert forecast["metrics"]["mae"] >= 0.0
    assert forecast["metrics"]["rmse"] >= 0.0
    assert "smape_pct" in forecast["metrics"]
    assert len(forecast["future"]) == 3
