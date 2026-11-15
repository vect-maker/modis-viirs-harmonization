from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Literal

import numpy as np
from sqlalchemy import text
from sqlmodel import Session

from analytics.DashboardAnalytics import compute_descriptive_stats
from repositories.spatial_filter import SpatialAreaFilter, build_spatial_sql


def _as_datetime(value: Any) -> datetime:
    """SQLite devuelve texto en agregados MIN/MAX; PostgreSQL devuelve datetime."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


class DashboardRepository:
    """
    Repositorio optimizado con SQLModel/SQLAlchemy que delega las agregaciones,
    correlaciones, mapeos de confianza y agrupamientos espaciales/temporales a SQL.
    """

    def __init__(self, session: Session):
        self.session = session
        bind = session.get_bind()
        self.dialect = bind.dialect.name if bind is not None else "postgresql"

    def _confidence_sql(self, high_value: int = 90) -> str:
        hv = int(high_value)
        if self.dialect == "postgresql":
            return (
                "CASE "
                "WHEN LOWER(TRIM(CAST(confidence AS TEXT))) IN ('l', 'low') THEN 15 "
                "WHEN LOWER(TRIM(CAST(confidence AS TEXT))) IN ('n', 'nominal') THEN 50 "
                f"WHEN LOWER(TRIM(CAST(confidence AS TEXT))) IN ('h', 'high') THEN {hv} "
                "WHEN TRIM(CAST(confidence AS TEXT)) ~ '^[0-9]+(\\.[0-9]+)?$' "
                "THEN CAST(ROUND(CAST(TRIM(CAST(confidence AS TEXT)) AS NUMERIC)) AS INTEGER) "
                "WHEN LOWER(TRIM(COALESCE(CAST(confidence_class AS TEXT), ''))) IN ('l', 'low') THEN 15 "
                "WHEN LOWER(TRIM(COALESCE(CAST(confidence_class AS TEXT), ''))) IN ('n', 'nominal') THEN 50 "
                f"WHEN LOWER(TRIM(COALESCE(CAST(confidence_class AS TEXT), ''))) IN ('h', 'high') THEN {hv} "
                "ELSE NULL END"
            )
        return (
            "CASE "
            "WHEN LOWER(TRIM(CAST(confidence AS TEXT))) IN ('l', 'low') THEN 15 "
            "WHEN LOWER(TRIM(CAST(confidence AS TEXT))) IN ('n', 'nominal') THEN 50 "
            f"WHEN LOWER(TRIM(CAST(confidence AS TEXT))) IN ('h', 'high') THEN {hv} "
            "WHEN TRIM(CAST(confidence AS TEXT)) GLOB '[0-9]*' AND TRIM(CAST(confidence AS TEXT)) != '' "
            "THEN CAST(ROUND(CAST(TRIM(CAST(confidence AS TEXT)) AS REAL)) AS INTEGER) "
            "WHEN LOWER(TRIM(COALESCE(CAST(confidence_class AS TEXT), ''))) IN ('l', 'low') THEN 15 "
            "WHEN LOWER(TRIM(COALESCE(CAST(confidence_class AS TEXT), ''))) IN ('n', 'nominal') THEN 50 "
            f"WHEN LOWER(TRIM(COALESCE(CAST(confidence_class AS TEXT), ''))) IN ('h', 'high') THEN {hv} "
            "ELSE NULL END"
        )

    def _year_expr(self) -> str:
        if self.dialect == "postgresql":
            return "CAST(EXTRACT(YEAR FROM acq_datetime) AS INTEGER)"
        return "CAST(strftime('%Y', acq_datetime) AS INTEGER)"

    def _month_expr(self) -> str:
        if self.dialect == "postgresql":
            return "CAST(EXTRACT(MONTH FROM acq_datetime) AS INTEGER)"
        return "CAST(strftime('%m', acq_datetime) AS INTEGER)"

    @staticmethod
    def _build_filters(
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
    ) -> tuple[list[str], dict[str, Any]]:
        conditions: list[str] = []
        params: dict[str, Any] = {}
        if start_date is not None:
            conditions.append("acq_datetime >= :start_date")
            params["start_date"] = start_date
        if end_date is not None:
            conditions.append("acq_datetime <= :end_date")
            params["end_date"] = end_date
        if min_lat is not None:
            conditions.append("latitude >= :min_lat")
            params["min_lat"] = min_lat
        if max_lat is not None:
            conditions.append("latitude <= :max_lat")
            params["max_lat"] = max_lat
        if min_lon is not None:
            conditions.append("longitude >= :min_lon")
            params["min_lon"] = min_lon
        if max_lon is not None:
            conditions.append("longitude <= :max_lon")
            params["max_lon"] = max_lon
        return conditions, params

    def get_confidence_value_counts(
        self,
        high_value: int = 90,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        country: str | None = None,
        polygon_wkt: str | None = None,
        metric: Literal["raw", "harmonized"] = "raw",
    ) -> list[tuple[int, int]]:
        conf_expr = self._confidence_sql(high_value)
        conditions, params = self._build_filters(start_date=start_date, end_date=end_date)
        area_conditions, area_params = self._area_conditions(country, polygon_wkt)
        conditions.extend(area_conditions)
        params.update(area_params)
        conditions.append("(confidence IS NOT NULL OR confidence_class IS NOT NULL)")
        if metric == "harmonized":
            conditions.append("COALESCE(harmonized_weight, 1.0) > 0")
        where_sql = " AND ".join(conditions)

        cnt_expr = (
            "GREATEST(1, CAST(ROUND(COALESCE(SUM(w), 0.0)) AS INTEGER))"
            if metric == "harmonized" and self.dialect == "postgresql"
            else (
                "MAX(1, CAST(ROUND(COALESCE(SUM(w), 0.0)) AS INTEGER))"
                if metric == "harmonized"
                else "COUNT(*)"
            )
        )
        weight_col = (
            ", COALESCE(harmonized_weight, 1.0) AS w"
            if metric == "harmonized"
            else ""
        )

        query = text(
            f"""
            SELECT conf_val, {cnt_expr} AS cnt
            FROM (
                SELECT {conf_expr} AS conf_val{weight_col}
                FROM hotspots
                WHERE {where_sql}
            ) sub
            WHERE conf_val IS NOT NULL
            GROUP BY conf_val
            ORDER BY conf_val ASC
            """
        )
        rows = self.session.execute(query, params).all()
        return [(int(r[0]), int(r[1])) for r in rows]

    def get_correlations(
        self,
        high_value: int = 90,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        country: str | None = None,
        polygon_wkt: str | None = None,
        metric: Literal["raw", "harmonized"] = "raw",
    ) -> list[dict[str, Any]]:
        conf_expr = self._confidence_sql(high_value)
        conditions, params = self._build_filters(start_date=start_date, end_date=end_date)
        area_conditions, area_params = self._area_conditions(country, polygon_wkt)
        conditions.extend(area_conditions)
        params.update(area_params)
        if metric == "harmonized":
            conditions.append("COALESCE(harmonized_weight, 1.0) > 0")
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        frp_expr = "COALESCE(harmonized_frp, frp)" if metric == "harmonized" else "frp"

        pairs = [
            ("frp", "confidence", "frp", "conf_val"),
            ("frp", "bright_tir", "frp", "bright_tir"),
            ("frp", "bright_mir", "frp", "bright_mir"),
            ("confidence", "bright_tir", "conf_val", "bright_tir"),
            ("confidence", "bright_mir", "conf_val", "bright_mir"),
            ("bright_tir", "bright_mir", "bright_tir", "bright_mir"),
        ]

        results: list[dict[str, Any]] = []
        for name_x, name_y, col_x, col_y in pairs:
            query = text(
                f"""
                WITH base AS (
                    SELECT
                        CAST({frp_expr} AS DOUBLE PRECISION) AS frp,
                        CAST({conf_expr} AS DOUBLE PRECISION) AS conf_val,
                        CAST(bright_tir AS DOUBLE PRECISION) AS bright_tir,
                        CAST(bright_mir AS DOUBLE PRECISION) AS bright_mir
                    FROM hotspots
                    {where_sql}
                )
                SELECT
                    COUNT(*) AS n,
                    AVG({col_x}) AS mean_x,
                    AVG({col_y}) AS mean_y,
                    SUM({col_x} * {col_x}) AS sum_xx,
                    SUM({col_y} * {col_y}) AS sum_yy,
                    SUM({col_x} * {col_y}) AS sum_xy,
                    SUM({col_x}) AS sum_x,
                    SUM({col_y}) AS sum_y
                FROM base
                WHERE {col_x} IS NOT NULL AND {col_y} IS NOT NULL
                """
                if self.dialect == "postgresql"
                else f"""
                WITH base AS (
                    SELECT
                        CAST({frp_expr} AS REAL) AS frp,
                        CAST({conf_expr} AS REAL) AS conf_val,
                        CAST(bright_tir AS REAL) AS bright_tir,
                        CAST(bright_mir AS REAL) AS bright_mir
                    FROM hotspots
                    {where_sql}
                )
                SELECT
                    COUNT(*) AS n,
                    AVG({col_x}) AS mean_x,
                    AVG({col_y}) AS mean_y,
                    SUM({col_x} * {col_x}) AS sum_xx,
                    SUM({col_y} * {col_y}) AS sum_yy,
                    SUM({col_x} * {col_y}) AS sum_xy,
                    SUM({col_x}) AS sum_x,
                    SUM({col_y}) AS sum_y
                FROM base
                WHERE {col_x} IS NOT NULL AND {col_y} IS NOT NULL
                """
            )
            row = self.session.execute(query, params).one()
            n = int(row[0] or 0)
            if n < 2:
                results.append(
                    {
                        "x": name_x,
                        "y": name_y,
                        "n": n,
                        "pearson_r": None,
                        "r2": None,
                        "mean_x": round(float(row[1]), 4) if row[1] is not None else None,
                        "mean_y": round(float(row[2]), 4) if row[2] is not None else None,
                    }
                )
                continue

            sum_xx, sum_yy, sum_xy = float(row[3]), float(row[4]), float(row[5])
            sum_x, sum_y = float(row[6]), float(row[7])
            var_x = max(0.0, sum_xx - (sum_x * sum_x) / n)
            var_y = max(0.0, sum_yy - (sum_y * sum_y) / n)
            cov_xy = sum_xy - (sum_x * sum_y) / n
            denom = math.sqrt(var_x * var_y)
            r = (cov_xy / denom) if denom > 0 else 0.0
            r = max(-1.0, min(1.0, r))
            std_x = math.sqrt(var_x / (n - 1)) if n > 1 else 0.0
            std_y = math.sqrt(var_y / (n - 1)) if n > 1 else 0.0

            results.append(
                {
                    "x": name_x,
                    "y": name_y,
                    "n": n,
                    "pearson_r": round(r, 6),
                    "r2": round(r * r, 6),
                    "mean_x": round(float(row[1]), 4),
                    "std_x": round(std_x, 4),
                    "mean_y": round(float(row[2]), 4),
                    "std_y": round(std_y, 4),
                }
            )
        return results

    def get_annual_stats(
        self,
        high_value: int = 90,
        start_year: int = 2001,
        end_year: int = 2025,
        country: str | None = None,
        polygon_wkt: str | None = None,
        metric: Literal["raw", "harmonized"] = "raw",
    ) -> list[dict[str, Any]]:
        conf_expr = self._confidence_sql(high_value)
        year_expr = self._year_expr()
        area_conditions, area_params = self._area_conditions(country, polygon_wkt)
        if metric == "harmonized":
            area_conditions.append("COALESCE(harmonized_weight, 1.0) > 0")
        area_sql = "".join(f" AND {c}" for c in area_conditions)
        frp_expr = "COALESCE(harmonized_frp, frp)" if metric == "harmonized" else "frp"
        params: dict[str, Any] = {
            "start_year": start_year,
            "end_year": end_year,
            **area_params,
        }

        if self.dialect == "postgresql":
            query = text(
                f"""
                WITH base AS (
                    SELECT
                        {year_expr} AS yr,
                        {frp_expr} AS frp,
                        CAST({conf_expr} AS DOUBLE PRECISION) AS conf_val,
                        bright_tir,
                        bright_mir
                    FROM hotspots
                    WHERE acq_datetime IS NOT NULL
                      AND {year_expr} BETWEEN :start_year AND :end_year{area_sql}
                )
                SELECT
                    yr,
                    COUNT(*) AS total_rows,
                    COUNT(frp) AS frp_count, SUM(frp) AS frp_sum, AVG(frp) AS frp_mean,
                    STDDEV_SAMP(frp) AS frp_std, MIN(frp) AS frp_min,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY frp) AS frp_p25,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY frp) AS frp_median,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY frp) AS frp_p75,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY frp) AS frp_p90,
                    MAX(frp) AS frp_max,

                    COUNT(conf_val) AS conf_count, SUM(conf_val) AS conf_sum, AVG(conf_val) AS conf_mean,
                    STDDEV_SAMP(conf_val) AS conf_std, MIN(conf_val) AS conf_min,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY conf_val) AS conf_p25,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY conf_val) AS conf_median,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY conf_val) AS conf_p75,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY conf_val) AS conf_p90,
                    MAX(conf_val) AS conf_max,

                    COUNT(bright_tir) AS tir_count, SUM(bright_tir) AS tir_sum, AVG(bright_tir) AS tir_mean,
                    STDDEV_SAMP(bright_tir) AS tir_std, MIN(bright_tir) AS tir_min,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY bright_tir) AS tir_p25,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY bright_tir) AS tir_median,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY bright_tir) AS tir_p75,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY bright_tir) AS tir_p90,
                    MAX(bright_tir) AS tir_max,

                    COUNT(bright_mir) AS mir_count, SUM(bright_mir) AS mir_sum, AVG(bright_mir) AS mir_mean,
                    STDDEV_SAMP(bright_mir) AS mir_std, MIN(bright_mir) AS mir_min,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY bright_mir) AS mir_p25,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY bright_mir) AS mir_median,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY bright_mir) AS mir_p75,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY bright_mir) AS mir_p90,
                    MAX(bright_mir) AS mir_max
                FROM base
                WHERE yr BETWEEN :start_year AND :end_year
                GROUP BY yr
                ORDER BY yr ASC
                """
            )
            rows = self.session.execute(query, params).mappings()

            def _pack(r: Any, prefix: str) -> dict[str, Any]:
                p25 = r[f"{prefix}_p25"]
                p75 = r[f"{prefix}_p75"]
                iqr = round(float(p75 - p25), 4) if p25 is not None and p75 is not None else None
                return {
                    "count": int(r[f"{prefix}_count"] or 0),
                    "sum": round(float(r[f"{prefix}_sum"]), 4) if r[f"{prefix}_sum"] is not None else None,
                    "mean": round(float(r[f"{prefix}_mean"]), 4) if r[f"{prefix}_mean"] is not None else None,
                    "std": round(float(r[f"{prefix}_std"]), 4) if r[f"{prefix}_std"] is not None else None,
                    "min": round(float(r[f"{prefix}_min"]), 4) if r[f"{prefix}_min"] is not None else None,
                    "p25": round(float(p25), 4) if p25 is not None else None,
                    "median": round(float(r[f"{prefix}_median"]), 4) if r[f"{prefix}_median"] is not None else None,
                    "p75": round(float(p75), 4) if p75 is not None else None,
                    "p90": round(float(r[f"{prefix}_p90"]), 4) if r[f"{prefix}_p90"] is not None else None,
                    "iqr": iqr,
                    "max": round(float(r[f"{prefix}_max"]), 4) if r[f"{prefix}_max"] is not None else None,
                }

            return [
                {
                    "year": int(r["yr"]),
                    "total_hotspots": int(r["total_rows"]),
                    "frp": _pack(r, "frp"),
                    "confidence": _pack(r, "conf"),
                    "bright_tir": _pack(r, "tir"),
                    "bright_mir": _pack(r, "mir"),
                }
                for r in rows
            ]

        # Fallback SQLite para pruebas unitarias (sin PERCENTILE_CONT nativo)
        query = text(
            f"""
            SELECT
                {year_expr} AS yr,
                {frp_expr} AS frp,
                {conf_expr} AS conf_val,
                bright_tir,
                bright_mir
            FROM hotspots
            WHERE acq_datetime IS NOT NULL
              AND {year_expr} BETWEEN :start_year AND :end_year{area_sql}
            ORDER BY yr ASC
            """
        )
        rows = self.session.execute(query, params).all()
        by_year: dict[int, dict[str, list[float]]] = {}
        totals: dict[int, int] = {}
        for yr, frp, conf, tir, mir in rows:
            y = int(yr)
            totals[y] = totals.get(y, 0) + 1
            bucket = by_year.setdefault(
                y, {"frp": [], "confidence": [], "bright_tir": [], "bright_mir": []}
            )
            if frp is not None:
                bucket["frp"].append(float(frp))
            if conf is not None:
                bucket["confidence"].append(float(conf))
            if tir is not None:
                bucket["bright_tir"].append(float(tir))
            if mir is not None:
                bucket["bright_mir"].append(float(mir))

        return [
            {
                "year": y,
                "total_hotspots": totals[y],
                "frp": compute_descriptive_stats(np.array(b["frp"], dtype=np.float64)),
                "confidence": compute_descriptive_stats(
                    np.array(b["confidence"], dtype=np.float64)
                ),
                "bright_tir": compute_descriptive_stats(
                    np.array(b["bright_tir"], dtype=np.float64)
                ),
                "bright_mir": compute_descriptive_stats(
                    np.array(b["bright_mir"], dtype=np.float64)
                ),
            }
            for y, b in sorted(by_year.items())
        ]

    def get_spatial_density(
        self,
        cell_size_deg: float = 0.1,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        limit: int = 5000,
        country: str | None = None,
        polygon_wkt: str | None = None,
        metric: Literal["raw", "harmonized"] = "raw",
    ) -> list[dict[str, Any]]:
        cells, _, _ = self.get_spatial_density_with_totals(
            cell_size_deg=cell_size_deg,
            start_date=start_date,
            end_date=end_date,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            limit=limit,
            country=country,
            polygon_wkt=polygon_wkt,
            metric=metric,
        )
        return cells

    def get_spatial_density_with_totals(
        self,
        cell_size_deg: float = 0.1,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        limit: int = 5000,
        country: str | None = None,
        polygon_wkt: str | None = None,
        metric: Literal["raw", "harmonized"] = "raw",
    ) -> tuple[list[dict[str, Any]], int, int]:
        conditions, params = self._build_filters(
            start_date=start_date,
            end_date=end_date,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
        )
        area_conditions, area_params = self._area_conditions(country, polygon_wkt)
        conditions.extend(area_conditions)
        params.update(area_params)
        conditions.extend(["latitude IS NOT NULL", "longitude IS NOT NULL"])
        if metric == "harmonized":
            conditions.append("COALESCE(harmonized_weight, 1.0) > 0")
        params["cell_size"] = cell_size_deg
        params["limit"] = limit
        where_sql = " AND ".join(conditions)

        # FLOOR(x / c) * c + c / 2 funciona en PostgreSQL y SQLite
        if self.dialect == "postgresql":
            lat_bin = "FLOOR(latitude / :cell_size) * :cell_size + (:cell_size / 2.0)"
            lon_bin = "FLOOR(longitude / :cell_size) * :cell_size + (:cell_size / 2.0)"
            cnt_expr = (
                "GREATEST(1, CAST(ROUND(COALESCE(SUM(harmonized_weight), 0.0)) AS INTEGER))"
                if metric == "harmonized"
                else "COUNT(*)"
            )
        else:
            lat_bin = "ROUND(latitude / :cell_size - 0.5) * :cell_size + (:cell_size / 2.0)"
            lon_bin = "ROUND(longitude / :cell_size - 0.5) * :cell_size + (:cell_size / 2.0)"
            cnt_expr = (
                "MAX(1, CAST(ROUND(COALESCE(SUM(harmonized_weight), 0.0)) AS INTEGER))"
                if metric == "harmonized"
                else "COUNT(*)"
            )
        frp_col = "COALESCE(harmonized_frp, frp)" if metric == "harmonized" else "frp"

        totals_query = text(
            f"""
            SELECT
                COUNT(*) AS total_cells,
                COALESCE(SUM(cnt), 0) AS total_hotspots
            FROM (
                SELECT {cnt_expr} AS cnt
                FROM hotspots
                WHERE {where_sql}
                GROUP BY {lat_bin}, {lon_bin}
            ) all_cells
            """
        )
        tot_row = self.session.execute(totals_query, params).one()
        total_cells_all = int(tot_row[0] or 0)
        total_hotspots_all = int(tot_row[1] or 0)

        query = text(
            f"""
            SELECT
                {lat_bin} AS cell_lat,
                {lon_bin} AS cell_lon,
                {cnt_expr} AS cnt,
                COALESCE(SUM({frp_col}), 0.0) AS sum_frp,
                AVG({frp_col}) AS avg_frp,
                MAX({frp_col}) AS max_frp
            FROM hotspots
            WHERE {where_sql}
            GROUP BY cell_lat, cell_lon
            ORDER BY cnt DESC
            LIMIT :limit
            """
        )
        rows = self.session.execute(query, params).all()
        cells = [
            {
                "cell_lat": round(float(r[0]), 5),
                "cell_lon": round(float(r[1]), 5),
                "count": int(r[2]),
                "sum_frp": round(float(r[3] or 0.0), 4),
                "avg_frp": round(float(r[4]), 4) if r[4] is not None else None,
                "max_frp": round(float(r[5]), 4) if r[5] is not None else None,
            }
            for r in rows
        ]
        return cells, total_cells_all, total_hotspots_all

    def _area_conditions(
        self,
        country: str | None = None,
        polygon_wkt: str | None = None,
    ) -> tuple[list[str], dict[str, Any]]:
        """Filtros de país y polígono (PostGIS en PostgreSQL, bbox en SQLite)."""
        conditions: list[str] = []
        params: dict[str, Any] = {}
        if country is not None and country.strip():
            conditions.append("LOWER(TRIM(country)) = LOWER(TRIM(:country))")
            params["country"] = country
        if polygon_wkt is not None:
            spatial_conditions, spatial_params = build_spatial_sql(
                SpatialAreaFilter(polygon_wkt=polygon_wkt), self.dialect
            )
            conditions.extend(spatial_conditions)
            params.update(spatial_params)
        return conditions, params

    def get_annual_totals(
        self,
        start_year: int,
        end_year: int,
        country: str | None = None,
        polygon_wkt: str | None = None,
    ) -> dict[int, dict[str, Any]]:
        """
        Totales por año: detecciones crudas por sensor e índice armonizado
        (SUM(harmonized_weight)). Mucho más liviano que get_annual_stats.
        """
        year_expr = self._year_expr()
        conditions = [
            "acq_datetime IS NOT NULL",
            f"{year_expr} BETWEEN :start_year AND :end_year",
        ]
        params: dict[str, Any] = {"start_year": start_year, "end_year": end_year}
        area_conditions, area_params = self._area_conditions(country, polygon_wkt)
        conditions.extend(area_conditions)
        params.update(area_params)

        query = text(
            f"""
            SELECT
                {year_expr} AS yr,
                COUNT(*) AS total,
                SUM(CASE WHEN UPPER(instrument) = 'MODIS' THEN 1 ELSE 0 END) AS modis,
                SUM(CASE WHEN UPPER(instrument) = 'VIIRS' THEN 1 ELSE 0 END) AS viirs,
                COALESCE(SUM(harmonized_weight), 0.0) AS harmonized,
                AVG(frp) AS avg_frp
            FROM hotspots
            WHERE {" AND ".join(conditions)}
            GROUP BY yr
            ORDER BY yr ASC
            """
        )
        rows = self.session.execute(query, params).all()
        return {
            int(r[0]): {
                "total": int(r[1]),
                "modis": int(r[2] or 0),
                "viirs": int(r[3] or 0),
                "harmonized": round(float(r[4] or 0.0), 4),
                "avg_frp": round(float(r[5]), 4) if r[5] is not None else None,
            }
            for r in rows
        }

    def get_monthly_counts(
        self,
        start_year: int | None = None,
        end_year: int | None = None,
        metric: Literal["raw", "harmonized"] = "raw",
        country: str | None = None,
        polygon_wkt: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Agregado mensual. `count` siempre es el número de detecciones crudas;
        `value` es la métrica pedida: detecciones crudas o suma de
        `harmonized_weight` (índice armonizado MODIS-VIIRS con VIIRS como referencia).
        """
        year_expr = self._year_expr()
        month_expr = self._month_expr()
        conditions = ["acq_datetime IS NOT NULL"]
        params: dict[str, Any] = {}
        if start_year is not None:
            conditions.append(f"{year_expr} >= :start_year")
            params["start_year"] = start_year
        if end_year is not None:
            conditions.append(f"{year_expr} <= :end_year")
            params["end_year"] = end_year
        area_conditions, area_params = self._area_conditions(country, polygon_wkt)
        conditions.extend(area_conditions)
        params.update(area_params)

        value_expr = (
            "COALESCE(SUM(harmonized_weight), 0.0)"
            if metric == "harmonized"
            else "COUNT(*)"
        )
        where_sql = " AND ".join(conditions)
        query = text(
            f"""
            SELECT
                {year_expr} AS yr,
                {month_expr} AS mo,
                COUNT(*) AS cnt,
                COALESCE(SUM(frp), 0.0) AS sum_frp,
                AVG(frp) AS avg_frp,
                {value_expr} AS metric_value
            FROM hotspots
            WHERE {where_sql}
            GROUP BY yr, mo
            ORDER BY yr ASC, mo ASC
            """
        )
        rows = self.session.execute(query, params).all()
        return [
            {
                "year": int(r[0]),
                "month": int(r[1]),
                "month_key": f"{int(r[0]):04d}-{int(r[1]):02d}",
                "count": int(r[2]),
                "sum_frp": round(float(r[3] or 0.0), 4),
                "avg_frp": round(float(r[4]), 4) if r[4] is not None else None,
                "value": round(float(r[5] or 0.0), 4),
            }
            for r in rows
        ]

    def _day_expr(self) -> str:
        if self.dialect == "postgresql":
            return "CAST(EXTRACT(DAY FROM acq_datetime) AS INTEGER)"
        return "CAST(strftime('%d', acq_datetime) AS INTEGER)"

    def get_archive_months(
        self, country: str | None = None
    ) -> dict[tuple[int, int], dict[str, Any]]:
        """
        Meses con datos en el archivo (sin filtro espacial): primer y último día
        con detecciones y cuántas filas vienen del feed casi en tiempo real del
        worker (sin armonizar). Un mes ausente es un hueco de datos, no un cero.
        """
        year_expr = self._year_expr()
        month_expr = self._month_expr()
        day_expr = self._day_expr()
        conditions, params = self._area_conditions(country=country)
        conditions.append("acq_datetime IS NOT NULL")
        query = text(
            f"""
            SELECT
                {year_expr} AS yr,
                {month_expr} AS mo,
                MIN({day_expr}) AS first_day,
                MAX({day_expr}) AS last_day,
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN harmonization_category LIKE 'CATCHUP%'
                          OR harmonization_category LIKE 'NRT%'
                          OR harmonization_category = 'API_INGESTED'
                        THEN 1 ELSE 0
                    END
                ) AS nrt_rows
            FROM hotspots
            WHERE {" AND ".join(conditions)}
            GROUP BY yr, mo
            """
        )
        rows = self.session.execute(query, params).all()
        return {
            (int(r[0]), int(r[1])): {
                "first_day": int(r[2]),
                "last_day": int(r[3]),
                "total": int(r[4]),
                "nrt_rows": int(r[5] or 0),
            }
            for r in rows
        }

    def get_data_coverage(
        self, country: str | None = None
    ) -> tuple[datetime, datetime] | None:
        """
        Primera y última detección del archivo (sin filtro espacial). Define qué
        meses existen en el registro: dentro de este rango, un mes sin detecciones
        en el área elegida cuenta como 0; fuera de él, no hay dato.
        """
        conditions, params = self._area_conditions(country=country)
        conditions.append("acq_datetime IS NOT NULL")
        where_sql = " AND ".join(conditions)
        row = self.session.execute(
            text(
                "SELECT MIN(acq_datetime), MAX(acq_datetime) "
                f"FROM hotspots WHERE {where_sql}"
            ),
            params,
        ).first()
        if row is None or row[0] is None or row[1] is None:
            return None
        return _as_datetime(row[0]), _as_datetime(row[1])

    def fetch_spatial_points(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        max_rows: int = 20000,
        country: str | None = None,
        polygon_wkt: str | None = None,
    ) -> tuple[np.ndarray, list[str], list[float | None], list[str]]:
        conditions, params = self._build_filters(
            start_date=start_date,
            end_date=end_date,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
        )
        area_conditions, area_params = self._area_conditions(country, polygon_wkt)
        conditions.extend(area_conditions)
        params.update(area_params)
        conditions.extend(["latitude IS NOT NULL", "longitude IS NOT NULL"])
        params["max_rows"] = max_rows
        where_sql = " AND ".join(conditions)

        # Muestreo uniforme determinístico sobre todo el periodo consultado en vez de
        # truncar cronológicamente en los primeros días con ORDER BY acq_datetime ASC.
        order_expr = (
            "hashtext(CAST(id AS TEXT)) ASC"
            if self.dialect == "postgresql"
            else "CAST(id AS TEXT) ASC"
        )
        query = text(
            f"""
            SELECT id, latitude, longitude, frp, acq_datetime
            FROM hotspots
            WHERE {where_sql}
            ORDER BY {order_expr}
            LIMIT :max_rows
            """
        )
        rows = list(self.session.execute(query, params).all())
        if not rows:
            return np.empty((0, 2), dtype=np.float64), [], [], []

        rows.sort(key=lambda r: str(r[4] or ""))
        coords = np.array([[float(r[1]), float(r[2])] for r in rows], dtype=np.float64)
        ids = [str(r[0]) for r in rows]
        frps = [float(r[3]) if r[3] is not None else None for r in rows]
        datetimes = [str(r[4]) for r in rows]
        return coords, ids, frps, datetimes
