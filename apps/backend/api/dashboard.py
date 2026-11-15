from __future__ import annotations

import calendar
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
    eps: Annotated[float, Query(gt=0.0)] = 5.0,
    min_samples: Annotated[int, Query(ge=1)] = 2,
    high_value: Annotated[int, Query(ge=1, le=100)] = 90,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    country: Annotated[str | None, Query(max_length=100)] = None,
    polygon: Annotated[
        str | None,
        Query(description="GeoJSON Polygon o MultiPolygon (EPSG:4326) serializado"),
    ] = None,
    metric: Annotated[Literal["raw", "harmonized"], Query()] = "raw",
    session: Session = Depends(get_session),
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date no puede ser posterior a end_date"
        )
    polygon_wkt = parse_geojson_polygon_to_wkt(polygon)
    repo = DashboardRepository(session)
    unique_counts = repo.get_confidence_value_counts(
        high_value=high_value,
        start_date=start_date,
        end_date=end_date,
        country=country,
        polygon_wkt=polygon_wkt,
        metric=metric,
    )
    return run_confidence_dbscan(unique_counts, eps=eps, min_samples=min_samples)


@router.get(
    "/correlations",
    summary="Matriz de correlaciones Pearson y R² calculada directamente en SQL",
)
async def get_correlations(
    high_value: Annotated[int, Query(ge=1, le=100)] = 90,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    country: Annotated[str | None, Query(max_length=100)] = None,
    polygon: Annotated[
        str | None,
        Query(description="GeoJSON Polygon o MultiPolygon (EPSG:4326) serializado"),
    ] = None,
    metric: Annotated[Literal["raw", "harmonized"], Query()] = "raw",
    session: Session = Depends(get_session),
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date no puede ser posterior a end_date"
        )
    polygon_wkt = parse_geojson_polygon_to_wkt(polygon)
    repo = DashboardRepository(session)
    pairs = repo.get_correlations(
        high_value=high_value,
        start_date=start_date,
        end_date=end_date,
        country=country,
        polygon_wkt=polygon_wkt,
        metric=metric,
    )
    return {"data": pairs}


@router.get(
    "/annual-stats",
    summary="Actividad anual por sensor, índice armonizado y estadísticas descriptivas",
)
async def get_annual_stats(
    session: Annotated[Session, Depends(get_session)],
    high_value: Annotated[int, Query(ge=1, le=100)] = 90,
    start_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    end_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    country: Annotated[str | None, Query(max_length=100)] = None,
    polygon: Annotated[
        str | None,
        Query(description="GeoJSON Polygon o MultiPolygon (EPSG:4326) serializado"),
    ] = None,
    metric: Annotated[
        Literal["raw", "harmonized"],
        Query(description="raw: FRP crudo; harmonized: usa harmonized_frp y omite duplicados MODIS-VIIRS"),
    ] = "raw",
    include_distributions: Annotated[
        bool,
        Query(
            description=(
                "Incluye media, mediana, cuartiles, P90 e IQR de FRP, confianza y "
                "brillo por año. Es la parte costosa de la consulta."
            )
        ),
    ] = True,
):
    """
    Una fila por año dentro del archivo (sin filtro espacial), también los años
    sin detecciones en el área elegida. `months_in_archive` < 12 marca un año
    incompleto (inicio o fin del registro), que no debe leerse como una caída.
    """
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(
            status_code=400, detail="start_year debe ser menor o igual a end_year"
        )
    polygon_wkt = parse_geojson_polygon_to_wkt(polygon)
    repo = DashboardRepository(session)

    coverage = repo.get_data_coverage(country=country)
    if coverage is None:
        return {"range": None, "coverage": None, "data": []}
    first_dt, last_dt = coverage
    lo = max(start_year if start_year is not None else first_dt.year, first_dt.year)
    hi = min(end_year if end_year is not None else last_dt.year, last_dt.year)
    coverage_info = {
        "first_detection": first_dt.date().isoformat(),
        "last_detection": last_dt.date().isoformat(),
    }
    if lo > hi:
        return {"range": None, "coverage": coverage_info, "data": []}

    totals = repo.get_annual_totals(lo, hi, country=country, polygon_wkt=polygon_wkt)
    distributions: dict[int, dict[str, Any]] = {}
    if include_distributions:
        distributions = {
            int(r["year"]): r
            for r in repo.get_annual_stats(
                high_value=high_value,
                start_year=lo,
                end_year=hi,
                country=country,
                polygon_wkt=polygon_wkt,
                metric=metric,
            )
        }

    archive = classify_archive_months(repo.get_archive_months(country=country))
    rows: list[dict[str, Any]] = []
    for y in range(lo, hi + 1):
        year_states = [archive.get((y, m)) for m in range(1, 13)]
        months_in_archive = sum(
            1 for st in year_states if st is not None and st["state"] == "full"
        )
        provisional_months = sum(
            1 for st in year_states if st is not None and st["provisional"]
        )
        t = totals.get(y)
        row: dict[str, Any] = {
            "year": y,
            "months_in_archive": months_in_archive,
            "complete": months_in_archive == 12,
            "provisional_months": provisional_months,
            "total_hotspots": t["total"] if t else 0,
            "modis_count": t["modis"] if t else 0,
            "viirs_count": t["viirs"] if t else 0,
            "harmonized_index": t["harmonized"] if t else 0.0,
            "avg_frp": t["avg_frp"] if t else None,
        }
        if include_distributions:
            d = distributions.get(y)
            for key in ("frp", "confidence", "bright_tir", "bright_mir"):
                row[key] = d[key] if d else None
        rows.append(row)

    return {
        "range": {"start_year": lo, "end_year": hi},
        "coverage": coverage_info,
        "data": rows,
    }


