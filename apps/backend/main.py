import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from api.cluster_hotspots import router as cluster_hotspots_router
from api.clusters import router as clusters_router
from api.dashboard import router as dashboard_router
from api.environmental_records import router as environmental_records_router
from api.fire_analysis import router as fire_analysis_router
from api.fire_calendar import router as fire_calendar_router
from api.fire_cluster_forecast import router as fire_cluster_forecast_router
from api.weather import router as weather_router
from database.initDb import create_db_and_tables
from database.session import get_session
from model.StarSchema import (
    AvailableDatesResponse,
    CountryPublic,
    DailyActivityResponse,
    HistoricalCalendarResponse,
    HotspotPublic,
    PlatformPublic,
)
from repositories.CountryRepository import CountryRepository
from repositories.HotspotRepository import HotspotRepository
from repositories.PlatformRepository import PlatformRepository
from repositories.spatial_filter import parse_geojson_polygon_to_wkt
from schemas.health import HealthLiveResponse, HealthReadyResponse, HealthStatus
from schemas.pagination import PaginatedResponse, PaginationDep

SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(
    title="Fire Detection API",
    description="API para monitoreo y consulta de hotspots de incendios",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path=os.getenv("ROOT_PATH", ""),
    lifespan=lifespan,
)

app.include_router(weather_router)
app.include_router(clusters_router)
app.include_router(cluster_hotspots_router)
app.include_router(environmental_records_router)
app.include_router(fire_cluster_forecast_router)
app.include_router(fire_analysis_router)
app.include_router(dashboard_router)
app.include_router(fire_calendar_router)


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"error_type": "validation_error", "detail": str(exc)},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(_request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=503,
        content={
            "error_type": "database_error",
            "detail": "Error al consultar la base de datos",
            "message": str(getattr(exc, "orig", exc)),
        },
    )


@app.get("/health/live", tags=["Health"])
def health_live() -> HealthLiveResponse:
    return HealthLiveResponse(status="ok")


@app.get("/health/ready", tags=["Health"])
def health_ready(session: SessionDep, response: Response) -> HealthReadyResponse:
    db_status: HealthStatus = "ok"
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    dependencies: dict[str, HealthStatus] = {"database": db_status}
    overall_status: HealthStatus = (
        "ok" if all(s == "ok" for s in dependencies.values()) else "error"
    )
    if overall_status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthReadyResponse(status=overall_status, dependencies=dependencies)


@app.get("/platforms", tags=["Platforms"])
def get_platforms(
    session: SessionDep,
    pagination: PaginationDep,
) -> PaginatedResponse[PlatformPublic]:
    return PlatformRepository(session).get_platforms(pagination)


def _parse_polygon_or_422(polygon: str | None) -> str | None:
    if polygon is None:
        return None
    try:
        return parse_geojson_polygon_to_wkt(polygon)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@app.get("/hotspots", tags=["Hotspots"])
def get_hotspots(
    session: SessionDep,
    pagination: PaginationDep,
    start_date: date | None = Query(
        default=None,
        description="Filter detections on or after this UTC date (YYYY-MM-DD)",
    ),
    end_date: date | None = Query(
        default=None,
        description="Filter detections on or before this UTC date (YYYY-MM-DD)",
    ),
    polygon: str | None = Query(
        default=None,
        description=(
            "GeoJSON Polygon or MultiPolygon (RFC 7946, EPSG:4326) serialized as JSON"
        ),
    ),
) -> PaginatedResponse[HotspotPublic]:
    polygon_wkt = _parse_polygon_or_422(polygon)
    return HotspotRepository(session).get_hotspots(
        pagination, start_date=start_date, end_date=end_date, polygon_wkt=polygon_wkt
    )


@app.get("/hotspots/available-dates", tags=["Hotspots"])
def get_hotspot_available_dates(session: SessionDep) -> AvailableDatesResponse:
    return HotspotRepository(session).get_available_dates()


@app.get("/hotspots/daily-activity", tags=["Hotspots"])
def get_hotspot_daily_activity(
    session: SessionDep,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    instrument: str | None = Query(default=None),
    polygon: str | None = Query(
        default=None,
        description=(
            "GeoJSON Polygon or MultiPolygon (RFC 7946, EPSG:4326) serialized as JSON"
        ),
    ),
) -> DailyActivityResponse:
    polygon_wkt = _parse_polygon_or_422(polygon)
    return HotspotRepository(session).get_daily_activity(
        start_date=start_date,
        end_date=end_date,
        instrument=instrument,
        polygon_wkt=polygon_wkt,
    )


@app.get("/hotspots/historical-calendar", tags=["Hotspots"])
def get_hotspot_historical_calendar(session: SessionDep) -> HistoricalCalendarResponse:
    return HotspotRepository(session).get_historical_calendar()


@app.get("/countries", tags=["Countries"])
def get_countries(
    session: SessionDep,
    pagination: PaginationDep,
) -> PaginatedResponse[CountryPublic]:
    return CountryRepository(session).get_countries(pagination)
