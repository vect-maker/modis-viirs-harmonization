"""Agrupación espacial y temporal de hotspots con Scikit-learn DBSCAN y BallTree."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.neighbors import BallTree

from analytics.HotspotProcessor import PreparedHotspots

EARTH_RADIUS_KM = 6371.0


@dataclass(slots=True)
class ClusteringResult:
    """Resultado de agrupación espaciotemporal sin duplicar los datos fuente."""

    labels: np.ndarray
    cluster_count: int
    noise_count: int
    eps_km: float
    min_samples: int
    time_window_hours: float
    max_time_window_hours: float


class FireClusterer:
    """
    Agrupa detecciones de incendios combinando proximidad espacial (Haversine + BallTree)
    y continuidad temporal con ventana dinámica: cuando un incendio es confirmado
    (>= min_samples), su tolerancia temporal se amplía progresivamente hasta
    max_time_window_hours para no fragmentarlo por pausas de detección o nubosidad.
    """

    def __init__(
        self,
        eps_km: float = 1.0,
        min_samples: int = 2,
        time_window_hours: float = 24.0,
        max_time_window_hours: float = 72.0,
        window_extension_hours: float = 12.0,
    ) -> None:
        if eps_km <= 0:
            raise ValueError("eps_km debe ser mayor que 0")
        if min_samples < 1:
            raise ValueError("min_samples debe ser al menos 1")
        if time_window_hours <= 0:
            raise ValueError("time_window_hours debe ser mayor que 0")
        if max_time_window_hours < time_window_hours:
            raise ValueError("max_time_window_hours debe ser >= time_window_hours")
        if window_extension_hours < 0:
            raise ValueError("window_extension_hours no puede ser negativo")

        self.eps_km = float(eps_km)
        self.min_samples = int(min_samples)
        self.time_window_hours = float(time_window_hours)
        self.max_time_window_hours = float(max_time_window_hours)
        self.window_extension_hours = float(window_extension_hours)

    def build_ball_tree(self, coords_rad: np.ndarray) -> BallTree:
        """Construye un BallTree geográfico con métrica Haversine sobre radianes."""
        if len(coords_rad) == 0:
            raise ValueError("No se puede construir BallTree sin coordenadas")
        return BallTree(coords_rad, metric="haversine")

    def query_radius_km(
        self,
        tree: BallTree,
        query_coords_rad: np.ndarray,
        radius_km: float,
    ) -> np.ndarray:
        """Consulta vecinos dentro de un radio en kilómetros usando BallTree."""
        if radius_km <= 0:
            raise ValueError("radius_km debe ser mayor que 0")
        return tree.query_radius(query_coords_rad, r=radius_km / EARTH_RADIUS_KM)

    def _allowed_window_sec(self, episode_size: int) -> float:
        """
        Calcula la ventana temporal permitida en segundos según el tamaño del episodio.
        Si aún no alcanza min_samples usa time_window_hours; una vez confirmado el
        incendio, amplía la ventana gradualmente hasta max_time_window_hours.
        """
        if episode_size < self.min_samples:
            return self.time_window_hours * 3600.0

        extra_detections = episode_size - self.min_samples + 1
        dynamic_hours = min(
            self.max_time_window_hours,
            self.time_window_hours + extra_detections * self.window_extension_hours,
        )
        return dynamic_hours * 3600.0

    def _split_by_dynamic_window(
        self,
        ordered_indices: np.ndarray,
        timestamps_sec: np.ndarray,
    ) -> list[np.ndarray]:
        """Divide índices ordenados cronológicamente usando ventana dinámica."""
        if len(ordered_indices) == 0:
            return []

        episodes: list[np.ndarray] = []
        start = 0

        for pos in range(1, len(ordered_indices)):
            current_size = pos - start
            allowed_sec = self._allowed_window_sec(current_size)
            gap_sec = timestamps_sec[ordered_indices[pos]] - timestamps_sec[ordered_indices[pos - 1]]

            if gap_sec > allowed_sec:
                episodes.append(ordered_indices[start:pos])
                start = pos

        episodes.append(ordered_indices[start:])
        return episodes

    def fit_predict(self, hotspots: PreparedHotspots) -> ClusteringResult:
        """
        Ejecuta clustering espacial-temporal en memoria O(N):
        1. Agrupa componentes espaciales conexas con DBSCAN (haversine, ball_tree).
        2. Separa cada componente espacial con ventana temporal dinámica.
        3. Evalúa densidad (min_samples) con DBSCAN dentro de cada episodio temporal
           para detectar ruido (-1) sin mezclar incendios separados en el tiempo.
        """
        n = len(hotspots)
        if n == 0:
            return ClusteringResult(
                labels=np.empty(0, dtype=np.int32),
                cluster_count=0,
                noise_count=0,
                eps_km=self.eps_km,
                min_samples=self.min_samples,
                time_window_hours=self.time_window_hours,
                max_time_window_hours=self.max_time_window_hours,
            )

        eps_rad = self.eps_km / EARTH_RADIUS_KM

        spatial_dbscan = DBSCAN(
            eps=eps_rad,
            min_samples=1,
            metric="haversine",
            algorithm="ball_tree",
        )
        spatial_labels = spatial_dbscan.fit_predict(hotspots.coords_rad)

        final_labels = np.full(n, -1, dtype=np.int32)
        next_cluster_id = 0

        for sp_label in np.unique(spatial_labels):
            if sp_label == -1:
                continue

            sp_indices = np.flatnonzero(spatial_labels == sp_label)
            if len(sp_indices) < self.min_samples:
                continue

            order = np.argsort(hotspots.timestamps_sec[sp_indices], kind="mergesort")
            ordered_indices = sp_indices[order]
            episodes = self._split_by_dynamic_window(ordered_indices, hotspots.timestamps_sec)

            for ep_indices in episodes:
                if len(ep_indices) < self.min_samples:
                    continue

                ep_dbscan = DBSCAN(
                    eps=eps_rad,
                    min_samples=self.min_samples,
                    metric="haversine",
                    algorithm="ball_tree",
                )
                ep_labels = ep_dbscan.fit_predict(hotspots.coords_rad[ep_indices])

                for local_lbl in np.unique(ep_labels):
                    if local_lbl == -1:
                        continue
                    member_mask = ep_labels == local_lbl
                    final_labels[ep_indices[member_mask]] = next_cluster_id
                    next_cluster_id += 1

        noise_count = int(np.sum(final_labels == -1))
        return ClusteringResult(
            labels=final_labels,
            cluster_count=next_cluster_id,
            noise_count=noise_count,
            eps_km=self.eps_km,
            min_samples=self.min_samples,
            time_window_hours=self.time_window_hours,
            max_time_window_hours=self.max_time_window_hours,
        )
