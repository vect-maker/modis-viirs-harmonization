from __future__ import annotations

from typing import Annotated, Any, Literal

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlmodel import Session

from analytics.DashboardAnalytics import classify_archive_months, compute_descriptive_stats
from database.session import get_session
from model.StarSchema import DailyActivityResponse, HistoricalCalendarResponse
from repositories.DashboardRepository import DashboardRepository
from repositories.HotspotRepository import HotspotRepository
from schemas.charts import ChartFiltersDep, ChartResponse, build_chart_response
from schemas.fire_calendar import FireCalendarQuery, FireCalendarResponse
from services.FireCalendarService import FireCalendarService

router = APIRouter(prefix="/temporal", tags=["Charts - Temporal"])


def _ratio_pct(value: float, reference: float | None) -> float | None:
    if reference is None or reference == 0.0:
        return None
    return round(((value - reference) / reference) * 100.0, 4)


@router.get(
    "/daily-activity",
    response_model=ChartResponse[DailyActivityResponse],
    summary="Conteo diario de detecciones para serie temporal",
)
def get_daily_activity(
    filters: ChartFiltersDep,
    instrument: Annotated[str | None, Query(description="Filtro por instrumento (MODIS, VIIRS)")] = None,
    session: Session = Depends(get_session),
) -> ChartResponse[DailyActivityResponse]:
    payload = HotspotRepository(session).get_daily_activity(
        start_date=filters.start_date,
        end_date=filters.end_date,
        instrument=instrument,
        polygon_wkt=filters.polygon_wkt,
    )
    coverage = (
        {
            "first_detection": payload.min_date.isoformat() if payload.min_date else None,
            "last_detection": payload.max_date.isoformat() if payload.max_date else None,
        }
        if payload.min_date or payload.max_date
        else None
    )
    return build_chart_response(
        "temporal.daily-activity",
        payload,
        filters,
        extra_filters={"instrument": instrument},
        coverage=coverage,
    )


@router.get(
    "/historical-calendar",
    response_model=ChartResponse[HistoricalCalendarResponse],
    summary="Resumen mensual histórico por instrumento para calendario",
)
def get_historical_calendar(
    filters: ChartFiltersDep,
    session: Session = Depends(get_session),
) -> ChartResponse[HistoricalCalendarResponse]:
    payload = HotspotRepository(session).get_historical_calendar()
    coverage = (
        {
            "first_detection": payload.first_detection.isoformat() if payload.first_detection else None,
            "last_detection": payload.last_detection.isoformat() if payload.last_detection else None,
        }
        if payload.first_detection or payload.last_detection
        else None
    )
    return build_chart_response(
        "temporal.historical-calendar",
        payload,
        filters,
        coverage=coverage,
    )


