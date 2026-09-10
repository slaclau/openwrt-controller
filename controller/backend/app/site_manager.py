import asyncio
import json
import logging
import os
import time
import uuid

import aiortc
import httpx
from fastapi import FastAPI
from rpc_router.protocol import DuplexRouter
from rpc_router.backends.websockets import WebsocketClient
from rpc_router.backends.websockets.transport import WebsocketsDuplexConnection

from .configuration import Protocol
from .dependencies import get_configuration

SITE_MANAGER_WS_URI = f"{"ws" if get_configuration().site_manager.protocol == Protocol.HTTP else "wss"}://{get_configuration().site_manager.host}:{get_configuration().site_manager.port}/api/ws"
SITE_MANAGER_ICE_SERVERS_URI = f"{get_configuration().site_manager.protocol}://{get_configuration().site_manager.host}:{get_configuration().site_manager.port}/api/ice-servers"

if not os.path.exists("SITE_ID"):
    with open("SITE_ID", "w") as f:
        f.write(str(uuid.uuid4()))


with open("SITE_ID") as f:
    SITE_ID = f.read()

logger = logging.getLogger(f"uvicorn.{__name__}")
access_logger = logging.getLogger(f"uvicorn.access.{__name__}")

ws_router = DuplexRouter()


class SiteManagerState:
    app: FastAPI = None
    connections: dict[tuple[str, int], aiortc.RTCPeerConnection] = {}


STATE = SiteManagerState()


@ws_router.on
async def initiate_webrtc(ctx, payload):
    transport = httpx.ASGITransport(app=STATE.app)
    logger.info(f"Connection request received from {payload["client"]}")
    async with httpx.AsyncClient() as client:
        response = await client.get(SITE_MANAGER_ICE_SERVERS_URI)
        servers = response.json()
    STATE.connections[payload["client"]] = aiortc.RTCPeerConnection(
        aiortc.RTCConfiguration(
            iceServers=[aiortc.RTCIceServer(**server) for server in servers]
        )
    )

    @STATE.connections[payload["client"]].on("iceconnectionstatechange")
    def on_ice_connection_state_change():
        match STATE.connections[payload["client"]].iceConnectionState:
            case "checking":
                logger.debug("Checking ICE candidates")
            case "completed":
                logger.debug("Finished checking ICE candidates")
            case other:
                logger.debug(f"ICE connection state is {other}")

    @STATE.connections[payload["client"]].on("icegatheringstatechange")
    def on_ice_gathering_state_change():
        match STATE.connections[payload["client"]].iceGatheringState:
            case "gathering":
                logger.debug("Gathering ICE candidates")
            case "complete":
                logger.debug("Finished gathering ICE candidates")
            case other:
                logger.debug(f"ICE gathering state is {other}")

    @STATE.connections[payload["client"]].on("datachannel")
    def on_data_channel(channel: aiortc.RTCDataChannel):
        logger.info("data channel opened")

        @channel.on("message")
        async def on_message(dc_message):
            dc_message = json.loads(dc_message)
            match dc_message["type"]:
                case "request":
                    async with httpx.AsyncClient(transport=transport) as client:
                        resp = await client.request(
                            method=dc_message["method"],
                            url="http://internal" + dc_message["path"],
                            json=(
                                json.loads(dc_message["body"])
                                if dc_message["body"]
                                else None
                            ),
                        )
                        access_logger.info(
                            '%s - "%s %s HTTP/%s" %d',
                            "WebRTC Data Channel",
                            dc_message["method"],
                            dc_message["path"],
                            "WebRTC",
                            resp.status_code,
                        )
                        channel.send(
                            json.dumps(
                                {
                                    "type": "response",
                                    "id": dc_message["id"],
                                    "body": resp.json(),
                                    "status": resp.status_code,
                                }
                            )
                        )
                case _:
                    logger.warning(f"unexpected data channel message {dc_message}")

    return "success"


@ws_router.on
async def webrtc_offer(ctx, payload):
    offer = aiortc.RTCSessionDescription(**payload["offer"])
    logger.info("Received WebRTC offer %s", offer)

    async def gather():
        logger.debug("Preparing WebRTC answer")
        await STATE.connections[payload["client"]].setRemoteDescription(offer)

        answer = await STATE.connections[payload["client"]].createAnswer()
        logger.info("Created WebRTC answer %s", answer)
        await STATE.connections[payload["client"]].setLocalDescription(answer)
        while STATE.connections[payload["client"]].iceGatheringState != "complete":
            logger.warning(STATE.connections[payload["client"]].iceGatheringState)
            await asyncio.sleep(0.01)

        res = {
            "client": payload["client"],
            "answer": STATE.connections[payload["client"]].localDescription.__dict__,
        }
        await ctx.send(method="webrtc_answer", payload=res)

    asyncio.create_task(gather())
    logger.info("Accepted WebRTC offer")
    return "accepted"


@ws_router.on
async def add_ice_candidate(ctx, payload):
    candidate = payload["candidate"]
    logger.info("Received WebRTC ICE Candidate %s", candidate)
    if not (candidate and len(candidate["candidate"].split(" ")) > 7):
        raise RuntimeError("Invalid ICE candidate %s", candidate)
    ip = candidate["candidate"].split(" ")[4]
    port = candidate["candidate"].split(" ")[5]
    protocol = candidate["candidate"].split(" ")[7]
    priority = candidate["candidate"].split(" ")[3]
    foundation = candidate["candidate"].split(" ")[0]
    component = candidate["candidate"].split(" ")[1]
    type = candidate["candidate"].split(" ")[7]
    rtc_candidate = aiortc.RTCIceCandidate(
        ip=ip,
        port=port,
        protocol=protocol,
        priority=priority,
        foundation=foundation,
        component=component,
        type=type,
        sdpMid=candidate["sdpMid"],
        sdpMLineIndex=candidate["sdpMLineIndex"],
    )

    await STATE.connections[payload["client"]].addIceCandidate(rtc_candidate)


@ws_router.on
async def report_ips(ctx, payload):
    local_address = ctx.ws.local_address
    match len(local_address):
        case 2:
            return {"local": {"address": local_address[0], "version": 4}}
        case 4:
            return {"local": {"address": local_address[0], "version": 6}}
        case _:
            raise RuntimeError("Unknown address format %s", local_address)


async def manage_site_manager_connection(app: FastAPI):
    STATE.app = app
    try:
        while True:
            try:
                async with WebsocketClient(
                    router=ws_router, target_url=SITE_MANAGER_WS_URI
                ) as conn:
                    assert isinstance(conn, WebsocketsDuplexConnection)
                    while True:
                        payload = {
                            "site_id": SITE_ID,
                            "name": "Test Site",
                            "time": time.time(),
                        }

                        await conn.send("heartbeat", payload)
                        logger.info("sent heartbeat %s", payload)
                        await asyncio.sleep(10)
            except Exception as e:
                logger.warning("Exception: %s", e)
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.warning("site-manager heartbeat terminated")
