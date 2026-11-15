from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Literal

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    root_mean_squared_error,
)


def compute_descriptive_stats(values: np.ndarray) -> dict[str, float | int | None]:
    """Calcula estadísticas descriptivas completas para un arreglo numérico 1D."""
    clean = values[np.isfinite(values)]
    n = int(clean.size)
    if n == 0:
        return {
            "count": 0,
            "sum": None,
            "mean": None,
            "std": None,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p90": None,
            "iqr": None,
            "max": None,
        }

    q25, q50, q75, q90 = np.percentile(clean, [25.0, 50.0, 75.0, 90.0])
    std = float(np.std(clean, ddof=1)) if n > 1 else 0.0
    return {
        "count": n,
        "sum": round(float(np.sum(clean)), 4),
        "mean": round(float(np.mean(clean)), 4),
        "std": round(std, 4),
        "min": round(float(np.min(clean)), 4),
        "p25": round(float(q25), 4),
        "median": round(float(q50), 4),
        "p75": round(float(q75), 4),
        "p90": round(float(q90), 4),
        "iqr": round(float(q75 - q25), 4),
        "max": round(float(np.max(clean)), 4),
    }


def run_confidence_dbscan(
    unique_counts: list[tuple[int, int]],
    eps: float = 5.0,
    min_samples: int = 2,
) -> dict[str, Any]:
    """
    Aplica DBSCAN únicamente sobre los valores únicos de confianza ya agregados
    en SQL `(confidence_value, row_count)`, evitando comparar millones de filas.
    """
    if not unique_counts:
        return {
            "summary": {
                "total_rows": 0,
                "unique_values": 0,
                "clusters_count": 0,
                "anomaly_rows": 0,
                "anomaly_pct": 0.0,
                "eps": eps,
                "min_samples": min_samples,
            },
            "points": [],
            "anomalies": [],
        }

    values = np.array([v for v, _ in unique_counts], dtype=np.float64).reshape(-1, 1)
    counts = [int(c) for _, c in unique_counts]
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(values)

    total_rows = sum(counts)
    anomaly_rows = sum(c for c, lbl in zip(counts, labels) if int(lbl) == -1)
    unique_clusters = sorted({int(lbl) for lbl in labels if int(lbl) != -1})

    points = [
        {
            "confidence": int(val),
            "count": cnt,
            "cluster": int(lbl),
            "is_anomaly": int(lbl) == -1,
        }
        for (val, cnt), lbl in zip(unique_counts, labels)
    ]
    anomalies = [p for p in points if p["is_anomaly"]]

    return {
        "summary": {
            "total_rows": total_rows,
            "unique_values": len(unique_counts),
            "clusters_count": len(unique_clusters),
            "anomaly_rows": anomaly_rows,
            "anomaly_pct": round((anomaly_rows / total_rows) * 100.0, 4)
            if total_rows > 0
            else 0.0,
            "eps": eps,
            "min_samples": min_samples,
        },
        "points": points,
        "anomalies": anomalies,
    }


