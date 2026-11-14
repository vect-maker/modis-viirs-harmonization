from datetime import datetime, timedelta

import numpy as np
import pytest

from analytics.FireClusterer import FireClusterer
from analytics.HotspotProcessor import HotspotProcessor


def test_hotspot_processor_filters_invalid_records():
    processor = HotspotProcessor()
    records = [
        {"id": "1", "latitude": 12.10, "longitude": -86.20, "acq_datetime": datetime(2025, 3, 1, 10, 0), "frp": 15.5},
        {"id": "2", "latitude": 95.0, "longitude": -86.20, "acq_datetime": datetime(2025, 3, 1, 10, 0), "frp": 10.0},  # lat inválida
        {"id": "3", "latitude": 12.10, "longitude": None, "acq_datetime": datetime(2025, 3, 1, 10, 0), "frp": 10.0},   # lon nula
        {"id": "4", "latitude": 12.11, "longitude": -86.21, "acq_datetime": "2025-03-01T11:00:00", "frp": -5.0},        # frp negativo -> 0
        {"id": "5", "latitude": 12.12, "longitude": -86.22, "acq_datetime": "invalid-date", "frp": 10.0},              # fecha inválida
    ]

    prepared = processor.prepare(records)
    assert len(prepared) == 2
    assert prepared.dropped_count == 3
    assert prepared.ids == ["1", "4"]
    assert prepared.frp[1] == 0.0
    assert prepared.coords_rad.shape == (2, 2)
    assert np.allclose(prepared.coords_rad[0], np.radians([12.10, -86.20]))


def test_fire_clusterer_separates_space_time_and_detects_noise():
    processor = HotspotProcessor()
    t0 = datetime(2025, 4, 1, 12, 0)
    records = [
        # Incendio A (mismo sitio, t0 y t0 + 2h)
        {"id": "a1", "latitude": 12.100, "longitude": -86.200, "acq_datetime": t0, "frp": 20.0},
        {"id": "a2", "latitude": 12.102, "longitude": -86.199, "acq_datetime": t0 + timedelta(hours=2), "frp": 25.0},
        # Incendio B (mismo sitio que A, pero 10 días después -> NO debe mezclarse)
        {"id": "b1", "latitude": 12.100, "longitude": -86.200, "acq_datetime": t0 + timedelta(days=10), "frp": 30.0},
        {"id": "b2", "latitude": 12.101, "longitude": -86.201, "acq_datetime": t0 + timedelta(days=10, hours=3), "frp": 35.0},
        # Ruido aislado (lejos de todo)
        {"id": "noise", "latitude": 13.500, "longitude": -85.000, "acq_datetime": t0, "frp": 5.0},
    ]

    prepared = processor.prepare(records)
    clusterer = FireClusterer(eps_km=1.0, min_samples=2, time_window_hours=24.0)
    result = clusterer.fit_predict(prepared)

    assert result.cluster_count == 2
    assert result.noise_count == 1
    assert result.labels[0] == result.labels[1] >= 0
    assert result.labels[2] == result.labels[3] >= 0
    assert result.labels[0] != result.labels[2]
    assert result.labels[4] == -1


def test_fire_clusterer_ball_tree_query_radius():
    processor = HotspotProcessor()
    t0 = datetime(2025, 4, 1, 12, 0)
    prepared = processor.prepare([
        {"id": "p1", "latitude": 12.100, "longitude": -86.200, "acq_datetime": t0},
        {"id": "p2", "latitude": 12.103, "longitude": -86.200, "acq_datetime": t0},  # ~0.33 km
        {"id": "p3", "latitude": 12.200, "longitude": -86.200, "acq_datetime": t0},  # ~11.1 km
    ])

    clusterer = FireClusterer(eps_km=1.0, min_samples=2, time_window_hours=24.0)
    tree = clusterer.build_ball_tree(prepared.coords_rad)
    neighbors = clusterer.query_radius_km(tree, prepared.coords_rad[:1], radius_km=1.0)
    assert set(neighbors[0].tolist()) == {0, 1}


def test_fire_clusterer_extends_window_for_confirmed_fire():
    processor = HotspotProcessor()
    t0 = datetime(2025, 4, 1, 0, 0)
    records = [
        # Incendio confirmado (2 puntos cercanos dentro de 6h)
        {"id": "f1", "latitude": 12.100, "longitude": -86.200, "acq_datetime": t0},
        {"id": "f2", "latitude": 12.101, "longitude": -86.200, "acq_datetime": t0 + timedelta(hours=6)},
        # Pausa de 36h (> 24h base, pero <= 36h/48h ampliada porque ya hay incendio) -> debe unirse
        {"id": "f3", "latitude": 12.102, "longitude": -86.200, "acq_datetime": t0 + timedelta(hours=42)},
    ]

    prepared = processor.prepare(records)
    clusterer = FireClusterer(
        eps_km=1.0,
        min_samples=2,
        time_window_hours=24.0,
        max_time_window_hours=72.0,
        window_extension_hours=12.0,
    )
    result = clusterer.fit_predict(prepared)

    assert result.cluster_count == 1
    assert result.noise_count == 0
    assert result.labels.tolist() == [0, 0, 0]


def test_fire_clusterer_validates_params():
    with pytest.raises(ValueError):
        FireClusterer(eps_km=0)
    with pytest.raises(ValueError):
        FireClusterer(min_samples=0)
    with pytest.raises(ValueError):
        FireClusterer(time_window_hours=-1)
    with pytest.raises(ValueError):
        FireClusterer(time_window_hours=24.0, max_time_window_hours=12.0)
