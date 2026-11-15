"""
Entrenamiento, evaluación y predicción de desplazamiento futuro de incendios
con Scikit-learn RandomForestRegressor y arreglos NumPy compactos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from analytics.FireForecastService import bearing_to_cardinal
from analytics.FireMovementAnalyzer import MovementStep, _angular_difference_deg
from analytics.WeatherAnalyzer import WeatherAnalysisResult

FEATURE_NAMES: tuple[str, ...] = (
    "latitude",
    "longitude",
    "total_frp",
    "hotspot_count",
    "wind_speed",
    "wind_u",
    "wind_v",
    "humidity",
    "temperature",
    "prev_speed_kmh",
)


@dataclass(slots=True)
class TrainingDataset:
    """Dataset compacto en NumPy preservando incendio y timestamp para split temporal."""

    X: np.ndarray
    y: np.ndarray
    fire_ids: np.ndarray
    timestamps_sec: np.ndarray


@dataclass(slots=True)
class PredictionResult:
    """Predicción de desplazamiento futuro hacia el este/norte y su rumbo."""

    predicted_east_km: float
    predicted_north_km: float
    predicted_distance_km: float
    predicted_direction_deg: float
    predicted_cardinal_direction: str


@dataclass(slots=True)
class EvaluationMetrics:
    """Métricas de evaluación multi-criterio (no depende solo de R²)."""

    train_samples: int
    test_samples: int
    mae_km: float
    rmse_km: float
    mae_east_km: float
    mae_north_km: float
    rmse_east_km: float
    rmse_north_km: float
    r2: float
    mean_angular_error_deg: float
    feature_importances: dict[str, float]
    is_reliable: bool
    reliability_note: str


def displacement_to_direction_and_distance(
    east_km: float,
    north_km: float,
) -> tuple[float, str, float]:
    """
    Convierte desplazamiento (east_km, north_km) en rumbo [0, 360),
    dirección cardinal y distancia euclidiana local en km.
    """
    distance_km = math.hypot(east_km, north_km)
    direction_deg = (math.degrees(math.atan2(east_km, north_km)) + 360.0) % 360.0
    cardinal = bearing_to_cardinal(direction_deg)
    return direction_deg, cardinal, distance_km


def build_training_dataset(
    trajectories: dict[int, list[MovementStep]],
    weather_by_fire_step: dict[tuple[int, datetime], WeatherAnalysisResult],
) -> TrainingDataset:
    """
    Construye pares (X_t, y_{t+1}) a partir de pasos consecutivos del mismo incendio.
    No utiliza información futura como predictor y descarta observaciones sin clima completo.
    """
    rows_x: list[list[float]] = []
    rows_y: list[list[float]] = []
    fire_ids: list[int] = []
    timestamps: list[float] = []

    for fire_id, steps in trajectories.items():
        if len(steps) < 2:
            continue

        ordered = sorted(steps, key=lambda s: s.timestamp)
        for i in range(len(ordered) - 1):
            curr = ordered[i]
            nxt = ordered[i + 1]

            weather = weather_by_fire_step.get((fire_id, curr.timestamp))
            if weather is None or not weather.is_complete:
                continue
            if (
                weather.wind_speed is None
                or weather.wind_u is None
                or weather.wind_v is None
                or weather.humidity is None
                or weather.temperature is None
            ):
                continue

            avg_lat = (curr.centroid_lat + nxt.centroid_lat) / 2.0
            north_km = (nxt.centroid_lat - curr.centroid_lat) * 111.32
            east_km = (
                (nxt.centroid_lon - curr.centroid_lon)
                * 111.32
                * math.cos(math.radians(avg_lat))
            )

            features = [
                float(curr.centroid_lat),
                float(curr.centroid_lon),
                float(curr.total_frp),
                float(curr.hotspot_count),
                float(weather.wind_speed),
                float(weather.wind_u),
                float(weather.wind_v),
                float(weather.humidity),
                float(weather.temperature),
                float(curr.apparent_speed_kmh),
            ]
            target = [float(east_km), float(north_km)]

            if not (np.all(np.isfinite(features)) and np.all(np.isfinite(target))):
                continue

            rows_x.append(features)
            rows_y.append(target)
            fire_ids.append(fire_id)
            timestamps.append(curr.timestamp.timestamp())

    if not rows_x:
        return TrainingDataset(
            X=np.empty((0, len(FEATURE_NAMES)), dtype=np.float64),
            y=np.empty((0, 2), dtype=np.float64),
            fire_ids=np.empty(0, dtype=np.int64),
            timestamps_sec=np.empty(0, dtype=np.float64),
        )

    return TrainingDataset(
        X=np.asarray(rows_x, dtype=np.float64),
        y=np.asarray(rows_y, dtype=np.float64),
        fire_ids=np.asarray(fire_ids, dtype=np.int64),
        timestamps_sec=np.asarray(timestamps, dtype=np.float64),
    )


class FirePredictor:
    """
    Modelo predictivo multi-salida (east_km, north_km) basado en RandomForestRegressor.
    Valida cantidad mínima de datos, aplica split temporal sin fuga entre incendios
    y evalúa errores espaciales y angulares.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int | None = 12,
        random_state: int = 42,
        min_training_samples: int = 20,
    ) -> None:
        if n_estimators < 1:
            raise ValueError("n_estimators debe ser al menos 1")
        if min_training_samples < 5:
            raise ValueError("min_training_samples debe ser al menos 5")

        self.min_training_samples = min_training_samples
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=-1,
        )
        self.is_trained = False

    def _temporal_fire_split(
        self,
        dataset: TrainingDataset,
        test_ratio: float = 0.2,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Separa entrenamiento y prueba respetando orden temporal y evitando que
        un mismo incendio aparezca en ambos conjuntos. Si solo hay 1 incendio,
        hace un corte cronológico estricto.
        """
        unique_fires = np.unique(dataset.fire_ids)
        if len(unique_fires) >= 2:
            fire_start_times = [
                (int(fid), float(np.min(dataset.timestamps_sec[dataset.fire_ids == fid])))
                for fid in unique_fires
            ]
            fire_start_times.sort(key=lambda item: item[1])

            n_test_fires = max(1, int(round(len(fire_start_times) * test_ratio)))
            if n_test_fires >= len(fire_start_times):
                n_test_fires = len(fire_start_times) - 1

            test_fire_set = {fid for fid, _ in fire_start_times[-n_test_fires:]}
            test_mask = np.isin(dataset.fire_ids, list(test_fire_set))
            train_idx = np.flatnonzero(~test_mask)
            test_idx = np.flatnonzero(test_mask)
            if len(train_idx) > 0 and len(test_idx) > 0:
                return train_idx, test_idx

        order = np.argsort(dataset.timestamps_sec, kind="mergesort")
        split_at = max(1, int(len(order) * (1.0 - test_ratio)))
        if split_at >= len(order):
            split_at = len(order) - 1
        return order[:split_at], order[split_at:]

    def train_and_evaluate(
        self,
        dataset: TrainingDataset,
        test_ratio: float = 0.2,
    ) -> EvaluationMetrics:
        """
        Valida datos, entrena RandomForestRegressor con split temporal sin fugas
        y calcula MAE, RMSE, R², error angular e importancia de variables.
        """
        n_total = len(dataset.X)
        if n_total < self.min_training_samples:
            raise ValueError(
                f"Datos insuficientes para entrenar: se requieren al menos "
                f"{self.min_training_samples} observaciones válidas (recibidas: {n_total})."
            )
        if dataset.X.shape[1] != len(FEATURE_NAMES):
            raise ValueError("Número inválido de columnas predictoras")
        if not (np.all(np.isfinite(dataset.X)) and np.all(np.isfinite(dataset.y))):
            raise ValueError("El dataset contiene valores NaN o infinitos")

        train_idx, test_idx = self._temporal_fire_split(dataset, test_ratio=test_ratio)
        X_train, y_train = dataset.X[train_idx], dataset.y[train_idx]
        X_test, y_test = dataset.X[test_idx], dataset.y[test_idx]

        self.model.fit(X_train, y_train)
        self.is_trained = True

        y_pred = np.asarray(self.model.predict(X_test), dtype=np.float64)

        mae_east = float(mean_absolute_error(y_test[:, 0], y_pred[:, 0]))
        mae_north = float(mean_absolute_error(y_test[:, 1], y_pred[:, 1]))
        mae_global = float(mean_absolute_error(y_test, y_pred))

        rmse_east = float(math.sqrt(mean_squared_error(y_test[:, 0], y_pred[:, 0])))
        rmse_north = float(math.sqrt(mean_squared_error(y_test[:, 1], y_pred[:, 1])))
        rmse_global = float(math.sqrt(mean_squared_error(y_test, y_pred)))

        r2 = float(r2_score(y_test, y_pred)) if len(y_test) >= 2 else 0.0

        angular_errors: list[float] = []
        for (true_e, true_n), (pred_e, pred_n) in zip(y_test, y_pred, strict=True):
            if math.hypot(true_e, true_n) == 0.0 and math.hypot(pred_e, pred_n) == 0.0:
                angular_errors.append(0.0)
                continue
            true_dir, _, _ = displacement_to_direction_and_distance(float(true_e), float(true_n))
            pred_dir, _, _ = displacement_to_direction_and_distance(float(pred_e), float(pred_n))
            angular_errors.append(_angular_difference_deg(true_dir, pred_dir))

        mean_ang_err = float(np.mean(angular_errors)) if angular_errors else 0.0

        importances = {
            name: round(float(val), 4)
            for name, val in zip(
                FEATURE_NAMES,
                np.asarray(self.model.feature_importances_).tolist(),
                strict=True,
            )
        }

        # Evaluación multi-criterio: nunca confiar solo en R²
        is_reliable = (mean_ang_err <= 45.0) and (rmse_global <= 5.0) and (r2 >= 0.3)
        note = (
            "Modelo confiable según MAE/RMSE/error angular y R²."
            if is_reliable
            else "Precaución: evaluar error angular y RMSE; R² por sí solo no garantiza confiabilidad."
        )

        return EvaluationMetrics(
            train_samples=len(X_train),
            test_samples=len(X_test),
            mae_km=round(mae_global, 4),
            rmse_km=round(rmse_global, 4),
            mae_east_km=round(mae_east, 4),
            mae_north_km=round(mae_north, 4),
            rmse_east_km=round(rmse_east, 4),
            rmse_north_km=round(rmse_north, 4),
            r2=round(r2, 4),
            mean_angular_error_deg=round(mean_ang_err, 4),
            feature_importances=importances,
            is_reliable=is_reliable,
            reliability_note=note,
        )

    def predict(self, features: list[float] | np.ndarray) -> PredictionResult:
        """Predice desplazamiento futuro (east_km, north_km), rumbo y distancia."""
        if not self.is_trained:
            raise RuntimeError("El modelo debe entrenarse antes de realizar predicciones")

        arr = np.asarray(features, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.shape != (1, len(FEATURE_NAMES)):
            raise ValueError(f"Se esperaba vector de {len(FEATURE_NAMES)} características")
        if not np.all(np.isfinite(arr)):
            raise ValueError("Las variables predictoras contienen valores inválidos")

        pred = self.model.predict(arr)[0]
        east_km = float(pred[0])
        north_km = float(pred[1])
        direction_deg, cardinal, distance_km = displacement_to_direction_and_distance(
            east_km, north_km
        )

        return PredictionResult(
            predicted_east_km=round(east_km, 4),
            predicted_north_km=round(north_km, 4),
            predicted_distance_km=round(distance_km, 4),
            predicted_direction_deg=round(direction_deg, 4),
            predicted_cardinal_direction=cardinal,
        )
