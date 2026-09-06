import asyncio
import logging

from rpc_router.backends.websockets import WebsocketClient
from rpc_router.protocol import DuplexRouter

router = DuplexRouter()


@router.on("ping")
def ping(ctx, payload):
    print(f"received ping {payload}")


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("rpc_router").setLevel(logging.DEBUG)
    client = WebsocketClient(router=router, target_url="ws://localhost:8765")

    @client.before_receive
    def pre_receive_hook(ctx, frame):
        print(f"receiving frame: {frame}")

    @client.before_send
    def pre_send_hook(ctx, frame):
        print(f"sending frame: {frame}")

    async with client as conn:
        print("Say hello to Server")
        reply = await conn.call("echo", "hello")
        print(f"Result from Server: {reply}")

        await conn.wait_forever()


if __name__ == "__main__":
    asyncio.run(main())
