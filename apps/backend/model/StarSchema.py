import uuid
from datetime import date

from pydantic import BaseModel, NaiveDatetime
from sqlmodel import Field, Relationship, SQLModel


class CountryBase(SQLModel):
    id: uuid.UUID = Field(primary_key=True)
    name: str = Field(max_length=100, unique=True)


class DimCountry(CountryBase, table=True):
    """Country dimension table (`dim_country`)."""

    __tablename__ = "dim_country"  # type: ignore[assignment]

    hotspots: list["FactHotspot"] = Relationship(back_populates="country")


class CountryPublic(CountryBase):
    """Public schema for a country record."""


class PlatformBase(SQLModel):
    id: uuid.UUID = Field(primary_key=True)
    satellite: str = Field(max_length=50)
    instrument: str = Field(max_length=20)


class DimPlatform(PlatformBase, table=True):
    """Satellite/sensor platform dimension table (`dim_platform`)."""

    __tablename__ = "dim_platform"  # type: ignore[assignment]

    hotspots: list["FactHotspot"] = Relationship(back_populates="platform")


class PlatformPublic(PlatformBase):
    """Public schema for a platform record."""


class FactHotspotBase(SQLModel):
    id: uuid.UUID = Field(primary_key=True)
    country_id: uuid.UUID = Field(foreign_key="dim_country.id")
    platform_id: uuid.UUID = Field(foreign_key="dim_platform.id")
    latitude: float
    longitude: float
    acq_datetime: NaiveDatetime = Field(index=True)
    bright_mir: float | None = Field(default=None)
    bright_tir: float | None = Field(default=None)
    scan: float | None = Field(default=None)
    track: float | None = Field(default=None)
    confidence: int | None = Field(default=None)
    confidence_class: str | None = Field(default=None, max_length=20)
    frp: float | None = Field(default=None)
    daynight: str | None = Field(default=None, max_length=5)
    type: int | None = Field(default=None)
    version: str | None = Field(default=None, max_length=20)
    overpass_window: str | None = Field(default=None, max_length=30)
    harmonization_category: str | None = Field(default=None, max_length=40)
    harmonized_weight: float | None = Field(default=None)
    harmonized_frp: float | None = Field(default=None)


class FactHotspot(FactHotspotBase, table=True):
    """Active fire observations fact table (`fact_hotspots`)."""

    __tablename__ = "fact_hotspots"  # type: ignore[assignment]

    country: DimCountry = Relationship(back_populates="hotspots")
    platform: DimPlatform = Relationship(back_populates="hotspots")


class HotspotPublic(FactHotspotBase):
    """Public schema for a hotspot detection record."""


class AvailableDatesResponse(BaseModel):
    """Distinct UTC dates with available hotspot detections."""

    dates: list[date]
    min_date: date | None
    max_date: date | None
