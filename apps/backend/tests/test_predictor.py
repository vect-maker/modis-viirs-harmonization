from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from analytics.FireMovementAnalyzer import MovementStep
from analytics.FirePredictor import (
    FEATURE_NAMES,
    FirePredictor,
    build_training_dataset,
    displacement_to_direction_and_distance,
)
from analytics.WeatherAnalyzer import WeatherAnalysisResult


def test_displacement_to_direction_and_distance():
    deg_n, card_n, dist_n = displacement_to_direction_and_distance(0.0, 5.0)
    assert deg_n == 0.0
    assert card_n == "Norte"
    assert dist_n == 5.0

    deg_ne, card_ne, dist_ne = displacement_to_direction_and_distance(3.0, 3.0)
    assert pytest.approx(deg_ne, abs=1e-6) == 45.0
    assert card_ne == "Noreste"
    assert pytest.approx(dist_ne, abs=1e-6) == pytest.approx(4.2426406, abs=1e-4)

    deg_sw, card_sw, _ = displacement_to_direction_and_distance(-2.0, -2.0)
    assert pytest.approx(deg_sw, abs=1e-6) == 225.0
    assert card_sw == "Suroeste"


def test_build_dataset_and_train_evaluate_predictor():
    t0 = datetime(2025, 4, 1, 0, 0, tzinfo=UTC)
    trajectories: dict[int, list[MovementStep]] = {}
    weather_map: dict[tuple[int, datetime], WeatherAnalysisResult] = {}

    # Generar 10 incendios independientes en orden temporal (4 pasos cada uno -> 30 pares)
    for fire_id in range(10):
        base_t = t0 + timedelta(days=fire_id * 2)
        lat = 12.0 + fire_id * 0.05
        lon = -86.5 + fire_id * 0.05
        steps: list[MovementStep] = []

        # Viento hacia Noreste (u > 0, v > 0) impulsa desplazamiento al Noreste
        wind_u = 4.0 + (fire_id % 3)
        wind_v = 4.0 + (fire_id % 3)

        for k in range(4):
            dt = base_t + timedelta(hours=k * 6)
            step = MovementStep(
                fire_id=fire_id,
                timestamp=dt,
                centroid_lat=lat + k * 0.015,
                centroid_lon=lon + k * 0.015,
                direction_deg=45.0 if k > 0 else None,
                cardinal_direction="Noreste" if k > 0 else None,
                distance_km=2.3 if k > 0 else 0.0,
                apparent_speed_kmh=0.38 if k > 0 else 0.0,
                hotspot_count=3 + k,
                total_frp=50.0 + k * 10.0,
            )
            steps.append(step)
            weather_map[(fire_id, dt)] = WeatherAnalysisResult(
                is_complete=True,
                missing_variables=[],
                wind_speed=float(np.hypot(wind_u, wind_v)),
                wind_direction_from_deg=225.0,
                wind_direction_to_deg=45.0,
                wind_u=wind_u,
                wind_v=wind_v,
                temperature=31.0,
                humidity=40.0,
                precipitation=0.0,
            )

        trajectories[fire_id] = steps

    dataset = build_training_dataset(trajectories, weather_map)
    assert len(dataset.X) == 30
    assert dataset.X.shape[1] == len(FEATURE_NAMES)

    predictor = FirePredictor(n_estimators=30, random_state=42, min_training_samples=20)
    train_idx, test_idx = predictor._temporal_fire_split(dataset, test_ratio=0.2)
    # Garantizar cero fuga entre incendios
    assert set(dataset.fire_ids[train_idx]).isdisjoint(set(dataset.fire_ids[test_idx]))

    metrics = predictor.train_and_evaluate(dataset, test_ratio=0.2)
    assert metrics.train_samples == 24
    assert metrics.test_samples == 6
    assert metrics.mae_km >= 0.0
    assert metrics.rmse_km >= 0.0
    assert metrics.mean_angular_error_deg <= 20.0
    assert set(metrics.feature_importances.keys()) == set(FEATURE_NAMES)
    assert pytest.approx(sum(metrics.feature_importances.values()), abs=1e-2) == 1.0

    pred = predictor.predict([12.2, -86.3, 60.0, 4.0, 6.0, 4.2, 4.2, 40.0, 31.0, 0.4])
    assert pred.predicted_distance_km > 0.0
    assert pred.predicted_cardinal_direction == "Noreste"


def test_predictor_rejects_insufficient_data_or_untrained_predict():
    predictor = FirePredictor(min_training_samples=20)
    with pytest.raises(RuntimeError):
        predictor.predict([0.0] * len(FEATURE_NAMES))

    small_dataset = build_training_dataset({}, {})
    with pytest.raises(ValueError, match="Datos insuficientes"):
        predictor.train_and_evaluate(small_dataset)
