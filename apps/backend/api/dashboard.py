from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

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


@router.get(
    "/monthly-comparison",
    summary="Serie mensual de un año vs línea base histórica (media, mediana, std, z-score)",
)
async def get_monthly_comparison(
    year: int | None = Query(default=None, ge=1990, le=2100),
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
    if not monthly:
        return {"year": year, "available_years": [], "months": []}

    available_years = sorted({int(r["year"]) for r in monthly})
    target_year = year if year is not None else available_years[-1]

    by_month_num: dict[int, list[int]] = {m: [] for m in range(1, 13)}
    year_lookup: dict[int, dict[str, Any]] = {}
    for r in monthly:
        m = int(r["month"])
        by_month_num[m].append(int(r["count"]))
        if int(r["year"]) == target_year:
            year_lookup[m] = r

    comparison: list[dict[str, Any]] = []
    for m in range(1, 13):
        vals = np.array(by_month_num[m], dtype=np.float64)
        hist = compute_descriptive_stats(vals)
        hist_mean = hist["mean"]
        hist_std = hist["std"]
        yr_row = year_lookup.get(m)
        yr_count = int(yr_row["count"]) if yr_row is not None else 0

        anomaly_abs = (
            round(yr_count - float(hist_mean), 4) if hist_mean is not None else None
        )
        anomaly_pct = (
            round(((yr_count - float(hist_mean)) / float(hist_mean)) * 100.0, 4)
            if hist_mean not in (None, 0.0)
            else None
        )
        z_score = (
            round((yr_count - float(hist_mean)) / float(hist_std), 4)
            if hist_mean is not None and hist_std not in (None, 0.0)
            else None
        )

        comparison.append(
            {
                "month": m,
                "year_count": yr_count,
                "year_sum_frp": yr_row["sum_frp"] if yr_row is not None else 0.0,
                "year_avg_frp": yr_row["avg_frp"] if yr_row is not None else None,
                "historic": hist,
                "anomaly_abs": anomaly_abs,
                "anomaly_pct": anomaly_pct,
                "z_score": z_score,
            }
        )

    return {
        "year": target_year,
        "available_years": available_years,
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
