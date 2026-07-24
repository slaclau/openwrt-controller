from datetime import datetime, timedelta, timezone
import logging
from typing import TYPE_CHECKING, Annotated
import uuid

from fastapi.security import (
    APIKeyCookie,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
import jwt
from pwdlib import PasswordHash
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from .dependencies import SessionDep
from .users.model import User, UserInDb

logger = logging.getLogger(f"uvicorn.{__name__}")

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

with open("private.pem", "rb") as f:
    private_key = f.read()

with open("public.pem", "rb") as f:
    public_key = f.read()


password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
cookie_scheme = APIKeyCookie(name="refresh_token")

FAKE_HASH = password_hash.hash("password")


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


class TokenData(SQLModel, table=False):
    username: str = Field(foreign_key="userindb.username")


class RefreshTokenData(TokenData, table=True):
    jti: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    expires: datetime = Field(
        default_factory=lambda: (
            datetime.now(tz=timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )
    )


auth = APIRouter(prefix="/auth")


def authenticate_user(username, password, session: SessionDep) -> User:
    user = session.get(UserInDb, username)
    if not user:
        logger.info(f"failed login with nonexistent user {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="username or password is incorrect",
        )
    valid, new_hash = password_hash.verify_and_update(
        password=password, hash=user.hashed_password
    )
    if not valid:
        logger.info(f"failed login for user {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="username or password is incorrect",
        )
    if new_hash:
        user.hashed_password = new_hash
        session.commit()

    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(tz=timezone.utc) + expires_delta
        to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, private_key, algorithm="EdDSA")
    return encoded_jwt


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


@auth.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
    response: Response,
) -> Token:
    user = authenticate_user(form_data.username, form_data.password, session=session)
    return await create_token_pair(user, session, response)


async def create_token_pair(
    user: User, session: SessionDep, response: Response
) -> Token:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    refresh_token_data = RefreshTokenData(username=user.username)
    session.add(refresh_token_data)
    session.commit()

    access_token = create_access_token(
        data={
            "sub": refresh_token_data.username,
            "type": "access",
            "jti": str(refresh_token_data.jti),
        },
        expires_delta=access_token_expires,
    )
    refresh_token = create_access_token(
        data={
            "sub": refresh_token_data.username,
            "type": "refresh",
            "jti": str(refresh_token_data.jti),
            "exp": refresh_token_data.expires,
        },
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        expires=refresh_token_data.expires.astimezone(tz=timezone.utc),
        secure=True,
        httponly=True,
        samesite="strict",
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
    )


@auth.post("/refresh")
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

    return await create_token_pair(user, session, response)


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


@auth.get("/info")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    return current_user
