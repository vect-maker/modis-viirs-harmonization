from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from nats.js.errors import KeyNotFoundError

from schemas.sse import SSEEventEnvelope, SSETargetScope
from services.NatsService import SSE_BROADCAST_SUBJECT, NatsService
from services.SSEManager import SSEManager
from services.SSENotificationService import SSENotificationService


class _FakeKV:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    async def put(self, key: str, value: bytes) -> None:
        self.store[key] = value

    async def get(self, key: str) -> Any:
        if key not in self.store:
            raise KeyNotFoundError()

        @dataclass
        class _Entry:
            value: bytes

        return _Entry(value=self.store[key])

    async def delete(self, key: str) -> None:
        if key not in self.store:
            raise KeyNotFoundError()
        del self.store[key]

    async def keys(self) -> list[str]:
        return list(self.store.keys())


class _FakeNatsClient:
    def __init__(self) -> None:
        self.is_connected = True
        self.published: list[tuple[str, bytes]] = []
        self.subscriptions: dict[str, Any] = {}

    async def publish(self, subject: str, payload: bytes) -> None:
        self.published.append((subject, payload))

    async def flush(self, timeout: float = 1.0) -> None:
        return None

    async def subscribe(self, subject: str, cb: Any) -> Any:
        self.subscriptions[subject] = cb

        class _Sub:
            async def unsubscribe(self) -> None:
                return None

        return _Sub()


def test_sse_manager_delivers_to_unauthenticated_and_targeted_clients():
    manager = SSEManager()
    anon = manager.register()
    user_a = manager.register(user_id="user-a", tenant_id="tenant-1", is_authenticated=True)
    user_b = manager.register(user_id="user-b", tenant_id="tenant-2", is_authenticated=True)

    # Broadcast reaches both unauthenticated and authenticated clients
    env_all = SSEEventEnvelope(
        event_id="ev-all",
        target_scope=SSETargetScope.ALL,
        event_type="notification",
        payload={"title": "Public", "message": "Hello everyone"},
    )
    delivered_all = manager.deliver_envelope(env_all, "id: ev-all\n\n")
    assert delivered_all == 3
    assert anon.queue.qsize() == 1
    assert user_a.queue.qsize() == 1
    assert user_b.queue.qsize() == 1

    # User-targeted reaches only user-a
    env_user = SSEEventEnvelope(
        event_id="ev-user",
        target_scope=SSETargetScope.USER,
        target_id="user-a",
        event_type="notification",
        payload={"title": "Private", "message": "Only A"},
    )
    delivered_user = manager.deliver_envelope(env_user, "id: ev-user\n\n")
    assert delivered_user == 1
    assert anon.queue.qsize() == 1
    assert user_a.queue.qsize() == 2
    assert user_b.queue.qsize() == 1

    # Tenant-targeted reaches only tenant-2
    env_tenant = SSEEventEnvelope(
        event_id="ev-tenant",
        target_scope=SSETargetScope.TENANT,
        target_id="tenant-2",
        event_type="notification",
        payload={"title": "Tenant", "message": "Only T2"},
    )
    delivered_tenant = manager.deliver_envelope(env_tenant, "id: ev-tenant\n\n")
    assert delivered_tenant == 1
    assert user_b.queue.qsize() == 2


def test_nats_service_kv_presence_and_instance_routing():
    async def _run() -> None:
        kv = _FakeKV()
        fake_nc = _FakeNatsClient()

        replica_1 = NatsService(nats_url="nats://fake:4222", instance_id="api-replica-1")
        replica_1._nc = fake_nc  # type: ignore[assignment]
        replica_1._kv = kv  # type: ignore[assignment]

        manager = SSEManager()
        anon_client = manager.register()
        auth_client = manager.register(
            user_id="user-42", tenant_id="org-7", is_authenticated=True
        )

        await replica_1.register_client_presence(anon_client)
        await replica_1.register_client_presence(auth_client)

        assert f"client.{anon_client.client_id}" in kv.store
        assert f"user.user-42.{auth_client.client_id}" in kv.store
        assert f"tenant.org-7.{auth_client.client_id}" in kv.store

        # Broadcast publishes to firms.sse.broadcast
        env_all = SSEEventEnvelope(
            event_id="ev-1",
            target_scope=SSETargetScope.ALL,
            event_type="notification",
            payload={"title": "Global", "message": "For all"},
        )
        pub_all = await replica_1.publish_envelope(env_all)
        assert pub_all == 1
        assert fake_nc.published[-1][0] == SSE_BROADCAST_SUBJECT

        # User-targeted routes strictly to api-replica-1
        env_user = SSEEventEnvelope(
            event_id="ev-2",
            target_scope=SSETargetScope.USER,
            target_id="user-42",
            event_type="notification",
            payload={"title": "Direct", "message": "For user-42"},
        )
        pub_user = await replica_1.publish_envelope(env_user)
        assert pub_user == 1
        assert fake_nc.published[-1][0] == "firms.sse.instance.api-replica-1"

        # Anonymous client can also be targeted by client_id via KV
        env_anon = SSEEventEnvelope(
            event_id="ev-3",
            target_scope=SSETargetScope.USER,
            target_id=anon_client.client_id,
            event_type="notification",
            payload={"title": "Anon", "message": "For anon client"},
        )
        pub_anon = await replica_1.publish_envelope(env_anon)
        assert pub_anon == 1
        assert fake_nc.published[-1][0] == "firms.sse.instance.api-replica-1"

        # Subscription bridges incoming NATS messages to handler
        received: list[SSEEventEnvelope] = []
        await replica_1.subscribe_sse(lambda ev: received.append(ev))
        assert SSE_BROADCAST_SUBJECT in fake_nc.subscriptions
        assert "firms.sse.instance.api-replica-1" in fake_nc.subscriptions

        class _FakeMsg:
            def __init__(self, data: bytes) -> None:
                self.data = data

        await fake_nc.subscriptions["firms.sse.instance.api-replica-1"](
            _FakeMsg(json.dumps(env_user.model_dump(mode="json")).encode("utf-8"))
        )
        assert len(received) == 1
        assert received[0].event_id == "ev-2"

        # Unregister cleans up KV presence
        await replica_1.unregister_client_presence(auth_client)
        assert f"user.user-42.{auth_client.client_id}" not in kv.store
        assert await replica_1.resolve_target_instances(SSETargetScope.USER, "user-42") == set()

    asyncio.run(_run())


def test_sse_notification_service_falls_back_to_local_when_nats_disconnected():
    manager = SSEManager()
    client = manager.register()
    disconnected_nats = NatsService(nats_url="")
    notifier = SSENotificationService(manager=manager, nats=disconnected_nats)

    env, delivered = notifier.send_notification(
        title="Local fallback",
        message="Works without NATS",
    )
    assert delivered == 1
    assert client.queue.qsize() == 1
    assert env.event_type == "notification"
