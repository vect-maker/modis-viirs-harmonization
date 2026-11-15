from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from api.auth import router as auth_router
from api.feedback import router as feedback_router
from database.session import get_session
from model.HotspotFeedback import HotspotFeedback
from model.StarSchema import DimCountry, DimPlatform, FactHotspot
from model.User import User
from services.AuthService import AuthService, get_auth_service
from services.SSEManager import sse_manager


def _generate_ed25519_pem_pair() -> tuple[bytes, bytes]:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _seed_hotspot(session: Session) -> uuid.UUID:
    country = DimCountry(id=uuid.uuid4(), name="Nicaragua")
    platform = DimPlatform(
        id=uuid.uuid4(),
        instrument="VIIRS",
        satellite="Suomi NPP",
    )
    hotspot_id = uuid.uuid4()
    hotspot = FactHotspot(
        id=hotspot_id,
        country_id=country.id,
        platform_id=platform.id,
        latitude=12.1364,
        longitude=-86.2514,
        acq_datetime=datetime(2026, 4, 10, 18, 30, 0),
        frp=45.2,
    )
    session.add(country)
    session.add(platform)
    session.add(hotspot)
    session.commit()
    return hotspot_id


def _build_test_app() -> tuple[FastAPI, AuthService, Session, uuid.UUID]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[
            DimCountry.__table__,  # type: ignore[attr-defined]
            DimPlatform.__table__,  # type: ignore[attr-defined]
            FactHotspot.__table__,  # type: ignore[attr-defined]
            User.__table__,  # type: ignore[attr-defined]
            HotspotFeedback.__table__,  # type: ignore[attr-defined]
        ],
    )
    session = Session(engine)
    hotspot_id = _seed_hotspot(session)

    priv_pem, pub_pem = _generate_ed25519_pem_pair()
    auth_svc = AuthService(
        private_key=priv_pem,
        public_key=pub_pem,
        cookie_secure=False,
    )

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(feedback_router)

    def _override_session():
        yield session

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_auth_service] = lambda: auth_svc
    return app, auth_svc, session, hotspot_id


def _register_and_login(
    client: TestClient, email: str, username: str
) -> dict[str, Any]:
    reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "StrongPassword123!",
        },
    )
    assert reg.status_code == 201
    login = client.post(
        "/auth/authenticate",
        json={"email": email, "password": "StrongPassword123!"},
    )
    assert login.status_code == 200
    return login.json()


