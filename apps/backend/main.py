import os
from contextlib import asynccontextmanager
from typing import Annotated

<<<<<<< HEAD
from fastapi import FastAPI
=======
from fastapi import Depends, FastAPI, Response, status
from sqlalchemy import text
from sqlmodel import Session
>>>>>>> feat/frontend-development

from api.cluster_hotspots import router as cluster_hotspots_router
from api.clusters import router as clusters_router
from api.countries import router as countries_router
from api.environmental_records import router as environmental_records_router
from api.fact_hotspots import router as fact_hotspots_router
from api.fire_analysis import router as fire_analysis_router
from api.fire_cluster_forecast import router as fire_cluster_forecast_router
from api.hotspots import router as hotspots_router
from api.platforms import router as platforms_router
from api.weather import router as weather_router
from database.initDb import create_db_and_tables
<<<<<<< HEAD
=======
from database.session import get_session
from enviromental.WeatherDataClient import router as weather_router
from model.StarSchema import CountryPublic, HotspotPublic, PlatformPublic
from repositories.CountryRepository import CountryRepository
from repositories.HotspotRepository import HotspotRepository
from repositories.PlatformRepository import PlatformRepository
from schemas.health import HealthLiveResponse, HealthReadyResponse, HealthStatus
from schemas.pagination import PaginatedResponse, PaginationDep

SessionDep = Annotated[Session, Depends(get_session)]
>>>>>>> feat/frontend-development


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(
    title="Fire Detection API",
    description="API para detección y monitoreo de incendios",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path=os.getenv("ROOT_PATH", ""),
    lifespan=lifespan,
)

app.include_router(hotspots_router)
app.include_router(weather_router)
app.include_router(clusters_router)
app.include_router(cluster_hotspots_router)
app.include_router(environmental_records_router)
app.include_router(countries_router)
app.include_router(platforms_router)
app.include_router(fact_hotspots_router)
app.include_router(fire_cluster_forecast_router)
app.include_router(fire_analysis_router)


<<<<<<< HEAD
@app.get("/")
async def root():
    return {"message": "Servidor funcionando"}
=======
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


@app.get("/hotspots", tags=["Hotspots"])
def get_hotspots(
    session: SessionDep,
    pagination: PaginationDep,
) -> PaginatedResponse[HotspotPublic]:
    return HotspotRepository(session).get_hotspots(pagination)


@app.get("/countries", tags=["Countries"])
def get_countries(
    session: SessionDep,
    pagination: PaginationDep,
) -> PaginatedResponse[CountryPublic]:
    return CountryRepository(session).get_countries(pagination)
>>>>>>> feat/frontend-development
