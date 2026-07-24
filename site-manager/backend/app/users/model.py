from typing import TYPE_CHECKING, Annotated

from sqlmodel import Field, Relationship, SQLModel, select

from ..links import SiteAccessRelationship

if TYPE_CHECKING:
    from ..sites import Site


class User(SQLModel, table=False):
    username: str = Field(primary_key=True)
    email: str
    full_name: str
    disabled: bool
    permissions: str


class UserInDb(User, table=True):
    hashed_password: str

    sites: list["Site"] = Relationship(link_model=SiteAccessRelationship)
