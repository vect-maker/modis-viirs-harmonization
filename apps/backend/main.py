import os
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from sqlmodel import Session

from database.initDb import create_db_and_tables
from database.session import get_session
from apps.backend.enviromental.WeatherDataClient import router as weather_router
from repositories.HotspotRepository import HotspotRepository


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


@app.get("/hotspots", tags=["Hotspots"])
async def get_hotspots(session: Session = Depends(get_session)):
    repository = HotspotRepository(session)
    return repository.get_hotspots()