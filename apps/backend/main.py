import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlmodel import Session

from database.initDb import create_db_and_tables
from database.session import get_session
from enviromental.WeatherDataClient import router as weather_router
from model.StarSchema import CountryPublic, HotspotPublic, PlatformPublic
from repositories.CountryRepository import CountryRepository
from repositories.HotspotRepository import HotspotRepository
from repositories.PlatformRepository import PlatformRepository
from schemas.pagination import PaginatedResponse, PaginationDep

SessionDep = Annotated[Session, Depends(get_session)]


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

app.include_router(weather_router)


@app.get("/")
async def root():
    return {"message": "Servidor funcionando"}


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