def _parse_sse_frame(raw: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for line in raw.strip().splitlines():
        if line.startswith("id: "):
            parsed["id"] = line[4:]
        elif line.startswith("event: "):
            parsed["event"] = line[7:]
        elif line.startswith("data: "):
            parsed["data"] = json.loads(line[6:])
    return parsed


def test_hotspot_feedback_crud_consensus_and_sse_broadcast():
    app, auth_svc, session, hotspot_id = _build_test_app()
    guest_sse = sse_manager.register(user_id=None, is_authenticated=False)
    auth_sse = sse_manager.register(user_id="listener", is_authenticated=True)

    try:
        with (
            TestClient(app) as guest,
            TestClient(app) as user_one,
            TestClient(app) as user_two,
        ):
            # Unknown hotspot returns 404
            assert guest.get(f"/hotspots/{uuid.uuid4()}/feedback").status_code == 404

            # Unauthenticated writes rejected with 401
            assert (
                guest.put(
                    f"/hotspots/{hotspot_id}/feedback",
                    json={"classification": "confirmed_wildfire"},
                ).status_code
                == 401
            )
            assert (
                guest.delete(f"/hotspots/{hotspot_id}/feedback/me").status_code == 401
            )

            # Invalid cookie rejected on GET /feedback too
            guest.cookies.set(auth_svc.cookie_name, "invalid-jwt")
            assert guest.get(f"/hotspots/{hotspot_id}/feedback").status_code == 401
            guest.cookies.clear()

            # Register and authenticate two users
            u1 = _register_and_login(user_one, "ranger1@example.com", "ranger_one")
            _register_and_login(user_two, "ranger2@example.com", "ranger_two")

            # User 1 submits feedback -> 200 + SSE broadcast
            put1 = user_one.put(
                f"/hotspots/{hotspot_id}/feedback",
                json={
                    "classification": "agricultural_burn",
                    "severity": "low",
                    "comment": "  Quema agrícola controlada  ",
                },
            )
            assert put1.status_code == 200
            body1 = put1.json()
            assert body1["classification"] == "agricultural_burn"
            assert body1["comment"] == "Quema agrícola controlada"
            assert body1["username"] == "ranger_one"
            assert "email" not in body1

            # Both guest and auth SSE clients received the live event
            guest_frame = _parse_sse_frame(guest_sse.queue.get_nowait())
            auth_frame = _parse_sse_frame(auth_sse.queue.get_nowait())
            assert guest_frame["event"] == "hotspot.feedback"
            assert guest_frame["data"]["payload"]["action"] == "upserted"
            assert guest_frame["data"]["payload"]["summary"]["total_reports"] == 1
            assert auth_frame["data"]["payload"]["hotspot_id"] == str(hotspot_id)

            # User 1 updates same hotspot (idempotent upsert, total stays 1)
            put1_update = user_one.put(
                f"/hotspots/{hotspot_id}/feedback",
                json={
                    "classification": "confirmed_wildfire",
                    "severity": "high",
                    "comment": "Se propagó al bosque",
                },
            )
            assert put1_update.status_code == 200
            assert put1_update.json()["classification"] == "confirmed_wildfire"
            guest_sse.queue.get_nowait()
            auth_sse.queue.get_nowait()

            # User 2 submits conflicting classification -> tie -> consensus is None
            put2 = user_two.put(
                f"/hotspots/{hotspot_id}/feedback",
                json={"classification": "false_positive"},
            )
            assert put2.status_code == 200
            guest_sse.queue.get_nowait()
            auth_sse.queue.get_nowait()

            # Guest reads list: total=2, consensus=None, my_feedback=None
            guest_list = guest.get(f"/hotspots/{hotspot_id}/feedback")
            assert guest_list.status_code == 200
            g_data = guest_list.json()
            assert g_data["summary"]["total_reports"] == 2
            assert g_data["summary"]["consensus"] is None
            assert g_data["my_feedback"] is None
            assert len(g_data["items"]["data"]) == 2
            assert "email" not in g_data["items"]["data"][0]

            # Authenticated user reads list: my_feedback populated
            auth_list = user_one.get(f"/hotspots/{hotspot_id}/feedback")
            assert auth_list.status_code == 200
            assert auth_list.json()["my_feedback"]["user_id"] == u1["id"]

            # Batch summary endpoint
            other_id = uuid.uuid4()
            batch_resp = guest.post(
                "/hotspots/feedback/summary",
                json={"hotspot_ids": [str(hotspot_id), str(other_id)]},
            )
            assert batch_resp.status_code == 200
            summaries = batch_resp.json()["summaries"]
            assert summaries[str(hotspot_id)]["total_reports"] == 2
            assert summaries[str(other_id)]["total_reports"] == 0

            # User 2 deletes their feedback -> consensus becomes confirmed_wildfire
            del_resp = user_two.delete(f"/hotspots/{hotspot_id}/feedback/me")
            assert del_resp.status_code == 204
            del_frame = _parse_sse_frame(guest_sse.queue.get_nowait())
            auth_sse.queue.get_nowait()
            assert del_frame["data"]["payload"]["action"] == "deleted"
            assert del_frame["data"]["payload"]["summary"]["total_reports"] == 1
            assert (
                del_frame["data"]["payload"]["summary"]["consensus"]
                == "confirmed_wildfire"
            )

            # Deleting again returns 404
            assert (
                user_two.delete(f"/hotspots/{hotspot_id}/feedback/me").status_code
                == 404
            )
    finally:
        sse_manager.unregister(guest_sse.client_id)
        sse_manager.unregister(auth_sse.client_id)
        session.close()
