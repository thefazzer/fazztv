"""Unit tests for the old models.py module."""

import os
import sys
import tempfile
import importlib.util
import pytest
from unittest.mock import patch, MagicMock

# Import directly from the old models.py file
spec = importlib.util.spec_from_file_location('old_models', 'fazztv/models.py')
old_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_models)
MediaItem = old_models.MediaItem


class TestOldMediaItem:
    """Test the old MediaItem class in models.py."""
    
    def test_media_item_creation_with_defaults(self):
        """Test creating a MediaItem with default values."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt"
        )
        
        assert item.artist == "Test Artist"
        assert item.song == "Test Song"
        assert item.url == "https://youtube.com/watch?v=test"
        assert item.taxprompt == "Test tax prompt"
        assert item.length_percent == 100
        assert item.duration is None
        assert item.serialized is None
        assert item.source_path is None
        assert item.metadata == {}
    
    def test_media_item_creation_with_all_params(self):
        """Test creating a MediaItem with all parameters."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt",
            length_percent=75,
            duration=120,
            serialized="/path/to/serialized.mp4",
            source_path="/path/to/source.mp4",
            metadata={"key": "value"}
        )
        
        assert item.length_percent == 75
        assert item.duration == 120
        assert item.serialized == "/path/to/serialized.mp4"
        assert item.source_path == "/path/to/source.mp4"
        assert item.metadata == {"key": "value"}
    
    def test_media_item_invalid_length_percent_too_low(self):
        """Test MediaItem validation with length_percent too low."""
        with pytest.raises(ValueError, match="length_percent must be between 1 and 100, got 0"):
            MediaItem(
                artist="Test Artist",
                song="Test Song",
                url="https://youtube.com/watch?v=test",
                taxprompt="Test tax prompt",
                length_percent=0
            )
    
    def test_media_item_invalid_length_percent_too_high(self):
        """Test MediaItem validation with length_percent too high."""
        with pytest.raises(ValueError, match="length_percent must be between 1 and 100, got 101"):
            MediaItem(
                artist="Test Artist",
                song="Test Song",
                url="https://youtube.com/watch?v=test",
                taxprompt="Test tax prompt",
                length_percent=101
            )
    
    def test_media_item_invalid_duration_negative(self):
        """Test MediaItem validation with negative duration."""
        with pytest.raises(ValueError, match="duration must be positive, got -10"):
            MediaItem(
                artist="Test Artist",
                song="Test Song",
                url="https://youtube.com/watch?v=test",
                taxprompt="Test tax prompt",
                duration=-10
            )
    
    def test_media_item_invalid_duration_zero(self):
        """Test MediaItem validation with zero duration."""
        with pytest.raises(ValueError, match="duration must be positive, got 0"):
            MediaItem(
                artist="Test Artist",
                song="Test Song",
                url="https://youtube.com/watch?v=test",
                taxprompt="Test tax prompt",
                duration=0
            )
    
    def test_is_serialized_no_path(self):
        """Test is_serialized when no serialized path is set."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt"
        )
        assert item.is_serialized() is False
    
    def test_is_serialized_path_not_exists(self):
        """Test is_serialized when path doesn't exist."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt",
            serialized="/nonexistent/path.mp4"
        )
        assert item.is_serialized() is False
    
    def test_is_serialized_path_exists(self):
        """Test is_serialized when path exists."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            item = MediaItem(
                artist="Test Artist",
                song="Test Song",
                url="https://youtube.com/watch?v=test",
                taxprompt="Test tax prompt",
                serialized=tmp_path
            )
            assert item.is_serialized() is True
        finally:
            os.unlink(tmp_path)
    
    def test_is_downloaded_no_path(self):
        """Test is_downloaded when no source path is set."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt"
        )
        assert item.is_downloaded() is False
    
    def test_is_downloaded_path_not_exists(self):
        """Test is_downloaded when path doesn't exist."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt",
            source_path="/nonexistent/source.mp4"
        )
        assert item.is_downloaded() is False
    
    def test_is_downloaded_path_exists(self):
        """Test is_downloaded when path exists."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            item = MediaItem(
                artist="Test Artist",
                song="Test Song",
                url="https://youtube.com/watch?v=test",
                taxprompt="Test tax prompt",
                source_path=tmp_path
            )
            assert item.is_downloaded() is True
        finally:
            os.unlink(tmp_path)
    
    def test_get_effective_duration_with_duration_limit(self):
        """Test get_effective_duration with duration limit."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt",
            duration=60
        )
        
        # Duration limit is less than original
        assert item.get_effective_duration(120) == 60
        
        # Duration limit is more than original
        assert item.get_effective_duration(30) == 30
    
    def test_get_effective_duration_with_length_percent(self):
        """Test get_effective_duration with length_percent."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt",
            length_percent=50
        )
        
        assert item.get_effective_duration(120) == 60
        assert item.get_effective_duration(100) == 50
    
    def test_cleanup_removes_files(self):
        """Test cleanup removes temporary files."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp1:
            serialized_path = tmp1.name
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp2:
            source_path = tmp2.name
        
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt",
            serialized=serialized_path,
            source_path=source_path
        )
        
        # Files should exist
        assert os.path.exists(serialized_path)
        assert os.path.exists(source_path)
        
        # Cleanup
        item.cleanup()
        
        # Files should be removed
        assert not os.path.exists(serialized_path)
        assert not os.path.exists(source_path)
        assert item.serialized is None
        assert item.source_path is None
    
    def test_cleanup_handles_missing_files(self):
        """Test cleanup handles missing files gracefully."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt",
            serialized="/nonexistent/file1.mp4",
            source_path="/nonexistent/file2.mp4"
        )
        
        # Should not raise an error
        item.cleanup()
        # Files don't exist so they won't be removed and attributes stay the same
        assert item.serialized == "/nonexistent/file1.mp4"
        assert item.source_path == "/nonexistent/file2.mp4"
    
    @patch('os.remove')
    def test_cleanup_handles_oserror(self, mock_remove):
        """Test cleanup handles OSError gracefully."""
        mock_remove.side_effect = OSError("Permission denied")
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            item = MediaItem(
                artist="Test Artist",
                song="Test Song",
                url="https://youtube.com/watch?v=test",
                taxprompt="Test tax prompt",
                serialized=tmp_path
            )
            
            # Should not raise an error, just log warning
            item.cleanup()
            
            # Path should still be set since removal failed
            assert item.serialized == tmp_path
        finally:
            os.unlink(tmp_path)
    
    def test_to_dict(self):
        """Test converting MediaItem to dictionary."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt",
            length_percent=75,
            duration=120,
            metadata={"key": "value"}
        )
        
        result = item.to_dict()
        
        assert result["artist"] == "Test Artist"
        assert result["song"] == "Test Song"
        assert result["url"] == "https://youtube.com/watch?v=test"
        assert result["taxprompt"] == "Test tax prompt"
        assert result["length_percent"] == 75
        assert result["duration"] == 120
        assert result["is_serialized"] is False
        assert result["is_downloaded"] is False
        assert result["metadata"] == {"key": "value"}
    
    def test_to_dict_truncates_long_taxprompt(self):
        """Test to_dict truncates long taxprompt."""
        long_prompt = "x" * 150
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt=long_prompt
        )
        
        result = item.to_dict()
        assert result["taxprompt"] == "x" * 100 + "..."
    
    def test_str_representation(self):
        """Test string representation of MediaItem."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt"
        )
        
        assert str(item) == "Test Artist - Test Song"
    
    def test_repr_representation(self):
        """Test detailed string representation of MediaItem."""
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test tax prompt",
            length_percent=75
        )
        
        repr_str = repr(item)
        assert "MediaItem" in repr_str
        assert "artist='Test Artist'" in repr_str
        assert "song='Test Song'" in repr_str
        assert "length_percent=75" in repr_str
        assert "serialized=False" in repr_str