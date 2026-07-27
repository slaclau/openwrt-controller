from datetime import datetime, timezone, timedelta
from pprint import pprint
import secrets

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlmodel import Relationship, SQLModel, select, Field as SQLField
import yaml

from authlib.integrations.starlette_client import OAuth

from pydantic import BaseModel, Field, HttpUrl

from . import auth
from .main import get_tokens, mint_tokens, Token
from ..users.model import UserInDb
from ..dependencies import SessionDep


class OidcProviderConfig(BaseModel):
    name: str = Field()
    slug: str = Field()
    client_id: str = Field()
    client_secret: str = Field()
    auth_url: HttpUrl | None = Field(default=None)
    token_url: HttpUrl | None = Field(default=None)
    wellknown_url: HttpUrl | None = Field(default=None)
    scope: str = Field(default="")


class OidcProvider(BaseModel):
    name: str = Field()
    slug: str = Field()


class AuthConfig(BaseModel):
    providers: list[OidcProviderConfig] = Field()


class Config(BaseModel):
    auth: AuthConfig = Field()


providers: dict[str, OidcProviderConfig] = {}

with open("config.yml") as f:
    config = Config.model_validate(yaml.safe_load(f))
    print(config)


def load_config():
    for provider in config.auth.providers:
        if provider.wellknown_url:
            oauth.register(
                provider.slug,
                client_id=provider.client_id,
                client_secret=provider.client_secret,
                server_metadata_url=provider.wellknown_url.encoded_string(),
                client_kwargs={"scope": provider.scope},
            )

        else:
            oauth.register(
                provider.slug,
                client_id=provider.client_id,
                client_secret=provider.client_secret,
                authorize_url=provider.auth_url.encoded_string(),
                access_token_url=provider.token_url.encoded_string(),
                client_kwargs={"scope": provider.scope},
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
    )


class AuthCode(SQLModel, table=True):
    secret: str = SQLField(primary_key=True, default_factory=secrets.token_urlsafe)
    username: str = SQLField(foreign_key="userindb.username")
    expires: datetime = SQLField(
        default_factory=lambda: datetime.now(tz=timezone.utc) + timedelta(minutes=1)
    )

    user: UserInDb = Relationship()


@auth.get("/providers")
async def get_list_of_oidc_providers() -> list[OidcProvider]:
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

    userinfo = token["userinfo"]
    if not userinfo["email_verified"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = session.exec(
        select(UserInDb).where(UserInDb.email == token["userinfo"]["email"])
    ).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    auth_code = AuthCode(username=user.username)
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

    if auth_code.expires > datetime.now():
        session.delete(auth_code)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired authentication code, try again.",
        )

    user = auth_code.user
    session.delete(auth_code)
    session.commit()

    return await get_tokens(user, session, response)