def run_spatial_isolation_forest(
    coords: np.ndarray,
    ids: list[str],
    frps: list[float | None],
    datetimes: list[str],
    n_estimators: int = 300,
    contamination: float | Literal["auto"] = "auto",
    random_state: int = 42,
    max_points_returned: int = 5000,
) -> dict[str, Any]:
    """
    Detecta anomalías espaciales sobre (latitude, longitude) usando IsolationForest.
    """
    n = int(coords.shape[0])
    if n == 0:
        return {
            "summary": {
                "total_points": 0,
                "normal_count": 0,
                "anomaly_count": 0,
                "anomaly_pct": 0.0,
                "score_stats": compute_descriptive_stats(np.array([], dtype=np.float64)),
            },
            "points": [],
        }

    model = IsolationForest(
        n_estimators=n_estimators,
        max_samples="auto",
        contamination=contamination,  # type: ignore[arg-type]
        random_state=random_state,
    )
    preds = model.fit_predict(coords)
    scores = model.decision_function(coords)

    anomaly_mask = preds == -1
    anomaly_count = int(np.sum(anomaly_mask))
    normal_count = n - anomaly_count

    # Prioriza retornar todas las anomalías (hasta el límite) y muestrear normales si excede
    anomaly_indices = np.where(anomaly_mask)[0]
    normal_indices = np.where(~anomaly_mask)[0]

    selected_anom = anomaly_indices[:max_points_returned]
    remaining = max(0, max_points_returned - len(selected_anom))
    if len(normal_indices) > remaining and remaining > 0:
        step = max(1, len(normal_indices) // remaining)
        selected_norm = normal_indices[::step][:remaining]
    else:
        selected_norm = normal_indices[:remaining]

    selected_idx = np.concatenate([selected_anom, selected_norm])

    points = [
        {
            "id": ids[int(i)],
            "latitude": round(float(coords[int(i), 0]), 6),
            "longitude": round(float(coords[int(i), 1]), 6),
            "frp": frps[int(i)],
            "acq_datetime": datetimes[int(i)],
            "anomaly": int(preds[int(i)]),
            "is_anomaly": bool(preds[int(i)] == -1),
            "score": round(float(scores[int(i)]), 6),
        }
        for i in selected_idx
    ]

    return {
        "summary": {
            "total_points": n,
            "normal_count": normal_count,
            "anomaly_count": anomaly_count,
            "anomaly_pct": round((anomaly_count / n) * 100.0, 4),
            "returned_points": len(points),
            "score_stats": compute_descriptive_stats(scores),
        },
        "points": points,
    }


def _build_ts_features(
    history: Sequence[float],
    idx: int,
    month_num: int,
) -> list[float]:
    """Construye vector de características autoregresivas, estacionales y de tendencia."""
    lag1 = history[idx - 1] if idx - 1 >= 0 else history[0]
    lag2 = history[idx - 2] if idx - 2 >= 0 else lag1
    lag12 = history[idx - 12] if idx - 12 >= 0 else lag1
    angle = 2.0 * math.pi * (month_num / 12.0)
    return [
        float(idx),
        lag1,
        lag2,
        lag12,
        math.sin(angle),
        math.cos(angle),
        math.sin(2.0 * angle),
        math.cos(2.0 * angle),
    ]


def run_monthly_seasonal_forecast(
    months: list[str],
    counts: list[int],
    train_ratio: float = 0.8,
    future_months: int = 6,
) -> dict[str, Any]:
    """
    Pronóstico estacional mensual sin dependencia de statsmodels:
    ajusta Ridge autoregresivo con rezagos (1, 2, 12) + armónicos estacionales + tendencia,
    genera intervalos de confianza al 80% y 95%, y reporta MAE, MSE, RMSE, MAPE, SMAPE, R2 y MBE.
    """
    n = len(months)
    if n < 18:
        raise ValueError(
            "Se requieren al menos 18 meses de datos para entrenar y validar el pronóstico estacional."
        )

    train_size = max(14, min(n - 2, int(n * train_ratio)))
    y_all = np.array(counts, dtype=np.float64)

    start_idx = 12
    X_train_rows: list[list[float]] = []
    y_train_rows: list[float] = []
    for i in range(start_idx, train_size):
        m_num = int(months[i].split("-")[1])
        X_train_rows.append(_build_ts_features(counts[:train_size], i, m_num))
        y_train_rows.append(float(counts[i]))

    X_train = np.array(X_train_rows, dtype=np.float64)
    y_train = np.array(y_train_rows, dtype=np.float64)

    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)

    train_preds = np.maximum(0.0, model.predict(X_train))
    residuals = y_train - train_preds
    residual_std = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 1.0

    # Pronóstico recursivo sobre test y horizonte futuro
    history = [float(c) for c in counts[:train_size]]
    test_preds: list[float] = []
    test_lower_80: list[float] = []
    test_upper_80: list[float] = []
    test_lower_95: list[float] = []
    test_upper_95: list[float] = []

    for step_idx, i in enumerate(range(train_size, n), start=1):
        m_num = int(months[i].split("-")[1])
        feat = np.array([_build_ts_features(history, i, m_num)], dtype=np.float64)
        pred = max(0.0, float(model.predict(feat)[0]))
        history.append(pred)
        scale = math.sqrt(step_idx)
        test_preds.append(pred)
        test_lower_80.append(max(0.0, pred - 1.2816 * residual_std * scale))
        test_upper_80.append(pred + 1.2816 * residual_std * scale)
        test_lower_95.append(max(0.0, pred - 1.96 * residual_std * scale))
        test_upper_95.append(pred + 1.96 * residual_std * scale)

    y_test = y_all[train_size:]
    y_pred = np.array(test_preds, dtype=np.float64)

    mae = float(mean_absolute_error(y_test, y_pred))
    mse = float(mean_squared_error(y_test, y_pred))
    rmse = float(root_mean_squared_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred)) if len(y_test) > 1 else 0.0
    mbe = float(np.mean(y_pred - y_test))

    nonzero = y_test != 0
    mape = (
        float(np.mean(np.abs((y_test[nonzero] - y_pred[nonzero]) / y_test[nonzero])) * 100.0)
        if np.any(nonzero)
        else 0.0
    )
    denom = np.abs(y_test) + np.abs(y_pred)
    smape_mask = denom > 0
    smape = (
        float(
            np.mean(2.0 * np.abs(y_pred[smape_mask] - y_test[smape_mask]) / denom[smape_mask])
            * 100.0
        )
        if np.any(smape_mask)
        else 0.0
    )

    # Horizonte futuro a partir del último mes real
    full_history = [float(c) for c in counts]
    last_year, last_month = (int(x) for x in months[-1].split("-"))
    future_series: list[dict[str, Any]] = []
    for step_idx in range(1, future_months + 1):
        total_m = (last_year * 12 + (last_month - 1)) + step_idx
        f_year, f_month = divmod(total_m, 12)
        f_month += 1
        label = f"{f_year:04d}-{f_month:02d}"
        idx = len(full_history)
        feat = np.array([_build_ts_features(full_history, idx, f_month)], dtype=np.float64)
        pred = max(0.0, float(model.predict(feat)[0]))
        full_history.append(pred)
        scale = math.sqrt(step_idx)
        future_series.append(
            {
                "month": label,
                "predicted": round(pred, 2),
                "lower_80": round(max(0.0, pred - 1.2816 * residual_std * scale), 2),
                "upper_80": round(pred + 1.2816 * residual_std * scale, 2),
                "lower_95": round(max(0.0, pred - 1.96 * residual_std * scale), 2),
                "upper_95": round(pred + 1.96 * residual_std * scale, 2),
            }
        )

    train_series = [
        {"month": months[i], "actual": int(counts[i])} for i in range(train_size)
    ]
    test_series = [
        {
            "month": months[train_size + k],
            "actual": int(counts[train_size + k]),
            "predicted": round(test_preds[k], 2),
            "lower_80": round(test_lower_80[k], 2),
            "upper_80": round(test_upper_80[k], 2),
            "lower_95": round(test_lower_95[k], 2),
            "upper_95": round(test_upper_95[k], 2),
        }
        for k in range(len(test_preds))
    ]

    return {
        "metrics": {
            "total_months": n,
            "train_months": train_size,
            "test_months": len(test_preds),
            "mae": round(mae, 4),
            "mse": round(mse, 4),
            "rmse": round(rmse, 4),
            "mape_pct": round(mape, 4),
            "smape_pct": round(smape, 4),
            "r2": round(r2, 4),
            "mbe": round(mbe, 4),
            "residual_std": round(residual_std, 4),
            "train_stats": compute_descriptive_stats(y_all[:train_size]),
            "test_stats": compute_descriptive_stats(y_test),
        },
        "train": train_series,
        "test": test_series,
        "future": future_series,
    }
