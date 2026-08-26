from fastapi import APIRouter

auth = APIRouter(prefix="/auth")

from .mfa import mfa
from .oidc import oidc
from .passkeys import passkeys

auth.include_router(mfa)
auth.include_router(oidc)
auth.include_router(passkeys)
