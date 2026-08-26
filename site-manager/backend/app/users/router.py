from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from .model import UpdateUserData, User, UserInDb, CreateUserData, UserWithRemoteUsers
from ..auth.main import get_current_active_user
from ..auth.authentication import password_hash
from ..auth.permissions import PermissionChecker
from ..dependencies import SessionDep

users = APIRouter(prefix="/users")


@users.get("/")
async def get_all_users(
    session: SessionDep,
    _: bool = Depends(PermissionChecker(action="read", resource_type="user")),
) -> list[User]:
    return [user for user in session.exec(select(UserInDb))]


@users.post("/register")
async def register_user(user: CreateUserData, session: SessionDep):
    user_in_db = UserInDb(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=password_hash.hash(user.password),
    )
    session.add(user_in_db)
    session.commit()


@users.post("/me")
async def update(
    user_update: UpdateUserData,
    user: Annotated[UserInDb, Depends(get_current_active_user)],
    session: SessionDep,
) -> UserWithRemoteUsers:
    if user_update.username != user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        # check_user = session.get(UserInDb, user_update.username)
        # if check_user:
        #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        # for k, v in user_update.model_dump().items():
        #     setattr(user, k, v)
        # session.commit()
        # return user
    else:
        for k, v in user_update.model_dump().items():
            setattr(user, k, v)
        session.commit()
        return user
