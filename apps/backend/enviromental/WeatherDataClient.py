import httpx
from fastapi import APIRouter, HTTPException

from .RequestWeather import RequestWeather

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.post("/")
async def get_weather_params(data: RequestWeather):
    params = {
        "latitude": data.latitude,
        "longitude": data.longitude,
        "start": data.start.strftime("%Y%m%d"),
        "end": data.end.strftime("%Y%m%d"),
        "parameters": data.parameters,
        "community": data.community,
        "format": "JSON",
    }

    url = "https://power.larc.nasa.gov/api/temporal/daily/point"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Error al consultar la API de NASA POWER",
            )

    return response.json()
