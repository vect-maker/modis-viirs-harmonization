from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from model import ClusterHotspots


class Hotspots(SQLModel, table=True):
    id: UUID | None = Field(default=None, primary_key=True)
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)
    bright_mir: float | None = Field(default=None)
    scan: float | None = Field(default=None)
    track: float | None = Field(default=None)
    acq_datetime: datetime | None = Field(default=None, index=True)
    satellite: str | None = Field(default=None)
    instrument: str | None = Field(default=None)
    confidence: str | None = Field(default=None)
    confidence_class: str | None = Field(default=None)
    version: str | None = Field(default=None)
    bright_tir: float | None = Field(default=None)
    frp: float | None = Field(default=None)
    daynight: str | None = Field(default=None)
    type: int | None = Field(default=None)

    clusters: list["ClusterHotspots"] = Relationship(back_populates="hotspots")