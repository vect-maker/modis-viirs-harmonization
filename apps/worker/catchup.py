from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

import httpx
from nats.js.errors import KeyNotFoundError

from firms_client import FirmsApiClient, QuotaExhaustedError
from hotspot_writer import HotspotWriter

logger = logging.getLogger("firms.worker.catchup")

SENSOR_FAMILIES: list[tuple[str, str]] = [
    ("MODIS_SP", "MODIS_NRT"),
    ("VIIRS_SNPP_SP", "VIIRS_SNPP_NRT"),
    ("VIIRS_NOAA20_SP", "VIIRS_NOAA20_NRT"),
    ("VIIRS_NOAA21_SP", "VIIRS_NOAA21_NRT"),
]


class KVStoreProtocol(Protocol):
    async def get(self, key: str) -> object: ...
    async def put(self, key: str, value: bytes) -> object: ...


def _resolve_source_for_window(
    sp_source: str,
    nrt_source: str,
    window_end: date,
    availability: dict[str, tuple[date, date]],
) -> str | None:
    sp_range = availability.get(sp_source)
    if sp_range and sp_range[0] <= window_end <= sp_range[1]:
        return sp_source
    nrt_range = availability.get(nrt_source)
    if nrt_range and window_end >= nrt_range[0]:
        return nrt_source
    return None


class CatchUpProcess:
    """
    Phase 1: Quota-aware backfill process that catches up missing FIRMS dates
    in 5-day chunks from the latest stored hotspot (or NATS KV cursor) up to today.
    """

    def __init__(
        self,
        *,
        firms_client: FirmsApiClient,
        writer: HotspotWriter,
        kv: KVStoreProtocol | None,
        bbox: str,
        country_name: str,
        cooldown_seconds: float = 610.0,
        default_lookback_days: int = 30,
    ) -> None:
        self.firms_client = firms_client
        self.writer = writer
        self.kv = kv
        self.bbox = bbox
        self.country_name = country_name
        self.cooldown_seconds = cooldown_seconds
        self.default_lookback_days = default_lookback_days

    async def _kv_get_str(self, key: str) -> str | None:
        if self.kv is None:
            return None
        try:
            entry = await self.kv.get(key)
            value = getattr(entry, "value", None)
            if isinstance(value, (bytes, bytearray)) and value:
                return value.decode("utf-8")
        except KeyNotFoundError:
            return None
        except Exception as exc:
            logger.warning("Failed reading KV key %s: %s", key, exc)
        return None

    async def _kv_put_str(self, key: str, value: str) -> None:
        if self.kv is None:
            return
        await self.kv.put(key, value.encode("utf-8"))

    async def is_completed(self) -> bool:
        return (await self._kv_get_str("catchup.completed")) == "true"

    async def _resolve_start_date(self, today_utc: date) -> date:
        cursor_raw = await self._kv_get_str("catchup.cursor")
        if cursor_raw:
            return date.fromisoformat(cursor_raw) + timedelta(days=1)

        latest_db = self.writer.get_latest_hotspot_date()
        if latest_db is not None:
            return latest_db + timedelta(days=1)

        return today_utc - timedelta(days=self.default_lookback_days)

    async def run_once(
        self,
        *,
        http_client: httpx.AsyncClient,
        today_utc: date | None = None,
    ) -> bool:
        """
        Runs catch-up chunks until caught up to `today_utc`.
        Returns True when catch-up is complete; returns False if interrupted by quota.
        """
        target_today = today_utc or datetime.now(UTC).date()
        if await self.is_completed():
            return True

        cursor = await self._resolve_start_date(target_today)
        if cursor > target_today:
            await self._kv_put_str("catchup.completed", "true")
            logger.info("Catch-up already at %s; marking complete.", target_today)
            return True

        availability = await self.firms_client.fetch_data_availability(http_client)

        while cursor <= target_today:
            window_end = min(cursor + timedelta(days=4), target_today)
            day_range = (window_end - cursor).days + 1
            total_inserted = 0

            for sp_src, nrt_src in SENSOR_FAMILIES:
                source = _resolve_source_for_window(
                    sp_src, nrt_src, window_end, availability
                )
                if source is None:
                    continue

                await self.firms_client.ensure_budget(http_client)
                rows = await self.firms_client.fetch_area_csv(
                    http_client,
                    source=source,
                    bbox=self.bbox,
                    day_range=day_range,
                    end_date=window_end,
                )
                inserted = self.writer.insert_new_hotspots(
                    rows,
                    country_name=self.country_name,
                    harmonization_category=f"CATCHUP_{source}",
                )
                total_inserted += inserted

            await self._kv_put_str("catchup.cursor", window_end.isoformat())
            await self._kv_put_str(
                "catchup.last_progress",
                json.dumps(
                    {
                        "cursor": window_end.isoformat(),
                        "inserted": total_inserted,
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                ),
            )
            logger.info(
                "Catch-up chunk %s..%s complete (inserted=%d)",
                cursor.isoformat(),
                window_end.isoformat(),
                total_inserted,
            )
            cursor = window_end + timedelta(days=1)

        await self._kv_put_str("catchup.completed", "true")
        logger.info("Catch-up phase completed up to %s.", target_today.isoformat())
        return True

    async def run_until_caught_up(self, stop_event: asyncio.Event) -> None:
        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            while not stop_event.is_set():
                try:
                    done = await self.run_once(http_client=http_client)
                    if done:
                        return
                except QuotaExhaustedError as exc:
                    logger.warning(
                        "Catch-up paused due to FIRMS quota (%s). Sleeping %.0fs...",
                        exc,
                        self.cooldown_seconds,
                    )
                except Exception as exc:
                    logger.exception(
                        "Catch-up cycle failed (%s). Retrying in %.0fs...",
                        exc,
                        self.cooldown_seconds,
                    )

                try:
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=self.cooldown_seconds
                    )
                except TimeoutError:
                    continue
