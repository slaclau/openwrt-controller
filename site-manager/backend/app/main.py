from contextlib import asynccontextmanager
import secrets

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from .dependencies import create_db_and_tables
from .auth import auth
from .auth.oidc import load_config
from .users.router import users
from .sites import sites
from .webrtc import webrtc


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=secrets.token_bytes())

app.include_router(auth)
app.include_router(users)
app.include_router(sites)
app.include_router(webrtc)
