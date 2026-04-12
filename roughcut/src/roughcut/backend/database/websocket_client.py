"""WebSocket client for SpacetimeDB.

Provides a native Python WebSocket client for connecting to SpacetimeDB
without requiring an official SDK. Implements the SpacetimeDB wire protocol
for subscriptions, reducer calls, and real-time updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
import struct
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# WebSocket library - using websockets as it's the most robust
try:
    import websockets
    try:
        from websockets.client import WebSocketClientProtocol
    except ImportError:
        from websockets.legacy.client import WebSocketClientProtocol
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    WebSocketClientProtocol = Any

from ...backend.database.models import MediaAsset

logger = logging.getLogger(__name__)


class MessageType(IntEnum):
    """SpacetimeDB message types."""
    # Connection
    CONNECT = 0
    CONNECT_SUCCESS = 1
    CONNECT_FAILURE = 2
    
    # Queries/Subscriptions
    SUBSCRIBE = 10
    SUBSCRIBE_SUCCESS = 11
    SUBSCRIBE_FAILURE = 12
    UNSUBSCRIBE = 13
    
    # Transactions/Reducers
    CALL_REDUCER = 20
    TRANSACTION_UPDATE = 21
    REDUCER_RESULT = 22
    
    # Data Updates
    TABLE_UPDATE = 30
    TABLE_ROW_OP = 31
    
    # Heartbeat
    PING = 100
    PONG = 101
    
    # Errors
    ERROR = 255


@dataclass
class SpacetimeIdentity:
    """Represents a SpacetimeDB identity."""
    bytes: bytes
    
    @classmethod
    def from_hex(cls, hex_str: str) -> 'SpacetimeIdentity':
        """Create identity from hex string."""
        return cls(bytes.fromhex(hex_str.replace('0x', '')))
    
    def to_hex(self) -> str:
        """Convert to hex string."""
        return '0x' + self.bytes.hex()
    
    def __str__(self) -> str:
        return self.to_hex()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, SpacetimeIdentity):
            return False
        return self.bytes == other.bytes


@dataclass
class ConnectionConfig:
    """Configuration for WebSocket connection."""
    host: str = "localhost"
    port: int = 3000
    database_name: str = "roughcut"
    module_name: str = "roughcut"
    identity_token: Optional[str] = None
    use_ssl: bool = False
    
    @property
    def ws_uri(self) -> str:
        """Build WebSocket URI."""
        protocol = "wss" if self.use_ssl else "ws"
        return f"{protocol}://{self.host}:{self.port}/v1/database/{self.database_name}"


@dataclass
class ReducerResult:
    """Result of a reducer call."""
    success: bool = False
    reducer_name: str = ""
    error: Optional[str] = None
    return_value: Any = None
    timestamp: Optional[datetime] = None


@dataclass
class TableUpdate:
    """Update to a table."""
    table_name: str = ""
    operation: str = ""  # "insert", "update", "delete"
    row: Optional[Dict[str, Any]] = None
    old_row: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None


class SpacetimeWebSocketClient:
    """Native WebSocket client for SpacetimeDB.
    
    Implements the SpacetimeDB wire protocol for Python without requiring
    an official SDK. Supports subscriptions, reducer calls, and real-time
    updates via WebSocket.
    
    Example:
        >>> config = ConnectionConfig(
        ...     host="localhost",
        ...     port=3000,
        ...     database_name="roughcut",
        ...     identity_token="my_token"
        ... )
        >>> async with SpacetimeWebSocketClient(config) as client:
        ...     await client.connect()
        ...     # Subscribe to table
        ...     await client.subscribe("SELECT * FROM media_assets")
        ...     # Call reducer
        ...     result = await client.call_reducer("insert_asset", {...})
    """
    
    def __init__(self, config: ConnectionConfig):
        """Initialize WebSocket client.
        
        Args:
            config: Connection configuration
        """
        if not HAS_WEBSOCKETS:
            raise RuntimeError(
                "websockets library is required. Install with: "
                "pip install websockets"
            )
        
        self.config = config
        self._ws: Optional[WebSocketClientProtocol] = None
        self._connected = False
        self._identity: Optional[SpacetimeIdentity] = None
        self._connection_token: Optional[str] = None
        
        # Message handling
        self._message_handlers: Dict[MessageType, Callable] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._pending_message_types: Dict[str, List[asyncio.Future]] = {}
        self._subscriptions: Dict[str, Callable[[TableUpdate], None]] = {}
        
        # Callbacks
        self._on_connect: Optional[Callable[[SpacetimeIdentity, str], None]] = None
        self._on_disconnect: Optional[Callable[[Optional[str]], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        
        # Background tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        
        # Locks
        self._send_lock = asyncio.Lock()
        self._subscription_lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False
    
    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected and self._ws is not None
    
    @property
    def identity(self) -> Optional[SpacetimeIdentity]:
        """Get current identity."""
        return self._identity
    
    def on_connect(self, callback: Callable[[SpacetimeIdentity, str], None]):
        """Register connection callback.
        
        Args:
            callback: Function(identity, token) called on successful connect
        """
        self._on_connect = callback
    
    def on_disconnect(self, callback: Callable[[Optional[str]], None]):
        """Register disconnection callback.
        
        Args:
            callback: Function(error_or_none) called on disconnect
        """
        self._on_disconnect = callback
    
    def on_error(self, callback: Callable[[str], None]):
        """Register error callback.
        
        Args:
            callback: Function(error_message) called on errors
        """
        self._on_error = callback
    
    async def connect(self, timeout: float = 10.0) -> bool:
        """Establish WebSocket connection to SpacetimeDB.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected successfully
            
        Raises:
            ConnectionError: If connection fails
        """
        if self._connected:
            return True
        
        try:
            logger.info(f"Connecting to {self.config.ws_uri}")
            
            # Build headers
            headers = {
                "Authorization": f"Bearer {self.config.identity_token or ''}",
                "X-SpacetimeDB-Module": self.config.module_name,
            }
            
            # Connect with timeout
            self._ws = await asyncio.wait_for(
                websockets.connect(
                    self.config.ws_uri,
                    extra_headers=headers,
                    subprotocols=["v1.spacetimedb"]
                ),
                timeout=timeout
            )
            
            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            # Send connect message
            connect_msg = {
                "type": "connect",
                "module": self.config.module_name,
            }
            await self._send_message(connect_msg)
            
            # Wait for connect response
            try:
                response = await self._wait_for_message(
                    expected_type="connect_response",
                    timeout=5.0
                )
                
                if response.get("success"):
                    self._connected = True
                    identity_hex = response.get("identity", "0x" + "0" * 64)
                    self._identity = SpacetimeIdentity.from_hex(identity_hex)
                    self._connection_token = response.get("token")
                    
                    logger.info(f"Connected with identity: {self._identity}")
                    
                    # Start heartbeat
                    self._ping_task = asyncio.create_task(self._heartbeat_loop())
                    
                    if self._on_connect:
                        try:
                            self._on_connect(self._identity, self._connection_token or "")
                        except Exception as e:
                            logger.warning(f"Connect callback error: {e}")
                    
                    return True
                else:
                    error = response.get("error", "Unknown error")
                    raise ConnectionError(f"Connection rejected: {error}")
                    
            except asyncio.TimeoutError:
                raise ConnectionError("Timeout waiting for connect response")
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            await self._cleanup()
            raise ConnectionError(f"Failed to connect: {e}")
    
    async def disconnect(self):
        """Disconnect from SpacetimeDB."""
        if not self._connected and not self._ws:
            return
        
        logger.info("Disconnecting...")
        self._connected = False
        
        # Cancel background tasks
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket
        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            finally:
                self._ws = None
        
        # Clear pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(ConnectionError("Disconnected"))
        self._pending_requests.clear()
        for futures in self._pending_message_types.values():
            for future in futures:
                if not future.done():
                    future.set_exception(ConnectionError("Disconnected"))
        self._pending_message_types.clear()
        
        if self._on_disconnect:
            try:
                self._on_disconnect(None)
            except Exception as e:
                logger.warning(f"Disconnect callback error: {e}")
        
        logger.info("Disconnected")
    
    async def _cleanup(self):
        """Clean up resources."""
        if self._ping_task:
            self._ping_task.cancel()
        if self._receive_task:
            self._receive_task.cancel()
        if self._ws:
            await self._ws.close()
            self._ws = None
        self._connected = False
        self._pending_requests.clear()
        self._pending_message_types.clear()
    
    async def _receive_loop(self):
        """Background task to receive and process messages."""
        try:
            while self._ws is not None:
                try:
                    message = await self._ws.recv()
                    await self._handle_message(message)
                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebSocket connection closed")
                    break
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    if self._on_error:
                        self._on_error(str(e))
        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
        finally:
            if self._connected:
                # Connection was lost unexpectedly
                self._connected = False
                if self._on_disconnect:
                    try:
                        self._on_disconnect("Connection lost")
                    except Exception:
                        pass
    
    async def _heartbeat_loop(self):
        """Send periodic ping messages."""
        try:
            while self._connected:
                await asyncio.sleep(30)  # Ping every 30 seconds
                if self._connected and self._ws:
                    try:
                        await self._send_message({"type": "ping"})
                    except Exception as e:
                        logger.warning(f"Ping failed: {e}")
                        break
        except asyncio.CancelledError:
            logger.debug("Heartbeat loop cancelled")
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send a message over WebSocket.
        
        Args:
            message: Message dictionary to send
        """
        if not self._ws:
            raise ConnectionError("Not connected")
        
        async with self._send_lock:
            try:
                message_json = json.dumps(message)
                await self._ws.send(message_json)
            except Exception as e:
                raise ConnectionError(f"Send failed: {e}")
    
    async def _handle_message(self, message: Union[str, bytes]):
        """Handle incoming WebSocket message.
        
        Args:
            message: Raw message from WebSocket
        """
        try:
            if isinstance(message, bytes):
                # Handle binary messages (e.g., MessagePack)
                data = self._decode_binary(message)
            else:
                data = json.loads(message)
            
            msg_type = data.get("type", "unknown")
            request_id = data.get("request_id")
            
            # Check for pending request
            if request_id and request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                if not future.done():
                    future.set_result(data)
                return

            pending_type_waiters = self._pending_message_types.get(msg_type)
            if pending_type_waiters:
                future = pending_type_waiters.pop(0)
                if not pending_type_waiters:
                    self._pending_message_types.pop(msg_type, None)
                if not future.done():
                    future.set_result(data)
                return
            
            # Handle based on type
            if msg_type == "connect_response":
                pass  # Handled in connect()
            elif msg_type == "table_update":
                await self._handle_table_update(data)
            elif msg_type == "reducer_result":
                await self._handle_reducer_result(data)
            elif msg_type == "subscription_update":
                await self._handle_subscription_update(data)
            elif msg_type == "pong":
                pass  # Heartbeat response
            elif msg_type == "error":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Server error: {error_msg}")
                if self._on_error:
                    self._on_error(error_msg)
            else:
                logger.debug(f"Unhandled message type: {msg_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def _decode_binary(self, data: bytes) -> Dict[str, Any]:
        """Decode binary message (MessagePack or similar).
        
        Args:
            data: Binary message data
            
        Returns:
            Decoded dictionary
        """
        # Try MessagePack first
        try:
            import msgpack
            return msgpack.unpackb(data, raw=False)
        except ImportError:
            pass
        
        # Fallback: assume it's JSON in bytes
        return json.loads(data.decode('utf-8'))
    
    async def _wait_for_message(
        self,
        expected_type: Optional[str] = None,
        timeout: float = 30.0,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Wait for a specific message type or request id.
        
        Args:
            expected_type: Expected message type
            timeout: Maximum wait time
            request_id: Specific request identifier to await
            
        Returns:
            Message data
        """
        future = asyncio.get_event_loop().create_future()

        if request_id is not None:
            self._pending_requests[request_id] = future
        elif expected_type is not None:
            self._pending_message_types.setdefault(expected_type, []).append(future)
        else:
            raise ValueError("expected_type or request_id must be provided")
        
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            if request_id is not None:
                self._pending_requests.pop(request_id, None)
            elif expected_type is not None:
                waiters = self._pending_message_types.get(expected_type, [])
                if future in waiters:
                    waiters.remove(future)
                if not waiters:
                    self._pending_message_types.pop(expected_type, None)
            raise
    
    async def _handle_table_update(self, data: Dict[str, Any]):
        """Handle table update message."""
        table_name = data.get("table_name", "")
        operation = data.get("operation", "")
        row = data.get("row")
        
        update = TableUpdate(
            table_name=table_name,
            operation=operation,
            row=row,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Notify subscribers
        async with self._subscription_lock:
            callback = self._subscriptions.get(table_name)
        
        if callback:
            try:
                callback(update)
            except Exception as e:
                logger.warning(f"Subscription callback error: {e}")
    
    async def _handle_reducer_result(self, data: Dict[str, Any]):
        """Handle reducer result message."""
        # This is handled via pending requests
        pass
    
    async def _handle_subscription_update(self, data: Dict[str, Any]):
        """Handle subscription update."""
        # Notify all subscribers
        pass
    
    async def subscribe(
        self,
        query: str,
        on_update: Optional[Callable[[TableUpdate], None]] = None,
        timeout: float = 30.0
    ) -> str:
        """Subscribe to a query.
        
        Args:
            query: SQL-like query string (e.g., "SELECT * FROM media_assets")
            on_update: Callback for table updates
            timeout: Subscription timeout
            
        Returns:
            Subscription ID
        """
        if not self._connected:
            raise ConnectionError("Not connected")
        
        subscription_id = str(uuid.uuid4())
        
        # Register callback
        if on_update:
            table_name = self._extract_table_name(query)
            async with self._subscription_lock:
                self._subscriptions[table_name] = on_update
        
        # Send subscribe message
        msg = {
            "type": "subscribe",
            "request_id": subscription_id,
            "query": query
        }
        
        await self._send_message(msg)
        
        # Wait for confirmation
        try:
            response = await self._wait_for_message(
                expected_type="subscription_response",
                timeout=timeout,
                request_id=subscription_id
            )
            if not response.get("success"):
                error = response.get("error", "Unknown error")
                raise RuntimeError(f"Subscription failed: {error}")
        except asyncio.TimeoutError:
            raise RuntimeError("Subscription timeout")
        
        logger.info(f"Subscribed to: {query[:50]}...")
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str):
        """Unsubscribe from a query.
        
        Args:
            subscription_id: Subscription ID to cancel
        """
        if not self._connected:
            return
        
        msg = {
            "type": "unsubscribe",
            "subscription_id": subscription_id
        }
        
        await self._send_message(msg)
        
        # Remove callback
        async with self._subscription_lock:
            for table, callback in list(self._subscriptions.items()):
                # Note: In real implementation, track subscription_id -> table mapping
                pass
        
        logger.info(f"Unsubscribed: {subscription_id}")
    
    async def call_reducer(
        self,
        reducer_name: str,
        args: Dict[str, Any],
        timeout: float = 30.0
    ) -> ReducerResult:
        """Call a reducer function.
        
        Args:
            reducer_name: Name of the reducer to call
            args: Arguments for the reducer
            timeout: Call timeout
            
        Returns:
            ReducerResult with success status and return value
        """
        if not self._connected:
            raise ConnectionError("Not connected")
        
        request_id = str(uuid.uuid4())
        
        msg = {
            "type": "call_reducer",
            "request_id": request_id,
            "reducer": reducer_name,
            "args": args
        }
        
        await self._send_message(msg)
        
        # Wait for result
        try:
            response = await self._wait_for_message(
                expected_type="reducer_result",
                timeout=timeout,
                request_id=request_id
            )
            
            return ReducerResult(
                success=response.get("success", False),
                reducer_name=reducer_name,
                error=response.get("error"),
                return_value=response.get("return_value"),
                timestamp=datetime.now(timezone.utc)
            )
            
        except asyncio.TimeoutError:
            return ReducerResult(
                success=False,
                reducer_name=reducer_name,
                error="Timeout waiting for reducer result",
                timestamp=datetime.now(timezone.utc)
            )
    
    def _extract_table_name(self, query: str) -> str:
        """Extract table name from SQL-like query.
        
        Args:
            query: Query string
            
        Returns:
            Table name
        """
        # Simple extraction: look for "FROM table_name"
        import re
        match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        if match:
            return match.group(1)
        return "unknown"


# Convenience function for MediaAsset operations
async def connect_to_spacetime_db(
    host: str = "localhost",
    port: int = 3000,
    database_name: str = "roughcut",
    identity_token: Optional[str] = None
) -> SpacetimeWebSocketClient:
    """Create and connect to SpacetimeDB.
    
    Args:
        host: SpacetimeDB host
        port: SpacetimeDB port
        database_name: Database name
        identity_token: Authentication token
        
    Returns:
        Connected SpacetimeWebSocketClient
    """
    config = ConnectionConfig(
        host=host,
        port=port,
        database_name=database_name,
        identity_token=identity_token
    )
    
    client = SpacetimeWebSocketClient(config)
    await client.connect()
    return client


__all__ = [
    'SpacetimeWebSocketClient',
    'ConnectionConfig',
    'SpacetimeIdentity',
    'ReducerResult',
    'TableUpdate',
    'MessageType',
    'connect_to_spacetime_db'
]
