#!/usr/bin/env python3
"""Asset query operations for RoughCut.

Handles querying assets from the database with various filters.
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


async def main() -> None:
    """Main query operation."""
    setup_logging()

    # Parse arguments
    parser = argparse.ArgumentParser(description='Query assets')
    parser.add_argument('--roughcut-path', required=True, help='Path to roughcut module')
    parser.add_argument('--params', required=True, help='JSON-encoded parameters')
    args = parser.parse_args()

    roughcut_path = args.roughcut_path
    params = json.loads(args.params)

    log_indexing("Starting query operation")
    add_roughcut_to_path(roughcut_path)

    # Import modules
    try:
        from roughcut.backend.database.spacetime_client import SpacetimeClient, SpacetimeConfig
        from roughcut.config.settings import get_config_manager
    except Exception as e:
        output_error("Import failed", e)
        sys.exit(1)

    # Get config
    config_manager = get_config_manager()
    spacetime_cfg = config_manager.get_spacetime_config()

    db_config = SpacetimeConfig(
        host=spacetime_cfg.get('host', 'localhost'),
        port=spacetime_cfg.get('port', 3000),
        database_name=spacetime_cfg.get('database_name', 'roughcut'),
        identity_token=spacetime_cfg.get('identity_token')
    )

    # Connect and query
    client = SpacetimeClient(db_config)
    connected = await client.connect()

    if not connected:
        raise RuntimeError('Could not connect to SpacetimeDB')

    try:
        assets = await client.query_assets(
            category=params.get('category'),
            limit=params.get('limit', 1000),
            scope_folders=[params.get('folder_path')] if params.get('folder_path') else None,
            verify_on_disk=params.get('verify_on_disk', False),
        )

        # Convert assets to JSON-serializable format
        asset_list = []
        for asset in assets.assets:
            asset_list.append({
                'id': asset.id,
                'file_path': str(asset.file_path),
                'file_name': asset.file_name,
                'category': asset.category,
                'file_size': asset.file_size,
                'ai_tags': asset.ai_tags,
                'duration': getattr(asset, 'duration', None),
                'used': getattr(asset, 'used', False)
            })

        result = {
            'assets': asset_list,
            'total_count': assets.total_count,
            'database_connected': True
        }

        output_result(result)

    finally:
        await client.disconnect()


if __name__ == "__main__":
    run_async_main(main)
