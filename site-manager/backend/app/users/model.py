from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, Field
from sqlmodel import Field as SQLField, Relationship, SQLModel, select

from ..links import SiteAccessRelationship

if TYPE_CHECKING:
    from ..sites import Site
    from ..auth.main import RefreshTokenData
    from ..auth.oidc import RemoteUser, RemoteUserOut


class User(SQLModel, table=False):
    username: str = SQLField(primary_key=True)
    email: str
    full_name: str
    disabled: bool = SQLField(default=False)
    permissions: str | None = SQLField(default="")


class UserInDb(User, table=True):
    __tablename__ = "users"

    hashed_password: str

    sites: list["Site"] = Relationship(
        link_model=SiteAccessRelationship, back_populates="users"
    )

    refresh_tokens: list["RefreshTokenData"] = Relationship(back_populates="user")
    remote_users: list["RemoteUser"] = Relationship(back_populates="linked_user")


class CreateUserData(SQLModel, table=False):
    username: str
    email: str
    full_name: str
    password: str


class UserWithRemoteUsers(User):
    remote_users: list["RemoteUserOut"] = []
