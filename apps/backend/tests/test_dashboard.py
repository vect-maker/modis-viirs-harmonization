from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session, SQLModel, create_engine

from api.charts.diagnostics import (
    get_confidence_dbscan,
    get_correlations,
    get_spatial_anomalies,
    get_spatial_density,
)
from api.charts.models import get_monthly_forecast
from api.charts.temporal import get_annual_stats, get_monthly_comparison
from model import Hotspots
from schemas.charts import ChartFilterParams


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
    dbscan_resp = _run_coro(
        get_confidence_dbscan(
            filters=ChartFilterParams(),
            eps=5.0,
            min_samples=2,
            high_value=90,
            session=session,
        )
    )
    assert dbscan_resp.chart == "diagnostics.confidence-dbscan"
    dbscan_res = dbscan_resp.data
    assert dbscan_res["summary"]["total_rows"] > 0
    assert dbscan_res["summary"]["anomaly_rows"] >= 1
    assert any(p["confidence"] == 5 and p["is_anomaly"] for p in dbscan_res["points"])

    corr_resp = _run_coro(
        get_correlations(
            filters=ChartFilterParams(),
            high_value=90,
            session=session,
        )
    )
    assert corr_resp.chart == "diagnostics.correlations"
    assert len(corr_resp.data) == 6
    frp_tir = next(
        p for p in corr_resp.data if p["x"] == "frp" and p["y"] == "bright_tir"
    )
    assert frp_tir["n"] > 0
    assert frp_tir["pearson_r"] is not None
    assert frp_tir["r2"] is not None


def test_dashboard_annual_stats_and_spatial_density():
    session = _seed_session()
    annual_resp = _run_coro(
        get_annual_stats(
            filters=ChartFilterParams(),
            high_value=85,
            start_year=2023,
            end_year=2024,
            session=session,
        )
    )
    assert annual_resp.chart == "temporal.annual-stats"
    annual = annual_resp.data
    assert len(annual["rows"]) == 2
    assert annual["rows"][0]["year"] == 2023
    assert annual["rows"][0]["frp"]["p50"] if "p50" in annual["rows"][0]["frp"] else True
    assert annual["rows"][0]["frp"]["median"] is not None
    assert annual["rows"][0]["frp"]["iqr"] is not None
    assert annual["rows"][0]["frp"]["p90"] is not None

    density_resp = _run_coro(
        get_spatial_density(
            filters=ChartFilterParams(),
            cell_size_deg=0.1,
            min_lat=None,
            max_lat=None,
            min_lon=None,
            max_lon=None,
            limit=5000,
            session=session,
        )
    )
    assert density_resp.chart == "diagnostics.spatial-density"
    density = density_resp.data
    assert density["summary"]["total_cells"] >= 1
    assert density["summary"]["total_hotspots"] > 0
    assert density["cells"][0]["count"] >= 1


def test_dashboard_monthly_comparison_anomalies_and_forecast():
    session = _seed_session()
    comp_resp = _run_coro(
        get_monthly_comparison(
            filters=ChartFilterParams(),
            year=2024,
            start_year=2023,
            end_year=2024,
            session=session,
        )
    )
    comp = comp_resp.data
    assert comp["year"] == 2024
    assert len(comp["months"]) == 12
    assert comp["months"][0]["historic"]["mean"] is not None

    anom_resp = _run_coro(
        get_spatial_anomalies(
            filters=ChartFilterParams(),
            n_estimators=100,
            contamination=None,
            random_state=42,
            max_rows=5000,
            max_points_returned=500,
            min_lat=None,
            max_lat=None,
            min_lon=None,
            max_lon=None,
            session=session,
        )
    )
    anom = anom_resp.data
    assert anom["summary"]["total_points"] > 0
    assert anom["summary"]["anomaly_count"] >= 1
    assert "score_stats" in anom["summary"]

    forecast_resp = _run_coro(
        get_monthly_forecast(
            filters=ChartFilterParams(),
            train_ratio=0.8,
            future_months=3,
            start_year=2023,
            end_year=2024,
            session=session,
        )
    )
    forecast = forecast_resp.data
    assert "metrics" in forecast
    assert forecast["metrics"]["mae"] >= 0.0
    assert forecast["metrics"]["rmse"] >= 0.0
    assert "smape_pct" in forecast["metrics"]
    assert len(forecast["future"]) == 3


