from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Annotated, Any, Generic, Literal, TypeVar

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field

from repositories.spatial_filter import parse_geojson_polygon_to_wkt

T = TypeVar("T")

MetricMode = Literal["raw", "harmonized"]


class ChartFilterParams(BaseModel):
    """Shared filter parameters standardized across all /charts/* endpoints."""

    start_date: date | None = Field(
        default=None,
        description="Filter detections on or after this UTC date (YYYY-MM-DD)",
    )
    end_date: date | None = Field(
        default=None,
        description="Filter detections on or before this UTC date (YYYY-MM-DD)",
    )
    country: str | None = Field(
        default=None,
        max_length=100,
        description="Filter by country name",
    )
    polygon: str | None = Field(
        default=None,
        description="GeoJSON Polygon or MultiPolygon (RFC 7946, EPSG:4326) serialized as JSON",
    )
    metric: MetricMode = Field(
        default="raw",
        description="Counting/FRP mode: raw or harmonized",
    )

    def validate_dates(self) -> None:
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise HTTPException(
                status_code=400,
                detail="start_date no puede ser posterior a end_date",
            )

    @property
    def polygon_wkt(self) -> str | None:
        if self.polygon is None:
            return None
        try:
            return parse_geojson_polygon_to_wkt(self.polygon)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    def to_datetime_bounds(self) -> tuple[datetime | None, datetime | None]:
        start_dt = (
            datetime.combine(self.start_date, time.min)
            if self.start_date is not None
            else None
        )
        end_dt = (
            datetime.combine(self.end_date, time.max)
            if self.end_date is not None
            else None
        )
        return start_dt, end_dt

    def to_year_bounds(self) -> tuple[int | None, int | None]:
        return (
            self.start_date.year if self.start_date is not None else None,
            self.end_date.year if self.end_date is not None else None,
        )

    def active_dict(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "country": self.country,
            "has_polygon": self.polygon is not None,
        }
        if extra:
            payload.update(extra)
        return payload


def get_chart_filters(
    start_date: Annotated[
        date | None,
        Query(description="Filter detections on or after this UTC date (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="Filter detections on or before this UTC date (YYYY-MM-DD)"),
    ] = None,
    country: Annotated[
        str | None,
        Query(max_length=100, description="Filter by country name"),
    ] = None,
    polygon: Annotated[
        str | None,
        Query(
            description="GeoJSON Polygon or MultiPolygon (RFC 7946, EPSG:4326) serialized as JSON"
        ),
    ] = None,
    metric: Annotated[
        MetricMode,
        Query(description="Counting/FRP mode: raw or harmonized"),
    ] = "raw",
) -> ChartFilterParams:
    filters = ChartFilterParams(
        start_date=start_date,
        end_date=end_date,
        country=country,
        polygon=polygon,
        metric=metric,
    )
    filters.validate_dates()
    return filters


ChartFiltersDep = Annotated[ChartFilterParams, Depends(get_chart_filters)]


class ChartMeta(BaseModel):
    """Standardized metadata block returned by every /charts/* endpoint."""

    metric: MetricMode
    filters: dict[str, Any]
    coverage: dict[str, Any] | None = None
    generated_at: datetime


class ChartResponse(BaseModel, Generic[T]):
    """Generic response envelope for all standardized graph-populating endpoints."""

    chart: str
    meta: ChartMeta
    data: T


def build_chart_response(
    chart: str,
    data: T,
    filters: ChartFilterParams | None = None,
    *,
    extra_filters: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
) -> ChartResponse[T]:
    resolved_filters = filters or ChartFilterParams()
    return ChartResponse[T](
        chart=chart,
        meta=ChartMeta(
            metric=resolved_filters.metric,
            filters=resolved_filters.active_dict(extra_filters),
            coverage=coverage,
            generated_at=datetime.now(UTC),
        ),
        data=data,
    )
