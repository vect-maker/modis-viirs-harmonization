from __future__ import annotations

from datetime import date
from typing import Literal

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
    year: int = Query(..., ge=1990, le=2100, description="Año que se desea consultar"),
    month: int | None = Query(default=None, ge=1, le=12, description="Mes específico (1-12)"),
    start_date: date | None = Query(default=None, description="Fecha inicial del período"),
    end_date: date | None = Query(default=None, description="Fecha final del período"),
    country: str | None = Query(default=None, description="País"),
    department: str | None = Query(default=None, description="Departamento"),
    municipality: str | None = Query(default=None, description="Municipio"),
    min_confidence: float | None = Query(default=None, ge=0.0, le=100.0, description="Confianza mínima"),
    confidence_class: str | None = Query(default=None, description="Categoría de confianza"),
    satellite: str | None = Query(default=None, description="Satélite utilizado"),
    instrument: str | None = Query(default=None, description="Instrumento de detección"),
    daynight: str | None = Query(default=None, description="Detecciones diurnas ('D') o nocturnas ('N')"),
    min_frp: float | None = Query(default=None, ge=0.0, description="FRP mínimo"),
    max_frp: float | None = Query(default=None, ge=0.0, description="FRP máximo"),
    cluster_id: int | None = Query(default=None, ge=1, description="Identificador de un incendio específico"),
    aggregation: Literal["day", "week", "month"] = Query(
        default="day", description="Tipo de agrupación: day, week o month"
    ),
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
            aggregation=aggregation,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    service = FireCalendarService(session)
    return service.get_calendar(query)