def _seed_comparison_session() -> Session:
    """
    2022 y 2023 completos, 2024 solo hasta marzo. Marzo 2023 sin detecciones.
    Cada MODIS pesa 2.0 y cada VIIRS 1.0 en harmonized_weight.
    """
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine, tables=[Hotspots.__table__])  # type: ignore[attr-defined]
    session = Session(engine)
    records: list[Hotspots] = []

    def add(yr: int, mo: int, n: int, instrument: str, lat: float = 12.1) -> None:
        for k in range(n):
            records.append(
                Hotspots(
                    id=uuid4(),
                    country="Nicaragua",
                    latitude=lat,
                    longitude=-86.2,
                    frp=10.0,
                    instrument=instrument,
                    harmonized_weight=2.0 if instrument == "MODIS" else 1.0,
                    acq_datetime=datetime(yr, mo, 1 + k, 10, 0, 0, tzinfo=UTC),
                )
            )

    for yr, n in ((2022, 4), (2023, 6)):
        for mo in range(1, 13):
            if (yr, mo) != (2023, 3):
                add(yr, mo, n, "MODIS")
    for mo in (1, 2, 3):
        add(2024, mo, 10, "VIIRS")
    add(2024, 1, 3, "VIIRS", lat=14.9)  # fuera del polígono de prueba
    session.add_all(records)
    session.commit()
    return session


def test_monthly_comparison_baseline_excludes_target_and_fills_gaps():
    session = _seed_comparison_session()
    comp = _run_coro(
        get_monthly_comparison(filters=ChartFilterParams(), session=session, year=2024)
    ).data

    assert comp["year"] == 2024
    assert comp["baseline_years"] == [2022, 2023]
    assert comp["coverage"] == {
        "first_detection": "2022-01-01",
        "last_detection": "2024-03-10",
    }
    jan, feb, mar, apr = comp["months"][:4]

    assert jan["year_count"] == 13.0
    assert jan["historic"]["median"] == 5.0
    assert jan["anomaly_pct_median"] == 160.0

    assert mar["historic"]["count"] == 1
    assert mar["archive_state"] == "partial"
    assert mar["anomaly_pct_median"] is None
    assert jan["archive_state"] == "full"

    assert apr["has_data"] is False
    assert apr["year_count"] is None
    assert apr["anomaly_pct"] is None
    assert feb["has_data"] is True


def test_monthly_comparison_harmonized_metric_and_polygon():
    session = _seed_comparison_session()
    harmonized = _run_coro(
        get_monthly_comparison(
            filters=ChartFilterParams(metric="harmonized"),
            session=session,
            year=2023,
        )
    ).data
    jan = harmonized["months"][0]
    assert harmonized["metric"] == "harmonized"
    assert jan["year_count"] == 12.0
    assert jan["year_raw_count"] == 6
    assert jan["historic"]["median"] == 10.5

    polygon = (
        '{"type":"Polygon","coordinates":[[[-87,11],[-85,11],[-85,13],[-87,13],[-87,11]]]}'
    )
    clipped = _run_coro(
        get_monthly_comparison(
            filters=ChartFilterParams(polygon=polygon),
            session=session,
            year=2024,
        )
    ).data
    assert clipped["months"][0]["year_count"] == 10.0


def test_monthly_comparison_rejects_year_outside_archive():
    session = _seed_comparison_session()
    try:
        _run_coro(
            get_monthly_comparison(filters=ChartFilterParams(), session=session, year=2030)
        )
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("Se esperaba HTTPException")


def test_annual_stats_sensor_totals_partial_years_and_polygon():
    session = _seed_comparison_session()
    annual = _run_coro(
        get_annual_stats(
            filters=ChartFilterParams(), session=session, include_distributions=False
        )
    ).data

    assert annual["range"] == {"start_year": 2022, "end_year": 2024}
    by_year = {row["year"]: row for row in annual["rows"]}
    assert by_year[2022]["modis_count"] == 48
    assert by_year[2022]["harmonized_index"] == 96.0
    assert by_year[2023]["total_hotspots"] == 66
    assert by_year[2024]["viirs_count"] == 33
    assert by_year[2024]["months_in_archive"] == 2
    assert by_year[2023]["months_in_archive"] == 10
    assert by_year[2024]["complete"] is False
    assert by_year[2022]["complete"] is True
    assert "frp" not in by_year[2022]

    polygon = (
        '{"type":"Polygon","coordinates":[[[-87,11],[-85,11],[-85,13],[-87,13],[-87,11]]]}'
    )
    clipped = _run_coro(
        get_annual_stats(
            filters=ChartFilterParams(polygon=polygon),
            session=session,
            start_year=2024,
        )
    ).data
    row = clipped["rows"][0]
    assert clipped["range"] == {"start_year": 2024, "end_year": 2024}
    assert row["total_hotspots"] == 30
    assert row["frp"]["median"] == 10.0


