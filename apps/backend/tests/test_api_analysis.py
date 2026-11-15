from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, patch

from api.charts.models import (
    get_cluster_movement,
    get_fire_displacement_prediction,
    get_weather_correlation,
)
from schemas.charts import ChartFilterParams
from schemas.pagination import PaginationParams


def _run_coro(coro):
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


class _DummySession:
    pass


def test_cluster_movement_endpoint():
    t0 = datetime(2025, 4, 1, 10, 0, tzinfo=UTC)
    sample_rows = [
        {
            "id": "1",
            "latitude": 12.100,
            "longitude": -86.200,
            "acq_datetime": t0,
            "frp": 15.0,
        },
        {
            "id": "2",
            "latitude": 12.102,
            "longitude": -86.198,
            "acq_datetime": t0 + timedelta(hours=1),
            "frp": 20.0,
        },
        {
            "id": "3",
            "latitude": 12.108,
            "longitude": -86.192,
            "acq_datetime": t0 + timedelta(hours=7),
            "frp": 35.0,
        },
    ]

    with patch(
        "api.charts.models.HotspotRepository.iter_hotspots_filtered",
        return_value=iter(sample_rows),
    ):
        resp = _run_coro(
            get_cluster_movement(
                filters=ChartFilterParams(),
                pagination=PaginationParams(limit=10, offset=0),
                eps_km=2.0,
                min_samples=2,
                interval_hours=6.0,
                session=_DummySession(),  # type: ignore[arg-type]
            )
        )

    assert resp.chart == "models.cluster-movement"
    body = resp.data
    assert body["summary"]["hotspots_valid"] == 3
    assert body["summary"]["clusters"] == 1
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert len(body["fires"]) == 1
    assert len(body["fires"][0]["steps"]) == 2
    assert body["fires"][0]["steps"][1]["cardinal_direction"] == "Noreste"


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


def test_predict_endpoint_returns_metrics_and_prediction():
    t0 = datetime(2025, 4, 1, 0, 0, tzinfo=UTC)
    sample_rows = []
    fake_daily = []

    for fire_idx in range(8):
        day_base = t0 + timedelta(days=fire_idx * 3)
        lat = 12.0 + fire_idx * 0.2
        lon = -86.5 + fire_idx * 0.2
        for step in range(4):
            dt = day_base + timedelta(hours=step * 6)
            sample_rows.append(
                {
                    "id": f"{fire_idx}-{step}-a",
                    "latitude": lat + step * 0.005,
                    "longitude": lon + step * 0.005,
                    "acq_datetime": dt,
                    "frp": 25.0 + step * 5.0,
                }
            )
            sample_rows.append(
                {
                    "id": f"{fire_idx}-{step}-b",
                    "latitude": lat + step * 0.005 + 0.001,
                    "longitude": lon + step * 0.005 + 0.001,
                    "acq_datetime": dt + timedelta(minutes=10),
                    "frp": 25.0 + step * 5.0,
                }
            )
        fake_daily.append(
            {
                "date": day_base.strftime("%Y%m%d"),
                "T2M": 32.0,
                "RH2M": 38.0,
                "WS10M": 9.0,
                "WD10M": 225.0,
                "PRECTOTCORR": 0.0,
            }
        )

    with (
        patch(
            "api.charts.models.HotspotRepository.iter_hotspots_filtered",
            return_value=iter(sample_rows),
        ),
        patch(
            "api.charts.models.WeatherDataClient.fetch_daily_records",
            new=AsyncMock(return_value=fake_daily),
        ),
    ):
        resp = _run_coro(
            get_fire_displacement_prediction(
                filters=ChartFilterParams(),
                eps_km=2.0,
                min_samples=2,
                interval_hours=6.0,
                min_training_samples=10,
                n_estimators=20,
                session=_DummySession(),  # type: ignore[arg-type]
            )
        )

    assert resp.chart == "models.predict"
    body = resp.data
    assert "metrics" in body
    assert "latest_prediction" in body
    assert body["metrics"]["train_samples"] > 0
    assert body["metrics"]["test_samples"] > 0
    assert body["latest_prediction"]["predicted_cardinal_direction"] == "Noreste"
