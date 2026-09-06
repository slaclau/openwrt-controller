import logging

import websockets
from websockets.protocol import State

from ...exceptions import ConnectionBrokenException, ConnectionRefusedException
from ...lifecycle import AbstractClient, AbstractServer
from ...protocol import AbstractDuplexConnection, ConnectionManager, DuplexRouter

logger = logging.getLogger(__name__)


class WebsocketsDuplexConnection(AbstractDuplexConnection):
    """Framework specific pipe translation layer handling raw string frames."""

    def __init__(
        self,
        websocket,
        router: DuplexRouter,
        client_id: str | None = None,
        manager: ConnectionManager | None = None,
    ):
        super().__init__(router, client_id=client_id, manager=manager)
        self.ws = websocket

    async def _raw_send(self, payload_str: str) -> None:
        try:
            await self.ws.send(payload_str)
        except websockets.exceptions.ConnectionClosed as e:
            raise ConnectionBrokenException from e

    async def _raw_recv(self) -> str | None:
        try:
            return await self.ws.recv()
        except websockets.exceptions.ConnectionClosed:
            return None

    async def _raw_close(self) -> None:
        await self.ws.close()


class WebsocketServer(AbstractServer):
    """Concrete WebSocket Server mapping lifecycle hooks directly to the websockets library."""

    def __init__(self, router: DuplexRouter, host: str, port: int):
        super().__init__(router)
        self.host = host
        self.port = port
        self._server = None

    async def _raw_start(self) -> None:
        """Concrete implementation bootstrapping the websockets loop server handle."""

        async def handler(websocket):
            # Context entry handles manager tracking and listener loop tasks automatically
            async with WebsocketsDuplexConnection(
                websocket, self.router, manager=self.manager
            ) as conn:
                # Abstract helper blocks the function handle until the client disconnects
                await conn.wait_forever()

        self._server = await websockets.serve(handler, self.host, self.port)
        logger.info(f"WebSocket Server active on ws://{self.host}:{self.port}")

    async def _raw_stop(self) -> None:
        """Concrete implementation shutting down the web socket network listener descriptor."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("WebSocket Server shut down cleanly")


class WebsocketClient(AbstractClient):
    """Concrete WebSocket Client mapping connection handshakes directly to the websockets library."""

    def __init__(self, router: DuplexRouter, target_url: str):
        super().__init__(router)
        self.target_url = target_url

    async def _create_connection(self) -> WebsocketsDuplexConnection:
        websocket = await websockets.connect(self.target_url)
        if not websocket.state == State.OPEN:
            raise ConnectionRefusedException
        return WebsocketsDuplexConnection(websocket, self.router)
