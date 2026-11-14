from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from analytics.FireMovementAnalyzer import FireMovementAnalyzer
from analytics.HotspotProcessor import HotspotProcessor


def test_movement_analyzer_computes_trajectory_and_direction_change():
    processor = HotspotProcessor()
    t0 = datetime(2025, 5, 1, 10, 0, tzinfo=UTC)
    records = [
        # Intervalo 0 (10:00): 2 puntos alrededor de (12.100, -86.200)
        {"id": "1", "latitude": 12.100, "longitude": -86.200, "acq_datetime": t0, "frp": 10.0},
        {"id": "2", "latitude": 12.100, "longitude": -86.200, "acq_datetime": t0 + timedelta(minutes=10), "frp": 15.0},
        # Intervalo 1 (+6h): se mueve al Noreste
        {"id": "3", "latitude": 12.110, "longitude": -86.190, "acq_datetime": t0 + timedelta(hours=6), "frp": 30.0},
        # Intervalo 3 (+18h, saltando intervalo 2 vacío): gira hacia el Sureste
        {"id": "4", "latitude": 12.100, "longitude": -86.180, "acq_datetime": t0 + timedelta(hours=18), "frp": 40.0},
    ]

    prepared = processor.prepare(records)
    analyzer = FireMovementAnalyzer(interval_hours=6.0, direction_change_threshold_deg=45.0)
    steps = analyzer.analyze_fire(fire_id=1, hotspots=prepared)

    assert len(steps) == 3

    # Primer intervalo
    assert steps[0].hotspot_count == 2
    assert steps[0].total_frp == 25.0
    assert steps[0].distance_km == 0.0
    assert steps[0].direction_deg is None

    # Segundo intervalo: Noreste (~44.3°)
    assert steps[1].cardinal_direction == "Noreste"
    assert steps[1].distance_km > 1.0
    assert steps[1].apparent_speed_kmh > 0.0
    assert steps[1].empty_intervals_before == 0
    assert steps[1].direction_changed is False

    # Tercer intervalo: hubo 1 intervalo vacío intermedio y giró hacia el Sureste (~135°)
    assert steps[2].empty_intervals_before == 1
    assert steps[2].cardinal_direction == "Sureste"
    assert steps[2].direction_changed is True
    assert steps[2].angle_change_deg is not None and steps[2].angle_change_deg > 45.0


def test_movement_analyzer_ignores_noise_in_analyze_all():
    processor = HotspotProcessor()
    t0 = datetime(2025, 5, 1, 10, 0, tzinfo=UTC)
    prepared = processor.prepare([
        {"id": "1", "latitude": 12.100, "longitude": -86.200, "acq_datetime": t0, "frp": 10.0},
        {"id": "2", "latitude": 12.110, "longitude": -86.190, "acq_datetime": t0 + timedelta(hours=6), "frp": 20.0},
        {"id": "3", "latitude": 14.000, "longitude": -85.000, "acq_datetime": t0, "frp": 5.0},
    ])
    labels = np.array([0, 0, -1], dtype=np.int32)

    analyzer = FireMovementAnalyzer(interval_hours=6.0)
    trajectories = analyzer.analyze_all(prepared, labels)

    assert list(trajectories.keys()) == [0]
    assert len(trajectories[0]) == 2


def test_movement_analyzer_validates_params():
    with pytest.raises(ValueError):
        FireMovementAnalyzer(interval_hours=0)
    with pytest.raises(ValueError):
        FireMovementAnalyzer(direction_change_threshold_deg=0)
