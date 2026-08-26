import base64
import logging
import secrets
import uuid
from cryptography.fernet import Fernet
import datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Response, status
from pydantic import AnyUrl
from pyotp import TOTP
from sqlmodel import Field, Relationship, SQLModel, select, and_

from ..dependencies import get_configuration, ConfigurationDep, SessionDep
from ..users.model import UserFullPublic, UserInDb
from . import auth
from .main import get_current_active_user, get_token_scope, get_current_user, Token
from .token import get_tokens

logger = logging.getLogger(f"uvicorn.{__name__}")


def generate_encryted_secret():
    key_bytes = secrets.token_bytes(20)

    f = Fernet(get_configuration().auth.totp.key)
    return base64.b64encode(f.encrypt(key_bytes)).decode("utf-8")


class TotpConfiguration(SQLModel, table=True):
    __tablename__ = "totp_configurations"
    username: str = Field(foreign_key="users.username")
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    encrypted_secret: str = Field(default_factory=generate_encryted_secret)

    active: bool = Field(default=False)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    device_name: str = Field(default="")

    user: UserInDb = Relationship(back_populates="totp_configurations")

    @property
    def secret(self):
        f = Fernet(get_configuration().auth.totp.key)
        encrypted_secret_bytes = base64.b64decode(self.encrypted_secret)
        secret_bytes = f.decrypt(encrypted_secret_bytes)
        return base64.b32encode(secret_bytes)

    @property
    def totp(self):
        return TOTP(self.secret, name=self.username, issuer="OpenWrt Site Manager")

    def verify(self, code: str):
        return self.totp.verify(code, valid_window=1)


class TotpVerificationPayload(SQLModel, table=False):
    code: str


@auth.post("/mfa/verify")
async def verify_mfa(
    payload: TotpVerificationPayload,
    user: Annotated[UserInDb, Depends(get_current_user)],
    scope: Annotated[str, Depends(get_token_scope)],
    config: ConfigurationDep,
    session: SessionDep,
    response: Response,
) -> Token:
    assert scope == "limited:mfa"
    for config in user.active_totp_configurations:
        if config.verify(payload.code):
            return await get_tokens(user=user, session=session, response=response)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


class TotpCreationResponse(SQLModel, table=False):
    url: AnyUrl


@auth.get("/mfa/setup")
def setup_mfa(
    user: Annotated[UserInDb, Depends(get_current_user)],
    scope: Annotated[str, Depends(get_token_scope)],
    session: SessionDep,
) -> TotpCreationResponse:
    if scope not in ["limited:setup_mfa", "access"]:
        logger.warning(f"invalid scope {scope}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if user.pending_totp_configurations:
        totp_config = user.pending_totp_configurations[0]
    else:
        totp_config = TotpConfiguration(user=user)
        session.add(totp_config)
        session.commit()
    return TotpCreationResponse(url=totp_config.totp.provisioning_uri())


class TotpRegistrationPayload(TotpVerificationPayload):
    device_name: str


@auth.post("/mfa/register")
async def register_mfa(
    payload: TotpRegistrationPayload,
    user: Annotated[UserInDb, Depends(get_current_user)],
    scope: Annotated[str, Depends(get_token_scope)],
    session: SessionDep,
    response: Response,
) -> Token:
    if scope not in ["limited:setup_mfa", "access"]:
        logger.warning(f"invalid scope {scope}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    for config in user.pending_totp_configurations:
        if config.verify(payload.code):
            config.active = True
            config.device_name = payload.device_name
            session.commit()
            return await get_tokens(user=user, session=session, response=response)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@auth.post("/mfa/skip")
async def skip_mfa(
    user: Annotated[UserInDb, Depends(get_current_user)],
    scope: Annotated[str, Depends(get_token_scope)],
    session: SessionDep,
    response: Response,
) -> Token:
    if scope not in ["limited:setup_mfa"]:
        logger.warning(f"invalid scope {scope}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return await get_tokens(user=user, session=session, response=response)


@auth.delete("/mfa/{id}")
async def delete_mfa(
    id: uuid.UUID,
    user: Annotated[UserInDb, Depends(get_current_active_user)],
    session: SessionDep,
):
    config = session.get(TotpConfiguration, id)
    if config.user != user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    session.delete(config)
    session.commit()
