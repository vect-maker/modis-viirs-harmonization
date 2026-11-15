from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import httpx
import pytest
from nats.js.errors import KeyNotFoundError
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select

from catchup import CatchUpProcess
from country_resolver import CentralAmericaCountryResolver
from firms_client import FirmsApiClient, FirmsBudget, QuotaExhaustedError
from hotspot_writer import DimCountry, FactHotspot, HotspotWriter
from nrt_sync import NrtSyncProcess


class _FakeKV:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    async def get(self, key: str) -> Any:
        if key not in self.data:
            raise KeyNotFoundError()

        @dataclass
        class _Entry:
            value: bytes

        return _Entry(value=self.data[key])

    async def put(self, key: str, value: bytes) -> None:
        self.data[key] = value


class _FakeFirmsClient(FirmsApiClient):
    def __init__(self, *, fail_after_calls: int | None = None) -> None:
        super().__init__(map_key="test-key")
        self.calls = 0
        self.fail_after_calls = fail_after_calls
        self.requested_sources: list[tuple[str, date, int]] = []

    async def ensure_budget(self, client: httpx.AsyncClient) -> FirmsBudget:
        if self.fail_after_calls is not None and self.calls >= self.fail_after_calls:
            raise QuotaExhaustedError("Simulated quota limit")
        return FirmsBudget(transaction_limit=5000, current_transactions=self.calls)

    async def fetch_data_availability(
        self, client: httpx.AsyncClient
    ) -> dict[str, tuple[date, date]]:
        return {
            "MODIS_SP": (date(2000, 11, 1), date(2026, 8, 31)),
            "MODIS_NRT": (date(2026, 9, 1), date(2026, 11, 15)),
            "VIIRS_NOAA20_SP": (date(2018, 4, 1), date(2026, 7, 31)),
            "VIIRS_NOAA20_NRT": (date(2026, 8, 1), date(2026, 11, 15)),
        }

    async def fetch_area_csv(
        self,
        client: httpx.AsyncClient,
        *,
        source: str,
        bbox: str,
        day_range: int,
        end_date: date,
    ) -> list[dict[str, str]]:
        self.calls += 1
        self.requested_sources.append((source, end_date, day_range))
        if source.startswith("MODIS"):
            return [
                {
                    "latitude": "12.50000",
                    "longitude": "-86.10000",
                    "brightness": "325.4",
                    "bright_t31": "295.1",
                    "scan": "1.0",
                    "track": "1.0",
                    "acq_date": end_date.isoformat(),
                    "acq_time": "1930",
                    "satellite": "Aqua",
                    "instrument": "MODIS",
                    "confidence": "85",
                    "version": "6.1NRT",
                    "frp": "24.5",
                    "daynight": "D",
                    "type": "0",
                }
            ]
        return [
            {
                "latitude": "12.60000",
                "longitude": "-86.20000",
                "bright_ti4": "340.2",
                "bright_ti5": "298.0",
                "scan": "0.4",
                "track": "0.4",
                "acq_date": end_date.isoformat(),
                "acq_time": "1935",
                "satellite": "N20",
                "instrument": "VIIRS",
                "confidence": "n",
                "version": "2.0NRT",
                "frp": "12.0",
                "daynight": "D",
                "type": "0",
            }
        ]


def _make_sqlite_writer() -> HotspotWriter:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return HotspotWriter(engine)


def test_catchup_resumes_from_kv_cursor_after_quota_pause():
    async def _run() -> None:
        writer = _make_sqlite_writer()
        kv = _FakeKV()

        # Simulate quota exhaustion after 2 API calls (first 5-day chunk)
        client_part1 = _FakeFirmsClient(fail_after_calls=2)
        catchup = CatchUpProcess(
            firms_client=client_part1,
            writer=writer,
            kv=kv,
            bbox="-87.7,10.7,-82.7,15.1",
            country_name="Nicaragua",
            cooldown_seconds=0.01,
            default_lookback_days=7,
        )

        async with httpx.AsyncClient() as http_client:
            with pytest.raises(QuotaExhaustedError):
                await catchup.run_once(
                    http_client=http_client,
                    today_utc=date(2026, 9, 10),
                )

        # First chunk (2026-09-03..2026-09-07) completed and checkpointed
        assert kv.data["catchup.cursor"] == b"2026-09-07"
        assert "catchup.completed" not in kv.data

        # Resume with fresh quota
        client_part2 = _FakeFirmsClient(fail_after_calls=None)
        catchup_resumed = CatchUpProcess(
            firms_client=client_part2,
            writer=writer,
            kv=kv,
            bbox="-87.7,10.7,-82.7,15.1",
            country_name="Nicaragua",
        )

        async with httpx.AsyncClient() as http_client:
            done = await catchup_resumed.run_once(
                http_client=http_client,
                today_utc=date(2026, 9, 10),
            )

        assert done is True
        assert kv.data["catchup.completed"] == b"true"
        assert kv.data["catchup.cursor"] == b"2026-09-10"
        # Resumed chunk only fetched 2026-09-08..2026-09-10 (day_range=3)
        assert all(
            end == date(2026, 9, 10) and dr == 3
            for _, end, dr in client_part2.requested_sources
        )

        with Session(writer.engine) as session:
            rows = list(session.exec(select(FactHotspot)).all())
            assert len(rows) == 4  # 2 sensors x 2 chunks

    asyncio.run(_run())


