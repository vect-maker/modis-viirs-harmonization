from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, overload

from sqlalchemy import select as sa_select
from sqlmodel import Session, col, func, select

from model.Hotspots import Hotspots
from model.StarSchema import (
    AvailableDatesResponse,
    DailyActivityItem,
    DailyActivityResponse,
    DimPlatform,
    FactHotspot,
    HistoricalCalendarResponse,
    HistoricalMonthSummary,
    HotspotPublic,
)
from repositories.pagination import paginate_statement
from schemas.pagination import PaginatedResponse, PaginationParams


def parse_datetime(value: str | datetime | date, is_end: bool = False) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    if isinstance(value, date):
        t = (
            time(23, 59, 59, 999999, tzinfo=UTC)
            if is_end
            else time(0, 0, 0, 0, tzinfo=UTC)
        )
        return datetime.combine(value, t)

    val_str = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(val_str)
        if len(val_str) == 10 and is_end:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        pass

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            if fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d") and is_end:
                dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            return dt.replace(tzinfo=UTC)
        except ValueError:
            continue

    raise ValueError(
        f"Formato de fecha inválido: '{value}'. "
        "Formatos soportados: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO 8601."
    )


class HotspotRepository:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def serialize_hotspot(hotspot: Hotspots) -> dict:
        if hotspot.acq_datetime:
            if hotspot.acq_datetime.tzinfo is None:
                acq_dt_utc = hotspot.acq_datetime.replace(tzinfo=UTC)
            else:
                acq_dt_utc = hotspot.acq_datetime.astimezone(UTC)
            acq_dt = acq_dt_utc.strftime("%Y-%m-%d %H:%M:%S")
        else:
            acq_dt = None

        conf = hotspot.confidence
        if conf is not None:
            try:
                conf_val = float(conf)
                if conf_val.is_integer():
                    conf_val = int(conf_val)
            except (ValueError, TypeError):
                conf_val = conf
        else:
            conf_val = None

        return {
            "id": str(hotspot.id) if hotspot.id is not None else None,
            "country": getattr(hotspot, "country", None),
            "latitude": hotspot.latitude,
            "longitude": hotspot.longitude,
            "acq_datetime": acq_dt,
            "instrument": hotspot.instrument,
            "satellite": hotspot.satellite,
            "confidence_class": hotspot.confidence_class,
            "confidence": conf_val,
            "frp": hotspot.frp,
            "bright_mir": hotspot.bright_mir,
            "bright_tir": hotspot.bright_tir,
            "scan": hotspot.scan,
            "track": hotspot.track,
            "daynight": hotspot.daynight,
            "version": hotspot.version,
            "type": hotspot.type,
        }

    @overload
    def get_hotspots(
        self,
        pagination: PaginationParams,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> PaginatedResponse[HotspotPublic]: ...

    @overload
    def get_hotspots(
        self,
        pagination: None = None,
        *,
        satellite_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[dict]: ...

    def get_hotspots(
        self,
        pagination: PaginationParams | None = None,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        satellite_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> PaginatedResponse[HotspotPublic] | list[dict]:
        if pagination is not None:
            statement = select(FactHotspot)
            if start_date is not None:
                statement = statement.where(
                    col(FactHotspot.acq_datetime)
                    >= datetime.combine(start_date, time.min)
                )
            if end_date is not None:
                statement = statement.where(
                    col(FactHotspot.acq_datetime)
                    < datetime.combine(end_date + timedelta(days=1), time.min)
                )
            statement = statement.order_by(
                col(FactHotspot.acq_datetime).desc(),
                col(FactHotspot.id),
            )
            return paginate_statement(
                self.session, statement, pagination, HotspotPublic
            )

        statement = select(Hotspots)
        if satellite_type:
            sat = satellite_type.strip().upper()
            statement = statement.where(func.upper(Hotspots.instrument) == sat)
        statement = statement.offset(offset).limit(limit)
        results = self.session.exec(statement).all()
        return [self.serialize_hotspot(h) for h in results]

    def get_available_dates(self) -> AvailableDatesResponse:
        date_expr = func.date(col(FactHotspot.acq_datetime))
        statement = select(date_expr).distinct().order_by(date_expr.asc())
        raw_dates = self.session.exec(statement).all()
        dates = [
            d if isinstance(d, date) else date.fromisoformat(str(d))
            for d in raw_dates
            if d is not None
        ]
        return AvailableDatesResponse(
            dates=dates,
            min_date=dates[0] if dates else None,
            max_date=dates[-1] if dates else None,
        )

    def get_daily_activity(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        instrument: str | None = None,
    ) -> DailyActivityResponse:
        date_expr = func.date(col(FactHotspot.acq_datetime))
        count_expr = func.count(col(FactHotspot.id))
        statement = select(date_expr, count_expr)

        if instrument and instrument.strip().upper() in {"MODIS", "VIIRS"}:
            statement = statement.join(
                DimPlatform, col(FactHotspot.platform_id) == col(DimPlatform.id)
            ).where(func.upper(col(DimPlatform.instrument)) == instrument.strip().upper())

        if start_date is not None:
            statement = statement.where(
                col(FactHotspot.acq_datetime) >= datetime.combine(start_date, time.min)
            )
        if end_date is not None:
            statement = statement.where(
                col(FactHotspot.acq_datetime)
                < datetime.combine(end_date + timedelta(days=1), time.min)
            )

        statement = statement.group_by(date_expr).order_by(date_expr.asc())
        rows = self.session.exec(statement).all()

        counts_by_date: dict[date, int] = {}
        for raw_day, raw_count in rows:
            if raw_day is None:
                continue
            parsed_day = (
                raw_day if isinstance(raw_day, date) else date.fromisoformat(str(raw_day))
            )
            counts_by_date[parsed_day] = int(raw_count)

        resolved_start = start_date or (min(counts_by_date) if counts_by_date else None)
        resolved_end = end_date or (max(counts_by_date) if counts_by_date else None)
        if resolved_start is None or resolved_end is None or resolved_start > resolved_end:
            return DailyActivityResponse(days=[], min_date=None, max_date=None)

        days: list[DailyActivityItem] = []
        cursor = resolved_start
        while cursor <= resolved_end:
            days.append(
                DailyActivityItem(date=cursor, count=counts_by_date.get(cursor, 0))
            )
            cursor += timedelta(days=1)

        return DailyActivityResponse(
            days=days,
            min_date=resolved_start,
            max_date=resolved_end,
        )

    def get_historical_calendar(self) -> HistoricalCalendarResponse:
        date_expr = func.date(col(FactHotspot.acq_datetime))
        instrument_expr = func.upper(col(DimPlatform.instrument))
        count_expr = func.count(col(FactHotspot.id))

        statement = (
            select(date_expr, instrument_expr, count_expr)
            .join(DimPlatform, col(FactHotspot.platform_id) == col(DimPlatform.id))
            .group_by(date_expr, instrument_expr)
            .order_by(date_expr.asc())
        )
        rows = self.session.exec(statement).all()

        if not rows:
            return HistoricalCalendarResponse(
                first_detection=None,
                last_detection=None,
                total_records=0,
                months=[],
            )

        monthly: dict[tuple[int, int], dict[str, object]] = {}
        first_day: date | None = None
        last_day: date | None = None
        total_records = 0

        for raw_day, raw_instrument, raw_count in rows:
            if raw_day is None:
                continue
            parsed_day = (
                raw_day if isinstance(raw_day, date) else date.fromisoformat(str(raw_day))
            )
            count = int(raw_count)
            instrument = str(raw_instrument or "").upper()

            if first_day is None or parsed_day < first_day:
                first_day = parsed_day
            if last_day is None or parsed_day > last_day:
                last_day = parsed_day
            total_records += count

            key = (parsed_day.year, parsed_day.month)
            bucket = monthly.get(key)
            if bucket is None:
                bucket = {
                    "total": 0,
                    "modis": 0,
                    "viirs": 0,
                    "days": set(),
                }
                monthly[key] = bucket

            bucket["total"] = int(bucket["total"]) + count  # type: ignore[arg-type]
            if instrument == "MODIS":
                bucket["modis"] = int(bucket["modis"]) + count  # type: ignore[arg-type]
            elif instrument == "VIIRS":
                bucket["viirs"] = int(bucket["viirs"]) + count  # type: ignore[arg-type]
            bucket["days"].add(parsed_day)  # type: ignore[attr-defined]

        months = [
            HistoricalMonthSummary(
                year=year,
                month=month,
                total=int(data["total"]),  # type: ignore[arg-type]
                modis_count=int(data["modis"]) if int(data["modis"]) > 0 else None,  # type: ignore[arg-type]
                viirs_count=int(data["viirs"]) if int(data["viirs"]) > 0 else None,  # type: ignore[arg-type]
                observed_days=len(data["days"]),  # type: ignore[arg-type]
            )
            for (year, month), data in sorted(monthly.items())
        ]

        return HistoricalCalendarResponse(
            first_detection=first_day,
            last_detection=last_day,
            total_records=total_records,
            months=months,
        )

    def get_hostspot_by_dates(
        self,
        start_date: str | datetime | date,
        end_date: str | datetime | date,
        satellite_type: str | None = None,
        offset: int = 0,
        limit: int = 1000,
    ) -> list[dict]:
        start_dt = parse_datetime(start_date, is_end=False)
        end_dt = parse_datetime(end_date, is_end=True)

        statement = (
            select(Hotspots)
            .where(col(Hotspots.acq_datetime) >= start_dt)
            .where(col(Hotspots.acq_datetime) <= end_dt)
        )
        if satellite_type:
            sat = satellite_type.strip().upper()
            statement = statement.where(func.upper(Hotspots.instrument) == sat)

        statement = (
            statement.order_by(col(Hotspots.acq_datetime).desc())
            .offset(offset)
            .limit(limit)
        )
        results = self.session.exec(statement).all()
        return [self.serialize_hotspot(h) for h in results]

    def get_hostspot_by_location(
        self,
        latitude: float,
        longitude: float,
        radius: float = 0.05,
        satellite_type: str | None = None,
        offset: int = 0,
        limit: int = 1000,
    ) -> list[dict]:
        if radius > 0:
            statement = (
                select(Hotspots)
                .where(col(Hotspots.latitude) >= (latitude - radius))
                .where(col(Hotspots.latitude) <= (latitude + radius))
                .where(col(Hotspots.longitude) >= (longitude - radius))
                .where(col(Hotspots.longitude) <= (longitude + radius))
            )
        else:
            statement = (
                select(Hotspots)
                .where(col(Hotspots.latitude) == latitude)
                .where(col(Hotspots.longitude) == longitude)
            )

        if satellite_type:
            sat = satellite_type.strip().upper()
            statement = statement.where(func.upper(Hotspots.instrument) == sat)

        statement = statement.offset(offset).limit(limit)
        results = self.session.exec(statement).all()
        return [self.serialize_hotspot(h) for h in results]

    def get_hotspots_by_satellite(
        self,
        satellite_type: str,
        start_date: str | datetime | date | None = None,
        end_date: str | datetime | date | None = None,
        offset: int = 0,
        limit: int = 1000,
    ) -> list[dict]:
        sat = satellite_type.strip().upper()
        statement = select(Hotspots).where(func.upper(Hotspots.instrument) == sat)

        if start_date:
            start_dt = parse_datetime(start_date, is_end=False)
            statement = statement.where(col(Hotspots.acq_datetime) >= start_dt)
        if end_date:
            end_dt = parse_datetime(end_date, is_end=True)
            statement = statement.where(col(Hotspots.acq_datetime) <= end_dt)

        statement = (
            statement.order_by(col(Hotspots.acq_datetime).desc())
            .offset(offset)
            .limit(limit)
        )
        results = self.session.exec(statement).all()
        return [self.serialize_hotspot(h) for h in results]

    def get_hotspots_paginated(
        self, limit: int = 50, offset: int = 0
    ) -> list[Hotspots]:
        stmt = (
            select(Hotspots)
            .order_by(col(Hotspots.acq_datetime).desc(), col(Hotspots.id))
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())

    def iter_hotspots_filtered(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        max_rows: int = 20000,
    ) -> Iterator[dict[str, Any]]:
        stmt = sa_select(
            col(Hotspots.id),
            col(Hotspots.latitude),
            col(Hotspots.longitude),
            col(Hotspots.acq_datetime),
            col(Hotspots.frp),
        )
        if start_date is not None:
            stmt = stmt.where(col(Hotspots.acq_datetime) >= start_date)
        if end_date is not None:
            stmt = stmt.where(col(Hotspots.acq_datetime) <= end_date)
        if min_lat is not None:
            stmt = stmt.where(col(Hotspots.latitude) >= min_lat)
        if max_lat is not None:
            stmt = stmt.where(col(Hotspots.latitude) <= max_lat)
        if min_lon is not None:
            stmt = stmt.where(col(Hotspots.longitude) >= min_lon)
        if max_lon is not None:
            stmt = stmt.where(col(Hotspots.longitude) <= max_lon)

        stmt = stmt.order_by(col(Hotspots.acq_datetime)).limit(max_rows)
        for row in self.session.execute(stmt):
            yield {
                "id": str(row[0]),
                "latitude": row[1],
                "longitude": row[2],
                "acq_datetime": row[3],
                "frp": row[4],
            }
