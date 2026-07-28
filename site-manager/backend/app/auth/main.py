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
from ..dependencies import SessionDep
from ..users.model import User, UserInDb
from .authentication import authenticate_user
from .token import get_tokens, public_key, Token, RefreshTokenData
from .oidc import LogoutUrl, handle_rp_logout

logger = logging.getLogger(f"uvicorn.{__name__}")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
cookie_scheme = APIKeyCookie(name="refresh_token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep
) -> User:
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


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
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
    refresh_token_data = session.get(RefreshTokenData, uuid.UUID(payload.get("jti")))
    if not refresh_token_data:
        raise credentials_exception
    session.delete(refresh_token_data)
    session.commit()
    response.delete_cookie("refresh_token")

    if upstream_issuer:
        return await handle_rp_logout(upstream_issuer, request)

    return LogoutUrl()


class PermissionChecker:
    def __init__(
        self, action: str, resource_type: str, path_param_name: str | None = None
    ):
        self.action = action
        self.resource_type = resource_type
        self.path_param_name = path_param_name

    def __call__(
        self, request: Request, user: Annotated[User, Depends(get_current_active_user)]
    ):
        user_perms = user.permissions.split(" ")

        # --- SCENARIO A: Collection Endpoint (No specific path param) ---
        if not self.path_param_name:
            # Must possess a wildcard to access the full collection
            wildcard_match = f"{self.action}:{self.resource_type}:*"
            global_wildcard = f"*:{self.resource_type}:*"

            if wildcard_match in user_perms or global_wildcard in user_perms:
                return True

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You do not have global '{self.action}' access to all '{self.resource_type}' resources.",
            )

        # --- SCENARIO B: Instance Endpoint (Has path param) ---
        resource_id = request.path_params.get(self.path_param_name)
        if resource_id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Configuration error: '{self.path_param_name}' missing from route path.",
            )

        res_id_str = str(resource_id)

        exact_match = f"{self.action}:{self.resource_type}:{res_id_str}"
        action_wildcard = f"*:{self.resource_type}:{res_id_str}"
        id_wildcard = f"{self.action}:{self.resource_type}:*"
        full_wildcard = f"*:{self.resource_type}:*"

        has_permission = any(
            perm in user_perms
            for perm in (exact_match, action_wildcard, id_wildcard, full_wildcard)
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Missing '{self.action}' on '{self.resource_type}:{res_id_str}'",
            )

        return True


@auth.get("/info", tags=["auth"])
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    return current_user
