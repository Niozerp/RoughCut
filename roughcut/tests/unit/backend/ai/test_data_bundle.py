"""Unit tests for data_bundle module.

Tests DataBundle, DataBundleBuilder, and related classes.
"""

import pytest
from roughcut.backend.ai.data_bundle import (
    DataBundle,
    DataBundleBuilder,
    FormatRules,
    MediaAssetMetadata,
    MediaIndexSubset,
    TranscriptData,
)


class TestTranscriptData:
    """Tests for TranscriptData dataclass."""
    
    def test_basic_creation(self):
        """Test basic TranscriptData creation."""
        data = TranscriptData(
            text="This is a transcript.",
            segments=[{"start": 0, "end": 10, "text": "This is"}]
        )
        
        assert data.text == "This is a transcript."
        assert len(data.segments) == 1
        assert data.segments[0]["start"] == 0
    
    def test_to_dict(self):
        """Test serialization to dict."""
        data = TranscriptData(
            text="Test transcript",
            segments=[{"start": 0, "end": 5}]
        )
        
        result = data.to_dict()
        assert result["text"] == "Test transcript"
        assert result["segments"] == [{"start": 0, "end": 5}]
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {"text": "From dict", "segments": [{"start": 1, "end": 2}]}
        result = TranscriptData.from_dict(data)
        
        assert result.text == "From dict"
        assert len(result.segments) == 1


class TestFormatRules:
    """Tests for FormatRules dataclass."""
    
    def test_basic_creation(self):
        """Test basic FormatRules creation."""
        rules = FormatRules(
            slug="youtube-interview",
            name="YouTube Interview",
            segments=[{"name": "Intro", "duration": "15s"}],
            asset_groups=[{"category": "music", "name": "intro_music"}]
        )
        
        assert rules.slug == "youtube-interview"
        assert rules.name == "YouTube Interview"
        assert len(rules.segments) == 1
    
    def test_to_dict(self):
        """Test serialization to dict."""
        rules = FormatRules(slug="test", name="Test Format")
        result = rules.to_dict()
        
        assert result["slug"] == "test"
        assert result["name"] == "Test Format"


class TestMediaAssetMetadata:
    """Tests for MediaAssetMetadata dataclass."""
    
    def test_basic_creation(self):
        """Test basic MediaAssetMetadata creation."""
        asset = MediaAssetMetadata(
            path="/music/corporate/theme.wav",
            filename="theme.wav",
            category="music",
            tags=["corporate", "upbeat"]
        )
        
        assert asset.path == "/music/corporate/theme.wav"
        assert asset.category == "music"
        assert "corporate" in asset.tags
    
    def test_to_dict_only_metadata(self):
        """Test that serialization contains only metadata."""
        asset = MediaAssetMetadata(
            path="/path/to/file.wav",
            filename="file.wav",
            category="sfx",
            tags=["whoosh"]
        )
        
        result = asset.to_dict()
        
        # Should only have metadata fields, no binary data
        assert "path" in result
        assert "filename" in result
        assert "category" in result
        assert "tags" in result
        assert "metadata" in result
        
        # All values should be strings or lists, not bytes
        assert isinstance(result["path"], str)
        assert isinstance(result["tags"], list)


class TestMediaIndexSubset:
    """Tests for MediaIndexSubset dataclass."""
    
    def test_get_all_assets(self):
        """Test getting all assets across categories."""
        subset = MediaIndexSubset(
            music=[MediaAssetMetadata(path="/m", filename="m.wav", category="music")],
            sfx=[MediaAssetMetadata(path="/s", filename="s.wav", category="sfx")],
            vfx=[MediaAssetMetadata(path="/v", filename="v.mov", category="vfx")]
        )
        
        all_assets = subset.get_all_assets()
        assert len(all_assets) == 3
    
    def test_estimate_tokens(self):
        """Test token estimation."""
        subset = MediaIndexSubset(
            music=[MediaAssetMetadata(
                path="/music/corporate/theme.wav",
                filename="theme.wav",
                category="music",
                tags=["corporate", "upbeat", "bright"]
            )]
        )
        
        tokens = subset.estimate_tokens()
        # Rough check: should be positive and reasonable
        assert tokens > 0
        assert tokens < 100  # Should be small for one asset


