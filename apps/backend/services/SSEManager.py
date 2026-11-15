from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from uuid import uuid4

logger = logging.getLogger("firms.sse")


@dataclass
class SSEClient:
    """Representa una conexión SSE activa con cola acotada no bloqueante."""

    client_id: str
    queue: asyncio.Queue[str]
    loop: asyncio.AbstractEventLoop | None = field(default=None)


class SSEManager:
    """
    Administrador desacoplado de clientes SSE en memoria.
    Gestiona registro, limpieza de desconexiones y difusión no bloqueante.
    """

    def __init__(self, default_queue_size: int = 256) -> None:
        self._clients: dict[str, SSEClient] = {}
        self._lock = threading.Lock()
        self._default_queue_size = default_queue_size

    @property
    def active_connections(self) -> int:
        with self._lock:
            return len(self._clients)

    def register(self, max_queue_size: int | None = None) -> SSEClient:
        size = max_queue_size or self._default_queue_size
        try:
            loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        client = SSEClient(
            client_id=uuid4().hex,
            queue=asyncio.Queue(maxsize=size),
            loop=loop,
        )
        with self._lock:
            self._clients[client.client_id] = client
        logger.debug(
            "Cliente SSE registrado: %s (activos=%d)",
            client.client_id,
            self.active_connections,
        )
        return client

    def unregister(self, client_id: str) -> None:
        with self._lock:
            removed = self._clients.pop(client_id, None)
        if removed is not None:
            logger.debug(
                "Cliente SSE desconectado: %s (activos=%d)",
                client_id,
                self.active_connections,
            )

    @staticmethod
    def _enqueue_nonblocking(client: SSEClient, frame: str) -> None:
        if client.queue.full():
            try:
                client.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            client.queue.put_nowait(frame)
        except asyncio.QueueFull:
            logger.warning("Cola SSE llena para cliente %s; evento descartado", client.client_id)

    def broadcast(self, frame: str) -> int:
        """Difunde un frame SSE a todos los clientes sin bloquear."""
        with self._lock:
            clients = list(self._clients.values())

        try:
            running_loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        delivered = 0
        for client in clients:
            try:
                if (
                    client.loop is not None
                    and client.loop.is_running()
                    and running_loop is not client.loop
                ):
                    client.loop.call_soon_threadsafe(
                        self._enqueue_nonblocking, client, frame
                    )
                else:
                    self._enqueue_nonblocking(client, frame)
                delivered += 1
            except Exception as exc:
                logger.warning("Error difundiendo SSE a %s: %s", client.client_id, exc)
                self.unregister(client.client_id)
        return delivered

    async def abroadcast(self, frame: str) -> int:
        return self.broadcast(frame)


sse_manager = SSEManager()