def test_monthly_comparison_marks_gaps_and_near_real_time_months():
    """Datos del worker (CATCHUP_*) tras un hueco: provisionales y fuera de la base."""
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine, tables=[Hotspots.__table__])  # type: ignore[attr-defined]
    session = Session(engine)

    def add(yr: int, mo: int, days: range, category: str, weight: float) -> None:
        session.add_all(
            Hotspots(
                id=uuid4(),
                latitude=12.1,
                longitude=-86.2,
                instrument="VIIRS",
                harmonization_category=category,
                harmonized_weight=weight,
                acq_datetime=datetime(yr, mo, d, 10, 0, 0, tzinfo=UTC),
            )
            for d in days
        )

    for yr in (2021, 2022, 2023):
        for mo in range(1, 13):
            add(yr, mo, range(1, 29), "BOTH_VIIRS_MODIS", 0.5)
    add(2024, 3, range(20, 32), "CATCHUP_VIIRS_SNPP_SP", 1.0)
    add(2024, 4, range(1, 31), "CATCHUP_VIIRS_SNPP_SP", 1.0)
    add(2024, 5, range(1, 16), "NRT_VIIRS_SNPP_NRT", 1.0)
    session.commit()

    comp = _run_coro(
        get_monthly_comparison(filters=ChartFilterParams(), session=session, year=2024)
    ).data
    jan, _, mar, apr, may = comp["months"][:5]
    assert jan["archive_state"] == "missing" and jan["year_count"] is None
    assert mar["archive_state"] == "partial" and mar["provisional"] is True
    assert apr["archive_state"] == "full" and apr["provisional"] is True
    assert apr["anomaly_pct_median"] is not None
    assert may["archive_state"] == "partial"
    assert apr["historic"]["count"] == 3

    harmonized = _run_coro(
        get_monthly_comparison(
            filters=ChartFilterParams(metric="harmonized"),
            session=session,
            year=2024,
        )
    ).data
    assert harmonized["months"][3]["anomaly_pct_median"] is None

    annual = _run_coro(
        get_annual_stats(
            filters=ChartFilterParams(), session=session, include_distributions=False
        )
    ).data
    row_2024 = {r["year"]: r for r in annual["rows"]}[2024]
    assert row_2024["months_in_archive"] == 1
    assert row_2024["provisional_months"] == 3
    assert row_2024["complete"] is False


def test_dashboard_polygon_harmonized_and_pre_limit_totals():
    session = _seed_comparison_session()
    polygon = (
        '{"type":"Polygon","coordinates":[[[-87,11],[-85,11],[-85,13],[-87,13],[-87,11]]]}'
    )

    density_raw = _run_coro(
        get_spatial_density(
            filters=ChartFilterParams(polygon=polygon, metric="raw"),
            cell_size_deg=0.1,
            limit=1,
            session=session,
        )
    ).data
    assert len(density_raw["cells"]) == 1
    assert density_raw["summary"]["total_hotspots"] == 144

    density_harm = _run_coro(
        get_spatial_density(
            filters=ChartFilterParams(polygon=polygon, metric="harmonized"),
            cell_size_deg=0.1,
            limit=1,
            session=session,
        )
    ).data
    assert density_harm["summary"]["total_hotspots"] == 258

    forecast = _run_coro(
        get_monthly_forecast(
            filters=ChartFilterParams(polygon=polygon, metric="harmonized"),
            train_ratio=0.8,
            future_months=3,
            session=session,
        )
    ).data
    assert forecast["metrics"]["total_months"] == 27
    assert len(forecast["future"]) == 3
    assert forecast["future"][0]["month"] == "2024-04"
