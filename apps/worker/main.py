from __future__ import annotations

import asyncio
import logging
import os
import signal

import nats
from dotenv import load_dotenv
from nats.aio.client import Client as NatsClient
from nats.js.api import KeyValueConfig
from nats.js.errors import BucketNotFoundError
from nats.js.kv import KeyValue
from shared_core.constants import CENTRAL_AMERICA_BBOX

from catchup import CatchUpProcess
from firms_client import FirmsApiClient
from hotspot_writer import HotspotWriter, build_db_engine
from nrt_sync import NrtSyncProcess

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("firms.worker")

WORKER_STATE_BUCKET = "worker_state"


class WorkerRunner:
    """
    Coordinates the two-phase worker lifecycle:
    1. CatchUpProcess (quota-aware historical backfill up to today)
    2. NrtSyncProcess (frequent Near Real-Time polling)
    """

    def __init__(self) -> None:
        self.nats_url = os.getenv("NATS_URL", "nats://localhost:4222").strip()
        self.bbox = os.getenv("FIRMS_AREA_BBOX", CENTRAL_AMERICA_BBOX).strip()
        self.country_name = os.getenv("FIRMS_COUNTRY_NAME", "Central_America").strip()
        self.cooldown_seconds = float(os.getenv("CATCHUP_COOLDOWN_SECONDS", "610"))
        self.poll_interval_seconds = float(
            os.getenv("NRT_POLL_INTERVAL_SECONDS", "300")
        )
        self._nc: NatsClient | None = None
        self._kv: KeyValue | None = None
        self._stop_event = asyncio.Event()

    async def connect_nats(self) -> None:
        if not self.nats_url:
            return
        self._nc = await nats.connect(servers=[self.nats_url], name="firms-worker")
        js = self._nc.jetstream()
        try:
            self._kv = await js.key_value(WORKER_STATE_BUCKET)
        except BucketNotFoundError:
            self._kv = await js.create_key_value(
                config=KeyValueConfig(bucket=WORKER_STATE_BUCKET)
            )
        logger.info("Worker connected to NATS KV at %s", self.nats_url)

    async def close(self) -> None:
        if self._nc is not None:
            try:
                await self._nc.drain()
            except Exception:
                try:
                    await self._nc.close()
                except Exception:
                    pass
            self._nc = None
        self._kv = None

    def request_stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        engine = build_db_engine()
        writer = HotspotWriter(engine)
        firms_client = FirmsApiClient()

        await self.connect_nats()
        try:
            catchup = CatchUpProcess(
                firms_client=firms_client,
                writer=writer,
                kv=self._kv,
                bbox=self.bbox,
                country_name=self.country_name,
                cooldown_seconds=self.cooldown_seconds,
            )
            await catchup.run_until_caught_up(self._stop_event)

            if self._stop_event.is_set():
                return

            nrt_sync = NrtSyncProcess(
                firms_client=firms_client,
                writer=writer,
                kv=self._kv,
                bbox=self.bbox,
                country_name=self.country_name,
                poll_interval_seconds=self.poll_interval_seconds,
            )
            await nrt_sync.run_forever(self._stop_event)
        finally:
            await self.close()


async def main() -> None:
    runner = WorkerRunner()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, runner.request_stop)
        except NotImplementedError:
            pass
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
