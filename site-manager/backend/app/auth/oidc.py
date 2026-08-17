from datetime import datetime, timezone, timedelta
import logging
import secrets
from typing import Annotated

from fastapi.security import OAuth2PasswordRequestForm
from joserfc import jwt
from joserfc.jwk import KeySet
from fastapi import Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from sqlmodel import Relationship, SQLModel, and_, select, Field as SQLField
import yaml

from authlib.integrations.starlette_client import OAuth

from pydantic import BaseModel, Field, HttpUrl

from . import auth
from .authentication import authenticate_user
from .token import RefreshTokenData, Token, get_tokens
from ..users.model import UserInDb
from ..configuration import Config, OidcProvider, OidcProviderConfig
from ..dependencies import ConfigurationDep, SessionDep, get_configuration

logger = logging.getLogger(f"uvicorn.{__name__}")


providers: dict[str, OidcProviderConfig] = {}


def load_config():
    for provider in get_configuration().auth.providers:
        if provider.wellknown_url:
            oauth.register(
                provider.slug,
                client_id=provider.client_id,
                client_secret=provider.client_secret,
                server_metadata_url=provider.wellknown_url.encoded_string(),
                client_kwargs={"scope": "openid profile email"},
            )

        else:
            oauth.register(
                provider.slug,
                client_id=provider.client_id,
                client_secret=provider.client_secret,
                authorize_url=provider.auth_url.encoded_string(),
                access_token_url=provider.token_url.encoded_string(),
                client_kwargs={"scope": "openid profile email"},
            )
        providers[provider.slug] = provider


oauth = OAuth()


class TokenExchangeRequest(BaseModel):
    code: str


@auth.get("/{provider}/login", tags=["oidc"])
async def login(
    provider: str,
    request: Request,
    config: ConfigurationDep,
    pending: str | None = None,
):
    logger.info(f"logging in to {provider}, pending login: {pending}")
    provider_config = providers.get(provider)

    if not provider_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    client = oauth.create_client(provider)

    auth_url = f"{config.frontend.url}api/auth/{provider}/authorize"

    if pending:
        request.session["link_code"] = pending

    return await client.authorize_redirect(
        request,
        auth_url,
        prompt="select_account",
    )


class AuthCode(SQLModel, table=True):
    __tablename__ = "auth_codes"

    secret: str = SQLField(primary_key=True, default_factory=secrets.token_urlsafe)
    subject: str = SQLField(foreign_key="remote_users.subject")
    expires: datetime = SQLField(
        default_factory=lambda: datetime.now() + timedelta(minutes=1),
    )
    upstream_issuer: str = SQLField(foreign_key="remote_users.provider")
    upstream_session: str = SQLField(default="")

    remote_user: "RemoteUser" = Relationship(
        back_populates="auth_codes",
        sa_relationship_kwargs={
            "primaryjoin": (
                "and_("
                "AuthCode.subject == RemoteUser.subject, "
                "AuthCode.upstream_issuer == RemoteUser.provider"
                ")"
            )
        },
    )


class RemoteUser(SQLModel, table=True):
    __tablename__ = "remote_users"

    subject: str = SQLField(primary_key=True)
    provider: str = SQLField(primary_key=True)
    link_authorized: bool = SQLField(default=False)

    linked_username: str = SQLField(foreign_key="users.username")

    linked_user: UserInDb = Relationship(back_populates="remote_users")

    auth_codes: list[AuthCode] = Relationship(
        back_populates="remote_user",
        sa_relationship_kwargs={
            "primaryjoin": (
                "and_("
                "AuthCode.subject == RemoteUser.subject, "
                "AuthCode.upstream_issuer == RemoteUser.provider"
                ")"
            )
        },
    )


@auth.get("/providers", response_model=list[OidcProvider], tags=["oidc"])
async def get_list_of_oidc_providers(
    config: ConfigurationDep,
) -> list[OidcProviderConfig]:
    return config.auth.providers


@auth.get("/{provider}/authorize", tags=["oidc"])
async def authorize(
    provider: str, request: Request, session: SessionDep, config: ConfigurationDep
):
    provider_config = providers.get(provider)

    if not provider_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    client = oauth.create_client(provider)

    token = await client.authorize_access_token(request)
    if "link_code" not in request.session:
        request.session["id_token"] = token["id_token"]

    userinfo = token["userinfo"]
    if not userinfo["email_verified"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User must have a verified email address.",
        )

    user = session.exec(
        select(UserInDb).where(UserInDb.email == token["userinfo"]["email"])
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User must already have an account.",
        )

    remote_user = session.get(RemoteUser, (userinfo["sub"], provider))
    if not remote_user:
        remote_user = RemoteUser(
            subject=userinfo["sub"], provider=provider, linked_user=user
        )

    logger.info(f"authorizing {remote_user}")
    if remote_user.link_authorized:
        link_code = request.session.pop("link_code", None)
        if link_code:
            auth_code = session.get(AuthCode, link_code)
            if auth_code:
                auth_code.remote_user.link_authorized = (
                    auth_code.remote_user.linked_user == user
                )
                session.commit()
                return RedirectResponse(
                    f"{config.frontend.url}?code={auth_code.secret}"
                )

        auth_code = AuthCode(
            remote_user=remote_user,
            upstream_session=userinfo.get("sid", ""),
            expires=datetime.now() + timedelta(minutes=1),
        )
        session.add(auth_code)
        session.commit()
        return RedirectResponse(f"{config.frontend.url}?code={auth_code.secret}")

    link_code = request.session.pop("link_code", None)
    if link_code:
        auth_code = session.get(AuthCode, link_code)
        if auth_code:
            return RedirectResponse(
                f"{config.frontend.url}link-account?pending={auth_code.secret}"
            )
    auth_code = AuthCode(
        remote_user=remote_user,
        upstream_session=userinfo.get("sid", ""),
        expires=datetime.now() + timedelta(minutes=5),
    )
    session.add(auth_code)
    session.commit()
    return RedirectResponse(
        f"{config.frontend.url}link-account?pending={auth_code.secret}"
    )


