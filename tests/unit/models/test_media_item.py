"""Unit tests for MediaItem model."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fazztv.models.media_item import MediaItem
from fazztv.models.exceptions import ValidationError


class TestMediaItemCreation:
    """Test MediaItem creation and validation."""
    
    def test_valid_media_item_creation(self):
        """Test creating a valid MediaItem."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=abc123",
            taxprompt="Tax information"
        )
        
        assert item.artist == "Test Artist"
        assert item.song == "Test Song"
        assert item.url == "https://youtube.com/watch?v=abc123"
        assert item.taxprompt == "Tax information"
        assert item.length_percent == 100
        assert item.duration is None
        assert item.serialized is None
    
    def test_media_item_with_all_parameters(self):
        """Test creating MediaItem with all parameters."""
        item = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com/watch?v=xyz",
            taxprompt="Tax info",
            length_percent=75,
            duration=180,
            serialized=Path("/tmp/test.mp4")
        )
        
        assert item.length_percent == 75
        assert item.duration == 180
        assert isinstance(item.serialized, Path)
        assert str(item.serialized) == "/tmp/test.mp4"
    
    def test_serialized_string_converted_to_path(self):
        """Test that serialized string is converted to Path."""
        item = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com/watch?v=xyz",
            taxprompt="Tax info",
            serialized="/tmp/video.mp4"
        )
        
        assert isinstance(item.serialized, Path)
        assert str(item.serialized) == "/tmp/video.mp4"


class TestMediaItemValidation:
    """Test MediaItem validation rules."""
    
    def test_invalid_length_percent_too_low(self):
        """Test validation fails for length_percent < 1."""
        with pytest.raises(ValidationError, match="length_percent must be between 1 and 100"):
            MediaItem(
                artist="Artist",
                song="Song",
                url="https://youtube.com",
                taxprompt="Tax",
                length_percent=0
            )
    
    def test_invalid_length_percent_too_high(self):
        """Test validation fails for length_percent > 100."""
        with pytest.raises(ValidationError, match="length_percent must be between 1 and 100"):
            MediaItem(
                artist="Artist",
                song="Song",
                url="https://youtube.com",
                taxprompt="Tax",
                length_percent=101
            )
    
    def test_invalid_length_percent_negative(self):
        """Test validation fails for negative length_percent."""
        with pytest.raises(ValidationError, match="length_percent must be between 1 and 100"):
            MediaItem(
                artist="Artist",
                song="Song",
                url="https://youtube.com",
                taxprompt="Tax",
                length_percent=-50
            )
    
    def test_empty_artist_validation(self):
        """Test validation fails for empty artist."""
        with pytest.raises(ValidationError, match="Artist name is required"):
            MediaItem(
                artist="",
                song="Song",
                url="https://youtube.com",
                taxprompt="Tax"
            )
    
    def test_empty_song_validation(self):
        """Test validation fails for empty song."""
        with pytest.raises(ValidationError, match="Song title is required"):
            MediaItem(
                artist="Artist",
                song="",
                url="https://youtube.com",
                taxprompt="Tax"
            )
    
    def test_empty_url_validation(self):
        """Test validation fails for empty URL."""
        with pytest.raises(ValidationError, match="URL is required"):
            MediaItem(
                artist="Artist",
                song="Song",
                url="",
                taxprompt="Tax"
            )
    
    def test_boundary_length_percent_values(self):
        """Test boundary values for length_percent."""
        # Test minimum valid value
        item1 = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com",
            taxprompt="Tax",
            length_percent=1
        )
        assert item1.length_percent == 1
        
        # Test maximum valid value
        item2 = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com",
            taxprompt="Tax",
            length_percent=100
        )
        assert item2.length_percent == 100