@router.get(
    "/spatial-density",
    summary="Mapa de densidad espacial por celdas (alternativa SQL a hexbin)",
)
async def get_spatial_density(
    cell_size_deg: Annotated[float, Query(gt=0.001, le=5.0)] = 0.1,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    max_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    min_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    max_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    limit: Annotated[int, Query(ge=1, le=20000)] = 5000,
    country: Annotated[str | None, Query(max_length=100)] = None,
    polygon: Annotated[
        str | None,
        Query(description="GeoJSON Polygon o MultiPolygon (EPSG:4326) serializado"),
    ] = None,
    metric: Annotated[Literal["raw", "harmonized"], Query()] = "raw",
    session: Session = Depends(get_session),
):
    polygon_wkt = parse_geojson_polygon_to_wkt(polygon)
    repo = DashboardRepository(session)
    cells, total_cells_all, total_hotspots_all = repo.get_spatial_density_with_totals(
        cell_size_deg=cell_size_deg,
        start_date=start_date,
        end_date=end_date,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        limit=limit,
        country=country,
        polygon_wkt=polygon_wkt,
        metric=metric,
    )
    counts = np.array([c["count"] for c in cells], dtype=np.float64)
    return {
        "summary": {
            "cell_size_deg": cell_size_deg,
            "total_cells": len(cells),
            "total_cells_all": total_cells_all,
            "total_hotspots": total_hotspots_all,
            "cell_count_stats": compute_descriptive_stats(counts),
        },
        "data": cells,
    }


def _month_neighbors(y: int, m: int) -> tuple[tuple[int, int], tuple[int, int]]:
    prev_key = (y, m - 1) if m > 1 else (y - 1, 12)
    next_key = (y, m + 1) if m < 12 else (y + 1, 1)
    return prev_key, next_key


