from __future__ import annotations

import calendar
from typing import Any

import numpy as np


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


def _month_neighbors(y: int, m: int) -> tuple[tuple[int, int], tuple[int, int]]:
    prev_key = (y, m - 1) if m > 1 else (y - 1, 12)
    next_key = (y, m + 1) if m < 12 else (y + 1, 1)
    return prev_key, next_key


def classify_archive_months(
    info: dict[tuple[int, int], dict[str, Any]],
) -> dict[tuple[int, int], dict[str, Any]]:
    """
    Estado de cada mes con datos en el archivo:
    - partial: abre o cierra un tramo de datos y le faltan días (p. ej. el mes en
      curso, o el primer mes tras un hueco). No es comparable con meses completos.
    - provisional: más de la mitad de las filas vienen del feed casi en tiempo
      real del worker, que todavía no pasa por la armonización.
    Los meses que no aparecen son huecos de datos (no ceros).
    """
    states: dict[tuple[int, int], dict[str, Any]] = {}
    for (y, m), row in info.items():
        days_in_month = calendar.monthrange(y, m)[1]
        prev_key, next_key = _month_neighbors(y, m)
        starts_run = prev_key not in info
        ends_run = next_key not in info
        partial = (starts_run and row["first_day"] > 3) or (
            ends_run and row["last_day"] < days_in_month - 2
        )
        states[(y, m)] = {
            "state": "partial" if partial else "full",
            "provisional": row["total"] > 0 and row["nrt_rows"] / row["total"] > 0.5,
            "first_day": row["first_day"],
            "last_day": row["last_day"],
            "days_in_month": days_in_month,
        }
    return states
