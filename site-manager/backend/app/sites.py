import logging
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.datastructures import Address
from pydantic import computed_field
from sqlmodel import Field, Relationship, SQLModel, select

from .auth.main import get_current_active_user
from .dependencies import SessionDep
from .links import SiteAccessRelationship
from .users.model import UserInDb
from .webrtc import client_websockets, site_websockets

logger = logging.getLogger(f"uvicorn.{__name__}")


class Outage(SQLModel, table=True):
    __tablename__ = "outages"
    site_id: uuid.UUID = Field(primary_key=True, foreign_key="sites.site_id")
    outage_start: float | None = Field(primary_key=True)
    outage_end: float = Field()

    site: "Site" = Relationship(back_populates="outages")

    @computed_field
    @property
    def duration(self) -> float:
        return self.outage_end - self.outage_start


class OutageWithoutSite(SQLModel, table=False):
    site_id: uuid.UUID
    outage_start: float | None
    outage_end: float
    duration: float


class Site(SQLModel, table=True):
    __tablename__ = "sites"
    site_id: uuid.UUID = Field(primary_key=True)
    name: str = Field()
    last_heartbeat: float = Field()

    users: list[UserInDb] = Relationship(
        link_model=SiteAccessRelationship, back_populates="sites"
    )

    outages: list[Outage] = Relationship(back_populates="site")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def time_since_heartbeat(self) -> float | None:
        if not self.last_heartbeat:
            return None
        return time.time() - self.last_heartbeat

    @computed_field  # type: ignore[prop-decorator]
    @property
    def up(self) -> bool:
        t = self.time_since_heartbeat
        if t is None:
            return False
        return t < 30


class SiteWithOutages(SQLModel, table=False):
    site_id: uuid.UUID
    name: str
    last_heartbeat: float
    time_since_heartbeat: float
    up: bool
    outages: list[OutageWithoutSite]


sites = APIRouter(prefix="/sites")


@sites.websocket("/ws")
async def controller_websocket_endpoint(websocket: WebSocket, session: SessionDep):
    await websocket.accept()
    logger.info(f"ws connection from site at {websocket.client}")
    try:
        while True:
            data = await websocket.receive_json()
            site_id = data["site_id"]
            site_websockets[site_id] = websocket
            match data["type"]:
                case "answer":
                    client = Address(host=data["client"][0], port=data["client"][1])
                    await client_websockets[client].send_json(data)
                    logger.info(f"forwarded answer to {client} from {site_id}")
                case "heartbeat":
                    logger.info(f"got heartbeat from {site_id}")
                    site = session.get(Site, uuid.UUID(hex=data["site_id"]))
                    if not site:
                        site = Site(
                            site_id=uuid.UUID(hex=data["site_id"]),
                            name=data["name"],
                        )
                    if not site.up:
                        outage = Outage(
                            site_id=site.site_id,
                            outage_start=site.last_heartbeat,
                            outage_end=data["time"],
                        )
                        session.add(outage)
                        logger.info(f"New outage: {outage}")
                    site.last_heartbeat = data["time"]

                    session.merge(site)
                    session.commit()
                    logger.info(site)
                case _:
                    logger.warning(f"got unknown ws type {data["type"]}")
    except WebSocketDisconnect:
        logger.info(f"controller {websocket.client} disconnected")
        site_websockets.pop(site_id)


@sites.get("/")
def get_all_my_sites(
    session: SessionDep, user: Annotated[UserInDb, Depends(get_current_active_user)]
) -> list[SiteWithOutages]:
    return [
        site for site in session.exec(select(Site).where(Site.users.contains(user)))  # type: ignore[attr-defined]
    ]
