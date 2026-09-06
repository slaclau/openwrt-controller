import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket

from rpc_router.backends.fastapi import FastAPIServer
from rpc_router.protocol import DuplexRouter

logging.basicConfig(level=logging.INFO)
logging.getLogger("rpc_router").setLevel(logging.DEBUG)

router = DuplexRouter()
server = FastAPIServer(router=router)


async def ping():
    count = 0
    while True:
        count += 1
        await server.manager.broadcast(method="ping", payload={"count": count})
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ping_task = asyncio.create_task(ping())
    yield
    await ping_task.cancel()


app = FastAPI(lifespan=lifespan)


@router.on_connect
async def on_connect(conn):
    print(f"server connected to {conn}")
    raise Exception


@router.on("echo")
async def handle_echo(ctx, payload: any):
    return {"result": payload}


@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """
    FastAPI Entrypoint Route.
    Accepts handshakes and passes the socket execution straight to our server class.
    """
    await websocket.accept()
    await server.handle_websocket(websocket)