@router.get(
    "/fire-calendar",
    response_model=ChartResponse[FireCalendarResponse],
    summary="Estadísticas históricas de incendios agrupadas por día, semana o mes",
)
async def get_fire_calendar(
    filters: ChartFiltersDep,
    year: Annotated[int, Query(ge=1990, le=2100, description="Año que se desea consultar")],
    month: Annotated[int | None, Query(ge=1, le=12, description="Mes específico (1-12)")] = None,
    department: Annotated[str | None, Query(description="Departamento")] = None,
    municipality: Annotated[str | None, Query(description="Municipio")] = None,
    min_confidence: Annotated[float | None, Query(ge=0.0, le=100.0, description="Confianza mínima")] = None,
    confidence_class: Annotated[str | None, Query(description="Categoría de confianza")] = None,
    satellite: Annotated[str | None, Query(description="Satélite utilizado")] = None,
    instrument: Annotated[str | None, Query(description="Instrumento de detección")] = None,
    daynight: Annotated[str | None, Query(description="Detecciones diurnas ('D') o nocturnas ('N')")] = None,
    min_frp: Annotated[float | None, Query(ge=0.0, description="FRP mínimo")] = None,
    max_frp: Annotated[float | None, Query(ge=0.0, description="FRP máximo")] = None,
    cluster_id: Annotated[int | None, Query(ge=1, description="Identificador de un incendio específico")] = None,
    aggregation: Annotated[
        Literal["day", "week", "month"],
        Query(description="Tipo de agrupación: day, week o month"),
    ] = "day",
    session: Session = Depends(get_session),
) -> ChartResponse[FireCalendarResponse]:
    try:
        query = FireCalendarQuery(
            year=year,
            month=month,
            start_date=filters.start_date,
            end_date=filters.end_date,
            country=filters.country,
            department=department,
            municipality=municipality,
            min_confidence=min_confidence,
            confidence_class=confidence_class,
            satellite=satellite,
            instrument=instrument,
            daynight=daynight,
            min_frp=min_frp,
            max_frp=max_frp,
            cluster_id=cluster_id,
            polygon=filters.polygon,
            metric=filters.metric,
            aggregation=aggregation,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    payload = FireCalendarService(session).get_calendar(query)
    return build_chart_response(
        "temporal.fire-calendar",
        payload,
        filters,
        extra_filters={
            "year": year,
            "month": month,
            "aggregation": aggregation,
            "department": department,
            "municipality": municipality,
            "instrument": instrument,
        },
    )


@router.get(
    "/annual-stats",
    response_model=ChartResponse[dict[str, Any]],
    summary="Actividad anual por sensor, índice armonizado y estadísticas descriptivas",
)
async def get_annual_stats(
    filters: ChartFiltersDep,
    session: Annotated[Session, Depends(get_session)],
    high_value: Annotated[int, Query(ge=1, le=100)] = 90,
    start_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    end_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    include_distributions: Annotated[
        bool,
        Query(
            description=(
                "Incluye media, mediana, cuartiles, P90 e IQR de FRP, confianza y "
                "brillo por año. Es la parte costosa de la consulta."
            )
        ),
    ] = True,
) -> ChartResponse[dict[str, Any]]:
    filter_start_yr, filter_end_yr = filters.to_year_bounds()
    eff_start_year = start_year if start_year is not None else filter_start_yr
    eff_end_year = end_year if end_year is not None else filter_end_yr

    if eff_start_year is not None and eff_end_year is not None and eff_start_year > eff_end_year:
        raise HTTPException(
            status_code=400, detail="start_year debe ser menor o igual a end_year"
        )
    polygon_wkt = filters.polygon_wkt
    repo = DashboardRepository(session)

    coverage = repo.get_data_coverage(country=filters.country)
    if coverage is None:
        return build_chart_response(
            "temporal.annual-stats",
            {"range": None, "coverage": None, "rows": []},
            filters,
            extra_filters={
                "high_value": high_value,
                "include_distributions": include_distributions,
            },
        )
    first_dt, last_dt = coverage
    lo = max(eff_start_year if eff_start_year is not None else first_dt.year, first_dt.year)
    hi = min(eff_end_year if eff_end_year is not None else last_dt.year, last_dt.year)
    coverage_info = {
        "first_detection": first_dt.date().isoformat(),
        "last_detection": last_dt.date().isoformat(),
    }
    if lo > hi:
        return build_chart_response(
            "temporal.annual-stats",
            {"range": None, "coverage": coverage_info, "rows": []},
            filters,
            extra_filters={
                "high_value": high_value,
                "include_distributions": include_distributions,
            },
            coverage=coverage_info,
        )

    totals = repo.get_annual_totals(
        lo, hi, country=filters.country, polygon_wkt=polygon_wkt
    )
    distributions: dict[int, dict[str, Any]] = {}
    if include_distributions:
        distributions = {
            int(r["year"]): r
            for r in repo.get_annual_stats(
                high_value=high_value,
                start_year=lo,
                end_year=hi,
                country=filters.country,
                polygon_wkt=polygon_wkt,
                metric=filters.metric,
            )
        }

    archive = classify_archive_months(repo.get_archive_months(country=filters.country))
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

    return build_chart_response(
        "temporal.annual-stats",
        {
            "range": {"start_year": lo, "end_year": hi},
            "coverage": coverage_info,
            "rows": rows,
        },
        filters,
        extra_filters={
            "high_value": high_value,
            "start_year": lo,
            "end_year": hi,
            "include_distributions": include_distributions,
        },
        coverage=coverage_info,
    )


@router.get(
    "/monthly-comparison",
    response_model=ChartResponse[dict[str, Any]],
    summary="Serie mensual de un año vs línea base histórica (media, mediana, std, z-score)",
)
async def get_monthly_comparison(
    filters: ChartFiltersDep,
    session: Annotated[Session, Depends(get_session)],
    year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    start_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    end_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
) -> ChartResponse[dict[str, Any]]:
    filter_start_yr, filter_end_yr = filters.to_year_bounds()
    eff_start_year = start_year if start_year is not None else filter_start_yr
    eff_end_year = end_year if end_year is not None else filter_end_yr

    if eff_start_year is not None and eff_end_year is not None and eff_start_year > eff_end_year:
        raise HTTPException(
            status_code=400, detail="start_year debe ser menor o igual a end_year"
        )
    polygon_wkt = filters.polygon_wkt
    repo = DashboardRepository(session)

    empty = {
        "year": year,
        "metric": filters.metric,
        "available_years": [],
        "baseline_years": [],
        "coverage": None,
        "months": [],
    }
    coverage = repo.get_data_coverage(country=filters.country)
    if coverage is None:
        return build_chart_response(
            "temporal.monthly-comparison",
            empty,
            filters,
            extra_filters={"year": year},
        )
    first_dt, last_dt = coverage
    archive = classify_archive_months(repo.get_archive_months(country=filters.country))

    lo = max(eff_start_year if eff_start_year is not None else first_dt.year, first_dt.year)
    hi = min(eff_end_year if eff_end_year is not None else last_dt.year, last_dt.year)
    coverage_info = {
        "first_detection": first_dt.date().isoformat(),
        "last_detection": last_dt.date().isoformat(),
    }
    if lo > hi:
        return build_chart_response(
            "temporal.monthly-comparison",
            empty,
            filters,
            extra_filters={"year": year},
            coverage=coverage_info,
        )
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
        metric=filters.metric,
        country=filters.country,
        polygon_wkt=polygon_wkt,
    )
    lookup: dict[tuple[int, int], dict[str, Any]] = {
        (int(r["year"]), int(r["month"])): r for r in monthly
    }

    def comparable(y: int, m: int) -> bool:
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
        can_compare = not is_partial and not (
            is_provisional and filters.metric == "harmonized"
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

    return build_chart_response(
        "temporal.monthly-comparison",
        {
            "year": target_year,
            "metric": filters.metric,
            "available_years": available_years,
            "baseline_years": baseline_years,
            "coverage": coverage_info,
            "months": comparison,
        },
        filters,
        extra_filters={"year": target_year, "start_year": lo, "end_year": hi},
        coverage=coverage_info,
    )
