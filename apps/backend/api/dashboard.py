from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from analytics.DashboardAnalytics import (
    compute_descriptive_stats,
    run_confidence_dbscan,
    run_monthly_seasonal_forecast,
    run_spatial_isolation_forest,
)
from database.session import get_session
from repositories.DashboardRepository import DashboardRepository
from repositories.spatial_filter import parse_geojson_polygon_to_wkt

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/confidence-dbscan",
    summary="Detección de anomalías en confidence con DBSCAN sobre valores únicos SQL",
)
async def get_confidence_dbscan(
    eps: float = Query(default=5.0, gt=0.0),
    min_samples: int = Query(default=2, ge=1),
    high_value: int = Query(default=90, ge=1, le=100),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    session: Session = Depends(get_session),
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date no puede ser posterior a end_date"
        )
    repo = DashboardRepository(session)
    unique_counts = repo.get_confidence_value_counts(
        high_value=high_value,
        start_date=start_date,
        end_date=end_date,
    )
    return run_confidence_dbscan(unique_counts, eps=eps, min_samples=min_samples)


@router.get(
    "/correlations",
    summary="Matriz de correlaciones Pearson y R² calculada directamente en SQL",
)
async def get_correlations(
    high_value: int = Query(default=90, ge=1, le=100),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    session: Session = Depends(get_session),
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date no puede ser posterior a end_date"
        )
    repo = DashboardRepository(session)
    pairs = repo.get_correlations(
        high_value=high_value,
        start_date=start_date,
        end_date=end_date,
    )
    return {"data": pairs}


@router.get(
    "/annual-stats",
    summary="Estadísticas descriptivas anuales (media, std, mediana, cuartiles, P90, IQR)",
)
async def get_annual_stats(
    high_value: int = Query(default=85, ge=1, le=100),
    start_year: int = Query(default=2001, ge=1990, le=2100),
    end_year: int = Query(default=2025, ge=1990, le=2100),
    session: Session = Depends(get_session),
):
    if start_year > end_year:
        raise HTTPException(
            status_code=400, detail="start_year debe ser menor o igual a end_year"
        )
    repo = DashboardRepository(session)
    rows = repo.get_annual_stats(
        high_value=high_value,
        start_year=start_year,
        end_year=end_year,
    )
    return {
        "range": {"start_year": start_year, "end_year": end_year},
        "data": rows,
    }


@router.get(
    "/spatial-density",
    summary="Mapa de densidad espacial por celdas (alternativa SQL a hexbin)",
)
async def get_spatial_density(
    cell_size_deg: float = Query(default=0.1, gt=0.001, le=5.0),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_lat: float | None = Query(default=None, ge=-90.0, le=90.0),
    max_lat: float | None = Query(default=None, ge=-90.0, le=90.0),
    min_lon: float | None = Query(default=None, ge=-180.0, le=180.0),
    max_lon: float | None = Query(default=None, ge=-180.0, le=180.0),
    limit: int = Query(default=5000, ge=1, le=20000),
    session: Session = Depends(get_session),
):
    repo = DashboardRepository(session)
    cells = repo.get_spatial_density(
        cell_size_deg=cell_size_deg,
        start_date=start_date,
        end_date=end_date,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        limit=limit,
    )
    counts = np.array([c["count"] for c in cells], dtype=np.float64)
    return {
        "summary": {
            "cell_size_deg": cell_size_deg,
            "total_cells": len(cells),
            "total_hotspots": int(np.sum(counts)) if counts.size > 0 else 0,
            "cell_count_stats": compute_descriptive_stats(counts),
        },
        "data": cells,
    }


def _ratio_pct(value: float, reference: float | None) -> float | None:
    if reference is None or reference == 0.0:
        return None
    return round(((value - reference) / reference) * 100.0, 4)


