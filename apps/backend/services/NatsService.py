from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import nats
from nats.aio.client import Client as NatsClient
from nats.aio.msg import Msg
from nats.aio.subscription import Subscription
from nats.js.api import KeyValueConfig
from nats.js.errors import BucketNotFoundError, KeyNotFoundError, NoKeysError
from nats.js.kv import KeyValue
from shared_core.sse import SSE_BROADCAST_SUBJECT

from schemas.sse import SSEEventEnvelope, SSETargetScope
from services.SSEManager import SSEClient

logger = logging.getLogger("firms.nats")

SSE_INSTANCE_SUBJECT_PREFIX = "firms.sse.instance"
SSE_PRESENCE_BUCKET = "sse_presence"


def _default_instance_id() -> str:
    env_id = os.getenv("INSTANCE_ID", "").strip()
    if env_id:
        return env_id
    return f"{socket.gethostname()}-{uuid4().hex[:8]}"


class NatsService:
    """
    Cliente NATS + JetStream KV para coordinar múltiples réplicas de FastAPI:
    - Registra qué réplica mantiene cada stream SSE activo en el bucket KV `sse_presence`.
    - Publica envelopes globales (`firms.sse.broadcast`) para usuarios autenticados y no autenticados.
    - Enruta envelopes dirigidos (`user`/`tenant`) solo a las réplicas que poseen la conexión.
    """

    def __init__(
        self,
        *,
        nats_url: str | None = None,
        instance_id: str | None = None,
        presence_ttl_seconds: float | None = None,
    ) -> None:
        self._nats_url = nats_url
        self.instance_id = instance_id or _default_instance_id()
        self.presence_ttl_seconds = (
            presence_ttl_seconds
            if presence_ttl_seconds is not None
            else float(os.getenv("SSE_PRESENCE_TTL_SECONDS", "45"))
        )
        self._nc: NatsClient | None = None
        self._kv: KeyValue | None = None
        self._subs: list[Subscription] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def nats_url(self) -> str:
        if self._nats_url is not None:
            return self._nats_url.strip()
        return os.getenv("NATS_URL", "").strip()

    @property
    def is_connected(self) -> bool:
        return self._nc is not None and self._nc.is_connected

    @property
    def instance_subject(self) -> str:
        return f"{SSE_INSTANCE_SUBJECT_PREFIX}.{self.instance_id}"

    async def connect(self) -> bool:
        url = self.nats_url
        if not url:
            logger.info("NATS_URL no configurado; SSE operará en modo local en memoria.")
            return False

        if self.is_connected:
            return True

        self._loop = asyncio.get_running_loop()
        self._nc = await nats.connect(servers=[url], name=f"firms-api-{self.instance_id}")
        js = self._nc.jetstream()
        try:
            self._kv = await js.key_value(SSE_PRESENCE_BUCKET)
        except BucketNotFoundError:
            self._kv = await js.create_key_value(
                config=KeyValueConfig(
                    bucket=SSE_PRESENCE_BUCKET,
                    ttl=self.presence_ttl_seconds,
                )
            )
        logger.info(
            "Conectado a NATS (%s) como instancia %s", url, self.instance_id
        )
        return True

    async def close(self) -> None:
        for sub in self._subs:
            try:
                await sub.unsubscribe()
            except Exception:
                pass
        self._subs.clear()

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
        self._loop = None

    def _presence_keys_for_client(self, client: SSEClient) -> list[tuple[str, bytes]]:
        payload = json.dumps(
            {
                "instance_id": self.instance_id,
                "client_id": client.client_id,
                "user_id": client.user_id,
                "tenant_id": client.tenant_id,
                "authenticated": client.is_authenticated,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            separators=(",", ":"),
        ).encode("utf-8")

        entries: list[tuple[str, bytes]] = [(f"client.{client.client_id}", payload)]
        instance_bytes = self.instance_id.encode("utf-8")
        if client.user_id:
            entries.append((f"user.{client.user_id}.{client.client_id}", instance_bytes))
        if client.tenant_id:
            entries.append((f"tenant.{client.tenant_id}.{client.client_id}", instance_bytes))
        return entries

    async def register_client_presence(self, client: SSEClient) -> None:
        if self._kv is None:
            return
        for key, value in self._presence_keys_for_client(client):
            try:
                await self._kv.put(key, value)
            except Exception as exc:
                logger.warning("No se pudo registrar presencia KV (%s): %s", key, exc)

    async def refresh_client_presence(self, client: SSEClient) -> None:
        await self.register_client_presence(client)

    async def unregister_client_presence(self, client: SSEClient) -> None:
        if self._kv is None:
            return
        for key, _ in self._presence_keys_for_client(client):
            try:
                await self._kv.delete(key)
            except KeyNotFoundError:
                pass
            except Exception as exc:
                logger.warning("No se pudo eliminar presencia KV (%s): %s", key, exc)

    async def resolve_target_instances(
        self,
        target_scope: SSETargetScope,
        target_id: str | None,
    ) -> set[str]:
        if self._kv is None or not target_id:
            return set()

        instances: set[str] = set()
        if target_scope == SSETargetScope.USER:
            prefix = f"user.{target_id}."
            try:
                keys = await self._kv.keys()
            except NoKeysError:
                keys = []

            for key in keys:
                if key.startswith(prefix):
                    entry = await self._kv.get(key)
                    if entry.value:
                        instances.add(entry.value.decode("utf-8"))

            if not instances:
                try:
                    anon_entry = await self._kv.get(f"client.{target_id}")
                    if anon_entry.value:
                        meta = json.loads(anon_entry.value.decode("utf-8"))
                        iid = meta.get("instance_id")
                        if isinstance(iid, str) and iid:
                            instances.add(iid)
                except KeyNotFoundError:
                    pass
            return instances

        if target_scope == SSETargetScope.TENANT:
            prefix = f"tenant.{target_id}."
            try:
                keys = await self._kv.keys()
            except NoKeysError:
                keys = []
            for key in keys:
                if key.startswith(prefix):
                    entry = await self._kv.get(key)
                    if entry.value:
                        instances.add(entry.value.decode("utf-8"))
            return instances

        return set()

    async def publish_envelope(self, envelope: SSEEventEnvelope) -> int:
        if not self.is_connected or self._nc is None:
            return 0

        raw_bytes = envelope.model_dump_json().encode("utf-8")

        if envelope.target_scope == SSETargetScope.ALL:
            await self._nc.publish(SSE_BROADCAST_SUBJECT, raw_bytes)
            await self._nc.flush(timeout=1.0)
            return 1

        target_instances = await self.resolve_target_instances(
            envelope.target_scope,
            envelope.target_id,
        )
        for iid in target_instances:
            await self._nc.publish(f"{SSE_INSTANCE_SUBJECT_PREFIX}.{iid}", raw_bytes)
        if target_instances:
            await self._nc.flush(timeout=1.0)
        return len(target_instances)

    def publish_envelope_sync(self, envelope: SSEEventEnvelope) -> bool:
        """
        Publica un envelope hacia NATS desde contextos síncronos o asíncronos.
        Retorna True si se despachó (o programó) vía NATS.
        """
        if not self.is_connected or self._loop is None or not self._loop.is_running():
            return False

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is self._loop:
            self._loop.create_task(self.publish_envelope(envelope))
            return True

        asyncio.run_coroutine_threadsafe(self.publish_envelope(envelope), self._loop)
        return True

    async def subscribe_sse(
        self,
        handler: Callable[[SSEEventEnvelope], Awaitable[Any] | Any],
    ) -> None:
        if not self.is_connected or self._nc is None:
            return

        async def _on_message(msg: Msg) -> None:
            try:
                envelope = SSEEventEnvelope.model_validate_json(msg.data.decode("utf-8"))
                result = handler(envelope)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.warning("Error procesando mensaje NATS SSE: %s", exc)

        sub_broadcast = await self._nc.subscribe(SSE_BROADCAST_SUBJECT, cb=_on_message)
        sub_instance = await self._nc.subscribe(self.instance_subject, cb=_on_message)
        self._subs.extend([sub_broadcast, sub_instance])


nats_service = NatsService()
