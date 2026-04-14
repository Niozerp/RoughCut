
#!/usr/bin/env python3
"""Indexing operations for RoughCut media assets.

Handles indexing and reindexing of music, SFX, and VFX folders.
Receives parameters via command line as JSON.
"""

import sys
import json
import argparse
from typing import Any

from common import (
    setup_logging,
    log_indexing,
    output_progress,
    output_result,
    output_error,
    output_streaming_asset,
    add_roughcut_to_path,
    run_async_main
)


async def main() -> None:
    """Main indexing operation."""
    setup_logging()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Index media assets')
    parser.add_argument('--roughcut-path', required=True, help='Path to roughcut module')
    parser.add_argument('--params', required=True, help='JSON-encoded parameters')
    args = parser.parse_args()

    roughcut_path = args.roughcut_path
    params = json.loads(args.params)

    # Initial logging
    log_indexing(f"Python script starting at import time")
    log_indexing(f"Python version: {sys.version}")
    log_indexing(f"Roughcut path: {roughcut_path}")
    log_indexing(f"Command: {'reindex' if params.get('reindex') else 'index'}")

    # Add roughcut to path
    add_roughcut_to_path(roughcut_path)

    # Import roughcut modules
    try:
        log_indexing("Importing MediaIndexer...")
        from roughcut.backend.indexing.indexer import MediaIndexer
        log_indexing("MediaIndexer imported successfully")

        from roughcut.config.models import MediaFolderConfig
        log_indexing("MediaFolderConfig imported successfully")
    except Exception as import_err:
        log_indexing(f"CRITICAL: Import failed: {str(import_err)}")
        output_error("Import error", import_err)
        sys.exit(1)

    log_indexing("Main async function started")

    # Extract parameters
    folders = params.get('folders', [])
    reindex = params.get('reindex', False)
    category = None

    if folders:
        category = folders[0].get('category')

    log_indexing(f"Parameters parsed, category: {category}")
    log_indexing(f"Configuring folders: {len(folders)} folder(s)")

    # Create folder config
    config = MediaFolderConfig()
    for folder in folders:
        if folder['category'] == 'music':
            config.music_folder = folder['path']
        elif folder['category'] == 'sfx':
            config.sfx_folder = folder['path']
        elif folder['category'] == 'vfx':
            config.vfx_folder = folder['path']

    # Create indexer
    log_indexing("Creating MediaIndexer instance...")
    indexer = MediaIndexer()
    log_indexing("MediaIndexer created")

    # Connect to database
    log_indexing("PHASE 0: Connecting to database...")
    connected = await indexer.connect_database()
    log_indexing(f"Database connection result: {connected}")

    if not connected:
        raise RuntimeError('Could not connect to SpacetimeDB')

    # Set up progress callback
    def progress_callback(update: dict[str, Any]) -> None:
        if category and 'category' not in update:
            update['category'] = category
        output_progress(update)

    indexer.progress_callback = progress_callback

    # Set up streaming callback for real-time asset display
    def streaming_callback(asset: dict[str, Any]) -> None:
        """Called immediately after an asset is written to the database."""
        if category and 'category' not in asset:
            asset['category'] = category
        output_streaming_asset(asset)
        log_indexing(f"[STREAM] Asset sent to GUI: {asset.get('file_name', 'unknown')}")

    # Attach streaming callback if the indexer supports it
    if hasattr(indexer, 'streaming_callback'):
        indexer.streaming_callback = streaming_callback
        log_indexing("Streaming callback attached for real-time GUI updates")
    else:
        log_indexing("Note: Indexer does not support streaming callback")

    # Run indexing
    operation_name = 'reindex_folders' if reindex else 'index_media'
    log_indexing(f"Starting indexing operation ({operation_name})...")

    if reindex:
        log_indexing("Executing reindex_folders...")
        result = await indexer.reindex_folders(config)
    else:
        log_indexing("Executing index_media...")
        result = await indexer.index_media(config)

    log_indexing("Indexing operation completed")

    # Build result dict
    result_dict = {
        'category': category,
        'indexed_count': result.indexed_count,
        'new_count': result.new_count,
        'modified_count': result.modified_count,
        'deleted_count': result.deleted_count,
        'moved_count': getattr(result, 'moved_count', 0),
        'total_scanned': getattr(result, 'total_scanned', 0),
        'duration_ms': result.duration_ms,
        'errors': result.errors,
        'database_connected': connected
    }

    log_indexing(f"Result: {result.indexed_count} assets indexed")
    output_result(result_dict)

    # Disconnect
    log_indexing("Disconnecting from database...")
    await indexer.disconnect_database()
    log_indexing("Database disconnected")


if __name__ == "__main__":
    run_async_main(main)
