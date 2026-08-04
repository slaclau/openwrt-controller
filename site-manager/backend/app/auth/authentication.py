import logging

from fastapi import HTTPException, status
from pwdlib import PasswordHash

from ..dependencies import SessionDep
from ..users.model import UserInDb

logger = logging.getLogger(f"uvicorn.{__name__}")

password_hash = PasswordHash.recommended()


def authenticate_user(username, password, session: SessionDep) -> UserInDb:
    user = session.get(UserInDb, username)
    if not user:
        logger.info(f"failed login with nonexistent user {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="username or password is incorrect",
        )
    valid, new_hash = password_hash.verify_and_update(
        password=password, hash=user.hashed_password
    )
    if not valid:
        logger.info(f"failed login for user {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="username or password is incorrect",
        )
    if new_hash:
        user.hashed_password = new_hash
        session.commit()

    return user
