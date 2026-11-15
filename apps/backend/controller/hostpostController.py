from enum import StrEnum
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlmodel import Session

try:
    from apps.backend.database.session import get_session
    from apps.backend.repositories.HotspotRepository import HotspotRepository
except ImportError:
    from database.session import get_session
    from repositories.HotspotRepository import HotspotRepository


class SatelliteFilter(StrEnum):
    MODIS = "MODIS"
    VIIRS = "VIIRS"


class HotspotResponse(BaseModel):
    id: UUID | str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    acq_datetime: str | None = None
    instrument: str | None = None
    satellite: str | None = None
    confidence_class: str | None = None
    confidence: Any = None
    frp: float | None = None
    bright_mir: float | None = None
    bright_tir: float | None = None
    scan: float | None = None
    track: float | None = None
    daynight: str | None = None
    version: str | None = None
    type: int | str | None = None


router = APIRouter(
    prefix="/hostpost",
    tags=["Hostpost"],
)


@router.get("/", response_model=list[HotspotResponse])
async def get_hotspots(
    satellite_type: SatelliteFilter | None = Query(
        None,
        description="Filtro opcional por satélite/sensor ('MODIS' o 'VIIRS')",
    ),
    offset: int = Query(0, ge=0, description="Offset de paginación"),
    limit: int = Query(50, ge=1, le=5000, description="Límite de registros"),
    session: Session = Depends(get_session),
):
    repository = HotspotRepository(session)
    return repository.get_hotspots(
        satellite_type=satellite_type.value if satellite_type else None,
        offset=offset,
        limit=limit,
    )


@router.get("/satellite/{satellite_type}", response_model=list[HotspotResponse])
async def get_hotspots_by_satellite(
    satellite_type: SatelliteFilter = Path(
        ...,
        description="Tipo de satélite o sensor ('MODIS' o 'VIIRS')",
    ),
    start_date: str | None = Query(
        None,
        description="Fecha inicial opcional (ej. '2024-05-01')",
    ),
    end_date: str | None = Query(
        None,
        description="Fecha final opcional (ej. '2024-05-31')",
    ),
    offset: int = Query(0, ge=0, description="Offset de paginación"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de registros"),
    session: Session = Depends(get_session),
):
    repository = HotspotRepository(session)
    try:
        return repository.get_hotspots_by_satellite(
            satellite_type=satellite_type.value,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/satellite", response_model=list[HotspotResponse])
async def get_hotspots_by_satellite_query(
    satellite_type: SatelliteFilter = Query(
        ...,
        description="Tipo de satélite o sensor ('MODIS' o 'VIIRS')",
    ),
    start_date: str | None = Query(
        None,
        description="Fecha inicial opcional (ej. '2024-05-01')",
    ),
    end_date: str | None = Query(
        None,
        description="Fecha final opcional (ej. '2024-05-31')",
    ),
    offset: int = Query(0, ge=0, description="Offset de paginación"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de registros"),
    session: Session = Depends(get_session),
):
    repository = HotspotRepository(session)
    try:
        return repository.get_hotspots_by_satellite(
            satellite_type=satellite_type.value,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dates", response_model=list[HotspotResponse])
async def get_hotspots_by_dates(
    start_date: str = Query(
        ...,
        description="Fecha inicial (ej. '2024-05-01' o '2024-05-01 00:00:00')",
    ),
    end_date: str = Query(
        ...,
        description="Fecha final (ej. '2024-05-31' o '2024-05-31 23:59:59')",
    ),
    satellite_type: SatelliteFilter | None = Query(
        None,
        description="Filtro opcional por satélite/sensor ('MODIS' o 'VIIRS')",
    ),
    offset: int = Query(0, ge=0, description="Offset de paginación"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de registros"),
    session: Session = Depends(get_session),
):
    repository = HotspotRepository(session)
    try:
        return repository.get_hostspot_by_dates(
            start_date=start_date,
            end_date=end_date,
            satellite_type=satellite_type.value if satellite_type else None,
            offset=offset,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/location", response_model=list[HotspotResponse])
async def get_hotspots_by_location(
    latitude: float = Query(..., description="Latitud del punto (ej. 12.9226)"),
    longitude: float = Query(..., description="Longitud del punto (ej. -87.4937)"),
    radius: float = Query(
        0.05,
        ge=0.0,
        description="Radio en grados (~0.05 ≈ 5.5 km). 0 = coincidencia exacta.",
    ),
    satellite_type: SatelliteFilter | None = Query(
        None,
        description="Filtro opcional por satélite/sensor ('MODIS' o 'VIIRS')",
    ),
    offset: int = Query(0, ge=0, description="Offset de paginación"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de registros"),
    session: Session = Depends(get_session),
):
    repository = HotspotRepository(session)
    return repository.get_hostspot_by_location(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        satellite_type=satellite_type.value if satellite_type else None,
        offset=offset,
        limit=limit,
    )
