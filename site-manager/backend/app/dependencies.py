from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from .configuration import Config, OidcProviderConfig

sqlite_file_name = "site-manager.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@lru_cache
def get_configuration():
    return Config()


ConfigurationDep = Annotated[Config, Depends(get_configuration)]
