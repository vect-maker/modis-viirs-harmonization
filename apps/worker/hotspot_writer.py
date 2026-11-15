from __future__ import annotations

import os
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from shared_core.constants import firms_uuid5
from shared_core.models import DimCountry, DimPlatform, FactHotspot
from sqlalchemy import Engine, create_engine, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, col, select

from country_resolver import (
    CentralAmericaCountryResolver,
    get_default_country_resolver,
)


def build_db_engine(database_url: str | None = None) -> Engine:
    url = (database_url or os.getenv("DATABASE_URL", "")).strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required for worker DB access.")
    return create_engine(url, pool_pre_ping=True)


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
        return 20, "l"
    if lower in {"n", "nominal"}:
        return 50, "n"
    if lower in {"h", "high"}:
        return 90, "h"
    try:
        num = int(float(cleaned))
    except ValueError:
        return None, cleaned[:20]
    if num >= 80:
        return num, "h"
    if num >= 30:
        return num, "n"
    return num, "l"


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


def _normalize_satellite(raw: str) -> str:
    cleaned = raw.strip()
    upper = cleaned.upper()
    mapping = {
        "N": "Suomi-NPP",
        "SNPP": "Suomi-NPP",
        "SUOMI NPP": "Suomi-NPP",
        "N20": "NOAA-20",
        "NOAA20": "NOAA-20",
        "N21": "NOAA-21",
        "NOAA21": "NOAA-21",
        "T": "Terra",
        "TERRA": "Terra",
        "A": "Aqua",
        "AQUA": "Aqua",
    }
    return mapping.get(upper, cleaned[:50])


def _classify_overpass_window(acq_dt: datetime, lon: float) -> str:
    solar_hour = (acq_dt.hour + acq_dt.minute / 60.0 + lon / 15.0) % 24.0
    if 6.0 <= solar_hour < 12.0:
        return "MORNING"
    if 12.0 <= solar_hour < 18.0:
        return "AFTERNOON"
    return "NIGHT"


@dataclass(frozen=True)
class InsertedHotspot:
    """Summary of a newly persisted hotspot row for downstream notifications."""

    id: uuid.UUID
    country: str
    satellite: str
    instrument: str
    latitude: float
    longitude: float
    acq_datetime: datetime
    frp: float | None
    confidence_class: str | None


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
        return len(
            self.insert_new_hotspots_with_details(
                rows,
                country_name=country_name,
                harmonization_category=harmonization_category,
            )
        )

    def insert_new_hotspots_with_details(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        country_name: str | None = None,
        harmonization_category: str = "API_INGESTED",
    ) -> list[InsertedHotspot]:
        if not rows:
            return []

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
        candidate_details: dict[uuid.UUID, InsertedHotspot] = {}

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
            satellite_norm = _normalize_satellite(satellite)
            platform_id = firms_uuid5(
                f"platform:{satellite_norm.lower()}:{instrument.lower()}"
            )
            platforms[platform_id] = (satellite_norm, instrument)

            acq_dt = _parse_acq_datetime(acq_date_raw, acq_time_raw)
            hotspot_id = firms_uuid5(
                f"hotspot:{resolved_country.lower()}:{satellite_norm.lower()}:"
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
            overpass_win = _classify_overpass_window(acq_dt, lon)
            # Peso armonizado por plataforma (3 satélites VIIRS activos en era post-2024: 1/3)
            if instrument == "VIIRS":
                h_weight = round(1.0 / 3.0, 4) if acq_dt.year >= 2024 else 0.5
            else:
                h_weight = (
                    2.65
                    if overpass_win == "MORNING"
                    else (1.85 if overpass_win == "AFTERNOON" else 1.45)
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
                    "overpass_window": overpass_win,
                    "harmonization_category": harmonization_category,
                    "harmonized_weight": h_weight,
                    "harmonized_frp": (
                        round(frp * h_weight, 4) if frp is not None else None
                    ),
                }
            )
            candidate_details.setdefault(
                hotspot_id,
                InsertedHotspot(
                    id=hotspot_id,
                    country=resolved_country,
                    satellite=satellite_norm,
                    instrument=instrument,
                    latitude=lat,
                    longitude=lon,
                    acq_datetime=acq_dt,
                    frp=frp,
                    confidence_class=conf_cls,
                ),
            )

        if not fact_rows:
            return []

        # Si MODIS coincide espacial (~2 km) y temporalmente (<= 4 h) con VIIRS, peso = 0.0
        viirs_pts = [
            (item["latitude"], item["longitude"], item["acq_datetime"])
            for item in fact_rows
            if platforms.get(item["platform_id"], ("", ""))[1] == "VIIRS"
        ]
        if viirs_pts:
            for item in fact_rows:
                if platforms.get(item["platform_id"], ("", ""))[1] != "MODIS":
                    continue
                lat_m = item["latitude"]
                lon_m = item["longitude"]
                dt_m = item["acq_datetime"]
                if any(
                    abs(lat_m - v_lat) <= 0.02
                    and abs(lon_m - v_lon) <= 0.02
                    and abs((dt_m - v_dt).total_seconds()) <= 14400
                    for v_lat, v_lon, v_dt in viirs_pts
                ):
                    item["harmonized_weight"] = 0.0
                    item["harmonized_frp"] = 0.0 if item["frp"] is not None else None

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
            inserted_details: list[InsertedHotspot] = []
            for offset in range(0, len(fact_rows), batch_size):
                batch = fact_rows[offset : offset + batch_size]
                stmt = (
                    insert_fn(FactHotspot)
                    .values(batch)
                    .on_conflict_do_nothing(index_elements=["id"])
                    .returning(col(FactHotspot.id))
                )
                for row in session.exec(stmt).all():
                    raw_id = row[0] if not isinstance(row, uuid.UUID) else row
                    inserted_id = (
                        raw_id
                        if isinstance(raw_id, uuid.UUID)
                        else uuid.UUID(str(raw_id))
                    )
                    detail = candidate_details.get(inserted_id)
                    if detail is not None:
                        inserted_details.append(detail)
            session.commit()

        return inserted_details
