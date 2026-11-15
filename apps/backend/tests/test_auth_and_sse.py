from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from api.alerts import router as alerts_router
from api.auth import router as auth_router
from database.session import get_session
from model.User import User
from schemas.sse import SSETargetScope
from services.AuthService import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    AuthService,
    get_auth_service,
)
from services.SSEManager import sse_manager
from services.SSENotificationService import sse_notifier


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


def _build_test_app() -> tuple[FastAPI, AuthService, Session, bytes]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine, tables=[User.__table__])  # type: ignore[attr-defined]
    session = Session(engine)

    priv_pem, pub_pem = _generate_ed25519_pem_pair()
    auth_svc = AuthService(
        private_key=priv_pem,
        public_key=pub_pem,
        cookie_secure=False,
    )

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(alerts_router)

    def _override_session():
        yield session

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_auth_service] = lambda: auth_svc
    return app, auth_svc, session, priv_pem


def test_register_authenticate_me_and_logout_flow():
    app, auth_svc, session, _ = _build_test_app()
    try:
        with TestClient(app) as client:
            # Unauthenticated /me is rejected
            assert client.get("/auth/me").status_code == 401

            # Register new user
            reg_resp = client.post(
                "/auth/register",
                json={
                    "email": "Analyst@Example.com",
                    "username": "analyst_one",
                    "password": "StrongPassword123!",
                },
            )
            assert reg_resp.status_code == 201
            reg_data = reg_resp.json()
            assert reg_data["email"] == "analyst@example.com"
            assert reg_data["username"] == "analyst_one"
            assert "hashed_password" not in reg_data
            assert auth_svc.cookie_name not in reg_resp.cookies

            # Duplicate email / username rejected with 409
            dup_email = client.post(
                "/auth/register",
                json={
                    "email": "analyst@example.com",
                    "username": "another_user",
                    "password": "StrongPassword123!",
                },
            )
            assert dup_email.status_code == 409

            dup_user = client.post(
                "/auth/register",
                json={
                    "email": "other@example.com",
                    "username": "analyst_one",
                    "password": "StrongPassword123!",
                },
            )
            assert dup_user.status_code == 409

            # Wrong password rejected
            bad_login = client.post(
                "/auth/authenticate",
                json={
                    "email": "analyst@example.com",
                    "password": "WrongPassword",
                },
            )
            assert bad_login.status_code == 401

            # Valid authentication sets HttpOnly cookie
            login_resp = client.post(
                "/auth/authenticate",
                json={
                    "email": "analyst@example.com",
                    "password": "StrongPassword123!",
                },
            )
            assert login_resp.status_code == 200
            set_cookie = login_resp.headers.get("set-cookie", "")
            assert "HttpOnly" in set_cookie
            assert auth_svc.cookie_name in client.cookies

            # /auth/me succeeds with HttpOnly cookie
            me_resp = client.get("/auth/me")
            assert me_resp.status_code == 200
            assert me_resp.json()["id"] == reg_data["id"]

            # Logout clears cookie and /auth/me fails again
            logout_resp = client.post("/auth/logout")
            assert logout_resp.status_code == 204
            assert client.get("/auth/me").status_code == 401
    finally:
        session.close()


def test_expired_or_invalid_cookie_rejected_on_me_and_sse():
    app, auth_svc, session, priv_pem = _build_test_app()
    try:
        with TestClient(app) as client:
            # Tampered token
            client.cookies.set(auth_svc.cookie_name, "not-a-valid-jwt")
            assert client.get("/auth/me").status_code == 401
            assert client.get("/alerts/stream").status_code == 401

            # Expired token
            expired_payload: dict[str, Any] = {
                "sub": str(uuid.uuid4()),
                "role": "user",
                "iss": JWT_ISSUER,
                "aud": JWT_AUDIENCE,
                "iat": int((datetime.now(UTC) - timedelta(hours=2)).timestamp()),
                "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
                "typ": "access",
            }
            expired_token = jwt.encode(
                expired_payload, priv_pem, algorithm=JWT_ALGORITHM
            )
            client.cookies.set(auth_svc.cookie_name, expired_token)
            assert client.get("/auth/me").status_code == 401
            assert client.get("/alerts/stream").status_code == 401
    finally:
        session.close()


