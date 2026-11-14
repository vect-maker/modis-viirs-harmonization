from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FireCalendarQuery(BaseModel):
    year: int = Field(ge=1990, le=2100)
    month: int | None = Field(default=None, ge=1, le=12)
    start_date: date | None = None
    end_date: date | None = None
    country: str | None = None
    department: str | None = None
    municipality: str | None = None
    min_confidence: float | None = Field(default=None, ge=0.0, le=100.0)
    confidence_class: str | None = None
    satellite: str | None = None
    instrument: str | None = None
    daynight: str | None = None
    min_frp: float | None = Field(default=None, ge=0.0)
    max_frp: float | None = Field(default=None, ge=0.0)
    cluster_id: int | None = Field(default=None, ge=1)
    aggregation: Literal["day", "week", "month"] = "day"

    @model_validator(mode="after")
    def validate_combinations(self) -> FireCalendarQuery:
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date no puede ser posterior a end_date")

        if self.start_date is not None and self.start_date.year != self.year:
            raise ValueError("start_date debe pertenecer al año indicado en year")

        if self.end_date is not None and self.end_date.year != self.year:
            raise ValueError("end_date debe pertenecer al año indicado en year")

        if self.month is not None:
            if self.start_date is not None and self.start_date.month != self.month:
                raise ValueError("start_date no corresponde al mes indicado en month")
            if self.end_date is not None and self.end_date.month != self.month:
                raise ValueError("end_date no corresponde al mes indicado en month")

        if (
            self.min_frp is not None
            and self.max_frp is not None
            and self.min_frp > self.max_frp
        ):
            raise ValueError("min_frp no puede ser mayor que max_frp")

        if self.daynight is not None:
            norm = self.daynight.strip().upper()
            if norm not in {"D", "N"}:
                raise ValueError("daynight solamente acepta 'D' o 'N'")
            self.daynight = norm

        return self


class FireCalendarInterval(BaseModel):
    date: date
    hotspot_count: int
    fire_count: int
    new_fires: int
    active_fires: int
    frp_total: float
    frp_average: float
    max_frp: float
    daytime_hotspots: int
    nighttime_hotspots: int
    high_confidence_count: int


class FireCalendarPeriod(BaseModel):
    year: int
    month: int | None = None
    start_date: date
    end_date: date
    start_datetime_utc: datetime
    end_datetime_utc: datetime


class FireCalendarResponse(BaseModel):
    period: FireCalendarPeriod
    aggregation: Literal["day", "week", "month"]
    total_hotspots: int
    total_fires: int
    new_fires: int
    active_fires: int
    frp_total: float
    frp_average: float
    max_frp: float
    daytime_hotspots: int
    nighttime_hotspots: int
    high_confidence_count: int
    intervals: list[FireCalendarInterval]
