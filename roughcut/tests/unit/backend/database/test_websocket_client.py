"""Unit tests for the low-level SpacetimeDB websocket client."""

import asyncio

from roughcut.backend.database.websocket_client import (
    ConnectionConfig,
    SpacetimeWebSocketClient,
)


def run_async(coro):
    """Run an async test body without requiring pytest-asyncio."""
    return asyncio.run(coro)


async def _await_next_loop_tick():
    await asyncio.sleep(0)


class TestWebsocketClientWaiters:
    def test_wait_for_message_resolves_by_request_id(self):
        async def scenario():
            client = SpacetimeWebSocketClient(ConnectionConfig())

            waiter = asyncio.create_task(
                client._wait_for_message(request_id="req-1", timeout=0.5)
            )
            await _await_next_loop_tick()

            await client._handle_message(
                '{"type": "reducer_result", "request_id": "req-1", "success": true}'
            )

            result = await waiter
            assert result["type"] == "reducer_result"
            assert result["success"] is True

        run_async(scenario())

    def test_wait_for_message_resolves_by_type_without_request_id(self):
        async def scenario():
            client = SpacetimeWebSocketClient(ConnectionConfig())

            waiter = asyncio.create_task(
                client._wait_for_message(expected_type="connect_response", timeout=0.5)
            )
            await _await_next_loop_tick()

            await client._handle_message(
                '{"type": "connect_response", "success": true, "identity": "0x'
                + ('0' * 64)
                + '"}'
            )

            result = await waiter
            assert result["type"] == "connect_response"
            assert result["success"] is True

        run_async(scenario())