def verify_auth_code(code: str, session: SessionDep) -> AuthCode:
    auth_code = session.get(AuthCode, code)

    if not auth_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired authentication code, try again.",
        )

    if auth_code.expires < datetime.now():
        session.delete(auth_code)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired authentication code, try again.",
        )

    return auth_code


@auth.post("/token", tags=["oidc"])
async def exchange_code_for_token(
    payload: TokenExchangeRequest, response: Response, session: SessionDep
) -> Token:
    auth_code = verify_auth_code(payload.code, session)

    upstream_issuer = auth_code.upstream_issuer
    upstream_session = auth_code.upstream_session

    if auth_code.remote_user.link_authorized:
        user = auth_code.remote_user.linked_user
        session.delete(auth_code)
        session.commit()
    else:
        session.delete(auth_code)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Remote account not linked.",
        )

    return await get_tokens(user, session, response, upstream_issuer, upstream_session)


class AccountLinkRequest(TokenExchangeRequest):
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)

    linked_auth_code: str | None = Field(default=None)


@auth.post("/link-account", tags=["oidc"])
async def exchange_code_for_token_and_link_account(
    payload: AccountLinkRequest,
    response: Response,
    session: SessionDep,
) -> Token:
    if payload.username and payload.password:
        user = authenticate_user(payload.username, payload.password, session=session)

    auth_code = verify_auth_code(payload.code, session)

    upstream_issuer = auth_code.upstream_issuer
    upstream_session = auth_code.upstream_session

    auth_code.remote_user.link_authorized = user == auth_code.remote_user.linked_user

    session.delete(auth_code)
    session.commit()

    return await get_tokens(user, session, response, upstream_issuer, upstream_session)


class LogoutUrl(BaseModel):
    location: HttpUrl | None = Field(default=None)


async def handle_oidc_logout(
    provider: str, sid: str, session: SessionDep, response: Response
):
    if sid:
        refresh_tokens = session.exec(
            select(RefreshTokenData).where(
                and_(
                    RefreshTokenData.upstream_session == sid,
                    RefreshTokenData.upstream_issuer == provider,
                )
            )
        )
    else:
        refresh_tokens = session.exec(
            select(RefreshTokenData).where(
                RefreshTokenData.upstream_issuer == provider,
            )
        )

    for token in refresh_tokens:
        session.delete(token)
    session.commit()

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"


@auth.get("/{provider}/logout", tags=["oidc"])
async def frontchannel_logout(
    provider: str, request: Request, response: Response, session: SessionDep
):
    sid = request.query_params.get("sid")

    if not sid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await handle_oidc_logout(
        provider=provider, sid=sid, session=session, response=response
    )


@auth.post("/{provider}/logout", tags=["oidc"])
async def backchannel_logout(
    provider: str,
    session: SessionDep,
    response: Response,
    logout_token: str = Form(...),
):
    client = oauth.create_client(provider)

    metadata = client.load_server_metadata()

    alg_values = metadata.get("id_token_signing_alg_values_supported")

    key_set = KeySet.import_key_set(await client.fetch_jwk_set())

    logout_token_decoded = jwt.decode(logout_token, key=key_set, algorithms=alg_values)
    sid = logout_token_decoded.claims.get("sid")

    if not sid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await handle_oidc_logout(
        provider=provider, sid=sid, session=session, response=response
    )


async def handle_rp_logout(provider: str, request: Request, config: ConfigurationDep):
    client = oauth.create_client(provider)
    if "end_session_endpoint" not in client.server_metadata:
        return LogoutUrl()
    logger.info(f"logging out from {provider} as well")
    id_token = request.session.pop("id_token", None)
    redirect_uri = f"{config.frontend.url}api/auth/{provider}/logged-out"
    ret: RedirectResponse = await client.logout_redirect(
        request,
        post_logout_redirect_uri=redirect_uri,
        id_token_hint=id_token,
    )
    return LogoutUrl(location=HttpUrl(ret.headers["location"]))


@auth.get("/{provider}/logged-out", tags=["oidc"])
async def logged_out(provider: str, request: Request, config: ConfigurationDep):
    client = oauth.create_client(provider)

    state_data = await client.validate_logout_response(request)
    return RedirectResponse(f"{config.frontend.url}login")
