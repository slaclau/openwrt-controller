from fastapi import APIRouter, Depends
from sqlmodel import select

from .model import User, UserInDb, CreateUserData
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
