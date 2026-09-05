import importlib.metadata
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime

import logfire
from alembic import command, config
from fastapi import FastAPI
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from .auth import auth
from .auth.oidc import AuthCode, load_config
from .auth.token import RefreshTokenData
from .dependencies import get_session
from .sites import sites
from .users.router import users
from .webrtc import webrtc

logger = logging.getLogger(f"uvicorn.{__name__}")


def run_migrations():
    alembic_cfg = config.Config()
    # Tell Alembic where to find env.py and the versions folder
    alembic_cfg.set_main_option("script_location", "alembic")

    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()
    run_migrations()
    await purge_expired_items(session=next(get_session()))
    yield


app = FastAPI(
    root_path="/api",
    lifespan=lifespan,
    version=importlib.metadata.version("openwrt_site_manager"),
)


@app.get("/version")
def get_version() -> str:
    return app.version


logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_httpx()
logfire.instrument_sqlalchemy()
logfire.instrument_fastapi(app=app)

app.frontend("/", directory="dist", fallback="index.html", check_dir=False)

app.add_middleware(SessionMiddleware, secret_key=secrets.token_bytes())

app.include_router(auth)
app.include_router(users)
app.include_router(sites)
app.include_router(webrtc)


async def purge_expired_items(session: Session):
    for table in [RefreshTokenData, AuthCode]:
        expired = session.exec(select(table).where(table.expires <= datetime.now()))  # type: ignore
        count = 0
        for row in expired:
            session.delete(row)
            count += 1
        if count:
            logger.info(f"purged {count} from {table}")

    session.commit()
