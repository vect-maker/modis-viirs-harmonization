from fastapi import APIRouter, HTTPException, Query

from enviromental.RequestWeather import RequestWeather
from enviromental.WeatherDataClient import WeatherClientError, WeatherDataClient

router = APIRouter(prefix="/weather", tags=["Weather"])
_weather_client = WeatherDataClient()


@router.post("/")
async def get_weather_params(
    data: RequestWeather,
    limit: int = Query(default=50, ge=1, le=1000, description="Número máximo de registros a retornar"),
    offset: int = Query(default=0, ge=0, description="Número de registros a saltar"),
):
    try:
        records = await _weather_client.fetch_daily_records(data)
    except WeatherClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    paginated = records[offset : offset + limit]

    return {
        "data": paginated,
        "limit": limit,
        "offset": offset,
    }
