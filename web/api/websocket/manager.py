"""
WebSocket manager for real-time usage monitoring.

This module provides WebSocket connection management and real-time data streaming.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

from ..models.schemas import WebSocketMessage
from ..services.usage_service import UsageService

logger = logging.getLogger("api.websocket")

websocket_router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and broadcasting."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict] = {}
        self.usage_service = UsageService()
        self._broadcast_task = None
        self._is_broadcasting = False

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        Accept a WebSocket connection.

        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_metadata[client_id] = {
            "connected_at": datetime.now(),
            "last_ping": datetime.now(),
            "plan": "pro",  # Default plan
        }

        logger.info(f"WebSocket client connected: {client_id}")

        # Send initial connection message
        await self.send_personal_message(
            {
                "type": "connection_established",
                "data": {
                    "client_id": client_id,
                    "server_time": datetime.now().isoformat(),
                    "update_interval": 3,
                },
            },
            client_id,
        )

        # Start broadcasting if this is the first connection
        if len(self.active_connections) == 1 and not self._is_broadcasting:
            await self.start_broadcasting()

    def disconnect(self, client_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            client_id: Client identifier to disconnect
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.connection_metadata[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")

        # Stop broadcasting if no connections remain
        if len(self.active_connections) == 0 and self._is_broadcasting:
            self.stop_broadcasting()

    async def send_personal_message(self, message: Dict, client_id: str) -> None:
        """
        Send message to specific client.

        Args:
            message: Message to send
            client_id: Target client ID
        """
        if client_id in self.active_connections:
            try:
                websocket_message = WebSocketMessage(
                    type=message["type"], data=message["data"], timestamp=datetime.now()
                )
                await self.active_connections[client_id].send_text(
                    websocket_message.model_dump_json()
                )
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: Dict) -> None:
        """
        Broadcast message to all connected clients.

        Args:
            message: Message to broadcast
        """
        if not self.active_connections:
            return

        websocket_message = WebSocketMessage(
            type=message["type"], data=message["data"], timestamp=datetime.now()
        )

        message_text = websocket_message.model_dump_json()

        # Send to all connections, removing failed ones
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"Failed to broadcast to {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def start_broadcasting(self) -> None:
        """Start the background broadcasting task."""
        if not self._is_broadcasting:
            self._is_broadcasting = True
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())
            logger.info("Started WebSocket broadcasting")

    def stop_broadcasting(self) -> None:
        """Stop the background broadcasting task."""
        if self._is_broadcasting:
            self._is_broadcasting = False
            if self._broadcast_task:
                self._broadcast_task.cancel()
            logger.info("Stopped WebSocket broadcasting")

    async def _broadcast_loop(self) -> None:
        """Background loop for broadcasting usage updates."""
        while self._is_broadcasting:
            try:
                # Get current usage data for all active plans
                plans = set(
                    meta.get("plan", "pro")
                    for meta in self.connection_metadata.values()
                )

                for plan in plans:
                    try:
                        # Get current status
                        status_data = await self.usage_service.get_current_status(plan)

                        # Broadcast to clients using this plan
                        await self.broadcast(
                            {
                                "type": "usage_update",
                                "data": {
                                    "plan": plan,
                                    "status": status_data,
                                    "timestamp": datetime.now().isoformat(),
                                },
                            }
                        )

                    except Exception as e:
                        logger.error(f"Failed to get usage data for plan {plan}: {e}")

                # Send heartbeat
                await self.broadcast(
                    {
                        "type": "heartbeat",
                        "data": {
                            "server_time": datetime.now().isoformat(),
                            "active_connections": len(self.active_connections),
                        },
                    }
                )

                # Wait for next update interval
                await asyncio.sleep(3)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    def get_connection_stats(self) -> Dict:
        """Get connection statistics."""
        return {
            "active_connections": len(self.active_connections),
            "is_broadcasting": self._is_broadcasting,
            "clients": [
                {
                    "client_id": client_id,
                    "connected_at": meta["connected_at"].isoformat(),
                    "plan": meta.get("plan", "pro"),
                }
                for client_id, meta in self.connection_metadata.items()
            ],
        }

    async def handle_reconnection(self, websocket: WebSocket, client_id: str) -> None:
        """
        Handle client reconnection with existing ID.

        Args:
            websocket: New WebSocket connection
            client_id: Existing client identifier
        """
        # Close old connection if it exists
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].close()
            except:
                pass  # Connection might already be closed

        # Update with new connection
        self.active_connections[client_id] = websocket

        # Update metadata but preserve some history
        if client_id in self.connection_metadata:
            self.connection_metadata[client_id].update(
                {
                    "reconnected_at": datetime.now(),
                    "last_ping": datetime.now(),
                    "reconnection_count": self.connection_metadata[client_id].get(
                        "reconnection_count", 0
                    )
                    + 1,
                }
            )
        else:
            # First time connection with this ID
            self.connection_metadata[client_id] = {
                "connected_at": datetime.now(),
                "last_ping": datetime.now(),
                "plan": "pro",
                "reconnection_count": 0,
            }

        logger.info(
            f"WebSocket client reconnected: {client_id} (attempt #{self.connection_metadata[client_id]['reconnection_count']})"
        )

        # Send reconnection confirmation
        await self.send_personal_message(
            {
                "type": "reconnection_established",
                "data": {
                    "client_id": client_id,
                    "server_time": datetime.now().isoformat(),
                    "reconnection_count": self.connection_metadata[client_id][
                        "reconnection_count"
                    ],
                },
            },
            client_id,
        )

    async def ping_clients(self) -> None:
        """Ping all clients to check connection health."""
        if not self.active_connections:
            return

        ping_message = {
            "type": "ping_request",
            "data": {"timestamp": datetime.now().isoformat(), "expected_pong": True},
        }

        await self.broadcast(ping_message)

    def get_stale_connections(self, timeout_seconds: int = 60) -> List[str]:
        """
        Get connections that haven't responded to ping in timeout period.

        Args:
            timeout_seconds: Timeout in seconds

        Returns:
            List of stale client IDs
        """
        stale_clients = []
        current_time = datetime.now()

        for client_id, metadata in self.connection_metadata.items():
            last_ping = metadata.get("last_ping", metadata["connected_at"])
            if (current_time - last_ping).total_seconds() > timeout_seconds:
                stale_clients.append(client_id)

        return stale_clients

    async def cleanup_stale_connections(self) -> int:
        """
        Remove stale connections that haven't responded to pings.

        Returns:
            Number of connections cleaned up
        """
        stale_clients = self.get_stale_connections()

        for client_id in stale_clients:
            logger.warning(f"Cleaning up stale connection: {client_id}")
            self.disconnect(client_id)

        return len(stale_clients)

    def graceful_disconnect(
        self, client_id: str, reason: str = "Server shutdown"
    ) -> None:
        """
        Gracefully disconnect a client with notification.

        Args:
            client_id: Client to disconnect
            reason: Reason for disconnection
        """
        if client_id in self.active_connections:
            try:
                # Send disconnect notification
                asyncio.create_task(
                    self.send_personal_message(
                        {
                            "type": "disconnect_notification",
                            "data": {
                                "reason": reason,
                                "timestamp": datetime.now().isoformat(),
                                "reconnection_info": {
                                    "endpoint": "/ws/usage",
                                    "recommended_delay": 1000,  # ms
                                },
                            },
                        },
                        client_id,
                    )
                )
            except:
                pass  # Best effort

            # Remove connection
            self.disconnect(client_id)

    async def graceful_shutdown(self) -> None:
        """Gracefully shutdown all connections."""
        logger.info("Starting graceful WebSocket shutdown...")

        # Notify all clients
        if self.active_connections:
            await self.broadcast(
                {
                    "type": "server_shutdown",
                    "data": {
                        "message": "Server is shutting down",
                        "timestamp": datetime.now().isoformat(),
                        "reconnection_delay": 5000,  # ms
                    },
                }
            )

            # Wait a moment for messages to be sent
            await asyncio.sleep(1)

        # Stop broadcasting
        self.stop_broadcasting()

        # Close all connections
        client_ids = list(self.active_connections.keys())
        for client_id in client_ids:
            self.graceful_disconnect(client_id, "Server shutdown")

        logger.info("WebSocket graceful shutdown completed")


# Global connection manager instance
connection_manager = ConnectionManager()


@websocket_router.websocket("/ws/usage")
async def websocket_usage_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time usage monitoring.

    Provides real-time updates of:
    - Token usage statistics
    - Burn rate calculations
    - Time predictions
    - Plan changes
    - Session events
    """
    client_id = f"client_{datetime.now().timestamp()}"

    await connection_manager.connect(websocket, client_id)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await handle_client_message(message, client_id)
            except json.JSONDecodeError:
                await connection_manager.send_personal_message(
                    {"type": "error", "data": {"message": "Invalid JSON format"}},
                    client_id,
                )
            except Exception as e:
                logger.error(f"Error handling client message: {e}")
                await connection_manager.send_personal_message(
                    {"type": "error", "data": {"message": "Message processing failed"}},
                    client_id,
                )

    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        connection_manager.disconnect(client_id)


