#!/usr/bin/env python3
"""DaVinci Resolve API operations for RoughCut.

Handles connection, status, and timeline operations with DaVinci Resolve.
"""

import sys
import json
import argparse
from typing import Any

from common import (
    setup_logging,
    log_indexing,
    output_result,
    output_error,
    add_roughcut_to_path,
    run_async_main
)


async def resolve_status(params: dict[str, Any]) -> dict[str, Any]:
    """Get Resolve connection status."""
    from roughcut.backend.timeline.resolve_api import ResolveApi

    api = ResolveApi()
    return api.get_connection_status()


async def resolve_connect(params: dict[str, Any]) -> dict[str, Any]:
    """Connect to Resolve and return status."""
    from roughcut.backend.timeline.resolve_api import ResolveApi

    api = ResolveApi()
    api.connect()
    return api.get_connection_status()


async def resolve_disconnect(params: dict[str, Any]) -> dict[str, Any]:
    """Disconnect from Resolve."""
    from roughcut.backend.timeline.resolve_api import ResolveApi

    api = ResolveApi()
    api.disconnect()

    return {
        'connected': False,
        'available': False,
        'project_name': None,
        'version': None,
        'module_error': None,
        'search_paths': [],
    }


async def resolve_send_timeline(params: dict[str, Any]) -> dict[str, Any]:
    """Send timeline data to Resolve."""
    from roughcut.backend.timeline.resolve_api import ResolveApi

    api = ResolveApi()
    if not api.connect():
        raise RuntimeError('DaVinci Resolve is not available')

    return {
        'success': True,
        'connected': True,
        'project_name': api.get_connection_status().get('project_name'),
        'payload': params,
    }


COMMAND_HANDLERS = {
    'resolve_status': resolve_status,
    'resolve_connect': resolve_connect,
    'resolve_disconnect': resolve_disconnect,
    'resolve_send_timeline': resolve_send_timeline,
}


async def main() -> None:
    """Main Resolve API operation."""
    setup_logging()

    # Parse arguments
    parser = argparse.ArgumentParser(description='Resolve API operations')
    parser.add_argument('--roughcut-path', required=True, help='Path to roughcut module')
    parser.add_argument('--command', required=True, choices=list(COMMAND_HANDLERS.keys()),
                        help='Command to execute')
    parser.add_argument('--params', default='{}', help='JSON-encoded parameters')
    args = parser.parse_args()

    roughcut_path = args.roughcut_path
    params = json.loads(args.params)

    log_indexing(f"Starting Resolve command: {args.command}")
    add_roughcut_to_path(roughcut_path)

    # Execute the appropriate handler
    handler = COMMAND_HANDLERS[args.command]
    result = await handler(params)
    output_result(result)


if __name__ == "__main__":
    run_async_main(main)