class TestMediaItemMethods:
    """Test MediaItem methods."""
    
    def test_is_serialized_no_file(self):
        """Test is_serialized when no serialized file."""
        item = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com",
            taxprompt="Tax"
        )
        assert not item.is_serialized()
    
    def test_is_serialized_with_nonexistent_file(self):
        """Test is_serialized with non-existent file path."""
        item = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com",
            taxprompt="Tax",
            serialized=Path("/nonexistent/file.mp4")
        )
        assert not item.is_serialized()
    
    def test_is_serialized_with_existing_file(self, tmp_path):
        """Test is_serialized with existing file."""
        # Create a temporary file
        test_file = tmp_path / "test.mp4"
        test_file.touch()
        
        item = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com",
            taxprompt="Tax",
            serialized=test_file
        )
        assert item.is_serialized()
    
    def test_get_display_title(self):
        """Test get_display_title method."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com",
            taxprompt="Tax"
        )
        assert item.get_display_title() == "Test Artist - Test Song"
    
    def test_get_filename_safe_title(self):
        """Test get_filename_safe_title method."""
        item = MediaItem(
            artist="Artist:Name",
            song="Song/Title*",
            url="https://youtube.com",
            taxprompt="Tax"
        )
        safe_title = item.get_filename_safe_title()
        assert safe_title == "Artist_Name - Song_Title_"
        assert ':' not in safe_title
        assert '/' not in safe_title
        assert '*' not in safe_title
    
    def test_get_filename_safe_title_with_special_chars(self):
        """Test filename sanitization with various special characters."""
        item = MediaItem(
            artist='Artist<>:"/\\|?*',
            song="Song. ",
            url="https://youtube.com",
            taxprompt="Tax"
        )
        safe_title = item.get_filename_safe_title()
        assert safe_title == "Artist_________ - Song"
        # Verify no invalid characters remain
        for char in '<>:"/\\|?*':
            assert char not in safe_title
    
    def test_str_method(self):
        """Test __str__ method."""
        item = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com",
            taxprompt="Tax"
        )
        assert str(item) == "Artist - Song"
    
    def test_repr_method(self):
        """Test __repr__ method."""
        item = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com/watch?v=verylongidhere12345678901234567890",
            taxprompt="Tax",
            length_percent=75
        )
        repr_str = repr(item)
        assert "MediaItem(" in repr_str
        assert "artist='Artist'" in repr_str
        assert "song='Song'" in repr_str
        assert "..." in repr_str  # URL should be truncated
        assert "length=75%" in repr_str


class TestMediaItemSerialization:
    """Test MediaItem serialization methods."""
    
    def test_to_dict(self):
        """Test converting MediaItem to dictionary."""
        item = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com",
            taxprompt="Tax",
            length_percent=80,
            duration=120,
            serialized=Path("/tmp/test.mp4")
        )
        
        data = item.to_dict()
        
        assert data["artist"] == "Artist"
        assert data["song"] == "Song"
        assert data["url"] == "https://youtube.com"
        assert data["taxprompt"] == "Tax"
        assert data["length_percent"] == 80
        assert data["duration"] == 120
        assert data["serialized"] == "/tmp/test.mp4"
    
    def test_to_dict_without_optional_fields(self):
        """Test to_dict with minimal fields."""
        item = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com",
            taxprompt="Tax"
        )
        
        data = item.to_dict()
        
        assert data["length_percent"] == 100
        assert data["duration"] is None
        assert data["serialized"] is None
    
    def test_from_dict(self):
        """Test creating MediaItem from dictionary."""
        data = {
            "artist": "Artist",
            "song": "Song",
            "url": "https://youtube.com",
            "taxprompt": "Tax",
            "length_percent": 90,
            "duration": 180,
            "serialized": "/tmp/video.mp4"
        }
        
        item = MediaItem.from_dict(data)
        
        assert item.artist == "Artist"
        assert item.song == "Song"
        assert item.url == "https://youtube.com"
        assert item.taxprompt == "Tax"
        assert item.length_percent == 90
        assert item.duration == 180
        assert isinstance(item.serialized, Path)
        assert str(item.serialized) == "/tmp/video.mp4"
    
    def test_from_dict_with_missing_fields(self):
        """Test from_dict with missing optional fields."""
        data = {
            "artist": "Artist",
            "song": "Song",
            "url": "https://youtube.com",
            "taxprompt": "Tax"
        }
        
        item = MediaItem.from_dict(data)
        
        assert item.length_percent == 100
        assert item.duration is None
        assert item.serialized is None
    
    def test_from_dict_with_empty_dict(self):
        """Test from_dict with empty dictionary raises validation error."""
        with pytest.raises(ValidationError):
            MediaItem.from_dict({})
    
    def test_roundtrip_serialization(self):
        """Test that to_dict and from_dict are inverses."""
        original = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=abc",
            taxprompt="Tax information",
            length_percent=65,
            duration=240,
            serialized=Path("/tmp/original.mp4")
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = MediaItem.from_dict(data)
        
        # Compare all fields
        assert restored.artist == original.artist
        assert restored.song == original.song
        assert restored.url == original.url
        assert restored.taxprompt == original.taxprompt
        assert restored.length_percent == original.length_percent
        assert restored.duration == original.duration
        assert str(restored.serialized) == str(original.serialized)