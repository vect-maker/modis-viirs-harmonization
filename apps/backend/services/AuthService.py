from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Literal

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from pwdlib import PasswordHash
from sqlmodel import Session, select

from database.session import get_session
from model.User import User

_DEFAULT_PRIVATE_KEY_PATH = "/etc/keys/auth-private.pem"
_DEFAULT_PUBLIC_KEY_PATH = "/etc/keys/auth-public.pem"

JWT_ALGORITHM = "EdDSA"
JWT_ISSUER = "firms-api"
JWT_AUDIENCE = "firms-client"


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_samesite(value: str | None) -> Literal["lax", "strict", "none"]:
    cleaned = (value or "lax").strip().lower()
    if cleaned == "strict":
        return "strict"
    if cleaned == "none":
        return "none"
    return "lax"


def _read_key_bytes(env_var: str, default_path: str) -> bytes:
    path = Path(os.getenv(env_var, default_path).strip() or default_path)
    if path.is_file():
        return path.read_bytes()
    raise RuntimeError(
        f"JWT key file not found at {path}. Run `just bootstrap-keys` and mount keys."
    )


class AuthService:
    """Handles Argon2 password hashing, Ed25519 JWT signing, and HttpOnly cookies."""

    def __init__(
        self,
        *,
        private_key: bytes | None = None,
        public_key: bytes | None = None,
        access_token_expire_minutes: int | None = None,
        cookie_name: str | None = None,
        cookie_secure: bool | None = None,
        cookie_samesite: Literal["lax", "strict", "none"] | None = None,
    ) -> None:
        self._private_key = private_key
        self._public_key = public_key
        self._password_hasher = PasswordHash.recommended()
        self.access_token_expire_minutes = (
            access_token_expire_minutes
            if access_token_expire_minutes is not None
            else int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        )
        self.cookie_name = (
            cookie_name
            if cookie_name is not None
            else os.getenv("AUTH_COOKIE_NAME", "access_token").strip() or "access_token"
        )
        self.cookie_secure = (
            cookie_secure
            if cookie_secure is not None
            else _parse_bool(os.getenv("AUTH_COOKIE_SECURE"), False)
        )
        self.cookie_samesite: Literal["lax", "strict", "none"] = (
            cookie_samesite
            if cookie_samesite is not None
            else _parse_samesite(os.getenv("AUTH_COOKIE_SAMESITE"))
        )

    def _get_private_key(self) -> bytes:
        if self._private_key is None:
            self._private_key = _read_key_bytes(
                "JWT_PRIVATE_KEY_PATH", _DEFAULT_PRIVATE_KEY_PATH
            )
        return self._private_key

    def _get_public_key(self) -> bytes:
        if self._public_key is None:
            self._public_key = _read_key_bytes(
                "JWT_PUBLIC_KEY_PATH", _DEFAULT_PUBLIC_KEY_PATH
            )
        return self._public_key

    async def hash_password(self, plain_password: str) -> str:
        return await asyncio.to_thread(self._password_hasher.hash, plain_password)

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return await asyncio.to_thread(
            self._password_hasher.verify, plain_password, hashed_password
        )

    def create_access_token(self, user: User) -> str:
        now = datetime.now(UTC)
        exp = now + timedelta(minutes=self.access_token_expire_minutes)
        payload: dict[str, Any] = {
            "sub": str(user.id),
            "role": user.role,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "typ": "access",
        }
        return jwt.encode(payload, self._get_private_key(), algorithm=JWT_ALGORITHM)

    def decode_access_token(self, token: str) -> dict[str, Any]:
        try:
            claims = jwt.decode(
                token,
                self._get_public_key(),
                algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER,
                audience=JWT_AUDIENCE,
            )
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticación expirado",
            ) from exc
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticación inválido",
            ) from exc

        if claims.get("typ") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tipo de token inválido",
            )
        return claims

    def set_auth_cookie(self, response: Response, token: str) -> None:
        response.set_cookie(
            key=self.cookie_name,
            value=token,
            httponly=True,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            path="/",
            max_age=self.access_token_expire_minutes * 60,
        )

    def clear_auth_cookie(self, response: Response) -> None:
        response.delete_cookie(
            key=self.cookie_name,
            httponly=True,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            path="/",
        )

    def get_user_by_email(self, session: Session, email: str) -> User | None:
        normalized = email.strip().lower()
        return session.exec(select(User).where(User.email == normalized)).first()

    def get_user_by_username(self, session: Session, username: str) -> User | None:
        return session.exec(
            select(User).where(User.username == username.strip())
        ).first()


auth_service = AuthService()


def get_auth_service() -> AuthService:
    return auth_service


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SessionDep = Annotated[Session, Depends(get_session)]


def get_optional_current_user(
    request: Request,
    session: SessionDep,
    service: AuthServiceDep,
) -> User | None:
    """
    Resolve the authenticated user from the HttpOnly JWT cookie.
    Returns None (guest) only when no auth cookie is present.
    Raises 401 when a cookie is present but invalid, expired, or inactive.
    """
    token = request.cookies.get(service.cookie_name)
    if token is None:
        return None
    if not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación vacío o inválido",
        )

    claims = service.decode_access_token(token)
    sub = claims.get("sub")
    if not isinstance(sub, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin identificador de usuario válido",
        )

    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuario inválido en el token",
        ) from exc

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )
    return user


OptionalUserDep = Annotated[User | None, Depends(get_optional_current_user)]


def get_current_user(user: OptionalUserDep) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida",
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
