from abc import ABC, abstractmethod

from .protocol import AbstractDuplexConnection, ConnectionManager, DuplexRouter


class AbstractEndpoint(ABC):
    def __init__(self, router: DuplexRouter):
        self.router = router
        self.on_connect = router.on_connect
        self.before_receive = router.before_receive
        self.before_send = router.before_send


class AbstractServer(AbstractEndpoint):
    """
    Abstract Lifecycle Context Manager for Servers.
    Manages global registries. Subclasses only implement raw boot hooks.
    """

    def __init__(self, router: DuplexRouter):
        super().__init__(router=router)
        self.manager = ConnectionManager()

    @abstractmethod
    async def _raw_start(self) -> None:
        """Low-level server startup primitive (e.g., websockets.serve, fastapi boot)."""

    @abstractmethod
    async def _raw_stop(self) -> None:
        """Low-level server shutdown primitive (e.g., closing server listeners)."""

    async def __aenter__(self):
        """Entering the server context automatically triggers the low-level infrastructure boot."""
        await self._raw_start()
        return self.manager

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exiting the server context guarantees infrastructure teardown and client purging."""
        # 1. Cleanly disconnect all remaining active connections tracked by the server
        for client_id, conn in list(self.manager.active_connections.items()):
            if conn.is_alive:
                await conn.__aexit__(None, None, None)

        # 2. Trigger transport shutdown
        await self._raw_stop()


class AbstractClient(AbstractEndpoint):
    """
    Abstract Lifecycle Context Manager for Clients.
    Subclasses only implement raw socket creation hooks.
    """

    def __init__(self, router: DuplexRouter):
        super().__init__(router=router)
        self._conn: AbstractDuplexConnection | None = None

    @abstractmethod
    async def _create_connection(self) -> AbstractDuplexConnection:
        """Subclasses override this to open a raw network stream pipe."""

    async def __aenter__(self) -> AbstractDuplexConnection:
        self._conn = await self._create_connection()
        # Simply enter the connection's context. The connection ABC starts the background loop natively!
        return await self._conn.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            return await self._conn.__aexit__(exc_type, exc_val, exc_tb)
