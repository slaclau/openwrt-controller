import asyncio
import logging

from rpc_router.backends.websockets import WebsocketServer
from rpc_router.protocol import DuplexRouter

router = DuplexRouter()


@router.on
async def echo(ctx, payload):
    return {"result": payload}


@router.on_connect
async def on_connect(conn):
    print(f"server connected to {conn}")
    print(conn.ws.request)
    print(conn.ws.response)


#    raise Exception


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("rpc_router").setLevel(logging.DEBUG)
    # Symmetrical context manager setup driven entirely from the ABC definitions!
    async with WebsocketServer(router=router, host="localhost", port=8765) as server:
        print(
            "Server pipeline initialization complete. Blocking main thread context gracefully..."
        )
        count = 0
        while True:
            count = count + 1
            await server.broadcast("ping", {"count": count})
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