@router.get(
    "/monthly-comparison",
    summary="Serie mensual de un año vs línea base histórica (media, mediana, std, z-score)",
)
async def get_monthly_comparison(
    session: Annotated[Session, Depends(get_session)],
    year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    start_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    end_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    metric: Annotated[
        Literal["raw", "harmonized"],
        Query(
            description=(
                "raw: detecciones crudas MODIS+VIIRS. harmonized: suma de "
                "harmonized_weight (índice armonizado con VIIRS como referencia)."
            )
        ),
    ] = "raw",
    country: Annotated[str | None, Query(max_length=100)] = None,
    polygon: Annotated[
        str | None,
        Query(description="GeoJSON Polygon o MultiPolygon (EPSG:4326) serializado"),
    ] = None,
):
    """
    Compara cada mes del año elegido contra la línea base de los demás años.

    - La línea base excluye el año comparado (evita que el año se compare consigo mismo).
    - Dentro del rango del archivo, un mes sin detecciones en el área cuenta como 0.
    - Los meses fuera del archivo (p. ej. meses futuros del año en curso) son `null`.
    """
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(
            status_code=400, detail="start_year debe ser menor o igual a end_year"
        )
    polygon_wkt = parse_geojson_polygon_to_wkt(polygon)
    repo = DashboardRepository(session)

    empty = {
        "year": year,
        "metric": metric,
        "available_years": [],
        "baseline_years": [],
        "coverage": None,
        "months": [],
    }
    coverage = repo.get_data_coverage(country=country)
    if coverage is None:
        return empty
    first_dt, last_dt = coverage
    first_key = (first_dt.year, first_dt.month)
    last_key = (last_dt.year, last_dt.month)

    lo = max(start_year if start_year is not None else first_dt.year, first_dt.year)
    hi = min(end_year if end_year is not None else last_dt.year, last_dt.year)
    if lo > hi:
        return empty
    available_years = list(range(lo, hi + 1))
    target_year = year if year is not None else hi
    if target_year not in available_years:
        raise HTTPException(
            status_code=400,
            detail=f"year debe estar entre {lo} y {hi} (rango con datos)",
        )
    baseline_years = [y for y in available_years if y != target_year]

    monthly = repo.get_monthly_counts(
        start_year=lo,
        end_year=hi,
        metric=metric,
        country=country,
        polygon_wkt=polygon_wkt,
    )
    lookup: dict[tuple[int, int], dict[str, Any]] = {
        (int(r["year"]), int(r["month"])): r for r in monthly
    }

    def in_archive(y: int, m: int) -> bool:
        return first_key <= (y, m) <= last_key

    comparison: list[dict[str, Any]] = []
    for m in range(1, 13):
        baseline = np.array(
            [
                float(lookup[(y, m)]["value"]) if (y, m) in lookup else 0.0
                for y in baseline_years
                if in_archive(y, m)
            ],
            dtype=np.float64,
        )
        hist = compute_descriptive_stats(baseline)
        hist_mean = hist["mean"]
        hist_median = hist["median"]
        hist_std = hist["std"]

        yr_row = lookup.get((target_year, m))
        has_data = in_archive(target_year, m)
        yr_value: float | None = (
            (float(yr_row["value"]) if yr_row is not None else 0.0)
            if has_data
            else None
        )

        anomaly_abs = anomaly_pct = anomaly_pct_median = z_score = None
        if yr_value is not None and hist_mean is not None:
            anomaly_abs = round(yr_value - float(hist_mean), 4)
            anomaly_pct = _ratio_pct(yr_value, float(hist_mean))
            anomaly_pct_median = _ratio_pct(
                yr_value, float(hist_median) if hist_median is not None else None
            )
            if hist_std not in (None, 0.0):
                z_score = round((yr_value - float(hist_mean)) / float(hist_std), 4)

        comparison.append(
            {
                "month": m,
                "has_data": has_data,
                "year_count": yr_value,
                "year_raw_count": (
                    int(yr_row["count"])
                    if yr_row is not None
                    else (0 if has_data else None)
                ),
                "year_sum_frp": yr_row["sum_frp"] if yr_row is not None else None,
                "year_avg_frp": yr_row["avg_frp"] if yr_row is not None else None,
                "historic": hist,
                "anomaly_abs": anomaly_abs,
                "anomaly_pct": anomaly_pct,
                "anomaly_pct_median": anomaly_pct_median,
                "z_score": z_score,
            }
        )

    return {
        "year": target_year,
        "metric": metric,
        "available_years": available_years,
        "baseline_years": baseline_years,
        "coverage": {
            "first_detection": first_dt.date().isoformat(),
            "last_detection": last_dt.date().isoformat(),
        },
        "months": comparison,
    }


@router.get(
    "/spatial-anomalies",
    summary="Detección de anomalías espaciales con IsolationForest sobre SQL",
)
async def get_spatial_anomalies(
    n_estimators: int = Query(default=300, ge=50, le=500),
    contamination: float | None = Query(default=None, gt=0.0, lt=0.5),
    random_state: int = Query(default=42),
    max_rows: int = Query(default=20000, ge=10, le=100000),
    max_points_returned: int = Query(default=5000, ge=10, le=20000),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_lat: float | None = Query(default=None, ge=-90.0, le=90.0),
    max_lat: float | None = Query(default=None, ge=-90.0, le=90.0),
    min_lon: float | None = Query(default=None, ge=-180.0, le=180.0),
    max_lon: float | None = Query(default=None, ge=-180.0, le=180.0),
    session: Session = Depends(get_session),
):
    repo = DashboardRepository(session)
    coords, ids, frps, datetimes = repo.fetch_spatial_points(
        start_date=start_date,
        end_date=end_date,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        max_rows=max_rows,
    )
    contam_val: float | Literal["auto"] = (
        contamination if contamination is not None else "auto"
    )
    return run_spatial_isolation_forest(
        coords=coords,
        ids=ids,
        frps=frps,
        datetimes=datetimes,
        n_estimators=n_estimators,
        contamination=contam_val,
        random_state=random_state,
        max_points_returned=max_points_returned,
    )


@router.get(
    "/monthly-forecast",
    summary="Pronóstico estacional mensual con intervalos de confianza y métricas de error",
)
async def get_monthly_forecast(
    train_ratio: float = Query(default=0.8, gt=0.5, lt=0.95),
    future_months: int = Query(default=6, ge=1, le=24),
    start_year: int | None = Query(default=None, ge=1990, le=2100),
    end_year: int | None = Query(default=None, ge=1990, le=2100),
    session: Session = Depends(get_session),
):
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(
            status_code=400, detail="start_year debe ser menor o igual a end_year"
        )
    repo = DashboardRepository(session)
    monthly = repo.get_monthly_counts(start_year=start_year, end_year=end_year)
    if len(monthly) < 18:
        raise HTTPException(
            status_code=400,
            detail="Se requieren al menos 18 meses de datos para generar el pronóstico estacional",
        )

    months = [str(r["month_key"]) for r in monthly]
    counts = [int(r["count"]) for r in monthly]
    try:
        return run_monthly_seasonal_forecast(
            months=months,
            counts=counts,
            train_ratio=train_ratio,
            future_months=future_months,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
