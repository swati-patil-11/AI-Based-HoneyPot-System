"""
WebSocket Connection Manager and Live Event Broadcaster (Phase 11).

Maintains active WebSocket connections for admin dashboard clients and
pushes live events:
- request_log: incoming requests and statuses
- score_update: suspicion score changes per IP
- trap_event: trap session start, progress, and completion
- block_event: IP blocks created, expired, or lifted
- system_metric: CPU, memory, RPS, and active trap counts
"""

import asyncio
from datetime import datetime
import json
import logging
from typing import Any

from fastapi import WebSocket
from security_database import utcnow

logger = logging.getLogger("ws_manager")


def _json_serial(obj: Any) -> str:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat() + "Z"
    raise TypeError(f"Type {type(obj)} not serializable")


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, websocket: WebSocket):
        self._loop = asyncio.get_running_loop()
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: dict):
        """Pushes an event to all connected admin clients."""
        if not self.active_connections:
            return

        payload = {
            "event": event_type,
            "data": data,
            "timestamp": utcnow().isoformat() + "Z",
        }
        message = json.dumps(payload, default=_json_serial)

        disconnected = []
        async with self._lock:
            targets = list(self.active_connections)

        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    if ws in self.active_connections:
                        self.active_connections.remove(ws)

    def broadcast_sync(self, event_type: str, data: dict):
        """Thread-safe sync helper to schedule a broadcast onto the running event loop."""
        if not self.active_connections:
            return

        loop = self._loop
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

        if loop and loop.is_running():
            try:
                running_loop = asyncio.get_running_loop()
                if running_loop is loop:
                    loop.create_task(self.broadcast(event_type, data))
                else:
                    asyncio.run_coroutine_threadsafe(self.broadcast(event_type, data), loop)
            except RuntimeError:
                asyncio.run_coroutine_threadsafe(self.broadcast(event_type, data), loop)


manager = ConnectionManager()
