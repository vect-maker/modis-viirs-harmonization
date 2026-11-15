from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, date, datetime
from typing import Protocol

import httpx
from shared_core.sse import (
    SSE_BROADCAST_SUBJECT,
    NotificationSeverity,
    SSEEventEnvelope,
    SSETargetScope,
)

from catchup import KVStoreProtocol
from firms_client import FirmsApiClient, QuotaExhaustedError
from hotspot_writer import HotspotWriter, InsertedHotspot

logger = logging.getLogger("firms.worker.nrt")

NRT_SOURCES: tuple[str, ...] = (
    "MODIS_NRT",
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
)


class NatsPublishProtocol(Protocol):
    async def publish(self, subject: str, payload: bytes = ...) -> None: ...
    async def flush(self, timeout: int = ...) -> None: ...


def _build_hotspot_envelope(hotspot: InsertedHotspot) -> SSEEventEnvelope:
    frp_text = f" · FRP {hotspot.frp:.1f} MW" if hotspot.frp is not None else ""
    severity = (
        NotificationSeverity.WARNING
        if hotspot.frp is not None and hotspot.frp >= 30.0
        else NotificationSeverity.INFO
    )
    return SSEEventEnvelope(
        event_id=f"hotspot-inserted-{hotspot.id}",
        emitter_service="firms-worker",
        target_scope=SSETargetScope.ALL,
        event_type="notification",
        payload={
            "title": f"New {hotspot.instrument} hotspot in {hotspot.country}",
            "message": (
                f"{hotspot.satellite} detected a hotspot at "
                f"({hotspot.latitude:.4f}, {hotspot.longitude:.4f}){frp_text}"
            ),
            "severity": severity.value,
            "duration_ms": 6000,
            "metadata": {
                "kind": "hotspot_inserted",
                "hotspot_id": str(hotspot.id),
                "country": hotspot.country,
                "satellite": hotspot.satellite,
                "instrument": hotspot.instrument,
                "latitude": hotspot.latitude,
                "longitude": hotspot.longitude,
                "acq_datetime": hotspot.acq_datetime.isoformat(),
                "frp": hotspot.frp,
                "confidence_class": hotspot.confidence_class,
            },
        },
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
        nats_client: NatsPublishProtocol | None = None,
        poll_interval_seconds: float = 300.0,
        day_range: int = 2,
    ) -> None:
        self.firms_client = firms_client
        self.writer = writer
        self.kv = kv
        self.bbox = bbox
        self.country_name = country_name
        self.nats_client = nats_client
        self.poll_interval_seconds = poll_interval_seconds
        self.day_range = day_range

    async def _broadcast_inserted_hotspots(
        self, hotspots: list[InsertedHotspot]
    ) -> None:
        if self.nats_client is None or not hotspots:
            return
        try:
            for hotspot in hotspots:
                envelope = _build_hotspot_envelope(hotspot)
                await self.nats_client.publish(
                    SSE_BROADCAST_SUBJECT,
                    envelope.model_dump_json().encode("utf-8"),
                )
            await self.nats_client.flush(timeout=1)
        except Exception as exc:
            logger.warning(
                "Failed broadcasting %d inserted hotspots to NATS: %s",
                len(hotspots),
                exc,
            )

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
            inserted_hotspots = self.writer.insert_new_hotspots_with_details(
                rows,
                country_name=self.country_name,
                harmonization_category=f"NRT_{source}",
            )
            await self._broadcast_inserted_hotspots(inserted_hotspots)
            total_inserted += len(inserted_hotspots)

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
                except httpx.HTTPError as exc:
                    logger.warning("NRT sync cycle failed due to HTTP error: %s", exc)
                except Exception as exc:
                    logger.exception("NRT sync cycle failed: %s", exc)

                try:
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=self.poll_interval_seconds
                    )
                except TimeoutError:
                    continue
