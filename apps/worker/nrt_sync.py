from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, date, datetime

import httpx

from catchup import KVStoreProtocol
from firms_client import FirmsApiClient, QuotaExhaustedError
from hotspot_writer import HotspotWriter

logger = logging.getLogger("firms.worker.nrt")

NRT_SOURCES: tuple[str, ...] = (
    "MODIS_NRT",
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
)


class NrtSyncProcess:
    """
    Phase 2: Frequent Near Real-Time polling process that fetches recent NRT
    detections (`DAY_RANGE=2`) and inserts only unseen hotspots into PostGIS.
    """

    def __init__(
        self,
        *,
        firms_client: FirmsApiClient,
        writer: HotspotWriter,
        kv: KVStoreProtocol | None,
        bbox: str,
        country_name: str,
        poll_interval_seconds: float = 300.0,
        day_range: int = 2,
    ) -> None:
        self.firms_client = firms_client
        self.writer = writer
        self.kv = kv
        self.bbox = bbox
        self.country_name = country_name
        self.poll_interval_seconds = poll_interval_seconds
        self.day_range = day_range

    async def run_once(
        self,
        *,
        http_client: httpx.AsyncClient,
        today_utc: date | None = None,
    ) -> int:
        target_today = today_utc or datetime.now(UTC).date()
        total_inserted = 0

        for source in NRT_SOURCES:
            await self.firms_client.ensure_budget(http_client)
            rows = await self.firms_client.fetch_area_csv(
                http_client,
                source=source,
                bbox=self.bbox,
                day_range=self.day_range,
                end_date=target_today,
            )
            inserted = self.writer.insert_new_hotspots(
                rows,
                country_name=self.country_name,
                harmonization_category=f"NRT_{source}",
            )
            total_inserted += inserted

        if self.kv is not None:
            payload = json.dumps(
                {
                    "last_sync_at": datetime.now(UTC).isoformat(),
                    "last_inserted_count": total_inserted,
                }
            ).encode("utf-8")
            await self.kv.put("nrt.last_sync", payload)

        logger.info(
            "NRT sync cycle finished (date=%s, inserted=%d)",
            target_today.isoformat(),
            total_inserted,
        )
        return total_inserted

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            while not stop_event.is_set():
                try:
                    await self.run_once(http_client=http_client)
                except QuotaExhaustedError as exc:
                    logger.warning("NRT sync skipped due to quota: %s", exc)
                except Exception as exc:
                    logger.exception("NRT sync cycle failed: %s", exc)

                try:
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=self.poll_interval_seconds
                    )
                except TimeoutError:
                    continue
