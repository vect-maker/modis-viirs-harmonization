from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from sqlmodel import Session

from database.connection import engine
from services.AlertDetectionService import AlertDetectionService

logger = logging.getLogger("firms.scheduler")


class AlertSchedulerService:
    """
    Ejecución periódica desacoplada para evaluar reglas de alerta temprana con
    control de concurrencia (Lock), reintentos y prevención de ejecuciones duplicadas.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self.interval_seconds = int(os.getenv("ALERT_POLL_INTERVAL_SECONDS", "300"))
        self.max_retries = int(os.getenv("ALERT_MAX_RETRIES", "3"))
        self.enabled = os.getenv("ALERT_SCHEDULER_ENABLED", "false").lower() == "true"

    @property
    def is_running(self) -> bool:
        return self._lock.locked()

    async def run_once_with_retries(
        self, rule_ids: list[int] | None = None
    ) -> dict[str, Any]:
        if self._lock.locked():
            logger.info("Evaluación de alertas omitida: ya existe una ejecución en curso.")
            return {"status": "skipped_already_running"}

        async with self._lock:
            last_error: Exception | None = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    with Session(engine) as session:
                        service = AlertDetectionService(session)
                        return await service.evaluate_rules(rule_ids=rule_ids)
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "Intento %d/%d de evaluación de alertas falló: %s",
                        attempt,
                        self.max_retries,
                        exc,
                    )
                    if attempt < self.max_retries:
                        await asyncio.sleep(min(2.0**attempt, 10.0))

            logger.error("Evaluación de alertas agotó reintentos: %s", last_error)
            return {
                "status": "error",
                "errors": [str(last_error) if last_error else "unknown_error"],
            }

    async def _loop(self) -> None:
        while not self._stop_event.is_set():
            await self.run_once_with_retries()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=float(self.interval_seconds)
                )
            except TimeoutError:
                continue

    def start(self) -> None:
        if not self.enabled or self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "AlertSchedulerService iniciado (interval=%ss)", self.interval_seconds
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None


alert_scheduler = AlertSchedulerService()
