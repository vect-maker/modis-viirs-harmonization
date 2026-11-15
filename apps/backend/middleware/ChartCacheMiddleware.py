from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from services.ChartCacheService import (
    ChartCacheService,
    build_chart_cache_key,
    chart_cache,
    resolve_chart_bucket,
)


class ChartCacheMiddleware(BaseHTTPMiddleware):
    """Cache 200 OK JSON responses for GET /charts/* requests in Moka."""

    def __init__(self, app: ASGIApp, cache: ChartCacheService = chart_cache) -> None:
        super().__init__(app)
        self._cache = cache

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.method != "GET" or not self._cache.enabled:
            return await call_next(request)

        bucket = resolve_chart_bucket(request.url.path)
        if bucket is None:
            return await call_next(request)

        cache_key = build_chart_cache_key(
            request.url.path,
            request.query_params.multi_items(),
        )
        cached_payload = self._cache.get(bucket, cache_key)
        if cached_payload is not None:
            return Response(
                content=cached_payload,
                status_code=200,
                media_type="application/json",
                headers={"X-Cache": "HIT"},
            )

        response = await call_next(request)
        chunks: list[bytes] = []
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
        body = b"".join(chunks)

        headers = {
            k: v
            for k, v in response.headers.items()
            if k.lower() != "content-length"
        }
        content_type = response.media_type or response.headers.get("content-type", "")
        if response.status_code == 200 and "application/json" in content_type:
            self._cache.set(bucket, cache_key, body)
            headers["X-Cache"] = "MISS"
        else:
            headers["X-Cache"] = "BYPASS"

        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
