from __future__ import annotations

import os
import uuid
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

from pydantic import NaiveDatetime
from sqlalchemy import Engine, create_engine, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Field, Session, SQLModel, col, select

from country_resolver import (
    CentralAmericaCountryResolver,
    get_default_country_resolver,
)

FIRMS_NAMESPACE = uuid.UUID("98b00dc4-63e7-5855-bfed-2cdc66170e68")


def firms_uuid5(name: str) -> uuid.UUID:
    return uuid.uuid5(FIRMS_NAMESPACE, name)


def build_db_engine(database_url: str | None = None) -> Engine:
    url = (database_url or os.getenv("DATABASE_URL", "")).strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required for worker DB access.")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, pool_pre_ping=True)


class DimCountry(SQLModel, table=True):
    __tablename__ = "dim_country"  # type: ignore[assignment]

    id: uuid.UUID = Field(primary_key=True)
    name: str = Field(max_length=100, unique=True)


class DimPlatform(SQLModel, table=True):
    __tablename__ = "dim_platform"  # type: ignore[assignment]

    id: uuid.UUID = Field(primary_key=True)
    satellite: str = Field(max_length=50)
    instrument: str = Field(max_length=20)


class FactHotspot(SQLModel, table=True):
    __tablename__ = "fact_hotspots"  # type: ignore[assignment]

    id: uuid.UUID = Field(primary_key=True)
    country_id: uuid.UUID = Field(foreign_key="dim_country.id")
    platform_id: uuid.UUID = Field(foreign_key="dim_platform.id")
    latitude: float
    longitude: float
    geom: str | None = Field(default=None)
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


def _float_or_none(val: Any) -> float | None:
    if val is None or str(val).strip() == "":
        return None
    return float(val)


def _int_or_none(val: Any) -> int | None:
    if val is None or str(val).strip() == "":
        return None
    return int(float(val))


def _parse_confidence(raw: str | None) -> tuple[int | None, str | None]:
    if raw is None:
        return None, None
    cleaned = raw.strip()
    if not cleaned:
        return None, None
    lower = cleaned.lower()
    if lower in {"l", "low"}:
        return 25, "low"
    if lower in {"n", "nominal"}:
        return 50, "nominal"
    if lower in {"h", "high"}:
        return 90, "high"
    try:
        num = int(float(cleaned))
    except ValueError:
        return None, cleaned[:20]
    if num >= 80:
        return num, "high"
    if num >= 30:
        return num, "nominal"
    return num, "low"


def _parse_acq_datetime(acq_date: str, acq_time: str) -> datetime:
    padded_time = acq_time.strip().zfill(4)
    hh = int(padded_time[:2])
    mm = int(padded_time[2:4])
    d = date.fromisoformat(acq_date.strip())
    return datetime(d.year, d.month, d.day, hh, mm)


def _normalize_instrument(raw: str) -> str:
    upper = raw.strip().upper()
    if "VIIRS" in upper:
        return "VIIRS"
    if "MODIS" in upper:
        return "MODIS"
    return upper[:20]


