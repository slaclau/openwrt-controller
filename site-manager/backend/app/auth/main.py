import logging
from typing import TYPE_CHECKING, Annotated
import uuid

from fastapi.security import (
    APIKeyCookie,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
import jwt
from fastapi import Depends, HTTPException, Request, Response, status

from . import auth
from ..dependencies import ConfigurationDep, SessionDep
from ..users.model import User, UserInDb
from .authentication import authenticate_user
from .token import get_tokens, public_key, Token, RefreshTokenData
from .oidc import LogoutUrl, handle_rp_logout

logger = logging.getLogger(f"uvicorn.{__name__}")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
cookie_scheme = APIKeyCookie(name="refresh_token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep
) -> UserInDb:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, public_key, algorithms=["EdDSA"])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
    user = session.get(UserInDb, username)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
    current_user: Annotated[UserInDb, Depends(get_current_user)],
) -> UserInDb:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@auth.post("/login", tags=["auth"])
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
    response: Response,
) -> Token:
    user = authenticate_user(form_data.username, form_data.password, session=session)
    return await get_tokens(user, session, response)


@auth.post("/refresh", tags=["auth"])
async def refresh_token(
    session: SessionDep, response: Response, refresh_token: str = Depends(cookie_scheme)
) -> Token:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(refresh_token, public_key, algorithms=["EdDSA"])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
    user = session.get(UserInDb, username)
    if not user:
        raise credentials_exception
    refresh_token_data = session.get(
        RefreshTokenData, uuid.UUID(hex=payload.get("jti"))
    )
    if not refresh_token_data:
        raise credentials_exception
    session.delete(refresh_token_data)
    session.commit()

    return await get_tokens(user, session, response)


@auth.post("/logout", tags=["auth"])
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
    response: Response,
    request: Request,
    config: ConfigurationDep,
) -> LogoutUrl:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, public_key, algorithms=["EdDSA"])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception

    upstream_issuer = str(payload.get("us_iss"))
    if not (jti := payload.get("jti")):
        raise credentials_exception
    refresh_token_data = session.get(RefreshTokenData, uuid.UUID(jti))
    if not refresh_token_data:
        raise credentials_exception
    session.delete(refresh_token_data)
    session.commit()
    response.delete_cookie("refresh_token")

    if upstream_issuer:
        return await handle_rp_logout(upstream_issuer, request, config)

    return LogoutUrl()


@auth.get("/info", tags=["auth"])
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    return current_user
