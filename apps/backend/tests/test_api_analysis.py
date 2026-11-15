from datetime import date
from unittest.mock import AsyncMock, patch

from api.charts.models import get_weather_correlation
from schemas.charts import ChartFilterParams
from schemas.pagination import PaginationParams


def _run_coro(coro):
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


def test_weather_correlation_endpoint():
    fake_daily = [
        {
            "date": "20250401",
            "T2M": 30.0,
            "RH2M": 42.0,
            "WS10M": 8.0,
            "WD10M": 225.0,
            "PRECTOTCORR": 0.0,
        }
    ]
    with patch(
        "api.charts.models.WeatherDataClient.fetch_daily_records",
        new=AsyncMock(return_value=fake_daily),
    ):
        resp = _run_coro(
            get_weather_correlation(
                filters=ChartFilterParams(
                    start_date=date(2025, 4, 1),
                    end_date=date(2025, 4, 1),
                ),
                pagination=PaginationParams(limit=50, offset=0),
                latitude=12.1,
                longitude=-86.2,
                fire_direction_deg=45.0,
            )
        )

    assert resp.chart == "models.weather-correlation"
    body = resp.data
    assert body["total"] == 1
    assert body["limit"] == 50
    assert body["offset"] == 0
    records = body["records"]
    assert len(records) == 1
    assert records[0]["is_complete"] is True
    assert records[0]["wind_direction_to_deg"] == 45.0
    assert records[0]["wind_fire_alignment_cos"] == 1.0
