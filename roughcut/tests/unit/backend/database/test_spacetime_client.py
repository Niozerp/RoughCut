"""Unit tests for the current SpacetimeDB client implementation."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import shutil
from unittest.mock import AsyncMock, Mock, patch

import pytest

from roughcut.backend.database.models import MediaAsset
from roughcut.backend.database.spacetime_client import (
    ConnectionState,
    DeleteResult,
    InsertResult,
    QueryResult,
    SpacetimeClient,
    SpacetimeConfig,
    TIMESTAMP_FIELD,
    UpdateResult,
)


def run_async(coro):
    """Run an async test body without requiring pytest-asyncio."""
    return asyncio.run(coro)


@pytest.fixture
def test_config():
    return SpacetimeConfig(
        host="localhost",
        port=3000,
        database_name="test_roughcut",
        identity_token="test_identity_token",
        connect_timeout=1.0,
        max_reconnect_attempts=2,
    )


@pytest.fixture
def mock_client(test_config):
    client = SpacetimeClient(test_config)
    client._connection_state = ConnectionState.CONNECTED
    client._client = Mock()
    return client


@pytest.fixture
def sample_asset():
    now = datetime.now(timezone.utc)
    return MediaAsset(
        id="asset-1",
        file_path=Path("/test/music/song.mp3"),
        file_name="song.mp3",
        category="music",
        file_size=1024,
        modified_time=now,
        file_hash="abc123",
        ai_tags=["upbeat", "energetic"],
        created_at=now,
        updated_at=now,
    )


class TestSpacetimeConfig:
    def test_default_values(self):
        config = SpacetimeConfig()

        assert config.host == "localhost"
        assert config.port == 3000
        assert config.database_name == "roughcut"
        assert config.identity_token is None
        assert config.pool_min_size == 2
        assert config.pool_max_size == 10

    def test_custom_values(self, test_config):
        assert test_config.database_name == "test_roughcut"
        assert test_config.identity_token == "test_identity_token"


class TestSpacetimeClientInitialization:
    def test_client_creation(self, test_config):
        client = SpacetimeClient(test_config)

        assert client.config == test_config
        assert client._client is None
        assert client._connection_state == ConnectionState.DISCONNECTED
        assert client._subscriptions == {}
        assert client.is_connected is False


class TestSpacetimeClientConnect:
    def test_connection_success(self, test_config):
        client = SpacetimeClient(test_config)

        with patch.object(client, "_create_connection", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = Mock()

            result = run_async(client.connect())

            assert result is True
            assert client.is_connected is True
            assert client._connection_state == ConnectionState.CONNECTED
            mock_create.assert_awaited_once()

    def test_connection_failure_transitions_to_error(self, test_config):
        client = SpacetimeClient(test_config)

        with patch.object(client, "_create_connection", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = None
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = run_async(client.connect())

        assert result is False
        assert client.is_connected is False
        assert client._connection_state == ConnectionState.ERROR
        assert mock_create.await_count == 2

    def test_disconnect_clears_client_and_state(self, mock_client):
        with patch.object(mock_client, "_close_connection", new_callable=AsyncMock) as mock_close:
            run_async(mock_client.disconnect())

        assert mock_client._client is None
        assert mock_client._connection_state == ConnectionState.DISCONNECTED
        mock_close.assert_awaited_once()


class TestInsertAssets:
    def test_insert_empty_list(self, mock_client):
        result = run_async(mock_client.insert_assets([]))

        assert isinstance(result, InsertResult)
        assert result.inserted_count == 0
        assert result.errors == []

    def test_insert_requires_connection(self, test_config):
        client = SpacetimeClient(test_config)

        with pytest.raises(ConnectionError, match="Not connected to SpacetimeDB"):
            run_async(client.insert_assets([Mock()]))

    def test_insert_single_asset(self, mock_client, sample_asset):
        with patch.object(mock_client, "_insert_batch", new_callable=AsyncMock) as mock_insert:
            mock_insert.return_value = 1

            result = run_async(mock_client.insert_assets([sample_asset]))

        assert result.inserted_count == 1
        assert result.errors == []
        mock_insert.assert_awaited_once()

    def test_insert_assets_reports_batch_progress(self, mock_client, sample_asset):
        progress_updates = []

        with patch.object(mock_client, "_insert_batch", new_callable=AsyncMock) as mock_insert:
            mock_insert.return_value = 1

            result = run_async(
                mock_client.insert_assets([sample_asset], progress_callback=progress_updates.append)
            )

        assert result.inserted_count == 1
        assert progress_updates[0] == {
            'current': 0,
            'total': 1,
            'batch_current': 0,
            'batch_total': 1,
        }
        assert progress_updates[-1] == {
            'current': 1,
            'total': 1,
            'batch_current': 1,
            'batch_total': 1,
        }
        mock_insert.assert_awaited_once()


class TestUpdateAsset:
    def test_update_returns_structured_result(self, mock_client):
        with patch.object(mock_client, "_update_record", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = True

            result = run_async(mock_client.update_asset("test-id", {"file_name": "new.mp3"}))

        assert isinstance(result, UpdateResult)
        assert result.success is True
        assert result.asset_id == "test-id"
        mock_update.assert_awaited_once()

    def test_update_rejects_invalid_category(self, mock_client):
        result = run_async(mock_client.update_asset("test-id", {"category": "bogus"}))

        assert result.success is False
        assert result.error_code == "INVALID_CATEGORY"


class TestDeleteAssets:
    def test_delete_empty_list(self, mock_client):
        result = run_async(mock_client.delete_assets([]))

        assert isinstance(result, DeleteResult)
        assert result.deleted_count == 0

    def test_delete_success(self, mock_client):
        with patch.object(mock_client, "_delete_records", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = 3

            result = run_async(mock_client.delete_assets(["a", "b", "c"]))

        assert result.deleted_count == 3
        assert result.failed_ids == []
        mock_delete.assert_awaited()


class TestQueryAssets:
    def test_query_returns_query_result(self, mock_client):
        now = datetime.now(timezone.utc).isoformat()
        records = [
            {
                "asset_id": "1",
                "file_path": "/test/song1.mp3",
                "file_name": "song1.mp3",
                "category": "music",
                "file_size": 1000,
                "file_hash": "hash1",
                "ai_tags": ["upbeat"],
                "modified_time": now,
                "created_at": now,
                "updated_at": now,
            }
        ]

        with patch.object(mock_client, "_execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = records

            result = run_async(mock_client.query_assets(category="music", limit=10))

        assert isinstance(result, QueryResult)
        assert result.error is None
        assert result.total_count == 1
        assert result.assets[0].category == "music"

    def test_query_rejects_invalid_limit(self, mock_client):
        result = run_async(mock_client.query_assets(limit=0))

        assert result.error is not None
        assert result.assets == []

    def test_query_filters_to_scope_and_cleans_stale_files(self, mock_client):
        temp_dir = tempfile.mkdtemp()
        try:
            existing_file = Path(temp_dir) / "song1.mp3"
            existing_file.write_text("ok", encoding="utf-8")
            stale_file = Path(temp_dir) / "missing.mp3"
            out_of_scope_file = Path(temp_dir).parent / "outside.mp3"

            now = datetime.now(timezone.utc).isoformat()
            records = [
                {
                    "asset_id": "keep",
                    "file_path": str(existing_file),
                    "file_name": existing_file.name,
                    "category": "music",
                    "file_size": 1000,
                    "file_hash": "hash1",
                    "ai_tags": ["upbeat"],
                    "modified_time": now,
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "asset_id": "stale",
                    "file_path": str(stale_file),
                    "file_name": stale_file.name,
                    "category": "music",
                    "file_size": 1000,
                    "file_hash": "hash2",
                    "ai_tags": ["stale"],
                    "modified_time": now,
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "asset_id": "outside",
                    "file_path": str(out_of_scope_file),
                    "file_name": out_of_scope_file.name,
                    "category": "music",
                    "file_size": 1000,
                    "file_hash": "hash3",
                    "ai_tags": ["outside"],
                    "modified_time": now,
                    "created_at": now,
                    "updated_at": now,
                },
            ]

            with patch.object(mock_client, "_execute_query", new_callable=AsyncMock) as mock_query:
                mock_query.return_value = records
                mock_client.delete_assets = AsyncMock(return_value=DeleteResult(deleted_count=1))

                result = run_async(
                    mock_client.query_assets(
                        category="music",
                        limit=10,
                        scope_folders=[temp_dir],
                        verify_on_disk=True,
                    )
                )

            assert result.error is None
            assert result.total_count == 1
            assert [asset.id for asset in result.assets] == ["keep"]
            mock_client.delete_assets.assert_awaited_once_with(["stale"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestAssetConversion:
    def test_asset_to_db_format_hashes_identity_token(self, mock_client, sample_asset):
        result = mock_client._asset_to_db_format(sample_asset)

        assert result["asset_id"] == sample_asset.id
        assert result["file_path"] == str(sample_asset.file_path)
        assert result["owner_identity"] == ""
        assert result["created_at"] == {TIMESTAMP_FIELD: int(sample_asset.created_at.timestamp() * 1_000_000)}

    def test_asset_to_db_format_uses_anonymous_identity_without_token(self, test_config, sample_asset):
        test_config.identity_token = None
        client = SpacetimeClient(test_config)

        result = client._asset_to_db_format(sample_asset)

        assert result["owner_identity"] == ""

    def test_db_record_to_asset_decodes_timestamp_products(self, mock_client):
        micros = 1_775_966_383_742_231
        record = {
            "asset_id": "asset-1",
            "file_path": "/test/music/song.mp3",
            "file_name": "song.mp3",
            "category": "music",
            "file_size": 1024,
            "file_hash": "abc123",
            "ai_tags": ["upbeat", "energetic"],
            "modified_time": [micros],
            "created_at": {TIMESTAMP_FIELD: micros},
            "updated_at": [micros],
        }

        asset = mock_client._db_record_to_asset(record)

        assert asset.modified_time == datetime.fromtimestamp(micros / 1_000_000, tz=timezone.utc)
        assert asset.created_at == datetime.fromtimestamp(micros / 1_000_000, tz=timezone.utc)
        assert asset.updated_at == datetime.fromtimestamp(micros / 1_000_000, tz=timezone.utc)


class TestSubscriptionsAndStats:
    def test_subscribe_to_changes_stores_callback_tuple(self, mock_client):
        callback = Mock()
        fake_task = Mock()
        fake_task.add_done_callback = Mock()

        def fake_create_task(coro):
            coro.close()
            return fake_task

        with patch("asyncio.create_task", side_effect=fake_create_task):
            subscription_id = run_async(mock_client.subscribe_to_changes(callback))

        assert subscription_id in mock_client._subscriptions
        assert mock_client._subscriptions[subscription_id] == (callback, None)
        fake_task.add_done_callback.assert_called_once()

    def test_unsubscribe_removes_subscription(self, mock_client):
        mock_client._subscriptions["sub-1"] = (Mock(), None)

        run_async(mock_client.unsubscribe("sub-1"))

        assert "sub-1" not in mock_client._subscriptions

    def test_get_stats_reports_connection_state(self, mock_client):
        mock_client._stats["total_inserts"] = 4
        mock_client._stats["connection_errors"] = 1

        stats = mock_client.get_stats()

        assert stats["total_inserts"] == 4
        assert stats["connection_errors"] == 1
        assert stats["connected"] is True
        assert stats["active_subscriptions"] == 0
        assert stats["connection_state"] == ConnectionState.CONNECTED.value
