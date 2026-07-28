import uuid

from sqlmodel import Field, SQLModel


class SiteAccessRelationship(SQLModel, table=True):
    site_id: uuid.UUID = Field(primary_key=True, foreign_key="sites.site_id")
    username: str = Field(primary_key=True, foreign_key="users.username")
