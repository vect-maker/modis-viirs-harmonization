from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from model.User import User
from schemas.auth import UserAuthenticateRequest, UserPublic, UserRegisterRequest
from services.AuthService import AuthServiceDep, CurrentUserDep, SessionDep

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva cuenta de usuario",
)
async def register(
    payload: UserRegisterRequest,
    session: SessionDep,
    auth_service: AuthServiceDep,
) -> UserPublic:
    normalized_email = payload.email.strip().lower()
    normalized_username = payload.username.strip()

    if auth_service.get_user_by_email(session, normalized_email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya está registrado",
        )
    if auth_service.get_user_by_username(session, normalized_username) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nombre de usuario ya está en uso",
        )

    hashed_password = await auth_service.hash_password(payload.password)
    user = User(
        email=normalized_email,
        username=normalized_username,
        hashed_password=hashed_password,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserPublic.model_validate(user)


@router.post(
    "/authenticate",
    response_model=UserPublic,
    summary="Autenticar usuario y establecer cookie HttpOnly con JWT",
)
async def authenticate(
    payload: UserAuthenticateRequest,
    response: Response,
    session: SessionDep,
    auth_service: AuthServiceDep,
) -> UserPublic:
    user = auth_service.get_user_by_email(session, payload.email)
    if user is None or not await auth_service.verify_password(
        payload.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de usuario está inactiva",
        )

    token = auth_service.create_access_token(user)
    auth_service.set_auth_cookie(response, token)
    return UserPublic.model_validate(user)


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Obtener el perfil del usuario autenticado",
)
async def get_me(current_user: CurrentUserDep) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión y eliminar cookie HttpOnly",
)
async def logout(
    response: Response,
    auth_service: AuthServiceDep,
) -> None:
    auth_service.clear_auth_cookie(response)
