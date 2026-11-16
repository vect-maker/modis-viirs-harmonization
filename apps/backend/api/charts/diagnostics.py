from __future__ import annotations

from typing import Annotated, Any, Literal

import numpy as np
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from analytics.DashboardAnalytics import (
    compute_descriptive_stats,
    run_spatial_isolation_forest,
)
from database.session import get_session
from repositories.DashboardRepository import DashboardRepository
from schemas.charts import ChartFiltersDep, ChartResponse, build_chart_response

router = APIRouter(prefix="/diagnostics", tags=["Charts - Diagnostics"])


@router.get(
    "/correlations",
    response_model=ChartResponse[list[dict[str, Any]]],
    summary="Matriz de correlaciones Pearson y R² calculada directamente en SQL",
)
async def get_correlations(
    filters: ChartFiltersDep,
    high_value: Annotated[int, Query(ge=1, le=100)] = 90,
    session: Session = Depends(get_session),
) -> ChartResponse[list[dict[str, Any]]]:
    start_dt, end_dt = filters.to_datetime_bounds()
    repo = DashboardRepository(session)
    pairs = repo.get_correlations(
        high_value=high_value,
        start_date=start_dt,
        end_date=end_dt,
        country=filters.country,
        polygon_wkt=filters.polygon_wkt,
        metric=filters.metric,
    )
    return build_chart_response(
        "diagnostics.correlations",
        pairs,
        filters,
        extra_filters={"high_value": high_value},
    )


@router.get(
    "/spatial-density",
    response_model=ChartResponse[dict[str, Any]],
    summary="Mapa de densidad espacial por celdas (alternativa SQL a hexbin)",
)
async def get_spatial_density(
    filters: ChartFiltersDep,
    cell_size_deg: Annotated[float, Query(gt=0.001, le=5.0)] = 0.1,
    min_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    max_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    min_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    max_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    limit: Annotated[int, Query(ge=1, le=20000)] = 5000,
    session: Session = Depends(get_session),
) -> ChartResponse[dict[str, Any]]:
    start_dt, end_dt = filters.to_datetime_bounds()
    repo = DashboardRepository(session)
    cells, total_cells_all, total_hotspots_all = repo.get_spatial_density_with_totals(
        cell_size_deg=cell_size_deg,
        start_date=start_dt,
        end_date=end_dt,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        limit=limit,
        country=filters.country,
        polygon_wkt=filters.polygon_wkt,
        metric=filters.metric,
    )
    counts = np.array([c["count"] for c in cells], dtype=np.float64)
    payload = {
        "summary": {
            "cell_size_deg": cell_size_deg,
            "total_cells": len(cells),
            "total_cells_all": total_cells_all,
            "total_hotspots": total_hotspots_all,
            "cell_count_stats": compute_descriptive_stats(counts),
        },
        "cells": cells,
    }
    return build_chart_response(
        "diagnostics.spatial-density",
        payload,
        filters,
        extra_filters={
            "cell_size_deg": cell_size_deg,
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon,
            "limit": limit,
        },
    )


@router.get(
    "/spatial-anomalies",
    response_model=ChartResponse[dict[str, Any]],
    summary="Detección de anomalías espaciales con IsolationForest sobre SQL",
)
async def get_spatial_anomalies(
    filters: ChartFiltersDep,
    n_estimators: Annotated[int, Query(ge=50, le=500)] = 300,
    contamination: Annotated[float | None, Query(gt=0.0, lt=0.5)] = None,
    random_state: Annotated[int, Query()] = 42,
    max_rows: Annotated[int, Query(ge=10, le=100000)] = 20000,
    max_points_returned: Annotated[int, Query(ge=10, le=20000)] = 5000,
    min_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    max_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    min_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    max_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    session: Session = Depends(get_session),
) -> ChartResponse[dict[str, Any]]:
    start_dt, end_dt = filters.to_datetime_bounds()
    repo = DashboardRepository(session)
    coords, ids, frps, datetimes = repo.fetch_spatial_points(
        start_date=start_dt,
        end_date=end_dt,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        max_rows=max_rows,
        country=filters.country,
        polygon_wkt=filters.polygon_wkt,
    )
    contam_val: float | Literal["auto"] = (
        contamination if contamination is not None else "auto"
    )
    payload = run_spatial_isolation_forest(
        coords=coords,
        ids=ids,
        frps=frps,
        datetimes=datetimes,
        n_estimators=n_estimators,
        contamination=contam_val,
        random_state=random_state,
        max_points_returned=max_points_returned,
    )
    return build_chart_response(
        "diagnostics.spatial-anomalies",
        payload,
        filters,
        extra_filters={
            "n_estimators": n_estimators,
            "contamination": contamination,
            "max_rows": max_rows,
            "max_points_returned": max_points_returned,
        },
    )
