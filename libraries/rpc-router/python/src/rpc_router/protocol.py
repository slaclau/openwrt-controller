import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Optional, Protocol

from .exceptions import ConnectionBrokenException

logger = logging.getLogger(__name__)


class SendReceiveHandler(Protocol):
    def __call__(self, ctx: AbstractDuplexConnection, frame: any) -> any:
        pass


class DuplexRouter:
    """Symmetrical routing registry using an intuitive event syntax."""

    def __init__(self):
        self.routes: dict[str, Callable] = {}
        self.connect_handler: Callable | None = None
        self.receive_handlers: list[SendReceiveHandler] = []
        self.send_handlers: list[SendReceiveHandler] = []

    def on(self, name_or_func: str | Callable | None = None):
        if callable(name_or_func):
            self.routes[name_or_func.__name__] = name_or_func
            return name_or_func

        def decorator(func):
            method_name = (
                name_or_func if isinstance(name_or_func, str) else func.__name__
            )
            self.routes[method_name] = func
            return func

        return decorator

    def on_connect(self, func: Callable):
        self.connect_handler = func
        return func

    def before_receive(self, func: SendReceiveHandler):
        self.receive_handlers.append(func)
        return func

    def before_send(self, func: SendReceiveHandler):
        self.send_handlers.append(func)
        return func


class ConnectionManager:
    """Manages active connection lifetimes across an application topology."""

    def __init__(self):
        self.active_connections: dict[str, AbstractDuplexConnection] = {}

    def register(self, client_id: str, connection: "AbstractDuplexConnection") -> None:
        self.active_connections[client_id] = connection
        logger.debug(f"Registered client: {client_id}")

    def unregister(self, client_id: str) -> None:
        if self.active_connections.pop(client_id, None):
            logger.debug(f"Unregistered client: {client_id}")

    def change_id(self, client_id: str, connection: "AbstractDuplexConnection") -> None:
        if connection.client_id == client_id:
            return
        if connection.client_id not in self.active_connections:
            raise RuntimeError("Unregistered connection")
        self.unregister(connection.client_id)
        connection.client_id = client_id
        self.register(client_id=client_id, connection=connection)

    def get(self, client_id: str) -> Optional["AbstractDuplexConnection"]:
        conn = self.active_connections.get(client_id)
        return conn if (conn and conn.is_alive) else None

    async def broadcast(
        self,
        method: str,
        payload: Any = None,
        exclude: list[str] | None = None,
    ):
        if exclude is None:
            exclude = []
        logger.debug(f"Broadcasting {method}: {payload}")
        count = 0
        for client_id in self.active_connections:
            if client_id in exclude:
                continue
            count += 1
            await self.send_to(client_id=client_id, method=method, payload=payload)
        logger.debug(f"Broadcasted {method}: {payload} to {count} clients")
        return count

    async def send_to(self, client_id: str, method: str, payload: Any = None):
        logger.debug(f"Sending {method}: {payload} to {client_id}")
        conn = self.active_connections.get(client_id)
        if not conn:
            raise RuntimeError("No client with id %s", client_id)
        await conn.send(method=method, payload=payload)


class AbstractDuplexConnection(ABC):
    """
    Symmetrical Protocol Engine & Self-Driving Context Manager.
    Completely encapsulates background task loops and lifecycles.
    """

    def __init__(
        self,
        router: DuplexRouter,
        client_id: str | None = None,
        manager: ConnectionManager | None = None,
    ):
        self.router = router
        self.client_id = client_id or f"rpc-{uuid.uuid4().hex[:8]}"
        self.manager = manager
        self.pending_calls: dict[str, asyncio.Future] = {}
        self.is_alive = True
        self._listener_task: asyncio.Task | None = None

    @abstractmethod
    async def _raw_send(self, payload_str: str) -> None:
        pass

    @abstractmethod
    async def _raw_recv(self) -> str | None:
        pass

    @abstractmethod
    async def _raw_close(self) -> None:
        pass

    async def send(self, method: str, payload: Any = None) -> None:
        if not self.is_alive:
            raise ConnectionBrokenException
        frame = {"id": None, "type": "signal", "method": method, "payload": payload}
        await self._dispatch_frame(frame)

    async def _dispatch_frame(self, frame):
        logger.debug("Sending %s", frame)
        for handler in self.router.send_handlers:
            handler(self, frame=frame)
        await self._raw_send(json.dumps(frame))

    async def call(self, method: str, payload: Any = None, timeout: float = 5.0) -> Any:
        if not self.is_alive:
            raise ConnectionBrokenException
        call_id = f"rpc-{uuid.uuid4()}"
        future = asyncio.get_running_loop().create_future()
        self.pending_calls[call_id] = future
        frame = {"id": call_id, "type": "request", "method": method, "payload": payload}
        await self._dispatch_frame(frame)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.pending_calls.pop(call_id, None)
            raise TimeoutError(f"Call to '{method}' timed out")

    async def wait_forever(self) -> None:
        """
        Abstract helper method to passively anchor any server-side or client-side context.
        Blocks execution natively until the underlying network stream finishes or drops.
        """
        if self._listener_task:
            try:
                await self._listener_task
            except (asyncio.CancelledError, Exception):
                pass

    async def __aenter__(self):
        self.is_alive = True
        if self.router.connect_handler:
            try:
                res = await self.router.connect_handler(self)
                logger.debug(f"Connect handler returned {res}")
            except Exception as e:
                logger.error(f"Exception {e} occured during connection")
                self.is_alive = False
                await self._raw_close()
        if self.is_alive:
            if self.manager:
                self.manager.register(self.client_id, self)
            self._listener_task = asyncio.create_task(self._listen_loop())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.is_alive = False
        if self.manager:
            self.manager.unregister(self.client_id)

        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except (asyncio.CancelledError, Exception):
                pass

        for fut in list(self.pending_calls.values()):
            if not fut.done():
                fut.cancel()
        self.pending_calls.clear()
        await self._raw_close()

    async def _listen_loop(self) -> None:
        try:
            while self.is_alive:
                message = await self._raw_recv()
                if message is None:
                    logger.debug("Connection terminated")
                    break
                if self.is_alive:
                    asyncio.create_task(self._handle_frame(message))
        finally:
            self.is_alive = False

    async def _handle_frame(self, raw_message: str) -> None:
        try:
            frame = json.loads(raw_message)
            logger.debug("Handling %s", frame)
            for handler in self.router.receive_handlers:
                handler(self, frame=frame)
            t, fid, m, p = (
                frame.get("type"),
                frame.get("id"),
                frame.get("method"),
                frame.get("payload"),
            )
            if t == "response" and fid in self.pending_calls:
                future = self.pending_calls.pop(fid, None)
                if future and not future.done():
                    (
                        future.set_exception(RuntimeError(frame["error"]))
                        if frame.get("error")
                        else future.set_result(p)
                    )
            elif t in ("request", "signal") and (handler := self.router.routes.get(m)):
                if t == "signal":
                    await handler(self, p)
                elif t == "request" and fid:
                    try:
                        res = await handler(self, p)
                        frame = {
                            "id": fid,
                            "type": "response",
                            "method": m,
                            "payload": res,
                        }
                        await self._dispatch_frame(frame)
                    except Exception as e:
                        frame = {
                            "id": fid,
                            "type": "response",
                            "method": m,
                            "payload": None,
                            "error": str(e),
                        }
                        await self._dispatch_frame(frame)
        except Exception:
            pass
