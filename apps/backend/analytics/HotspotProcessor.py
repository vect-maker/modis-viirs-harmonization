"""Limpieza, validación y preparación de hotspots en arreglos NumPy compactos."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np


@dataclass(slots=True)
class PreparedHotspots:
    """Contenedor ligero en memoria basado en arreglos NumPy."""

    ids: list[str]
    latitudes: np.ndarray
    longitudes: np.ndarray
    coords_rad: np.ndarray
    timestamps_sec: np.ndarray
    datetimes: list[datetime]
    frp: np.ndarray
    dropped_count: int = 0

    def __len__(self) -> int:
        return len(self.ids)

    @property
    def is_empty(self) -> bool:
        return len(self.ids) == 0

    def slice_by_indices(self, indices: np.ndarray) -> PreparedHotspots:
        """Retorna un subconjunto indexado sin copiar datos innecesariamente."""
        idx_list = indices.tolist()
        return PreparedHotspots(
            ids=[self.ids[i] for i in idx_list],
            latitudes=self.latitudes[indices],
            longitudes=self.longitudes[indices],
            coords_rad=self.coords_rad[indices],
            timestamps_sec=self.timestamps_sec[indices],
            datetimes=[self.datetimes[i] for i in idx_list],
            frp=self.frp[indices],
            dropped_count=0,
        )


class HotspotProcessor:
    """
    Limpia y transforma registros de hotspots (ORM, dicts o filas SQL)
    a arreglos NumPy compactos sin pasar por DataFrames pesados.
    """

    @staticmethod
    def _extract_field(record: Any, field: str) -> Any:
        if isinstance(record, Mapping):
            return record.get(field)
        return getattr(record, field, None)

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    def prepare(self, records: Iterable[Any]) -> PreparedHotspots:
        """
        Valida coordenadas, fechas y FRP, descartando registros corruptos.

        Reglas:
        - latitude en [-90.0, 90.0]
        - longitude en [-180.0, 180.0]
        - acq_datetime válido y no nulo
        - frp negativo se normaliza a 0.0; nulo se mantiene como 0.0 para agregación
        """
        ids: list[str] = []
        lats: list[float] = []
        lons: list[float] = []
        dts: list[datetime] = []
        ts_sec: list[float] = []
        frps: list[float] = []
        dropped = 0

        for idx, rec in enumerate(records):
            raw_lat = self._extract_field(rec, "latitude")
            raw_lon = self._extract_field(rec, "longitude")
            raw_dt = self._extract_field(rec, "acq_datetime")
            raw_frp = self._extract_field(rec, "frp")
            raw_id = self._extract_field(rec, "id")

            if raw_lat is None or raw_lon is None:
                dropped += 1
                continue

            try:
                lat = float(raw_lat)
                lon = float(raw_lon)
            except (TypeError, ValueError):
                dropped += 1
                continue

            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                dropped += 1
                continue

            dt = self._parse_datetime(raw_dt)
            if dt is None:
                dropped += 1
                continue

            try:
                frp_val = max(0.0, float(raw_frp)) if raw_frp is not None else 0.0
            except (TypeError, ValueError):
                frp_val = 0.0

            ids.append(str(raw_id) if raw_id is not None else str(idx))
            lats.append(lat)
            lons.append(lon)
            dts.append(dt)
            ts_sec.append(dt.timestamp())
            frps.append(frp_val)

        if not ids:
            empty_f64 = np.empty(0, dtype=np.float64)
            empty_rad = np.empty((0, 2), dtype=np.float64)
            return PreparedHotspots(
                ids=[],
                latitudes=empty_f64,
                longitudes=empty_f64,
                coords_rad=empty_rad,
                timestamps_sec=empty_f64,
                datetimes=[],
                frp=empty_f64,
                dropped_count=dropped,
            )

        lat_arr = np.asarray(lats, dtype=np.float64)
        lon_arr = np.asarray(lons, dtype=np.float64)
        coords_rad = np.column_stack((np.radians(lat_arr), np.radians(lon_arr)))

        return PreparedHotspots(
            ids=ids,
            latitudes=lat_arr,
            longitudes=lon_arr,
            coords_rad=coords_rad,
            timestamps_sec=np.asarray(ts_sec, dtype=np.float64),
            datetimes=dts,
            frp=np.asarray(frps, dtype=np.float64),
            dropped_count=dropped,
        )
