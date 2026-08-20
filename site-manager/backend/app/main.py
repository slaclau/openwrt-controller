from contextlib import asynccontextmanager
from datetime import datetime
import importlib.metadata
import logging
import secrets

from fastapi import FastAPI
from fastapi.responses import FileResponse
import logfire
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from .dependencies import create_db_and_tables, get_session
from .users.router import users
from .auth import auth
from .auth.token import RefreshTokenData
from .auth.oidc import load_config, AuthCode
from .sites import sites
from .webrtc import webrtc

logger = logging.getLogger(f"uvicorn.{__name__}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()
    create_db_and_tables()
    await purge_expired_items(session=next(get_session()))
    yield


app = FastAPI(root_path="/api", lifespan=lifespan, version=importlib.metadata.version("openwrt_site_manager"))

@app.get("/version")
def get_version():
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
