from fastapi import WebSocket, WebSocketDisconnect

from ...lifecycle import AbstractServer
from ...protocol import AbstractDuplexConnection, ConnectionManager, DuplexRouter


class FastAPIDuplexConnection(AbstractDuplexConnection):
    """
    Concrete transport mapping abstract string hooks directly to
    FastAPI's native WebSocket object structure.
    """

    def __init__(
        self,
        websocket: WebSocket,*,
        router: DuplexRouter,
        client_id: str | None = None,
        manager: ConnectionManager | None = None,
    ):
        super().__init__(router, client_id=client_id, manager=manager)
        self.ws = websocket

    async def _raw_send(self, payload_str: str) -> None:
        """Pushes raw text data straight through the FastAPI client pipe."""
        await self.ws.send_text(payload_str)

    async def _raw_recv(self) -> str | None:
        """Reads raw text out of FastAPI's incoming stream, catching disconnects safely."""
        try:
            return await self.ws.receive_text()
        except WebSocketDisconnect:
            return None

    async def _raw_close(self) -> None:
        """FastAPI automatically closes dropped socket tasks cleanly via context."""


class FastAPIServer(AbstractServer):
    """
    Concrete FastAPI Server Wrapper.
    Inherits the full abstract lifecycle context and handles connecting pipes cleanly.
    """

    async def _raw_start(self) -> None:
        """Agnostic server hook. FastAPI starts via its own ASGI server launcher (e.g., uvicorn)."""
        print(
            "🚀 FastAPIServer context initialized. Ready to route WebSocket pipelines."
        )

    async def _raw_stop(self) -> None:
        """Agnostic cleanup hook. Runs automatically when the server context exits."""
        print("🛑 FastAPIServer context torn down cleanly.")

    async def handle_websocket(self, websocket: WebSocket) -> None:
        """
        Public execution gateway route method.
        Accepts raw incoming websockets and couples them directly to the abstract engine.
        """
        conn = FastAPIDuplexConnection(websocket, router=self.router, manager=self.manager)

        async with conn:
            await conn.wait_forever()
