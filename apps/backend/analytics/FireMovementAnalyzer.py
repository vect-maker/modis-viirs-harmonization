"""
Análisis de movimiento aparente de incendios por intervalos temporales.

Nota metodológica: la velocidad y dirección calculadas describen el desplazamiento
aparente del centroide de detecciones entre intervalos, NO la velocidad física
real del frente de fuego.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from analytics.FireForecastService import (
    bearing_to_cardinal,
    calculate_bearing,
    haversine_km,
)
from analytics.HotspotProcessor import PreparedHotspots


@dataclass(slots=True)
class MovementStep:
    """Estado y desplazamiento aparente de un incendio en un intervalo con detecciones."""

    fire_id: int
    timestamp: datetime
    centroid_lat: float
    centroid_lon: float
    direction_deg: float | None
    cardinal_direction: str | None
    distance_km: float
    apparent_speed_kmh: float
    hotspot_count: int
    total_frp: float
    angle_change_deg: float | None = None
    direction_changed: bool = False
    empty_intervals_before: int = 0


def _angular_difference_deg(angle_a: float, angle_b: float) -> float:
    """Diferencia angular mínima absoluta en grados [0, 180] entre dos rumbos."""
    diff = abs(angle_a - angle_b) % 360.0
    return 360.0 - diff if diff > 180.0 else diff


class FireMovementAnalyzer:
    """
    Agrupa detecciones de un incendio por ventanas temporales configurables,
    calcula centroides y estima rumbo y velocidad aparente entre centroides
    consecutivos, manejando correctamente intervalos vacíos.
    """

    def __init__(
        self,
        interval_hours: float = 6.0,
        direction_change_threshold_deg: float = 45.0,
    ) -> None:
        if interval_hours <= 0:
            raise ValueError("interval_hours debe ser mayor que 0")
        if not (0.0 < direction_change_threshold_deg <= 180.0):
            raise ValueError("direction_change_threshold_deg debe estar en (0, 180]")

        self.interval_hours = float(interval_hours)
        self.direction_change_threshold_deg = float(direction_change_threshold_deg)

    def analyze_fire(
        self,
        fire_id: int,
        hotspots: PreparedHotspots,
    ) -> list[MovementStep]:
        """
        Analiza la trayectoria aparente de un único incendio.
        Los intervalos sin detecciones se omiten sin inventar datos, registrando
        cuántos intervalos vacíos transcurrieron para calcular velocidad con el
        tiempo real entre centroides observados.
        """
        if hotspots.is_empty:
            return []

        interval_sec = self.interval_hours * 3600.0
        order = np.argsort(hotspots.timestamps_sec, kind="mergesort")
        ts_sorted = hotspots.timestamps_sec[order]
        lats_sorted = hotspots.latitudes[order]
        lons_sorted = hotspots.longitudes[order]
        frp_sorted = hotspots.frp[order]

        t_min = float(ts_sorted[0])
        bin_ids = np.floor((ts_sorted - t_min) / interval_sec).astype(np.int64)
        unique_bins = np.unique(bin_ids)

        steps: list[MovementStep] = []
        prev_lat: float | None = None
        prev_lon: float | None = None
        prev_time_sec: float | None = None
        prev_bearing: float | None = None
        prev_bin: int | None = None

        for b in unique_bins:
            mask = bin_ids == b
            c_lat = float(np.mean(lats_sorted[mask]))
            c_lon = float(np.mean(lons_sorted[mask]))
            mean_ts = float(np.mean(ts_sorted[mask]))
            count = int(np.sum(mask))
            total_frp = float(np.sum(frp_sorted[mask]))

            # Preservar zona horaria si las entradas son aware, o usar UTC
            ref_tz = hotspots.datetimes[int(order[0])].tzinfo or UTC
            step_dt = datetime.fromtimestamp(mean_ts, tz=ref_tz)

            empty_before = int(b - prev_bin - 1) if prev_bin is not None else 0

            if prev_lat is None or prev_lon is None or prev_time_sec is None:
                steps.append(
                    MovementStep(
                        fire_id=fire_id,
                        timestamp=step_dt,
                        centroid_lat=round(c_lat, 6),
                        centroid_lon=round(c_lon, 6),
                        direction_deg=None,
                        cardinal_direction=None,
                        distance_km=0.0,
                        apparent_speed_kmh=0.0,
                        hotspot_count=count,
                        total_frp=round(total_frp, 4),
                        angle_change_deg=None,
                        direction_changed=False,
                        empty_intervals_before=0,
                    )
                )
            else:
                dist_km = haversine_km(prev_lat, prev_lon, c_lat, c_lon)
                elapsed_h = (mean_ts - prev_time_sec) / 3600.0
                speed_kmh = dist_km / elapsed_h if elapsed_h > 0 else 0.0

                if dist_km > 0.0:
                    bearing = calculate_bearing(prev_lat, prev_lon, c_lat, c_lon)
                    cardinal = bearing_to_cardinal(bearing)
                    if prev_bearing is not None:
                        angle_diff = _angular_difference_deg(bearing, prev_bearing)
                        dir_changed = angle_diff >= self.direction_change_threshold_deg
                    else:
                        angle_diff = None
                        dir_changed = False
                    prev_bearing = bearing
                else:
                    bearing = prev_bearing
                    cardinal = bearing_to_cardinal(bearing) if bearing is not None else None
                    angle_diff = 0.0 if prev_bearing is not None else None
                    dir_changed = False

                steps.append(
                    MovementStep(
                        fire_id=fire_id,
                        timestamp=step_dt,
                        centroid_lat=round(c_lat, 6),
                        centroid_lon=round(c_lon, 6),
                        direction_deg=round(bearing, 4) if bearing is not None else None,
                        cardinal_direction=cardinal,
                        distance_km=round(dist_km, 4),
                        apparent_speed_kmh=round(speed_kmh, 4),
                        hotspot_count=count,
                        total_frp=round(total_frp, 4),
                        angle_change_deg=round(angle_diff, 4) if angle_diff is not None else None,
                        direction_changed=dir_changed,
                        empty_intervals_before=empty_before,
                    )
                )

            prev_lat = c_lat
            prev_lon = c_lon
            prev_time_sec = mean_ts
            prev_bin = int(b)

        return steps

    def analyze_all(
        self,
        hotspots: PreparedHotspots,
        labels: np.ndarray,
    ) -> dict[int, list[MovementStep]]:
        """
        Analiza el movimiento de todos los clusters válidos (labels >= 0),
        ignorando ruido (-1).
        """
        if len(hotspots) != len(labels):
            raise ValueError("La longitud de hotspots y labels debe coincidir")

        trajectories: dict[int, list[MovementStep]] = {}
        for fire_id in np.unique(labels):
            fid = int(fire_id)
            if fid < 0:
                continue
            indices = np.flatnonzero(labels == fid)
            sub_hotspots = hotspots.slice_by_indices(indices)
            trajectories[fid] = self.analyze_fire(fid, sub_hotspots)

        return trajectories
