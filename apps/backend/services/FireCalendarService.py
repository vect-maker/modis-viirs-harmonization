from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException
from sqlmodel import Session

from model.ClusterStatus import ClusterStatus
from repositories.FireCalendarRepository import FireCalendarRepository
from schemas.fire_calendar import (
    FireCalendarInterval,
    FireCalendarPeriod,
    FireCalendarQuery,
    FireCalendarResponse,
)


class FireCalendarService:
    """Lógica de negocio y agregación temporal para el módulo Fire Calendar."""

    def __init__(self, session: Session):
        self.repo = FireCalendarRepository(session)

    @staticmethod
    def resolve_period(query: FireCalendarQuery) -> tuple[date, date, datetime, datetime]:
        if query.month is not None:
            last_day = calendar.monthrange(query.year, query.month)[1]
            default_start = date(query.year, query.month, 1)
            default_end = date(query.year, query.month, last_day)
        else:
            default_start = date(query.year, 1, 1)
            default_end = date(query.year, 12, 31)

        eff_start = query.start_date or default_start
        eff_end = query.end_date or default_end

        start_dt = datetime(eff_start.year, eff_start.month, eff_start.day, tzinfo=UTC)
        end_dt_exclusive = datetime(
            eff_end.year, eff_end.month, eff_end.day, tzinfo=UTC
        ) + timedelta(days=1)
        return eff_start, eff_end, start_dt, end_dt_exclusive

    def get_calendar(self, query: FireCalendarQuery) -> FireCalendarResponse:
        if query.department is not None or query.municipality is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Los filtros 'department' y 'municipality' no están disponibles "
                    "porque el esquema actual de base de datos solo incluye 'country' (dim_country)."
                ),
            )

        eff_start, eff_end, start_dt, end_dt_exclusive = self.resolve_period(query)

        hotspot_start = start_dt
        hotspot_end_excl = end_dt_exclusive
        if query.cluster_id is not None:
            cluster = self.repo.get_cluster(query.cluster_id)
            if cluster is None:
                raise HTTPException(status_code=404, detail="FireCluster no encontrado")
            if cluster.datetimeStart is not None:
                c_start = cluster.datetimeStart.replace(tzinfo=UTC)
                c_end = (cluster.datetimeEnd or cluster.datetimeStart).replace(
                    tzinfo=UTC
                ) + timedelta(seconds=1)
                hotspot_start = max(start_dt, c_start)
                hotspot_end_excl = min(end_dt_exclusive, c_end)

        if hotspot_start < hotspot_end_excl:
            hotspot_buckets = self.repo.get_hotspot_buckets(
                query, hotspot_start, hotspot_end_excl
            )
        else:
            hotspot_buckets = {}

        overlapping_clusters = self.repo.get_overlapping_clusters(
            start_dt, end_dt_exclusive, cluster_id=query.cluster_id
        )

        # Normalizar timestamps de clusters a naive UTC para comparar por bucket
        cluster_ranges: list[tuple[datetime, datetime, ClusterStatus]] = []
        for c in overlapping_clusters:
            if c.datetimeStart is None:
                continue
            c_start = c.datetimeStart.replace(tzinfo=None)
            c_end = (c.datetimeEnd or c.datetimeStart).replace(tzinfo=None)
            cluster_ranges.append((c_start, c_end, c.status))

        buckets = self.repo.generate_bucket_dates(
            eff_start, eff_end, query.aggregation
        )

        intervals: list[FireCalendarInterval] = []
        total_hotspots = 0
        total_frp = 0.0
        max_frp = 0.0
        daytime_hotspots = 0
        nighttime_hotspots = 0
        high_confidence_count = 0

        for b_date, b_start, b_end in buckets:
            hb = hotspot_buckets.get(b_date)
            if hb is not None:
                h_count = int(hb["hotspot_count"])
                h_frp_tot = float(hb["frp_total"])
                h_frp_avg = float(hb["frp_average"])
                h_frp_max = float(hb["max_frp"])
                h_day = int(hb["daytime_hotspots"])
                h_night = int(hb["nighttime_hotspots"])
                h_high = int(hb["high_confidence_count"])
            else:
                h_count = 0
                h_frp_tot = 0.0
                h_frp_avg = 0.0
                h_frp_max = 0.0
                h_day = 0
                h_night = 0
                h_high = 0

            new_in_bucket = 0
            active_in_bucket = 0
            for c_start, c_end, _ in cluster_ranges:
                if b_start <= c_start < b_end:
                    new_in_bucket += 1
                if c_start < b_end and c_end >= b_start:
                    active_in_bucket += 1

            total_hotspots += h_count
            total_frp += h_frp_tot
            if h_frp_max > max_frp:
                max_frp = h_frp_max
            daytime_hotspots += h_day
            nighttime_hotspots += h_night
            high_confidence_count += h_high

            intervals.append(
                FireCalendarInterval(
                    date=b_date,
                    hotspot_count=h_count,
                    fire_count=active_in_bucket,
                    new_fires=new_in_bucket,
                    active_fires=active_in_bucket,
                    frp_total=round(h_frp_tot, 4),
                    frp_average=round(h_frp_avg, 4),
                    max_frp=round(h_frp_max, 4),
                    daytime_hotspots=h_day,
                    nighttime_hotspots=h_night,
                    high_confidence_count=h_high,
                )
            )

        period_start_naive = start_dt.replace(tzinfo=None)
        period_end_naive = end_dt_exclusive.replace(tzinfo=None)
        period_new_fires = sum(
            1 for c_start, _, _ in cluster_ranges if period_start_naive <= c_start < period_end_naive
        )
        period_active_fires = sum(
            1 for _, _, status in cluster_ranges if status == ClusterStatus.ACTIVO
        )
        frp_average = round(total_frp / total_hotspots, 4) if total_hotspots > 0 else 0.0

        return FireCalendarResponse(
            period=FireCalendarPeriod(
                year=query.year,
                month=query.month,
                start_date=eff_start,
                end_date=eff_end,
                start_datetime_utc=start_dt,
                end_datetime_utc=end_dt_exclusive,
            ),
            aggregation=query.aggregation,
            total_hotspots=total_hotspots,
            total_fires=len(cluster_ranges),
            new_fires=period_new_fires,
            active_fires=period_active_fires,
            frp_total=round(total_frp, 4),
            frp_average=frp_average,
            max_frp=round(max_frp, 4),
            daytime_hotspots=daytime_hotspots,
            nighttime_hotspots=nighttime_hotspots,
            high_confidence_count=high_confidence_count,
            intervals=intervals,
        )
