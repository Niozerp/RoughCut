"""Unit tests for MediaPoolItem data model."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from roughcut.backend.media.models import MediaPoolItem, MediaType


class TestMediaType:
    """Tests for MediaType enum."""
    
    def test_video_enum_value(self):
        """Test VIDEO enum has correct value."""
        assert MediaType.VIDEO.value == "video", f"Expected 'video', got {MediaType.VIDEO.value}"
    
    def test_audio_enum_value(self):
        """Test AUDIO enum has correct value."""
        assert MediaType.AUDIO.value == "audio", f"Expected 'audio', got {MediaType.AUDIO.value}"
    
    def test_still_image_enum_value(self):
        """Test STILL_IMAGE enum has correct value."""
        assert MediaType.STILL_IMAGE.value == "still_image", f"Expected 'still_image', got {MediaType.STILL_IMAGE.value}"


class TestMediaPoolItem:
    """Tests for MediaPoolItem dataclass."""
    
    def test_create_valid_media_pool_item(self):
        """Test creating a valid MediaPoolItem."""
        item = MediaPoolItem(
            clip_name="interview_take1",
            file_path="/path/to/clip.mov",
            duration_seconds=2280.5,
            clip_id="resolve_clip_001"
        )
        
        assert item.clip_name == "interview_take1", f"Expected clip_name 'interview_take1', got '{item.clip_name}'"
        assert item.file_path == "/path/to/clip.mov", f"Expected file_path '/path/to/clip.mov', got '{item.file_path}'"
        assert item.duration_seconds == 2280.5, f"Expected duration 2280.5, got {item.duration_seconds}"
        assert item.clip_id == "resolve_clip_001", f"Expected clip_id 'resolve_clip_001', got '{item.clip_id}'"
        assert item.media_type == MediaType.VIDEO, f"Expected media_type VIDEO, got {item.media_type}"
        assert item.thumbnail_path is None, f"Expected thumbnail_path None, got {item.thumbnail_path}"
    
    def test_create_with_optional_thumbnail(self):
        """Test creating with thumbnail path."""
        item = MediaPoolItem(
            clip_name="broll_shot",
            file_path="/path/to/broll.mov",
            duration_seconds=45.0,
            clip_id="resolve_clip_002",
            thumbnail_path="/path/to/thumb.jpg"
        )
        
        assert item.thumbnail_path == "/path/to/thumb.jpg", f"Expected thumbnail_path '/path/to/thumb.jpg', got '{item.thumbnail_path}'"
    
    def test_create_with_explicit_media_type(self):
        """Test creating with explicit media type."""
        item = MediaPoolItem(
            clip_name="voiceover",
            file_path="/path/to/audio.wav",
            duration_seconds=120.0,
            clip_id="resolve_clip_003",
            media_type=MediaType.AUDIO
        )
        
        assert item.media_type == MediaType.AUDIO, f"Expected media_type AUDIO, got {item.media_type}"
    
    def test_validation_empty_clip_name(self):
        """Test validation rejects empty clip_name."""
        try:
            MediaPoolItem(
                clip_name="",
                file_path="/path/to/clip.mov",
                duration_seconds=100.0,
                clip_id="id001"
            )
            assert False, "Should have raised ValueError for empty clip_name"
        except ValueError as e:
            assert "clip_name is required" in str(e), f"Expected 'clip_name is required' in error, got: {e}"
    
    def test_validation_whitespace_clip_name(self):
        """Test validation rejects whitespace-only clip_name."""
        try:
            MediaPoolItem(
                clip_name="   ",
                file_path="/path/to/clip.mov",
                duration_seconds=100.0,
                clip_id="id001"
            )
            assert False, "Should have raised ValueError for whitespace-only clip_name"
        except ValueError as e:
            assert "clip_name is required" in str(e), f"Expected 'clip_name is required' in error, got: {e}"
    
    def test_validation_empty_file_path(self):
        """Test validation rejects empty file_path."""
        try:
            MediaPoolItem(
                clip_name="valid_name",
                file_path="",
                duration_seconds=100.0,
                clip_id="id001"
            )
            assert False, "Should have raised ValueError for empty file_path"
        except ValueError as e:
            assert "file_path is required" in str(e), f"Expected 'file_path is required' in error, got: {e}"
    
    def test_validation_zero_duration(self):
        """Test validation rejects zero duration."""
        try:
            MediaPoolItem(
                clip_name="valid_name",
                file_path="/path/to/clip.mov",
                duration_seconds=0,
                clip_id="id001"
            )
            assert False, "Should have raised ValueError for zero duration"
        except ValueError as e:
            assert "duration_seconds must be > 0" in str(e), f"Expected 'duration_seconds must be > 0' in error, got: {e}"
    
    def test_validation_negative_duration(self):
        """Test validation rejects negative duration."""
        try:
            MediaPoolItem(
                clip_name="valid_name",
                file_path="/path/to/clip.mov",
                duration_seconds=-10.0,
                clip_id="id001"
            )
            assert False, "Should have raised ValueError for negative duration"
        except ValueError as e:
            assert "duration_seconds must be > 0" in str(e), f"Expected 'duration_seconds must be > 0' in error, got: {e}"
    
    def test_validation_invalid_media_type(self):
        """Test validation rejects invalid media_type."""
        try:
            MediaPoolItem(
                clip_name="valid_name",
                file_path="/path/to/clip.mov",
                duration_seconds=100.0,
                clip_id="id001",
                media_type="video"  # String instead of enum
            )
            assert False, "Should have raised ValueError for invalid media_type"
        except ValueError as e:
            assert "media_type must be MediaType enum" in str(e), f"Expected 'media_type must be MediaType enum' in error, got: {e}"


class TestIsTranscribable:
    """Tests for is_transcribable() method."""
    
    def test_video_is_transcribable(self):
        """Test VIDEO type is transcribable."""
        item = MediaPoolItem(
            clip_name="video_clip",
            file_path="/path/to/clip.mov",
            duration_seconds=100.0,
            clip_id="id001",
            media_type=MediaType.VIDEO
        )
        assert item.is_transcribable() is True, "VIDEO type should be transcribable"
    
    def test_audio_is_not_transcribable(self):
        """Test AUDIO type is not transcribable."""
        item = MediaPoolItem(
            clip_name="audio_clip",
            file_path="/path/to/audio.wav",
            duration_seconds=100.0,
            clip_id="id002",
            media_type=MediaType.AUDIO
        )
        assert item.is_transcribable() is False, "AUDIO type should not be transcribable"
    
    def test_still_image_is_not_transcribable(self):
        """Test STILL_IMAGE type is not transcribable."""
        item = MediaPoolItem(
            clip_name="image",
            file_path="/path/to/image.png",
            duration_seconds=1.0,
            clip_id="id003",
            media_type=MediaType.STILL_IMAGE
        )
        assert item.is_transcribable() is False, "STILL_IMAGE type should not be transcribable"


class TestToDict:
    """Tests for to_dict() method."""
    
    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        item = MediaPoolItem(
            clip_name="test_clip",
            file_path="/path/to/test.mov",
            duration_seconds=123.45,
            clip_id="clip_abc123",
            media_type=MediaType.VIDEO,
            thumbnail_path="/path/to/thumb.jpg"
        )
        
        result = item.to_dict()
        
        assert result['clip_name'] == "test_clip", f"Expected clip_name 'test_clip', got '{result['clip_name']}'"
        assert result['file_path'] == "/path/to/test.mov", f"Expected file_path '/path/to/test.mov', got '{result['file_path']}'"
        assert result['duration_seconds'] == 123.45, f"Expected duration 123.45, got {result['duration_seconds']}"
        assert result['clip_id'] == "clip_abc123", f"Expected clip_id 'clip_abc123', got '{result['clip_id']}'"
        assert result['media_type'] == "video", f"Expected media_type 'video', got '{result['media_type']}'"
        assert result['thumbnail_path'] == "/path/to/thumb.jpg", f"Expected thumbnail_path '/path/to/thumb.jpg', got '{result['thumbnail_path']}'"
        assert result['is_transcribable'] is True, f"Expected is_transcribable True, got {result['is_transcribable']}"
    
    def test_to_dict_without_thumbnail(self):
        """Test serialization without thumbnail."""
        item = MediaPoolItem(
            clip_name="no_thumb",
            file_path="/path/to/clip.mov",
            duration_seconds=60.0,
            clip_id="id001"
        )
        
        result = item.to_dict()
        
        assert result['thumbnail_path'] is None, f"Expected thumbnail_path None, got {result['thumbnail_path']}"
        assert result['is_transcribable'] is True, f"Expected is_transcribable True, got {result['is_transcribable']}"


class TestFromResolveClip:
    """Tests for from_resolve_clip() factory method."""
    
    def test_from_resolve_video_clip(self):
        """Test creating from Resolve video clip data."""
        clip_data = {
            'name': 'interview_take1',
            'path': '/projects/interview.mov',
            'duration': 2280.5,
            'id': 'resolve_001',
            'type': 'video'
        }
        
        item = MediaPoolItem.from_resolve_clip(clip_data)
        
        assert item.clip_name == "interview_take1", f"Expected clip_name 'interview_take1', got '{item.clip_name}'"
        assert item.file_path == "/projects/interview.mov", f"Expected file_path '/projects/interview.mov', got '{item.file_path}'"
        assert item.duration_seconds == 2280.5, f"Expected duration 2280.5, got {item.duration_seconds}"
        assert item.clip_id == "resolve_001", f"Expected clip_id 'resolve_001', got '{item.clip_id}'"
        assert item.media_type == MediaType.VIDEO, f"Expected media_type VIDEO, got {item.media_type}"
    
    def test_from_resolve_audio_clip(self):
        """Test creating from Resolve audio clip data."""
        clip_data = {
            'name': 'voiceover_take1',
            'path': '/audio/voice.wav',
            'duration': 120.0,
            'id': 'resolve_002',
            'type': 'audio'
        }
        
        item = MediaPoolItem.from_resolve_clip(clip_data)
        
        assert item.media_type == MediaType.AUDIO, f"Expected media_type AUDIO, got {item.media_type}"
    
    def test_from_resolve_video_with_type_variations(self):
        """Test video type detection with variations."""
        test_cases = [
            ('video', MediaType.VIDEO),
            ('VideoClip', MediaType.VIDEO),
            ('VIDEO', MediaType.VIDEO),
            ('my_video_file', MediaType.VIDEO),
        ]
        
        for type_str, expected_enum in test_cases:
            clip_data = {
                'name': 'test',
                'path': '/test.mov',
                'duration': 100.0,
                'id': 'test_id',
                'type': type_str
            }
            
            item = MediaPoolItem.from_resolve_clip(clip_data)
            assert item.media_type == expected_enum, f"Failed for type: {type_str}"
    
    def test_from_resolve_default_to_still_image(self):
        """Test unknown type defaults to STILL_IMAGE."""
        clip_data = {
            'name': 'unknown',
            'path': '/unknown.xyz',
            'duration': 1.0,
            'id': 'resolve_003',
            'type': 'fusion_clip'
        }
        
        item = MediaPoolItem.from_resolve_clip(clip_data)
        
        assert item.media_type == MediaType.STILL_IMAGE, f"Expected media_type STILL_IMAGE, got {item.media_type}"
    
    def test_from_resolve_with_thumbnail(self):
        """Test creating with thumbnail from Resolve."""
        clip_data = {
            'name': 'with_thumb',
            'path': '/test.mov',
            'duration': 60.0,
            'id': 'resolve_004',
            'type': 'video',
            'thumbnail': '/thumbs/test.jpg'
        }
        
        item = MediaPoolItem.from_resolve_clip(clip_data)
        
        assert item.thumbnail_path == "/thumbs/test.jpg", f"Expected thumbnail_path '/thumbs/test.jpg', got '{item.thumbnail_path}'"
    
    def test_from_resolve_missing_optional_fields(self):
        """Test creating with minimal data (missing optional fields)."""
        clip_data = {
            'name': 'minimal',
            'path': '/minimal.mov',
            'duration': 30.0,
            'id': 'resolve_005'
            # type and thumbnail missing
        }
        
        item = MediaPoolItem.from_resolve_clip(clip_data)
        
        assert item.clip_name == "minimal", f"Expected clip_name 'minimal', got '{item.clip_name}'"
        assert item.media_type == MediaType.STILL_IMAGE, f"Expected media_type STILL_IMAGE (default), got {item.media_type}"
        assert item.thumbnail_path is None, f"Expected thumbnail_path None, got {item.thumbnail_path}"


def run_all_tests():
    """Run all tests and report results."""
    test_classes = [
        TestMediaType(),
        TestMediaPoolItem(),
        TestIsTranscribable(),
        TestToDict(),
        TestFromResolveClip()
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        methods = [m for m in dir(test_class) if m.startswith('test_')]
        
        for method_name in methods:
            test_name = f"{class_name}.{method_name}"
            try:
                method = getattr(test_class, method_name)
                method()
                print(f"✓ {test_name}")
                passed += 1
            except AssertionError as e:
                print(f"✗ {test_name}: {e}")
                failed += 1
                errors.append((test_name, str(e)))
            except Exception as e:
                print(f"✗ {test_name}: ERROR - {e}")
                failed += 1
                errors.append((test_name, str(e)))
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
