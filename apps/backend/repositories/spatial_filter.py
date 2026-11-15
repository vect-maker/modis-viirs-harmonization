from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from geojson_pydantic import MultiPolygon, Polygon
from pydantic import TypeAdapter, ValidationError
from shapely.geometry import shape

_GEOJSON_POLYGON_ADAPTER: TypeAdapter[Polygon | MultiPolygon] = TypeAdapter(
    Polygon | MultiPolygon
)


def parse_geojson_polygon_to_wkt(
    raw_geojson: str | dict[str, Any] | None,
) -> str | None:
    """Validate a GeoJSON Polygon/MultiPolygon (RFC 7946) and return its WKT."""
    if raw_geojson is None:
        return None
    if isinstance(raw_geojson, str):
        stripped = raw_geojson.strip()
        if not stripped:
            return None
        try:
            payload: Any = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid GeoJSON JSON: {exc.msg}") from exc
    else:
        payload = raw_geojson

    try:
        geojson_geom = _GEOJSON_POLYGON_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid GeoJSON Polygon/MultiPolygon: {exc}") from exc

    geom = shape(geojson_geom)
    if geom.is_empty or not geom.is_valid:
        raise ValueError("Invalid polygon geometry")
    return geom.wkt


@dataclass(slots=True)
class SpatialAreaFilter:
    """Filtro espacial reutilizable compatible con PostGIS (`geom`) y SQLite."""

    min_lat: float | None = None
    max_lat: float | None = None
    min_lon: float | None = None
    max_lon: float | None = None
    center_lat: float | None = None
    center_lon: float | None = None
    radius_km: float | None = None
    polygon_wkt: str | None = None

    def validate(self) -> None:
        if (
            self.min_lat is not None
            and self.max_lat is not None
            and self.min_lat > self.max_lat
        ):
            raise ValueError("min_lat no puede ser mayor que max_lat")
        if (
            self.min_lon is not None
            and self.max_lon is not None
            and self.min_lon > self.max_lon
        ):
            raise ValueError("min_lon no puede ser mayor que max_lon")

        circle_parts = [self.center_lat, self.center_lon, self.radius_km]
        if any(p is not None for p in circle_parts) and not all(
            p is not None for p in circle_parts
        ):
            raise ValueError(
                "Para filtrar por radio debes enviar center_lat, center_lon y radius_km"
            )
        if self.radius_km is not None and self.radius_km <= 0:
            raise ValueError("radius_km debe ser mayor que 0")

        if self.polygon_wkt is not None:
            wkt = self.polygon_wkt.strip().upper()
            if not (wkt.startswith("POLYGON") or wkt.startswith("MULTIPOLYGON")):
                raise ValueError("polygon_wkt debe iniciar con POLYGON o MULTIPOLYGON")


def build_spatial_sql(
    area: SpatialAreaFilter,
    dialect: str,
    geom_col: str = "geom",
    lat_col: str = "latitude",
    lon_col: str = "longitude",
) -> tuple[list[str], dict[str, Any]]:
    """
    Construye condiciones SQL espaciales.
    En PostgreSQL usa `geom` (GEOMETRY(Point, 4326)) con funciones PostGIS
    (`ST_MakeEnvelope`, `ST_DWithin`, `ST_Intersects`) para aprovechar el índice GIST.
    """
    area.validate()
    conditions: list[str] = []
    params: dict[str, Any] = {}

    has_bbox = any(
        v is not None
        for v in (area.min_lat, area.max_lat, area.min_lon, area.max_lon)
    )
    if has_bbox:
        if (
            dialect == "postgresql"
            and area.min_lat is not None
            and area.max_lat is not None
            and area.min_lon is not None
            and area.max_lon is not None
        ):
            conditions.append(
                f"{geom_col} && ST_MakeEnvelope(:sp_min_lon, :sp_min_lat, :sp_max_lon, :sp_max_lat, 4326)"
            )
            params["sp_min_lon"] = area.min_lon
            params["sp_min_lat"] = area.min_lat
            params["sp_max_lon"] = area.max_lon
            params["sp_max_lat"] = area.max_lat
        else:
            if area.min_lat is not None:
                conditions.append(f"{lat_col} >= :sp_min_lat")
                params["sp_min_lat"] = area.min_lat
            if area.max_lat is not None:
                conditions.append(f"{lat_col} <= :sp_max_lat")
                params["sp_max_lat"] = area.max_lat
            if area.min_lon is not None:
                conditions.append(f"{lon_col} >= :sp_min_lon")
                params["sp_min_lon"] = area.min_lon
            if area.max_lon is not None:
                conditions.append(f"{lon_col} <= :sp_max_lon")
                params["sp_max_lon"] = area.max_lon

    if (
        area.center_lat is not None
        and area.center_lon is not None
        and area.radius_km is not None
    ):
        if dialect == "postgresql":
            conditions.append(
                f"ST_DWithin({geom_col}::geography, "
                "ST_SetSRID(ST_MakePoint(:sp_center_lon, :sp_center_lat), 4326)::geography, "
                ":sp_radius_m)"
            )
            params["sp_center_lon"] = area.center_lon
            params["sp_center_lat"] = area.center_lat
            params["sp_radius_m"] = area.radius_km * 1000.0
        else:
            # Aproximación rectangular rápida para SQLite + filtro Haversine aproximado
            dlat = area.radius_km / 111.0
            dlon = area.radius_km / max(
                1e-6, 111.0 * abs(math.cos(math.radians(area.center_lat)))
            )
            conditions.append(
                f"{lat_col} BETWEEN :sp_c_min_lat AND :sp_c_max_lat "
                f"AND {lon_col} BETWEEN :sp_c_min_lon AND :sp_c_max_lon"
            )
            params["sp_c_min_lat"] = area.center_lat - dlat
            params["sp_c_max_lat"] = area.center_lat + dlat
            params["sp_c_min_lon"] = area.center_lon - dlon
            params["sp_c_max_lon"] = area.center_lon + dlon

    if area.polygon_wkt is not None:
        if dialect == "postgresql":
            conditions.append(
                f"ST_Intersects({geom_col}, ST_GeomFromText(:sp_polygon_wkt, 4326))"
            )
            params["sp_polygon_wkt"] = area.polygon_wkt.strip()
        else:
            # En SQLite sin PostGIS usamos el bounding box del WKT como respaldo
            coords_part = area.polygon_wkt.split("((")[-1].split("))")[0]
            lons: list[float] = []
            lats: list[float] = []
            for pair in coords_part.split(","):
                parts = pair.strip().split()
                if len(parts) >= 2:
                    lons.append(float(parts[0]))
                    lats.append(float(parts[1]))
            if lons and lats:
                conditions.append(
                    f"{lat_col} BETWEEN :sp_poly_min_lat AND :sp_poly_max_lat "
                    f"AND {lon_col} BETWEEN :sp_poly_min_lon AND :sp_poly_max_lon"
                )
                params["sp_poly_min_lat"] = min(lats)
                params["sp_poly_max_lat"] = max(lats)
                params["sp_poly_min_lon"] = min(lons)
                params["sp_poly_max_lon"] = max(lons)

    return conditions, params