class HotspotWriter:
    """Writes deduplicated FIRMS detections into the PostGIS star schema."""

    def __init__(
        self,
        engine: Engine,
        *,
        country_resolver: CentralAmericaCountryResolver | None = None,
    ) -> None:
        self.engine = engine
        self._country_resolver = country_resolver

    def get_latest_hotspot_date(self) -> date | None:
        with Session(self.engine) as session:
            latest = session.exec(select(func.max(FactHotspot.acq_datetime))).first()
            if latest is None:
                return None
            if isinstance(latest, datetime):
                return latest.date()
            return date.fromisoformat(str(latest)[:10])

    def _resolve_country(self, latitude: float, longitude: float) -> str | None:
        resolver = self._country_resolver or get_default_country_resolver()
        return resolver.resolve(latitude, longitude)

    def insert_new_hotspots(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        country_name: str | None = None,
        harmonization_category: str = "API_INGESTED",
    ) -> int:
        if not rows:
            return 0

        raw_country = (country_name or "").strip()
        auto_resolve = raw_country.lower() in {
            "",
            "auto",
            "central_america",
            "central america",
        }

        countries: dict[uuid.UUID, str] = {}
        platforms: dict[uuid.UUID, tuple[str, str]] = {}
        fact_rows: list[dict[str, Any]] = []

        for row in rows:
            lat = _float_or_none(row.get("latitude"))
            lon = _float_or_none(row.get("longitude"))
            acq_date_raw = str(row.get("acq_date") or "").strip()
            acq_time_raw = str(row.get("acq_time") or "").strip()
            satellite = str(row.get("satellite") or "").strip()
            instrument_raw = str(row.get("instrument") or "").strip()
            if (
                lat is None
                or lon is None
                or not acq_date_raw
                or not acq_time_raw
                or not satellite
                or not instrument_raw
            ):
                continue

            resolved_country = (
                self._resolve_country(lat, lon) if auto_resolve else raw_country
            )
            if not resolved_country:
                continue

            country_id = firms_uuid5(f"country:{resolved_country.lower()}")
            countries[country_id] = resolved_country

            instrument = _normalize_instrument(instrument_raw)
            platform_id = firms_uuid5(
                f"platform:{satellite.lower()}:{instrument.lower()}"
            )
            platforms[platform_id] = (satellite[:50], instrument)

            acq_dt = _parse_acq_datetime(acq_date_raw, acq_time_raw)
            hotspot_id = firms_uuid5(
                f"hotspot:{resolved_country.lower()}:{satellite.lower()}:"
                f"{instrument.lower()}:{acq_dt.isoformat()}:{lat:.5f}:{lon:.5f}"
            )
            bright_mir = _float_or_none(
                row.get("bright_ti4") or row.get("brightness") or row.get("bright_mir")
            )
            bright_tir = _float_or_none(
                row.get("bright_ti5") or row.get("bright_t31") or row.get("bright_tir")
            )
            frp = _float_or_none(row.get("frp"))
            raw_conf = row.get("confidence")
            conf_num, conf_cls = _parse_confidence(
                str(raw_conf) if raw_conf is not None else None
            )

            fact_rows.append(
                {
                    "id": hotspot_id,
                    "country_id": country_id,
                    "platform_id": platform_id,
                    "latitude": lat,
                    "longitude": lon,
                    "acq_datetime": acq_dt,
                    "bright_mir": bright_mir,
                    "bright_tir": bright_tir,
                    "scan": _float_or_none(row.get("scan")),
                    "track": _float_or_none(row.get("track")),
                    "confidence": conf_num,
                    "confidence_class": conf_cls,
                    "frp": frp,
                    "daynight": (
                        str(row.get("daynight")).strip()[:5]
                        if row.get("daynight")
                        else None
                    ),
                    "type": _int_or_none(row.get("type")),
                    "version": (
                        str(row.get("version")).strip()[:20]
                        if row.get("version")
                        else None
                    ),
                    "overpass_window": None,
                    "harmonization_category": harmonization_category,
                    "harmonized_weight": 1.0,
                    "harmonized_frp": frp,
                }
            )

        if not fact_rows:
            return 0

        dialect = self.engine.dialect.name
        insert_fn = pg_insert if dialect == "postgresql" else sqlite_insert
        if dialect == "postgresql":
            for item in fact_rows:
                item["geom"] = func.ST_SetSRID(
                    func.ST_MakePoint(item["longitude"], item["latitude"]), 4326
                )

        with Session(self.engine) as session:
            for cid, cname in countries.items():
                session.exec(
                    insert_fn(DimCountry)
                    .values(id=cid, name=cname)
                    .on_conflict_do_nothing()
                )
            for pid, (sat, inst) in platforms.items():
                session.exec(
                    insert_fn(DimPlatform)
                    .values(id=pid, satellite=sat, instrument=inst)
                    .on_conflict_do_nothing()
                )

            batch_size = 1000
            total_inserted = 0
            for offset in range(0, len(fact_rows), batch_size):
                batch = fact_rows[offset : offset + batch_size]
                stmt = (
                    insert_fn(FactHotspot)
                    .values(batch)
                    .on_conflict_do_nothing(index_elements=["id"])
                    .returning(col(FactHotspot.id))
                )
                total_inserted += len(list(session.exec(stmt).all()))
            session.commit()

        return total_inserted
