from datetime import datetime, timezone, timedelta
import logging
import secrets

from joserfc import jwt
from joserfc.jwk import KeySet
from fastapi import Form, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from sqlmodel import Relationship, SQLModel, and_, select, Field as SQLField
import yaml

from authlib.integrations.starlette_client import OAuth

from pydantic import BaseModel, Field, HttpUrl

from . import auth
from .token import RefreshTokenData, Token, get_tokens
from ..users.model import UserInDb
from ..dependencies import SessionDep

logger = logging.getLogger(f"uvicorn.{__name__}")


class OidcProviderConfig(BaseModel):
    name: str = Field()
    slug: str = Field()
    client_id: str = Field()
    client_secret: str = Field()
    auth_url: HttpUrl | None = Field(default=None)
    token_url: HttpUrl | None = Field(default=None)
    logo_url: HttpUrl | None = Field(default=None)
    wellknown_url: HttpUrl | None = Field(default=None)
    scope: str = Field(default="")


class OidcProvider(BaseModel):
    name: str = Field()
    slug: str = Field()
    logo_url: HttpUrl | None = Field(default=None)


class AuthConfig(BaseModel):
    providers: list[OidcProviderConfig] = Field()


class Config(BaseModel):
    auth: AuthConfig = Field()


providers: dict[str, OidcProviderConfig] = {}

with open("config.yml") as f:
    config = Config.model_validate(yaml.safe_load(f))


def load_config():
    for provider in config.auth.providers:
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


@auth.get("/{provider}/login")
async def login(provider: str, request: Request):
    provider_config = providers.get(provider)

    if not provider_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    client = oauth.create_client(provider)

    return await client.authorize_redirect(
        request,
        str(request.url).replace("8001", "5174/api").replace("login", "authorize"),
        prompt="select_account",
    )


class AuthCode(SQLModel, table=True):
    __tablename__ = "auth_codes"

    secret: str = SQLField(primary_key=True, default_factory=secrets.token_urlsafe)
    username: str = SQLField(foreign_key="userindb.username")
    expires: datetime = SQLField(
        default_factory=lambda: datetime.now() + timedelta(minutes=1),
    )
    upstream_issuer: str = SQLField(default="")
    upstream_session: str = SQLField(default="")
    user: UserInDb = Relationship()


@auth.get("/providers", response_model=list[OidcProvider])
async def get_list_of_oidc_providers() -> list[OidcProviderConfig]:
    return config.auth.providers


@auth.get("/{provider}/authorize")
async def authorize(
    provider: str, request: Request, response: Response, session: SessionDep
):
    provider_config = providers.get(provider)

    if not provider_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    client = oauth.create_client(provider)

    token = await client.authorize_access_token(request)
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

    auth_code = AuthCode(
        username=user.username,
        upstream_issuer=provider,
        upstream_session=userinfo.get("sid", ""),
    )
    session.add(auth_code)
    session.commit()

    return RedirectResponse(f"http://localhost:5174?code={auth_code.secret}")


class TokenExchangeRequest(BaseModel):
    code: str


@auth.post("/token")
async def exchange_code_for_token(
    payload: TokenExchangeRequest, response: Response, session: SessionDep
) -> Token:
    auth_code = session.get(AuthCode, payload.code)

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
    user = auth_code.user
    upstream_issuer = auth_code.upstream_issuer
    upstream_session = auth_code.upstream_session
    session.delete(auth_code)
    session.commit()

    return await get_tokens(user, session, response, upstream_issuer, upstream_session)


class LogoutUrl(BaseModel):
    location: HttpUrl | None = Field(default=None)


async def handle_oidc_logout(
    provider: str, sid: str, session: SessionDep, response: Response
):
    refresh_tokens = session.exec(
        select(RefreshTokenData).where(
            and_(
                RefreshTokenData.upstream_session == sid,
                RefreshTokenData.upstream_issuer == provider,
            )
        )
    )
    for token in refresh_tokens:
        session.delete(token)
    session.commit()

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"


@auth.get("/{provider}/logout")
async def frontchannel_logout(
    provider: str, request: Request, response: Response, session: SessionDep
):
    sid = request.query_params.get("sid")

    if not sid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await handle_oidc_logout(
        provider=provider, sid=sid, session=session, response=response
    )


@auth.post("/{provider}/logout")
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


async def handle_rp_logout(provider: str, request: Request):
    client = oauth.create_client(provider)
    if "end_session_endpoint" not in client.server_metadata:
        return LogoutUrl()
    logger.info(f"logging out from {provider} as well")
    id_token = request.session.pop("id_token", None)
    redirect_uri = f"http://localhost:5174/api/auth/{provider}/logged-out"
    ret: RedirectResponse = await client.logout_redirect(
        request,
        post_logout_redirect_uri=redirect_uri,
        id_token_hint=id_token,
    )
    return LogoutUrl(location=HttpUrl(ret.headers["location"]))


@auth.get("/{provider}/logged-out")
async def logged_out(provider: str, request: Request):
    client = oauth.create_client(provider)

    state_data = await client.validate_logout_response(request)
    return RedirectResponse("http://localhost:5174/login")
