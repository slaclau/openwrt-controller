import datetime
import random
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import computed_field
from sqlmodel import Field, Relationship, SQLModel
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    options_to_json_dict,
    bytes_to_base64url,
    base64url_to_bytes,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
)

from .main import get_current_active_user
from .token import Token, get_tokens
from ..users.model import UserInDb, UserFullPublic
from ..dependencies import SessionDep, ConfigurationDep

passkeys = APIRouter(prefix="/passkeys")

challenges = {}


class Passkey(SQLModel, table=True):
    __tablename__ = "passkeys"
    id: bytes = Field(primary_key=True)
    public_key: bytes = Field()
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    username: str = Field(foreign_key="users.username")

    user: UserInDb = Relationship(back_populates="passkeys")

    @computed_field
    @property
    def id_string(self) -> str:
        return bytes_to_base64url(self.id)


@passkeys.get("/register", tags=["passkeys"])
def begin_registration(
    user: Annotated[UserInDb, Depends(get_current_active_user)],
    config: ConfigurationDep,
    request: Request,
) -> dict:
    user_id = random.randbytes(64)
    options = generate_registration_options(
        rp_id=config.frontend.url,
        rp_name="OpenWrt Site Manager",
        user_display_name=user.display_name,
        user_id=user_id,
        user_name=user.full_name,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED
        ),
    )
    request.session["challenge"] = bytes_to_base64url(options.challenge)
    return options_to_json_dict(options=options)


@passkeys.post("/register", tags=["passkeys"])
def verify_registration(
    user: Annotated[UserInDb, Depends(get_current_active_user)],
    registration_response: dict,
    session: SessionDep,
    config: ConfigurationDep,
    request: Request,
) -> UserFullPublic:
    verified = verify_registration_response(
        credential=registration_response,
        expected_challenge=base64url_to_bytes(request.session.get("challenge")),
        expected_origin=str(config.frontend.url)[0:-1],
        expected_rp_id=str(config.frontend.url),
    )
    passkey = Passkey(
        id=verified.credential_id,
        username=user.username,
        public_key=verified.credential_public_key,
    )
    session.add(passkey)
    session.commit()
    return user


@passkeys.delete("/{id}", tags=["passkeys"])
def delete_passkey(
    id: str,
    user: Annotated[UserInDb, Depends(get_current_active_user)],
    session: SessionDep,
):
    id_bytes = base64url_to_bytes(id)
    passkey = session.get(Passkey, id_bytes)
    if passkey.user != user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    session.delete(passkey)
    session.commit()


@passkeys.get("/authenticate", tags=["passkeys"])
def begin_authentication(config: ConfigurationDep, request: Request) -> dict:
    options = generate_authentication_options(
        rp_id=config.frontend.url,
    )
    request.session["challenge"] = bytes_to_base64url(options.challenge)
    return options_to_json_dict(options=options)


@passkeys.post("/authenticate", tags=["passkeys"])
async def verify_authentication(
    authentication_response: dict,
    session: SessionDep,
    config: ConfigurationDep,
    request: Request,
    response: Response,
) -> Token:
    passkey_id = base64url_to_bytes(authentication_response["id"])
    passkey = session.get(Passkey, passkey_id)
    verify_authentication_response(
        credential=authentication_response,
        expected_challenge=base64url_to_bytes(request.session.get("challenge")),
        expected_origin=str(config.frontend.url)[0:-1],
        expected_rp_id=str(config.frontend.url),
        credential_public_key=passkey.public_key,
        credential_current_sign_count=0,
    )

    return await get_tokens(user=passkey.user, session=session, response=response)
