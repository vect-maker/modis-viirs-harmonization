from __future__ import annotations

import asyncio
import csv
import io
import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx
from shared_core.constants import DEFAULT_FIRMS_BASE_URL

logger = logging.getLogger("firms.worker.client")
FIRMS_BASE_URL = os.getenv("FIRMS_BASE_URL", DEFAULT_FIRMS_BASE_URL)
RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})


class QuotaExhaustedError(RuntimeError):
    """Raised when the NASA FIRMS MAP_KEY transaction budget is exhausted."""


@dataclass(frozen=True)
class FirmsBudget:
    transaction_limit: int
    current_transactions: int

    @property
    def remaining(self) -> int:
        return max(0, self.transaction_limit - self.current_transactions)


class FirmsApiClient:
    """Async HTTP client for NASA FIRMS data_availability, area CSV, and budget APIs."""

    def __init__(
        self,
        *,
        map_key: str | None = None,
        base_url: str | None = None,
        quota_reserve: int | None = None,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
    ) -> None:
        self.map_key = (
            map_key if map_key is not None else os.getenv("FIRMS_MAP_KEY", "")
        ).strip()
        self.base_url = (base_url or FIRMS_BASE_URL).rstrip("/")
        self.quota_reserve = (
            quota_reserve
            if quota_reserve is not None
            else int(os.getenv("FIRMS_QUOTA_RESERVE", "50"))
        )
        self.max_retries = max(1, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)

    def _require_key(self) -> str:
        if not self.map_key or self.map_key == "your_firms_map_key_here":
            raise RuntimeError("Valid FIRMS_MAP_KEY is required.")
        return self.map_key

    async def _get_with_retries(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        timeout: float = 30.0,
        context: str,
    ) -> httpx.Response:
        for attempt in range(self.max_retries):
            try:
                resp = await client.get(url, params=params, timeout=timeout)
            except httpx.TransportError as exc:
                if attempt + 1 >= self.max_retries:
                    raise
                delay = self.retry_backoff_seconds * (2**attempt)
                logger.warning(
                    "Transient transport error %s (attempt %d/%d): %s; "
                    "retrying in %.1fs",
                    context,
                    attempt + 1,
                    self.max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                continue

            if resp.status_code == 429:
                raise QuotaExhaustedError(f"HTTP 429 {context}")
            if (
                resp.status_code in RETRYABLE_STATUS_CODES
                and attempt + 1 < self.max_retries
            ):
                delay = self.retry_backoff_seconds * (2**attempt)
                logger.warning(
                    "Transient HTTP %d %s (attempt %d/%d); retrying in %.1fs",
                    resp.status_code,
                    context,
                    attempt + 1,
                    self.max_retries,
                    delay,
                )
                await asyncio.sleep(delay)
                continue

            resp.raise_for_status()
            return resp

        raise RuntimeError(f"Unreachable retry loop exit {context}")

    async def check_budget(self, client: httpx.AsyncClient) -> FirmsBudget:
        key = self._require_key()
        resp = await self._get_with_retries(
            client,
            f"{self.base_url}/mapserver/mapkey_status/",
            params={"MAP_KEY": key},
            timeout=15.0,
            context="from mapkey_status",
        )
        data: dict[str, Any] = resp.json()
        return FirmsBudget(
            transaction_limit=int(data.get("transaction_limit", 0)),
            current_transactions=int(data.get("current_transactions", 0)),
        )

    async def ensure_budget(self, client: httpx.AsyncClient) -> FirmsBudget:
        budget = await self.check_budget(client)
        if budget.transaction_limit > 0 and budget.remaining < self.quota_reserve:
            raise QuotaExhaustedError(
                f"FIRMS quota near limit ({budget.current_transactions}/"
                f"{budget.transaction_limit}, reserve={self.quota_reserve})"
            )
        return budget

    async def fetch_data_availability(
        self, client: httpx.AsyncClient
    ) -> dict[str, tuple[date, date]]:
        key = self._require_key()
        url = f"{self.base_url}/api/data_availability/csv/{key}/ALL"
        resp = await self._get_with_retries(
            client,
            url,
            timeout=30.0,
            context="from data_availability",
        )
        text = resp.text.strip()
        self._validate_csv_text(text, url)

        availability: dict[str, tuple[date, date]] = {}
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            data_id = (row.get("data_id") or "").strip()
            min_raw = (row.get("min_date") or "").strip()
            max_raw = (row.get("max_date") or "").strip()
            if data_id and min_raw and max_raw:
                availability[data_id] = (
                    date.fromisoformat(min_raw),
                    date.fromisoformat(max_raw),
                )
        return availability

    async def fetch_area_csv(
        self,
        client: httpx.AsyncClient,
        *,
        source: str,
        bbox: str,
        day_range: int,
        end_date: date,
    ) -> list[dict[str, str]]:
        key = self._require_key()
        if day_range < 1 or day_range > 5:
            raise ValueError("day_range must be between 1 and 5 for FIRMS area API")

        url = (
            f"{self.base_url}/api/area/csv/{key}/{source}/"
            f"{bbox}/{day_range}/{end_date.isoformat()}"
        )
        resp = await self._get_with_retries(
            client,
            url,
            timeout=60.0,
            context=f"fetching {source} ({end_date})",
        )

        text = resp.text.strip()
        if not text:
            return []
        self._validate_csv_text(text, url)

        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader if row]

    @staticmethod
    def _validate_csv_text(text: str, url: str) -> None:
        if "Invalid MAP_KEY" in text:
            raise RuntimeError(f"FIRMS rejected MAP_KEY for {url}: {text[:200]}")
        if "exceeded" in text.lower():
            raise QuotaExhaustedError(f"FIRMS quota exceeded for {url}: {text[:200]}")
        if text.lstrip().lower().startswith("<html"):
            raise RuntimeError(f"Unexpected HTML response from {url}: {text[:200]}")
