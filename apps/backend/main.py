import os

import httpx
from fastapi import FastAPI, Depends
from sqlmodel import Session

from database.session import get_session
from enviromental.RequestWeather import RequestWeather
from repositories.HotspotRepository import HotspotRepository

app = FastAPI(
    title="Fire Detection API",
    description="API para detección y monitoreo de incendios",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path=os.getenv("ROOT_PATH", ""),
)

@app.get("/")
async def root():
    return {"message": "Servidor funcionando"}

@app.post("/weather/")
async def getweatherparams(data: RequestWeather, tags=["Weather"]):
    params = {
        "latitude": data.latitude,
        "longitude": data.longitude,
        "start": data.start.strftime("%Y%m%d"),
        "end": data.end.strftime("%Y%m%d"),
        "parameters": data.parameters,
        "community": data.community,
        "format": "JSON"
    }

    url = "https://power.larc.nasa.gov/api/temporal/daily/point"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    return response.json()

@app.get("/hotspots")
async def get_hotspots(
    session: Session = Depends(get_session)
):
    repository = HotspotRepository(session)

    return repository.get_hotspots()