def test_nrt_sync_deduplicates_inserts_and_updates_kv():
    async def _run() -> None:
        writer = _make_sqlite_writer()
        kv = _FakeKV()
        firms = _FakeFirmsClient()

        nrt = NrtSyncProcess(
            firms_client=firms,
            writer=writer,
            kv=kv,
            bbox="-87.7,10.7,-82.7,15.1",
            country_name="Nicaragua",
            poll_interval_seconds=60.0,
            day_range=2,
        )

        async with httpx.AsyncClient() as http_client:
            inserted_first = await nrt.run_once(
                http_client=http_client,
                today_utc=date(2026, 11, 15),
            )
            inserted_second = await nrt.run_once(
                http_client=http_client,
                today_utc=date(2026, 11, 15),
            )

        # Fake returns 1 MODIS and 1 VIIRS shape across NRT sources -> 2 unique rows
        assert inserted_first == 2
        assert inserted_second == 0

        state = json.loads(kv.data["nrt.last_sync"].decode("utf-8"))
        assert state["last_inserted_count"] == 0
        assert writer.get_latest_hotspot_date() == date(2026, 11, 15)
        assert isinstance(datetime.fromisoformat(state["last_sync_at"]), datetime)

    asyncio.run(_run())


def test_country_resolver_maps_central_america_and_excludes_outside_points():
    resolver = CentralAmericaCountryResolver()
    assert resolver.resolve(17.25, -88.77) == "Belize"
    assert resolver.resolve(9.93, -84.08) == "Costa_Rica"
    assert resolver.resolve(13.69, -89.22) == "El_Salvador"
    assert resolver.resolve(14.63, -90.51) == "Guatemala"
    assert resolver.resolve(14.07, -87.19) == "Honduras"
    assert resolver.resolve(12.11, -86.24) == "Nicaragua"
    assert resolver.resolve(8.98, -79.52) == "Panama"
    # Points inside Central America bbox but outside the 7 countries
    assert resolver.resolve(16.75, -93.12) is None  # Chiapas, Mexico
    assert resolver.resolve(7.50, -76.80) is None  # Colombia


def test_hotspot_writer_resolves_real_countries_when_region_is_central_america():
    writer = _make_sqlite_writer()
    rows = [
        {
            "latitude": "12.11000",
            "longitude": "-86.24000",
            "acq_date": "2026-11-15",
            "acq_time": "1800",
            "satellite": "N20",
            "instrument": "VIIRS",
            "confidence": "n",
            "frp": "10.0",
        },
        {
            "latitude": "9.93000",
            "longitude": "-84.08000",
            "acq_date": "2026-11-15",
            "acq_time": "1805",
            "satellite": "N20",
            "instrument": "VIIRS",
            "confidence": "h",
            "frp": "22.5",
        },
        {
            # Outside Central America (southern Mexico) -> skipped
            "latitude": "16.75000",
            "longitude": "-93.12000",
            "acq_date": "2026-11-15",
            "acq_time": "1810",
            "satellite": "N20",
            "instrument": "VIIRS",
            "confidence": "h",
            "frp": "15.0",
        },
    ]

    inserted = writer.insert_new_hotspots(rows, country_name="Central_America")
    assert inserted == 2

    with Session(writer.engine) as session:
        country_names = sorted(
            c.name for c in session.exec(select(DimCountry)).all()
        )
        assert country_names == ["Costa_Rica", "Nicaragua"]


def test_firms_client_retries_transient_500_on_check_budget():
    async def _run() -> None:
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                return httpx.Response(500, request=request)
            return httpx.Response(
                200,
                json={"transaction_limit": 5000, "current_transactions": 120},
                request=request,
            )

        client = FirmsApiClient(
            map_key="test-key",
            max_retries=3,
            retry_backoff_seconds=0.0,
        )
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http_client:
            budget = await client.check_budget(http_client)

        assert attempts == 3
        assert budget == FirmsBudget(transaction_limit=5000, current_transactions=120)

    asyncio.run(_run())


def test_firms_client_raises_after_exhausting_500_retries():
    async def _run() -> None:
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(500, request=request)

        client = FirmsApiClient(
            map_key="test-key",
            max_retries=3,
            retry_backoff_seconds=0.0,
        )
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http_client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.check_budget(http_client)

        assert attempts == 3

    asyncio.run(_run())
