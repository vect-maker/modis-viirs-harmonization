from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

FIRMS_BASE_URL = os.getenv("FIRMS_BASE_URL", "https://firms.modaps.eosdis.nasa.gov")


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

    def _require_key(self) -> str:
        if not self.map_key or self.map_key == "your_firms_map_key_here":
            raise RuntimeError("Valid FIRMS_MAP_KEY is required.")
        return self.map_key

    async def check_budget(self, client: httpx.AsyncClient) -> FirmsBudget:
        key = self._require_key()
        resp = await client.get(
            f"{self.base_url}/mapserver/mapkey_status/",
            params={"MAP_KEY": key},
            timeout=15.0,
        )
        if resp.status_code == 429:
            raise QuotaExhaustedError("HTTP 429 from mapkey_status")
        resp.raise_for_status()
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
        resp = await client.get(url, timeout=30.0)
        if resp.status_code == 429:
            raise QuotaExhaustedError("HTTP 429 from data_availability")
        resp.raise_for_status()
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
        resp = await client.get(url, timeout=60.0)
        if resp.status_code == 429:
            raise QuotaExhaustedError(f"HTTP 429 fetching {source} ({end_date})")
        resp.raise_for_status()

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
