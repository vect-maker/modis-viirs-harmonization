from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import text
from sqlmodel import Session, col, select

from model import FireCluster
from repositories.DashboardRepository import DashboardRepository
from schemas.fire_calendar import FireCalendarQuery


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

    def get_cluster(self, cluster_id: int) -> FireCluster | None:
        return self.session.get(FireCluster, cluster_id)

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

        sql = text(
            f"""
            SELECT
                {bucket_expr} AS bucket_date,
                COUNT(*) AS hotspot_count,
                COALESCE(SUM(frp), 0.0) AS frp_total,
                COALESCE(AVG(frp), 0.0) AS frp_average,
                COALESCE(MAX(frp), 0.0) AS max_frp,
                SUM(CASE WHEN UPPER(TRIM(daynight)) = 'D' THEN 1 ELSE 0 END) AS daytime_hotspots,
                SUM(CASE WHEN UPPER(TRIM(daynight)) = 'N' THEN 1 ELSE 0 END) AS nighttime_hotspots,
                SUM(
                    CASE
                        WHEN LOWER(TRIM(COALESCE(confidence_class, ''))) = 'high'
                          OR ({conf_expr}) >= 80
                        THEN 1 ELSE 0
                    END
                ) AS high_confidence_count
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
            }
        return result

    def get_overlapping_clusters(
        self,
        start_dt: datetime,
        end_dt_exclusive: datetime,
        cluster_id: int | None = None,
    ) -> list[FireCluster]:
        stmt = select(FireCluster).where(
            col(FireCluster.datetimeStart).is_not(None),
            col(FireCluster.datetimeStart) < end_dt_exclusive,
        )
        if cluster_id is not None:
            stmt = stmt.where(col(FireCluster.id) == cluster_id)

        clusters = list(self.session.exec(stmt).all())
        overlapping: list[FireCluster] = []
        start_naive = start_dt.replace(tzinfo=None)
        for c in clusters:
            if c.datetimeStart is None:
                continue
            c_end = (c.datetimeEnd or c.datetimeStart).replace(tzinfo=None)
            if c_end >= start_naive:
                overlapping.append(c)
        return overlapping

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
