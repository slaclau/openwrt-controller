from fastapi import APIRouter, Depends
from sqlmodel import select

from .model import User, UserInDb
from ..auth import PermissionChecker
from ..dependencies import SessionDep

users = APIRouter(prefix="/users")


@users.get("/")
async def get_all_users(
    session: SessionDep,
    _: bool = Depends(PermissionChecker(action="read", resource_type="user")),
) -> list[User]:
    return [user for user in session.exec(select(UserInDb))]
