import math
from datetime import datetime

import pytest

from analytics.WeatherAnalyzer import WeatherAnalyzer
from enviromental.RequestWeather import RequestWeather
from enviromental.WeatherDataClient import WeatherDataClient


def test_weather_analyzer_converts_meteorological_wind_direction_and_vectors():
    analyzer = WeatherAnalyzer()

    # Viento viene del Suroeste (225°) -> se desplaza hacia el Noreste (45°)
    # Incendio también avanza hacia el Noreste (45°) -> alineación perfecta (cos = 1.0)
    record = {
        "WS10M": 10.0,
        "WD10M": 225.0,
        "T2M": 32.5,
        "RH2M": 40.0,
        "PRECTOTCORR": 0.0,
    }
    res = analyzer.analyze(record, fire_direction_deg=45.0)

    assert res.is_complete is True
    assert res.missing_variables == []
    assert res.wind_direction_to_deg == 45.0
    assert math.isclose(res.wind_u or 0.0, 10.0 * math.sin(math.radians(45.0)), rel_tol=1e-4)
    assert math.isclose(res.wind_v or 0.0, 10.0 * math.cos(math.radians(45.0)), rel_tol=1e-4)
    assert res.wind_fire_angle_diff_deg == 0.0
    assert res.wind_fire_alignment_cos == 1.0


def test_weather_analyzer_marks_incomplete_when_data_missing():
    analyzer = WeatherAnalyzer()

    # Caso sin registro
    empty_res = analyzer.analyze(None)
    assert empty_res.is_complete is False
    assert "incompleto" in empty_res.status_message.lower()
    assert len(empty_res.missing_variables) == 5

    # Caso con -999 (sentinela de NASA POWER) y campo faltante
    partial = {
        "WS10M": 5.0,
        "WD10M": -999.0,
        "T2M": 28.0,
        "RH2M": None,
        "PRECTOTCORR": 1.2,
    }
    partial_res = analyzer.analyze(partial)
    assert partial_res.is_complete is False
    assert "wind_direction_from_deg" in partial_res.missing_variables
    assert "humidity" in partial_res.missing_variables
    assert partial_res.wind_u is None
    assert partial_res.wind_v is None


def test_weather_client_parses_nasa_power_and_sanitizes_sentinel():
    raw_nasa = {
        "properties": {
            "parameter": {
                "T2M": {"20250401": 31.2, "20250402": -999.0},
                "RH2M": {"20250401": 45.0, "20250402": 50.0},
                "WS10M": {"20250401": 6.4, "20250402": 7.1},
                "WD10M": {"20250401": 180.0, "20250402": 190.0},
                "PRECTOTCORR": {"20250401": 0.0, "20250402": 2.5},
            }
        }
    }

    parsed = WeatherDataClient.parse_daily_records(raw_nasa)
    assert len(parsed) == 2
    assert parsed[0]["date"] == "20250401"
    assert parsed[0]["T2M"] == 31.2
    assert parsed[1]["T2M"] is None


def test_request_weather_includes_required_parameters():
    req = RequestWeather(
        latitude=12.1,
        longitude=-86.2,
        start=datetime(2025, 4, 1),
        end=datetime(2025, 4, 2),
    )
    for param in ("T2M", "RH2M", "WS10M", "WD10M", "PRECTOTCORR"):
        assert param in req.parameters


def test_weather_analyzer_rejects_negative_wind_speed():
    with pytest.raises(ValueError):
        WeatherAnalyzer.wind_to_vector(-2.0, 90.0)
