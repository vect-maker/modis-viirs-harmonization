from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from sqlmodel import Session

from services.AlertEventPublisher import AlertEventPublisher
from services.AlertEventSerializer import AlertEventSerializer
from services.SSEManager import SSEManager, sse_manager

logger = logging.getLogger("firms.sse.connection")


class SupportsDisconnect(Protocol):
    async def is_disconnected(self) -> bool: ...


def parse_last_event_id(
    header_value: str | None,
    query_value: int | None = None,
) -> int | None:
    if query_value is not None and query_value >= 0:
        return query_value
    if not header_value:
        return None
    cleaned = header_value.strip()
    if cleaned.isdigit():
        return int(cleaned)
    return None


class SSEConnectionService:
    """
    Administra el ciclo de vida de conexiones SSE:
    - Registro y limpieza de clientes en SSEManager
    - Recuperación de eventos perdidos desde PostgreSQL (Last-Event-ID)
    - Envío de directiva retry y heartbeats periódicos
    - Detección de desconexiones y prevención de duplicados en replay/live
    """

    def __init__(
        self,
        *,
        manager: SSEManager = sse_manager,
        heartbeat_seconds: float | None = None,
        retry_ms: int | None = None,
    ) -> None:
        self.manager = manager
        self.heartbeat_seconds = (
            heartbeat_seconds
            if heartbeat_seconds is not None
            else float(os.getenv("ALERT_SSE_HEARTBEAT_SECONDS", "15"))
        )
        self.retry_ms = (
            retry_ms
            if retry_ms is not None
            else int(os.getenv("ALERT_SSE_RETRY_MS", "3000"))
        )

    async def event_stream(
        self,
        *,
        request: SupportsDisconnect,
        session: Session,
        last_event_id: int | None = None,
        max_events: int | None = None,
    ) -> AsyncIterator[str]:
        client = self.manager.register()
        sent_event_ids: set[int] = set()
        emitted_count = 0

        try:
            # Directiva estándar de reconexión para EventSource
            yield f"retry: {self.retry_ms}\n\n"

            # Recuperación de eventos persistidos si el cliente envía Last-Event-ID
            if last_event_id is not None:
                publisher = AlertEventPublisher(session=session, manager=self.manager)
                missed_events = publisher.get_events_after(last_event_id)
                for ev in missed_events:
                    if ev.id is None:
                        continue
                    try:
                        payload = json.loads(ev.payloadJson)
                    except json.JSONDecodeError:
                        continue
                    sent_event_ids.add(ev.id)
                    yield AlertEventSerializer.format_sse_frame(
                        event_id=ev.id,
                        event_type=ev.eventType,
                        data=payload,
                    )
                    emitted_count += 1
                    if max_events is not None and emitted_count >= max_events:
                        return

            while True:
                if await request.is_disconnected():
                    break

                try:
                    frame = await asyncio.wait_for(
                        client.queue.get(), timeout=self.heartbeat_seconds
                    )
                    event_id = self._extract_event_id(frame)
                    if event_id is not None:
                        if event_id in sent_event_ids:
                            continue
                        sent_event_ids.add(event_id)
                    yield frame
                    emitted_count += 1
                    if max_events is not None and emitted_count >= max_events:
                        return
                except TimeoutError:
                    if await request.is_disconnected():
                        break
                    hb_id = f"hb-{uuid4().hex[:12]}"
                    hb_payload = AlertEventSerializer.build_heartbeat_payload(
                        event_id=hb_id,
                        timestamp=datetime.now(UTC),
                    )
                    yield AlertEventSerializer.format_sse_frame(
                        event_id=hb_id,
                        event_type="heartbeat",
                        data=hb_payload,
                    )
                    emitted_count += 1
                    if max_events is not None and emitted_count >= max_events:
                        return
        except asyncio.CancelledError:
            logger.debug("Stream SSE cancelado para cliente %s", client.client_id)
            raise
        except Exception as exc:
            logger.exception("Error en stream SSE para cliente %s: %s", client.client_id, exc)
        finally:
            self.manager.unregister(client.client_id)

    @staticmethod
    def _extract_event_id(frame: str) -> int | None:
        for line in frame.splitlines():
            if line.startswith("id: "):
                raw = line[4:].strip()
                if raw.isdigit():
                    return int(raw)
                return None
        return None