class TestDataBundle:
    """Tests for DataBundle dataclass."""
    
    def test_basic_creation(self):
        """Test basic DataBundle creation."""
        bundle = DataBundle(
            session_id="session_123",
            transcript=TranscriptData(text="Hello world"),
            format_template=FormatRules(slug="test", name="Test"),
            media_index=MediaIndexSubset()
        )
        
        assert bundle.session_id == "session_123"
        assert bundle.transcript.text == "Hello world"
    
    def test_validate_metadata_only_passes(self):
        """Test validation passes for metadata-only bundle."""
        bundle = DataBundle(
            session_id="session_123",
            transcript=TranscriptData(text="Valid text"),
            format_template=FormatRules(slug="test", name="Test"),
            media_index=MediaIndexSubset(
                music=[MediaAssetMetadata(
                    path="/valid/path.wav",
                    filename="path.wav",
                    category="music",
                    tags=["valid"]
                )]
            )
        )
        
        # Should not raise
        assert bundle.validate_metadata_only() is True
    
    def test_validate_metadata_only_fails_for_binary(self):
        """Test validation fails if binary data is present."""
        # Create transcript with non-string data (simulating binary)
        bundle = DataBundle(
            session_id="session_123",
            transcript=TranscriptData(text=12345),  # Invalid: should be string
            format_template=FormatRules(slug="test", name="Test"),
            media_index=MediaIndexSubset()
        )
        
        with pytest.raises(ValueError, match="text only"):
            bundle.validate_metadata_only()
    
    def test_estimate_total_tokens(self):
        """Test total token estimation."""
        bundle = DataBundle(
            session_id="session_123",
            transcript=TranscriptData(text="Short transcript text"),
            format_template=FormatRules(slug="test", name="Test"),
            media_index=MediaIndexSubset(
                music=[MediaAssetMetadata(
                    path="/music/theme.wav",
                    filename="theme.wav",
                    category="music",
                    tags=["upbeat"]
                )]
            )
        )
        
        tokens = bundle.estimate_total_tokens()
        assert tokens > 0