async def handle_client_message(message: Dict, client_id: str) -> None:
    """
    Handle incoming client messages.

    Args:
        message: Message from client
        client_id: Client identifier
    """
    message_type = message.get("type")
    data = message.get("data", {})

    if message_type == "ping":
        # Update last ping time
        if client_id in connection_manager.connection_metadata:
            connection_manager.connection_metadata[client_id]["last_ping"] = (
                datetime.now()
            )

        # Send pong response
        await connection_manager.send_personal_message(
            {"type": "pong", "data": {"timestamp": datetime.now().isoformat()}},
            client_id,
        )

    elif message_type == "set_plan":
        # Update client's plan preference
        plan = data.get("plan", "pro")
        if client_id in connection_manager.connection_metadata:
            connection_manager.connection_metadata[client_id]["plan"] = plan

        await connection_manager.send_personal_message(
            {"type": "plan_updated", "data": {"plan": plan}}, client_id
        )

    elif message_type == "get_status":
        # Send immediate status update
        plan = connection_manager.connection_metadata.get(client_id, {}).get(
            "plan", "pro"
        )
        try:
            status_data = await connection_manager.usage_service.get_current_status(
                plan
            )
            await connection_manager.send_personal_message(
                {"type": "status_response", "data": status_data}, client_id
            )
        except Exception as e:
            await connection_manager.send_personal_message(
                {
                    "type": "error",
                    "data": {"message": f"Failed to get status: {str(e)}"},
                },
                client_id,
            )

    else:
        await connection_manager.send_personal_message(
            {
                "type": "error",
                "data": {"message": f"Unknown message type: {message_type}"},
            },
            client_id,
        )


@websocket_router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return connection_manager.get_connection_stats()