def _parse_sse_events(raw_lines: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in raw_lines:
        if not line:
            if "data" in current:
                events.append(current)
            current = {}
            continue
        if line.startswith("id: "):
            current["id"] = line[4:]
        elif line.startswith("event: "):
            current["event"] = line[7:]
        elif line.startswith("data: "):
            current["data"] = json.loads(line[6:])
    if "data" in current:
        events.append(current)
    return events


def test_sse_delivers_to_authenticated_and_guest_clients():
    app, auth_svc, session, _ = _build_test_app()
    try:
        with TestClient(app) as guest_client, TestClient(app) as auth_client:
            # Register and authenticate user on auth_client
            reg = auth_client.post(
                "/auth/register",
                json={
                    "email": "sse@example.com",
                    "username": "sse_user",
                    "password": "StrongPassword123!",
                },
            )
            assert reg.status_code == 201
            user_id = reg.json()["id"]

            login = auth_client.post(
                "/auth/authenticate",
                json={
                    "email": "sse@example.com",
                    "password": "StrongPassword123!",
                },
            )
            assert login.status_code == 200

            # Verify SSEManager routing for both authenticated and guest clients
            guest_sse = sse_manager.register(user_id=None, is_authenticated=False)
            user_sse = sse_manager.register(user_id=user_id, is_authenticated=True)
            other_sse = sse_manager.register(
                user_id=str(uuid.uuid4()), is_authenticated=True
            )
            try:
                # User-targeted notification -> only user_sse receives it
                _, delivered_user = sse_notifier.send_notification(
                    title="Private Alert",
                    message="Solo para ti",
                    target_scope=SSETargetScope.USER,
                    target_id=user_id,
                )
                assert delivered_user == 1
                assert guest_sse.queue.empty()
                assert other_sse.queue.empty()
                assert not user_sse.queue.empty()

                # Broadcast notification -> all 3 receive it
                _, delivered_all = sse_notifier.send_notification(
                    title="Global Alert",
                    message="Para todos",
                    target_scope=SSETargetScope.ALL,
                )
                assert delivered_all == 3
                assert not guest_sse.queue.empty()
                assert not other_sse.queue.empty()
            finally:
                sse_manager.unregister(guest_sse.client_id)
                sse_manager.unregister(user_sse.client_id)
                sse_manager.unregister(other_sse.client_id)

            # Verify HTTP /alerts/stream works for both guest (no cookie) and auth user
            guest_lines: list[str] = []
            with guest_client.stream("GET", "/alerts/stream?max_events=1") as resp:
                assert resp.status_code == 200
                # Emit broadcast while connected or check stream opens cleanly
                sse_notifier.send_notification(
                    title="Guest Broadcast",
                    message="Mensaje público",
                    target_scope=SSETargetScope.ALL,
                )
                for line in resp.iter_lines():
                    guest_lines.append(line)

            guest_events = _parse_sse_events(guest_lines)
            assert len(guest_events) == 1
            assert guest_events[0]["data"]["payload"]["title"] == "Guest Broadcast"

            auth_lines: list[str] = []
            with auth_client.stream("GET", "/alerts/stream?max_events=1") as resp:
                assert resp.status_code == 200
                sse_notifier.send_notification(
                    title="User Direct",
                    message="Mensaje privado",
                    target_scope=SSETargetScope.USER,
                    target_id=user_id,
                )
                for line in resp.iter_lines():
                    auth_lines.append(line)

            auth_events = _parse_sse_events(auth_lines)
            assert len(auth_events) == 1
            assert auth_events[0]["data"]["payload"]["title"] == "User Direct"
    finally:
        session.close()
