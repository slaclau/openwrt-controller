from typing import Annotated

from fastapi import Depends, Response

from ..dependencies import SessionDep
from ..users.model import UserInDb
from . import auth
from .main import get_current_user_and_scope, Token
from .token import get_tokens

print(auth)


@auth.post("/mfa/verify")
def verify_mfa():
    pass


@auth.post("/mfa/skip")
async def skip_mfa(
    user_and_scope: Annotated[
        tuple[str | None, UserInDb], Depends(get_current_user_and_scope)
    ],
    session: SessionDep,
    response: Response,
) -> Token:
    scope, user = user_and_scope
    assert scope == "limited:setup_mfa"
    return await get_tokens(user, session, response)
