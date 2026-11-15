from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func, text
from sqlmodel import Session, col, select

from model import FireCluster
from model.ClusterStatus import ClusterStatus
from repositories.DashboardRepository import DashboardRepository
from repositories.spatial_filter import parse_geojson_polygon_to_wkt
from schemas.fire_calendar import FireCalendarQuery


@dataclass(frozen=True)
class FireClusterWindow:
    """Proyección mínima de FireCluster necesaria para Fire Calendar."""

    datetimeStart: datetime | None
    datetimeEnd: datetime | None
    status: ClusterStatus


class FireCalendarRepository:
    """
    Repositorio SQL para estadísticas agregadas de Fire Calendar sobre
    hotspots y firecluster (compatible con PostgreSQL y SQLite).
    """

    def __init__(self, session: Session):
        self.session = session
        bind = session.get_bind()
        self.dialect = bind.dialect.name if bind is not None else "postgresql"
        self._dashboard_repo = DashboardRepository(session)

    def get_cluster(self, cluster_id: int) -> FireClusterWindow | None:
        stmt = select(
            col(FireCluster.datetimeStart),
            col(FireCluster.datetimeEnd),
            col(FireCluster.status),
        ).where(col(FireCluster.id) == cluster_id)
        row = self.session.exec(stmt).first()
        if row is None:
            return None
        return FireClusterWindow(
            datetimeStart=row[0],
            datetimeEnd=row[1],
            status=ClusterStatus(row[2]),
        )

    def _bucket_expr(self, aggregation: Literal["day", "week", "month"]) -> str:
        if self.dialect == "postgresql":
            return f"CAST(DATE_TRUNC('{aggregation}', acq_datetime) AS DATE)"
        if aggregation == "day":
            return "DATE(acq_datetime)"
        if aggregation == "month":
            return "DATE(strftime('%Y-%m-01', acq_datetime))"
        # SQLite semana ISO aproximada al lunes de la semana
        return "DATE(acq_datetime, '-' || ((CAST(strftime('%w', acq_datetime) AS INTEGER) + 6) % 7) || ' days')"

    def _build_hotspot_where(
        self,
        query_params: FireCalendarQuery,
        start_dt: datetime,
        end_dt_exclusive: datetime,
    ) -> tuple[str, dict[str, Any], str]:
        conf_expr = self._dashboard_repo._confidence_sql(high_value=90)
        conditions: list[str] = [
            "acq_datetime IS NOT NULL",
            "acq_datetime >= :start_dt",
            "acq_datetime < :end_dt_exclusive",
        ]
        # En SQLite las fechas naive o con tz se comparan limpiamente en ISO naive UTC
        params: dict[str, Any] = {
            "start_dt": start_dt if self.dialect == "postgresql" else start_dt.replace(tzinfo=None),
            "end_dt_exclusive": (
                end_dt_exclusive
                if self.dialect == "postgresql"
                else end_dt_exclusive.replace(tzinfo=None)
            ),
        }

        if query_params.country is not None:
            conditions.append("LOWER(TRIM(country)) = LOWER(TRIM(:country))")
            params["country"] = query_params.country

        if query_params.min_confidence is not None:
            conditions.append(f"({conf_expr}) >= :min_confidence")
            params["min_confidence"] = query_params.min_confidence

        if query_params.confidence_class is not None:
            conditions.append("LOWER(TRIM(confidence_class)) = LOWER(TRIM(:confidence_class))")
            params["confidence_class"] = query_params.confidence_class

        if query_params.satellite is not None:
            conditions.append("LOWER(TRIM(satellite)) = LOWER(TRIM(:satellite))")
            params["satellite"] = query_params.satellite

        if query_params.instrument is not None:
            conditions.append("LOWER(TRIM(instrument)) = LOWER(TRIM(:instrument))")
            params["instrument"] = query_params.instrument

        if query_params.daynight is not None:
            conditions.append("UPPER(TRIM(daynight)) = :daynight")
            params["daynight"] = query_params.daynight

        if query_params.min_frp is not None:
            conditions.append("frp >= :min_frp")
            params["min_frp"] = query_params.min_frp

        if query_params.max_frp is not None:
            conditions.append("frp <= :max_frp")
            params["max_frp"] = query_params.max_frp

        if query_params.polygon is not None:
            polygon_wkt = parse_geojson_polygon_to_wkt(query_params.polygon)
            if polygon_wkt is not None:
                poly_conds, poly_params = self._dashboard_repo._area_conditions(
                    polygon_wkt=polygon_wkt
                )
                conditions.extend(poly_conds)
                params.update(poly_params)

        if query_params.metric == "harmonized":
            conditions.append("COALESCE(harmonized_weight, 1.0) > 0")

        return " AND ".join(conditions), params, conf_expr

    def get_hotspot_buckets(
        self,
        query_params: FireCalendarQuery,
        start_dt: datetime,
        end_dt_exclusive: datetime,
    ) -> dict[date, dict[str, Any]]:
        where_sql, params, conf_expr = self._build_hotspot_where(
            query_params, start_dt, end_dt_exclusive
        )
        bucket_expr = self._bucket_expr(query_params.aggregation)

        if query_params.metric == "harmonized":
            frp_col = "COALESCE(harmonized_frp, frp)"
            w_col = "COALESCE(harmonized_weight, 1.0)"
            if self.dialect == "postgresql":
                cnt_expr = f"GREATEST(1, CAST(ROUND(COALESCE(SUM({w_col}), 0.0)) AS INTEGER))"
            else:
                cnt_expr = f"MAX(1, CAST(ROUND(COALESCE(SUM({w_col}), 0.0)) AS INTEGER))"
            day_expr = f"CAST(ROUND(COALESCE(SUM(CASE WHEN UPPER(TRIM(daynight)) = 'D' THEN {w_col} ELSE 0.0 END), 0.0)) AS INTEGER)"
            night_expr = f"CAST(ROUND(COALESCE(SUM(CASE WHEN UPPER(TRIM(daynight)) = 'N' THEN {w_col} ELSE 0.0 END), 0.0)) AS INTEGER)"
            high_expr = (
                "CAST(ROUND(COALESCE(SUM("
                "CASE WHEN LOWER(TRIM(COALESCE(confidence_class, ''))) IN ('h', 'high') "
                f"OR ({conf_expr}) >= 80 THEN {w_col} ELSE 0.0 END"
                "), 0.0)) AS INTEGER)"
            )
        else:
            frp_col = "frp"
            cnt_expr = "COUNT(*)"
            day_expr = "SUM(CASE WHEN UPPER(TRIM(daynight)) = 'D' THEN 1 ELSE 0 END)"
            night_expr = "SUM(CASE WHEN UPPER(TRIM(daynight)) = 'N' THEN 1 ELSE 0 END)"
            high_expr = (
                "SUM(CASE "
                "WHEN LOWER(TRIM(COALESCE(confidence_class, ''))) IN ('h', 'high') "
                f"OR ({conf_expr}) >= 80 THEN 1 ELSE 0 END)"
            )

        if self.dialect == "postgresql":
            est_fires_expr = "COUNT(DISTINCT (FLOOR(latitude / 0.05), FLOOR(longitude / 0.05)))"
        else:
            est_fires_expr = "COUNT(DISTINCT (CAST(ROUND(latitude * 20.0) AS TEXT) || ':' || CAST(ROUND(longitude * 20.0) AS TEXT)))"

        sql = text(
            f"""
            SELECT
                {bucket_expr} AS bucket_date,
                {cnt_expr} AS hotspot_count,
                COALESCE(SUM({frp_col}), 0.0) AS frp_total,
                COALESCE(AVG({frp_col}), 0.0) AS frp_average,
                COALESCE(MAX({frp_col}), 0.0) AS max_frp,
                {day_expr} AS daytime_hotspots,
                {night_expr} AS nighttime_hotspots,
                {high_expr} AS high_confidence_count,
                {est_fires_expr} AS estimated_fires
            FROM hotspots
            WHERE {where_sql}
            GROUP BY bucket_date
            ORDER BY bucket_date ASC
            """
        )

        rows = self.session.execute(sql, params).mappings()
        result: dict[date, dict[str, Any]] = {}
        for r in rows:
            raw_date = r["bucket_date"]
            b_date = (
                raw_date
                if isinstance(raw_date, date) and not isinstance(raw_date, datetime)
                else date.fromisoformat(str(raw_date)[:10])
            )
            result[b_date] = {
                "hotspot_count": int(r["hotspot_count"] or 0),
                "frp_total": round(float(r["frp_total"] or 0.0), 4),
                "frp_average": round(float(r["frp_average"] or 0.0), 4),
                "max_frp": round(float(r["max_frp"] or 0.0), 4),
                "daytime_hotspots": int(r["daytime_hotspots"] or 0),
                "nighttime_hotspots": int(r["nighttime_hotspots"] or 0),
                "high_confidence_count": int(r["high_confidence_count"] or 0),
                "estimated_fires": int(r["estimated_fires"] or 0),
            }
        return result

    def has_any_clusters(self) -> bool:
        cnt = self.session.exec(select(func.count(col(FireCluster.id)))).one()
        return int(cnt or 0) > 0

    def get_archive_coverage_and_months(
        self, country: str | None = None
    ) -> tuple[tuple[datetime, datetime] | None, dict[tuple[int, int], dict[str, Any]]]:
        coverage = self._dashboard_repo.get_data_coverage(country=country)
        try:
            archive_months = self._dashboard_repo.get_archive_months(country=country)
        except Exception:
            archive_months = {}
        return coverage, archive_months

    def get_overlapping_clusters(
        self,
        start_dt: datetime,
        end_dt_exclusive: datetime,
        cluster_id: int | None = None,
    ) -> list[FireClusterWindow]:
        stmt = select(
            col(FireCluster.datetimeStart),
            col(FireCluster.datetimeEnd),
            col(FireCluster.status),
        ).where(
            col(FireCluster.datetimeStart).is_not(None),
            col(FireCluster.datetimeStart) < end_dt_exclusive,
            func.coalesce(col(FireCluster.datetimeEnd), col(FireCluster.datetimeStart))
            >= start_dt,
        )
        if cluster_id is not None:
            stmt = stmt.where(col(FireCluster.id) == cluster_id)

        rows = self.session.exec(stmt).all()
        return [
            FireClusterWindow(
                datetimeStart=row[0],
                datetimeEnd=row[1],
                status=ClusterStatus(row[2]),
            )
            for row in rows
        ]

    @staticmethod
    def generate_bucket_dates(
        start_d: date,
        end_d: date,
        aggregation: Literal["day", "week", "month"],
    ) -> list[tuple[date, datetime, datetime]]:
        """
        Genera la secuencia completa de intervalos (bucket_date, bucket_start, bucket_end)
        incluyendo períodos sin detecciones.
        """
        buckets: list[tuple[date, datetime, datetime]] = []
        if aggregation == "day":
            cur = start_d
            while cur <= end_d:
                b_start = datetime(cur.year, cur.month, cur.day)
                b_end = b_start + timedelta(days=1)
                buckets.append((cur, b_start, b_end))
                cur += timedelta(days=1)
            return buckets

        if aggregation == "week":
            cur = start_d - timedelta(days=start_d.weekday())
            while cur <= end_d:
                b_start = datetime(cur.year, cur.month, cur.day)
                b_end = b_start + timedelta(days=7)
                buckets.append((cur, b_start, b_end))
                cur += timedelta(days=7)
            return buckets

        # month
        cur = date(start_d.year, start_d.month, 1)
        while cur <= end_d:
            b_start = datetime(cur.year, cur.month, 1)
            if cur.month == 12:
                next_m = date(cur.year + 1, 1, 1)
            else:
                next_m = date(cur.year, cur.month + 1, 1)
            b_end = datetime(next_m.year, next_m.month, 1)
            buckets.append((cur, b_start, b_end))
            cur = next_m
        return buckets