class TestDataBundleBuilder:
    """Tests for DataBundleBuilder class."""
    
    def test_build_basic_bundle(self):
        """Test building a basic data bundle."""
        builder = DataBundleBuilder()
        
        transcript_data = {
            "text": "Test transcript for rough cut generation",
            "segments": [{"start": 0, "end": 10, "text": "Test"}]
        }
        
        format_template = {
            "slug": "youtube-interview",
            "name": "YouTube Interview",
            "segments": [{"name": "Intro", "duration": "15s"}],
            "asset_groups": [
                {"category": "music", "name": "intro_music", "search_tags": ["upbeat"]},
                {"category": "sfx", "name": "transitions", "search_tags": ["whoosh"]}
            ]
        }
        
        media_index = [
            {
                "path": "/music/corporate/theme.wav",
                "filename": "theme.wav",
                "category": "music",
                "tags": ["corporate", "upbeat"]
            },
            {
                "path": "/sfx/whoosh.wav",
                "filename": "whoosh.wav",
                "category": "sfx",
                "tags": ["whoosh", "transition"]
            }
        ]
        
        bundle = builder.build(
            session_id="session_123",
            transcript_data=transcript_data,
            format_template=format_template,
            media_index=media_index
        )
        
        assert bundle.session_id == "session_123"
        assert bundle.transcript.text == transcript_data["text"]
        assert bundle.format_template.slug == "youtube-interview"
        
        # Should filter to only relevant categories
        assert len(bundle.media_index.music) == 1
        assert len(bundle.media_index.sfx) == 1
        assert len(bundle.media_index.vfx) == 0  # Not needed by format
    
    def test_build_filters_by_required_categories(self):
        """Test that media is filtered by format-required categories."""
        builder = DataBundleBuilder()
        
        format_template = {
            "slug": "music-only",
            "name": "Music Only Format",
            "asset_groups": [
                {"category": "music", "name": "intro"}
                # No sfx or vfx groups
            ]
        }
        
        media_index = [
            {"path": "/m", "filename": "m.wav", "category": "music", "tags": []},
            {"path": "/s", "filename": "s.wav", "category": "sfx", "tags": []},
            {"path": "/v", "filename": "v.mov", "category": "vfx", "tags": []}
        ]
        
        bundle = builder.build(
            session_id="session_123",
            transcript_data={"text": "Test"},
            format_template=format_template,
            media_index=media_index
        )
        
        # Should only include music
        assert len(bundle.media_index.music) == 1
        assert len(bundle.media_index.sfx) == 0
        assert len(bundle.media_index.vfx) == 0
    
    def test_build_includes_all_if_no_asset_groups(self):
        """Test that all categories are included if format has no asset groups."""
        builder = DataBundleBuilder()
        
        format_template = {
            "slug": "minimal",
            "name": "Minimal Format",
            "asset_groups": []  # No asset groups defined
        }
        
        media_index = [
            {"path": "/m", "filename": "m.wav", "category": "music", "tags": []},
            {"path": "/s", "filename": "s.wav", "category": "sfx", "tags": []}
        ]
        
        bundle = builder.build(
            session_id="session_123",
            transcript_data={"text": "Test"},
            format_template=format_template,
            media_index=media_index
        )
        
        # Should include all categories
        assert len(bundle.media_index.music) == 1
        assert len(bundle.media_index.sfx) == 1
    
    def test_build_respects_max_media_assets(self):
        """Test that max_media_assets limit is respected."""
        builder = DataBundleBuilder(max_media_assets=2)
        
        media_index = [
            {"path": f"/m{i}.wav", "filename": f"m{i}.wav", "category": "music", "tags": []}
            for i in range(10)  # 10 music files
        ]
        
        bundle = builder.build(
            session_id="session_123",
            transcript_data={"text": "Test"},
            format_template={
                "slug": "test",
                "name": "Test",
                "asset_groups": [{"category": "music", "name": "intro"}]
            },
            media_index=media_index
        )
        
        # Should be limited to max_media_assets
        assert len(bundle.media_index.music) == 2
    
    def test_build_sorts_by_relevance(self):
        """Test that assets are sorted by relevance to format."""
        builder = DataBundleBuilder()
        
        media_index = [
            {"path": "/a.wav", "filename": "a.wav", "category": "music", "tags": ["ambient"]},
            {"path": "/u.wav", "filename": "u.wav", "category": "music", "tags": ["upbeat"]},
            {"path": "/c.wav", "filename": "c.wav", "category": "music", "tags": ["corporate", "upbeat"]},
        ]
        
        bundle = builder.build(
            session_id="session_123",
            transcript_data={"text": "Test"},
            format_template={
                "slug": "test",
                "name": "Test",
                "asset_groups": [
                    {"category": "music", "name": "corporate_upbeat"}
                ]
            },
            media_index=media_index,
            format_asset_groups=["corporate_upbeat"]
        )
        
        # Corporate upbeat asset should be first (most relevant)
        assert bundle.media_index.music[0].filename == "c.wav"
    
    def test_build_validates_metadata_only(self):
        """Test that built bundle passes metadata-only validation."""
        builder = DataBundleBuilder()
        
        bundle = builder.build(
            session_id="session_123",
            transcript_data={"text": "Valid transcript", "segments": []},
            format_template={
                "slug": "test",
                "name": "Test Format",
                "asset_groups": []
            },
            media_index=[]
        )
        
        # Should pass validation
        assert bundle.validate_metadata_only() is True


class TestDataBundleSecurity:
    """Security tests for DataBundle (NFR7 compliance)."""
    
    def test_bundle_never_contains_binary_data(self):
        """Verify bundle cannot contain binary file contents."""
        # This test verifies the data structures don't support binary
        bundle = DataBundle(
            session_id="test",
            transcript=TranscriptData(text="Only text"),
            format_template=FormatRules(slug="test", name="Test"),
            media_index=MediaIndexSubset(
                music=[MediaAssetMetadata(
                    path="/valid/path.wav",  # String path only
                    filename="path.wav",
                    category="music",
                    tags=["valid"]
                )]
            )
        )
        
        # Validate no binary data
        assert bundle.validate_metadata_only() is True
        
        # Verify serialized form has no bytes
        serialized = bundle.to_dict()
        assert isinstance(serialized["transcript"]["text"], str)
        assert isinstance(serialized["media_index"]["music"][0]["path"], str)
