from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from typing import Literal

from moka_py import Moka

ChartBucket = Literal["temporal", "diagnostics", "models"]

DEFAULT_MAX_CAPACITY = 512
DEFAULT_TTLS: dict[ChartBucket, float] = {
    "temporal": 300.0,
    "diagnostics": 900.0,
    "models": 900.0,
}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return max(1, int(raw))


def _env_optional_float(name: str, default: float | None) -> float | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = float(raw)
    return value if value > 0 else None


def resolve_chart_bucket(path: str) -> ChartBucket | None:
    """Map a request path under /charts/* to its cache bucket."""
    marker = "/charts/"
    idx = path.find(marker)
    if idx == -1:
        return None
    subpath = path[idx + len(marker) :]
    segment = subpath.split("/", 1)[0]
    if segment in ("temporal", "diagnostics", "models"):
        return segment
    return None


def build_chart_cache_key(
    path: str,
    query_items: Sequence[tuple[str, str]],
) -> str:
    """Build a deterministic Blake2b hash key from a route path and query parameters."""
    canonical = json.dumps(
        {"path": path, "query": sorted(query_items)},
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.blake2b(canonical.encode("utf-8"), digest_size=16).hexdigest()
    return f"{path}:{digest}"


class ChartCacheService:
    """In-memory Moka TTL cache partitioned by /charts/* router domain."""

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        max_capacity: int | None = None,
        ttls: dict[ChartBucket, float] | None = None,
        tti: float | None = None,
    ) -> None:
        self._enabled = (
            enabled if enabled is not None else _env_bool("CHART_CACHE_ENABLED", True)
        )
        capacity = (
            max_capacity
            if max_capacity is not None
            else _env_int("CHART_CACHE_MAX_CAPACITY", DEFAULT_MAX_CAPACITY)
        )
        eff_tti = (
            tti
            if tti is not None
            else _env_optional_float("CHART_CACHE_TTI_SECONDS", None)
        )
        resolved_ttls: dict[ChartBucket, float] = {
            "temporal": _env_optional_float(
                "CHART_CACHE_TEMPORAL_TTL_SECONDS", DEFAULT_TTLS["temporal"]
            )
            or DEFAULT_TTLS["temporal"],
            "diagnostics": _env_optional_float(
                "CHART_CACHE_DIAGNOSTICS_TTL_SECONDS", DEFAULT_TTLS["diagnostics"]
            )
            or DEFAULT_TTLS["diagnostics"],
            "models": _env_optional_float(
                "CHART_CACHE_MODELS_TTL_SECONDS", DEFAULT_TTLS["models"]
            )
            or DEFAULT_TTLS["models"],
        }
        if ttls:
            resolved_ttls.update(ttls)

        self._caches: dict[ChartBucket, Moka[str, bytes]] = {
            bucket: Moka(capacity=capacity, ttl=ttl, tti=eff_tti)
            for bucket, ttl in resolved_ttls.items()
        }

    @property
    def enabled(self) -> bool:
        return self._enabled

    def get(self, bucket: ChartBucket, key: str) -> bytes | None:
        if not self._enabled:
            return None
        return self._caches[bucket].get(key)

    def set(self, bucket: ChartBucket, key: str, payload: bytes) -> None:
        if not self._enabled:
            return
        self._caches[bucket].set(key, payload)

    def invalidate(self, bucket: ChartBucket, key: str) -> None:
        self._caches[bucket].remove(key)

    def clear(self) -> None:
        """Remove all cached entries across all chart buckets."""
        for cache in self._caches.values():
            cache.clear()

    def stats(self) -> dict[str, int]:
        """Return entry counts per chart cache bucket."""
        return {bucket: cache.count() for bucket, cache in self._caches.items()}


chart_cache = ChartCacheService()
