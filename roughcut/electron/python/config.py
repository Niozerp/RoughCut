#!/usr/bin/env python3
"""Configuration operations for RoughCut.

Handles config retrieval, saving media folders, onboarding state, and spacetime runtime config.
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


async def get_config_state(params: dict[str, Any]) -> dict[str, Any]:
    """Get the current configuration state."""
    from roughcut.config.settings import get_config_manager

    config_manager = get_config_manager()
    media_config = config_manager.get_media_folders_config()
    onboarding_state = config_manager.get_onboarding_state()
    spacetime_cfg = config_manager.get_spacetime_config()

    return {
        'media_folders': {
            'music_folder': media_config.music_folder,
            'sfx_folder': media_config.sfx_folder,
            'vfx_folder': media_config.vfx_folder,
        },
        'onboarding': onboarding_state,
        'spacetime': {
            'host': spacetime_cfg.get('host', 'localhost'),
            'port': spacetime_cfg.get('port', 3000),
            'database_name': spacetime_cfg.get('database_name', 'roughcut'),
            'module_path': spacetime_cfg.get('module_path'),
            'data_dir': spacetime_cfg.get('data_dir'),
            'binary_path': spacetime_cfg.get('binary_path'),
            'binary_version': spacetime_cfg.get('binary_version'),
            'module_published': spacetime_cfg.get('module_published', False),
            'module_fingerprint': spacetime_cfg.get('module_fingerprint'),
            'published_fingerprint': spacetime_cfg.get('published_fingerprint'),
            'last_ready_at': spacetime_cfg.get('last_ready_at'),
            'last_health_check_at': spacetime_cfg.get('last_health_check_at'),
        }
    }


async def save_media_folders(params: dict[str, Any]) -> dict[str, Any]:
    """Save media folder configuration."""
    from roughcut.config.settings import get_config_manager

    config_manager = get_config_manager()
    success, message, errors = config_manager.save_media_folders_config(
        music_folder=params.get('music_folder'),
        sfx_folder=params.get('sfx_folder'),
        vfx_folder=params.get('vfx_folder'),
    )

    if not success:
        raise RuntimeError(message if not errors else json.dumps(errors))

    onboarding_state = config_manager.get_onboarding_state()
    media_config = config_manager.get_media_folders_config()

    return {
        'success': True,
        'message': message,
        'media_folders': {
            'music_folder': media_config.music_folder,
            'sfx_folder': media_config.sfx_folder,
            'vfx_folder': media_config.vfx_folder,
        },
        'onboarding': onboarding_state,
    }


async def set_onboarding_complete(params: dict[str, Any]) -> dict[str, Any]:
    """Set onboarding completion state."""
    from roughcut.config.settings import get_config_manager

    config_manager = get_config_manager()
    success, message = config_manager.set_onboarding_complete(
        params.get('completed', True)
    )

    if not success:
        raise RuntimeError(message)

    return {
        'success': True,
        'message': message,
        'onboarding': config_manager.get_onboarding_state(),
    }


async def save_spacetime_runtime(params: dict[str, Any]) -> dict[str, Any]:
    """Save spacetime runtime configuration."""
    from roughcut.config.settings import get_config_manager

    config_manager = get_config_manager()
    success, message = config_manager.update_spacetime_runtime_state(
        host=params.get('host'),
        port=params.get('port'),
        database_name=params.get('database_name'),
        module_path=params.get('module_path'),
        data_dir=params.get('data_dir'),
        binary_path=params.get('binary_path'),
        binary_version=params.get('binary_version'),
        module_published=params.get('module_published'),
        module_fingerprint=params.get('module_fingerprint'),
        published_fingerprint=params.get('published_fingerprint'),
        last_ready_at=params.get('last_ready_at'),
        last_health_check_at=params.get('last_health_check_at'),
    )

    if not success:
        raise RuntimeError(message)

    return {
        'success': True,
        'message': message,
        'spacetime': config_manager.get_spacetime_config(),
    }


async def get_status(params: dict[str, Any]) -> dict[str, Any]:
    """Get database status and asset counts."""
    from roughcut.backend.database.spacetime_client import SpacetimeClient, SpacetimeConfig
    from roughcut.config.settings import get_config_manager

    config_manager = get_config_manager()
    spacetime_cfg = config_manager.get_spacetime_config()

    db_config = SpacetimeConfig(
        host=spacetime_cfg.get('host', 'localhost'),
        port=spacetime_cfg.get('port', 3000),
        database_name=spacetime_cfg.get('database_name', 'roughcut'),
        identity_token=spacetime_cfg.get('identity_token')
    )

    client = SpacetimeClient(db_config)
    connected = await client.connect()

    if not connected:
        raise RuntimeError('Could not connect to SpacetimeDB')

    try:
        counts = await client.get_asset_counts()
        return {
            'connected': True,
            'music_count': counts.music,
            'sfx_count': counts.sfx,
            'vfx_count': counts.vfx,
            'total_count': counts.total
        }
    finally:
        await client.disconnect()


async def purge_category(params: dict[str, Any]) -> dict[str, Any]:
    """Delete all assets in a category."""
    from roughcut.backend.database.spacetime_client import SpacetimeClient, SpacetimeConfig
    from roughcut.config.settings import get_config_manager

    config_manager = get_config_manager()
    spacetime_cfg = config_manager.get_spacetime_config()

    db_config = SpacetimeConfig(
        host=spacetime_cfg.get('host', 'localhost'),
        port=spacetime_cfg.get('port', 3000),
        database_name=spacetime_cfg.get('database_name', 'roughcut'),
        identity_token=spacetime_cfg.get('identity_token')
    )

    client = SpacetimeClient(db_config)
    connected = await client.connect()

    if not connected:
        raise RuntimeError('Could not connect to SpacetimeDB')

    try:
        assets = await client.query_assets(
            category=params.get('category'),
            limit=100000,
        )
        delete_result = await client.delete_assets([asset.id for asset in assets.assets])

        return {
            'deleted_count': delete_result.deleted_count,
            'database_connected': True,
        }
    finally:
        await client.disconnect()


COMMAND_HANDLERS = {
    'config_state': get_config_state,
    'save_media_folders': save_media_folders,
    'set_onboarding_complete': set_onboarding_complete,
    'save_spacetime_runtime': save_spacetime_runtime,
    'status': get_status,
    'purge_category': purge_category,
}


async def main() -> None:
    """Main configuration operation."""
    setup_logging()

    # Parse arguments
    parser = argparse.ArgumentParser(description='Configuration operations')
    parser.add_argument('--roughcut-path', required=True, help='Path to roughcut module')
    parser.add_argument('--command', required=True, choices=list(COMMAND_HANDLERS.keys()),
                        help='Command to execute')
    parser.add_argument('--params', default='{}', help='JSON-encoded parameters')
    args = parser.parse_args()

    roughcut_path = args.roughcut_path
    params = json.loads(args.params)

    log_indexing(f"Starting config command: {args.command}")
    add_roughcut_to_path(roughcut_path)

    # Execute the appropriate handler
    handler = COMMAND_HANDLERS[args.command]
    result = await handler(params)
    output_result(result)


if __name__ == "__main__":
    run_async_main(main)
