from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlmodel import Session

from database.session import get_session
from schemas.fire_calendar import FireCalendarQuery, FireCalendarResponse
from services.FireCalendarService import FireCalendarService

router = APIRouter(tags=["FireCalendar"])


@router.get(
    "/fire-calendar",
    response_model=FireCalendarResponse,
    summary="Estadísticas históricas de incendios agrupadas por día, semana o mes",
)
async def get_fire_calendar(
    year: Annotated[int, Query(ge=1990, le=2100, description="Año que se desea consultar")],
    month: Annotated[int | None, Query(ge=1, le=12, description="Mes específico (1-12)")] = None,
    start_date: Annotated[date | None, Query(description="Fecha inicial del período")] = None,
    end_date: Annotated[date | None, Query(description="Fecha final del período")] = None,
    country: Annotated[str | None, Query(description="País")] = None,
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
    polygon: Annotated[
        str | None,
        Query(description="GeoJSON Polygon o MultiPolygon (EPSG:4326) serializado"),
    ] = None,
    metric: Annotated[
        Literal["raw", "harmonized"],
        Query(description="Métrica de conteo y FRP: raw o harmonized"),
    ] = "raw",
    aggregation: Annotated[
        Literal["day", "week", "month"],
        Query(description="Tipo de agrupación: day, week o month"),
    ] = "day",
    session: Session = Depends(get_session),
):
    try:
        query = FireCalendarQuery(
            year=year,
            month=month,
            start_date=start_date,
            end_date=end_date,
            country=country,
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
            polygon=polygon,
            metric=metric,
            aggregation=aggregation,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    service = FireCalendarService(session)
    return service.get_calendar(query)