def classify_archive_months(
    info: dict[tuple[int, int], dict[str, Any]],
) -> dict[tuple[int, int], dict[str, Any]]:
    """
    Estado de cada mes con datos en el archivo:
    - partial: abre o cierra un tramo de datos y le faltan días (p. ej. el mes en
      curso, o el primer mes tras un hueco). No es comparable con meses completos.
    - provisional: más de la mitad de las filas vienen del feed casi en tiempo
      real del worker, que todavía no pasa por la armonización.
    Los meses que no aparecen son huecos de datos (no ceros).
    """
    states: dict[tuple[int, int], dict[str, Any]] = {}
    for (y, m), row in info.items():
        days_in_month = calendar.monthrange(y, m)[1]
        prev_key, next_key = _month_neighbors(y, m)
        starts_run = prev_key not in info
        ends_run = next_key not in info
        partial = (starts_run and row["first_day"] > 3) or (
            ends_run and row["last_day"] < days_in_month - 2
        )
        states[(y, m)] = {
            "state": "partial" if partial else "full",
            "provisional": row["total"] > 0 and row["nrt_rows"] / row["total"] > 0.5,
            "first_day": row["first_day"],
            "last_day": row["last_day"],
            "days_in_month": days_in_month,
        }
    return states


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

    - La línea base excluye el año comparado (no se compara consigo mismo).
    - Un mes con datos en el archivo pero sin detecciones en el área cuenta como 0.
    - Un mes sin datos en todo el archivo es un hueco: `archive_state="missing"`.
    - Los meses parciales o provisionales (feed del worker sin armonizar) no
      entran en la línea base; los parciales tampoco se clasifican.
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
    archive = classify_archive_months(repo.get_archive_months(country=country))

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

    def comparable(y: int, m: int) -> bool:
        """Mes completo y armonizado: apto para la línea base."""
        state = archive.get((y, m))
        return (
            state is not None
            and state["state"] == "full"
            and not state["provisional"]
        )

    comparison: list[dict[str, Any]] = []
    for m in range(1, 13):
        baseline = np.array(
            [
                float(lookup[(y, m)]["value"]) if (y, m) in lookup else 0.0
                for y in baseline_years
                if comparable(y, m)
            ],
            dtype=np.float64,
        )
        hist = compute_descriptive_stats(baseline)
        hist_mean = hist["mean"]
        hist_median = hist["median"]
        hist_std = hist["std"]

        yr_row = lookup.get((target_year, m))
        month_state = archive.get((target_year, m))
        has_data = month_state is not None
        is_partial = has_data and month_state["state"] == "partial"
        is_provisional = has_data and bool(month_state["provisional"])
        yr_value: float | None = (
            (float(yr_row["value"]) if yr_row is not None else 0.0)
            if has_data
            else None
        )
        # Un mes parcial no se compara con meses completos; un mes provisional
        # no tiene pesos armonizados, así que solo se compara en modo crudo.
        can_compare = not is_partial and not (
            is_provisional and metric == "harmonized"
        )

        anomaly_abs = anomaly_pct = anomaly_pct_median = z_score = None
        if yr_value is not None and hist_mean is not None and can_compare:
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
                "archive_state": (
                    "missing" if not has_data else month_state["state"]
                ),
                "provisional": is_provisional,
                "days_with_data": (
                    [month_state["first_day"], month_state["last_day"]]
                    if has_data
                    else None
                ),
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
    n_estimators: Annotated[int, Query(ge=50, le=500)] = 300,
    contamination: Annotated[float | None, Query(gt=0.0, lt=0.5)] = None,
    random_state: Annotated[int, Query()] = 42,
    max_rows: Annotated[int, Query(ge=10, le=100000)] = 20000,
    max_points_returned: Annotated[int, Query(ge=10, le=20000)] = 5000,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    max_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    min_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    max_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    country: Annotated[str | None, Query(max_length=100)] = None,
    polygon: Annotated[
        str | None,
        Query(description="GeoJSON Polygon o MultiPolygon (EPSG:4326) serializado"),
    ] = None,
    session: Session = Depends(get_session),
):
    polygon_wkt = parse_geojson_polygon_to_wkt(polygon)
    repo = DashboardRepository(session)
    coords, ids, frps, datetimes = repo.fetch_spatial_points(
        start_date=start_date,
        end_date=end_date,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        max_rows=max_rows,
        country=country,
        polygon_wkt=polygon_wkt,
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
    train_ratio: Annotated[float, Query(gt=0.5, lt=0.95)] = 0.8,
    future_months: Annotated[int, Query(ge=1, le=24)] = 6,
    start_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    end_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    metric: Annotated[Literal["raw", "harmonized"], Query()] = "raw",
    country: Annotated[str | None, Query(max_length=100)] = None,
    polygon: Annotated[
        str | None,
        Query(description="GeoJSON Polygon o MultiPolygon (EPSG:4326) serializado"),
    ] = None,
    session: Session = Depends(get_session),
):
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(
            status_code=400, detail="start_year debe ser menor o igual a end_year"
        )
    polygon_wkt = parse_geojson_polygon_to_wkt(polygon)
    repo = DashboardRepository(session)
    monthly = repo.get_monthly_counts(
        start_year=start_year,
        end_year=end_year,
        metric=metric,
        country=country,
        polygon_wkt=polygon_wkt,
    )
    if len(monthly) < 18:
        raise HTTPException(
            status_code=400,
            detail="Se requieren al menos 18 meses de datos para generar el pronóstico estacional",
        )

    months = [str(r["month_key"]) for r in monthly]
    counts = [float(r["value"]) for r in monthly]
    try:
        return run_monthly_seasonal_forecast(
            months=months,
            counts=counts,
            train_ratio=train_ratio,
            future_months=future_months,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
