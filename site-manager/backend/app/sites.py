import logging
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket
from fastapi.datastructures import Address
from pydantic import computed_field
from rpc_router.protocol import DuplexRouter
from rpc_router.backends.fastapi import FastAPIServer
from rpc_router.backends.fastapi.transport import FastAPIDuplexConnection
from sqlmodel import Field, Relationship, SQLModel, select

from .auth.main import get_current_active_user
from .dependencies import SessionDep, get_session
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


sites = APIRouter()

ws_router = DuplexRouter()
server = FastAPIServer(router=ws_router)


@ws_router.on("heartbeat")
def handle_heartbeat(ctx: FastAPIDuplexConnection, data):
    session = next(get_session())
    logger.info("Received heartbeat %s from site %s", data, data.get("site_id"))
    site = session.get(Site, uuid.UUID(hex=data["site_id"]))

    if not site:
        site = Site(
            site_id=uuid.UUID(hex=data["site_id"]), name=data["name"], last_heartbeat=0
        )
        session.add(site)
        logger.info("New site %s", site)
    if site.site_id not in server.manager.active_connections:
        server.manager.change_id(connection=ctx, client_id=f"site:{site.site_id}")
        logger.debug("Updated connection id to site id")
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


@ws_router.on
async def initiate_webrtc(ctx: FastAPIDuplexConnection, payload):
    logger.info(
        "initiate webrtc tunnel between %s and %s",
        ctx.client_id,
        payload.get("site_id"),
    )
    return await server.manager.call(
        client_id=f"site:{payload.get("site_id")}",
        method="initiate_webrtc",
        payload={"client": ctx.client_id},
    )


@ws_router.on
async def webrtc_offer(ctx: FastAPIDuplexConnection, payload):
    logger.info(
        "forward webrtc offer %s to site %s", payload["offer"], payload["site_id"]
    )
    res = await server.manager.call(
        client_id=f"site:{payload.get("site_id")}",
        method="webrtc_offer",
        payload={"client": ctx.client_id, "offer": payload["offer"]},
    )
    logger.info("got %s", res)
    return res


@ws_router.on
async def webrtc_answer(ctx: FastAPIDuplexConnection, payload):
    logger.info(
        "forward webrtc answer %s to client %s", payload["answer"], payload["client"]
    )
    res = await server.manager.call(
        client_id=payload["client"],
        method="webrtc_answer",
        payload={"answer": payload["answer"]},
    )
    logger.info("got %s", res)
    return res


@ws_router.on
async def add_ice_candidate(ctx: FastAPIDuplexConnection, payload):
    logger.info(
        "forward ice candidate %s to site %s", payload["candidate"], payload["site_id"]
    )
    await server.manager.send_to(
        client_id=f"site:{payload.get("site_id")}",
        method="add_ice_candidate",
        payload={"client": ctx.client_id, "candidate": payload["candidate"]},
    )


@ws_router.on
async def report_ips(ctx, payload):
    return await server.manager.call(
        client_id=f"site:{payload.get("site_id")}",
        method="report_ips",
    )


@sites.websocket("/ws")
async def controller_websocket_endpoint(websocket: WebSocket, session: SessionDep):
    await websocket.accept()
    await server.handle_websocket(websocket=websocket)


@sites.get("/sites")
def get_all_my_sites(
    session: SessionDep, user: Annotated[UserInDb, Depends(get_current_active_user)]
) -> list[SiteWithOutages]:
    return [
        site for site in session.exec(select(Site).where(Site.users.contains(user)))  # type: ignore[attr-defined]
    ]
