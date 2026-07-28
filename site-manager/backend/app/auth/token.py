from datetime import datetime, timedelta, timezone
import uuid

from fastapi import Response
import jwt
from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from ..dependencies import SessionDep
from ..users.model import User, UserInDb

REFRESH_TOKEN_EXPIRE_DAYS = 7
ACCESS_TOKEN_EXPIRE_MINUTES = 30


with open("private.pem", "rb") as f:
    private_key = f.read()

with open("public.pem", "rb") as f:
    public_key = f.read()


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


class TokenData(SQLModel, table=False):
    username: str = Field(foreign_key="userindb.username", serialization_alias="sub")
    upstream_issuer: str = Field(default="", serialization_alias="us_iss")
    upstream_session: str = Field(default="", serialization_alias="us_sid")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(tz=timezone.utc) + expires_delta
        to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, private_key, algorithm="EdDSA")
    return encoded_jwt


class RefreshTokenData(TokenData, table=True):
    __tablename__ = "refresh_tokens"

    jwt_id: uuid.UUID = Field(
        primary_key=True, default_factory=uuid.uuid4, serialization_alias="jti"
    )
    expires: datetime = Field(
        default_factory=lambda: (
            datetime.now(tz=timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        ),
        serialization_alias="exp",
    )

    user: UserInDb = Relationship(back_populates="refresh_tokens")


async def mint_tokens(
    user: User, session: SessionDep, upstream_issuer="", upstream_session=""
):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    refresh_token_data = RefreshTokenData(
        username=user.username,
        upstream_issuer=upstream_issuer,
        upstream_session=upstream_session,
    )
    session.add(refresh_token_data)

    refresh_token_dict = refresh_token_data.model_dump(by_alias=True, mode="json")
    refresh_token_dict["type"] = "refresh"
    access_token_dict = refresh_token_dict.copy()
    access_token_dict["type"] = "access"

    session.commit()

    access_token = create_access_token(
        data=access_token_dict,
        expires_delta=access_token_expires,
    )
    refresh_token = create_access_token(
        data=refresh_token_dict,
    )
    return access_token, refresh_token


async def get_tokens(
    user: User,
    session: SessionDep,
    response: Response,
    upstream_issuer: str = "",
    upstream_session: str = "",
) -> Token:
    access_token, refresh_token = await mint_tokens(
        user, session, upstream_issuer, upstream_session
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        secure=True,
        httponly=True,
        samesite="strict",
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
    )
