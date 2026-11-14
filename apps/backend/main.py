import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.cluster_hotspots import router as cluster_hotspots_router
from api.clusters import router as clusters_router
from api.countries import router as countries_router
from api.dashboard import router as dashboard_router
from api.environmental_records import router as environmental_records_router
from api.fact_hotspots import router as fact_hotspots_router
from api.fire_analysis import router as fire_analysis_router
from api.fire_calendar import router as fire_calendar_router
from api.fire_cluster_forecast import router as fire_cluster_forecast_router
from api.hotspots import router as hotspots_router
from api.platforms import router as platforms_router
from api.weather import router as weather_router
from database.initDb import create_db_and_tables


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
app.include_router(dashboard_router)
app.include_router(fire_calendar_router)


@app.get("/")
async def root():
    return {"message": "Servidor funcionando"}
