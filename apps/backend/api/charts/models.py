from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from analytics.WeatherAnalyzer import WeatherAnalyzer
from enviromental.RequestWeather import RequestWeather
from enviromental.WeatherDataClient import WeatherClientError, WeatherDataClient
from repositories.pagination import paginate_sequence
from schemas.charts import ChartFiltersDep, ChartResponse, build_chart_response
from schemas.pagination import PaginationDep

router = APIRouter(prefix="/models", tags=["Charts - Models"])


@router.get(
    "/weather-correlation",
    response_model=ChartResponse[dict[str, Any]],
    summary="Analizar vectores de viento NASA POWER y alineación con el fuego",
)
async def get_weather_correlation(
    filters: ChartFiltersDep,
    pagination: PaginationDep,
    latitude: Annotated[float, Query(ge=-90.0, le=90.0)],
    longitude: Annotated[float, Query(ge=-180.0, le=180.0)],
    fire_direction_deg: Annotated[float | None, Query(ge=0.0, lt=360.0)] = None,
) -> ChartResponse[dict[str, Any]]:
    start_dt, end_dt = filters.to_datetime_bounds()
    if start_dt is None or end_dt is None:
        raise HTTPException(
            status_code=422,
            detail="start_date y end_date son requeridos para weather-correlation",
        )

    client = WeatherDataClient()
    req = RequestWeather(
        latitude=latitude,
        longitude=longitude,
        start=start_dt,
        end=end_dt,
    )
    try:
        daily_records = await client.fetch_daily_records(req)
    except WeatherClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    analyzer = WeatherAnalyzer()
    results = [
        {
            "date": rec.get("date"),
            **asdict(analyzer.analyze(rec, fire_direction_deg)),
        }
        for rec in daily_records
    ]
    paginated = paginate_sequence(results, pagination)

    return build_chart_response(
        "models.weather-correlation",
        {
            "records": paginated.data,
            "total": paginated.total,
            "limit": paginated.limit,
            "offset": paginated.offset,
        },
        filters,
        extra_filters={
            "latitude": latitude,
            "longitude": longitude,
            "fire_direction_deg": fire_direction_deg,
        },
    )
