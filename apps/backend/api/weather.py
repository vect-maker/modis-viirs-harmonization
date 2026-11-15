from fastapi import APIRouter, HTTPException

from enviromental.RequestWeather import RequestWeather
from enviromental.WeatherDataClient import WeatherClientError, WeatherDataClient
from repositories.pagination import paginate_sequence
from schemas.pagination import PaginatedResponse, PaginationDep

router = APIRouter(prefix="/weather", tags=["Weather"])
_weather_client = WeatherDataClient()


@router.post("")
async def get_weather_params(
    data: RequestWeather,
    pagination: PaginationDep,
) -> PaginatedResponse[dict[str, object]]:
    try:
        records = await _weather_client.fetch_daily_records(data)
    except WeatherClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return paginate_sequence(records, pagination)
