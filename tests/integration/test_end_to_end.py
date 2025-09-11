"""End-to-end integration tests for FazzTV broadcasting system."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os

from fazztv.models import MediaItem
from fazztv.models.episode import Episode
from fazztv.config.settings import Settings
from fazztv.data.loader import DataLoader
from fazztv.data.cache import DataCache
from fazztv.utils import file as file_utils
from fazztv.utils.datetime import parse_date
from fazztv.utils.text import truncate_text, clean_filename, format_duration


class TestEndToEndWorkflow:
    """Test complete broadcasting workflow."""
    
    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create a temporary project directory with required structure."""
        # Create directories
        (tmp_path / "data").mkdir()
        (tmp_path / "cache").mkdir()
        (tmp_path / "logs").mkdir()
        (tmp_path / "output").mkdir()
        
        # Create sample data files
        artists_data = """[
            {
                "artist": "Test Artist 1",
                "song": "Test Song 1",
                "url": "https://youtube.com/watch?v=test1",
                "taxprompt": "Tax information 1"
            },
            {
                "artist": "Test Artist 2", 
                "song": "Test Song 2",
                "url": "https://youtube.com/watch?v=test2",
                "taxprompt": "Tax information 2"
            }
        ]"""
        
        (tmp_path / "data" / "artists.json").write_text(artists_data)
        
        return tmp_path
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_settings_initialization(self, mock_load_dotenv, temp_project_dir):
        """Test that settings can be initialized properly."""
        with patch.dict(os.environ, {
            "DATA_DIR": str(temp_project_dir / "data"),
            "CACHE_DIR": str(temp_project_dir / "cache"),
            "LOG_DIR": str(temp_project_dir / "logs"),
            "STREAM_KEY": "test_key",
            "ENABLE_CACHING": "true"
        }, clear=True):
            settings = Settings()
            
            assert settings.data_dir == temp_project_dir / "data"
            assert settings.cache_dir == temp_project_dir / "cache"
            assert settings.is_production() is True
            assert settings.enable_caching is True
            assert settings.validate() is True
    
    def test_media_item_workflow(self):
        """Test complete MediaItem creation and processing workflow."""
        # Create media item
        item = MediaItem(
            artist="Test Artist",
            song="Test Song",
            url="https://youtube.com/watch?v=test",
            taxprompt="Tax information",
            length_percent=75
        )
        
        # Test display methods
        assert item.get_display_title() == "Test Artist - Test Song"
        assert item.get_filename_safe_title() == "Test Artist - Test Song"
        
        # Test serialization
        data = item.to_dict()
        restored = MediaItem.from_dict(data)
        assert restored.artist == item.artist
        assert restored.song == item.song
        assert restored.length_percent == item.length_percent
    
    def test_episode_workflow(self):
        """Test complete Episode creation and processing workflow."""
        episode = Episode(
            title="Test Episode (Album Name) - January 15 2024",
            music_url="https://example.com/music.mp3",
            war_title="War Content",
            commentary="Episode commentary"
        )
        
        # Test extraction methods
        assert episode.get_song_name() == "Test Episode"
        assert episode.get_album_name() == "Album Name"
        
        # Test metadata
        episode.update_metadata("views", 1000)
        assert episode.get_metadata("views") == 1000
        
        # Test serialization
        data = episode.to_dict()
        restored = Episode.from_dict(data)
        assert restored.title == episode.title
        assert restored.metadata["views"] == 1000
    
    def test_file_operations_workflow(self, temp_project_dir):
        """Test file system operations workflow."""
        # Test directory creation
        test_dir = temp_project_dir / "test_workflow"
        file_utils.ensure_directory(test_dir)
        assert test_dir.exists()
        
        # Test file operations
        source_file = test_dir / "source.txt"
        source_file.write_text("test content")
        
        # Test copy
        dest_file = test_dir / "dest.txt"
        assert file_utils.copy_file(source_file, dest_file) is True
        assert dest_file.read_text() == "test content"
        
        # Test move
        moved_file = test_dir / "moved.txt"
        assert file_utils.move_file(dest_file, moved_file) is True
        assert moved_file.exists()
        assert not dest_file.exists()
        
        # Test file size
        size = file_utils.get_file_size(source_file)
        assert size == len("test content")
        formatted = file_utils.format_file_size(size)
        assert "B" in formatted
        
        # Test find files
        files = file_utils.find_files(test_dir, "*.txt")
        assert len([f for f in files if f.is_file()]) == 2
        
        # Test cleanup
        assert file_utils.safe_delete(test_dir) is True
        assert not test_dir.exists()
    
    @patch('fazztv.data.loader.DataLoader.load_json_file')
    def test_data_loading_workflow(self, mock_load_json_file, temp_project_dir):
        """Test data loading and caching workflow."""
        mock_data = {
            "artists": [
                {"artist": "Artist1", "song": "Song1"},
                {"artist": "Artist2", "song": "Song2"}
            ]
        }
        mock_load_json_file.return_value = mock_data
        
        loader = DataLoader(temp_project_dir / "data")
        data = loader.load_json_file("test.json")
        
        assert data == mock_data
        mock_load_json_file.assert_called_once()
    
    def test_cache_workflow(self, temp_project_dir):
        """Test caching workflow."""
        cache_mgr = DataCache()
        
        # Test setting cache
        test_data = {"key": "value", "number": 42}
        cache_mgr.set("test_key", test_data)
        
        # Test getting cache
        retrieved = cache_mgr.get("test_key")
        assert retrieved == test_data
        
        # Test cache exists
        assert cache_mgr.exists("test_key") is True
        assert cache_mgr.exists("nonexistent") is False
        
        # Test cache deletion
        cache_mgr.delete("test_key")
        assert cache_mgr.exists("test_key") is False
    
    def test_text_utilities_workflow(self):
        """Test text processing utilities."""
        # Test truncation
        long_text = "This is a very long text that should be truncated"
        truncated = truncate_text(long_text, 20)
        assert len(truncated) <= 23  # 20 + "..."
        
        # Test filename sanitization
        unsafe = "File:Name/With*Bad|Chars?.txt"
        safe = clean_filename(unsafe)
        assert "/" not in safe
        assert "*" not in safe
        assert "|" not in safe
    
    def test_datetime_utilities_workflow(self):
        """Test datetime utilities."""
        # Test duration formatting
        assert format_duration(0) == "0:00"
        assert format_duration(65) == "1:05"
        assert format_duration(3661) == "1:01:01"
        
        # Test date parsing
        date = parse_date("2024-01-15")
        assert date is not None
        assert date.year == 2024
        assert date.month == 1
        assert date.day == 15


class TestErrorHandling:
    """Test error handling across the system."""
    
    def test_media_item_validation_errors(self):
        """Test MediaItem validation error handling."""
        from fazztv.models.exceptions import ValidationError
        
        # Test invalid length_percent
        with pytest.raises(ValidationError):
            MediaItem(
                artist="Artist",
                song="Song",
                url="https://youtube.com/test",
                taxprompt="Tax",
                length_percent=150
            )
        
        # Test empty required fields
        with pytest.raises(ValidationError):
            MediaItem(
                artist="",
                song="Song",
                url="https://youtube.com/test",
                taxprompt="Tax"
            )
    
    def test_episode_validation_errors(self):
        """Test Episode validation error handling."""
        from fazztv.models.exceptions import ValidationError
        
        # Test invalid URL
        with pytest.raises(ValidationError):
            Episode(
                title="Test",
                music_url="not-a-url"
            )
        
        # Test empty title
        with pytest.raises(ValidationError):
            Episode(
                title="",
                music_url="https://example.com/music.mp3"
            )
    
    def test_file_operation_errors(self):
        """Test file operation error handling."""
        nonexistent = Path("/nonexistent/path/file.txt")
        
        # Test operations on non-existent files
        assert file_utils.get_file_size(nonexistent) == 0
        assert file_utils.safe_delete(nonexistent) is False
        assert file_utils.copy_file(nonexistent, Path("/tmp/dest.txt")) is False
        assert file_utils.move_file(nonexistent, Path("/tmp/dest.txt")) is False
    
    @patch('fazztv.config.settings.Path.mkdir')
    def test_settings_directory_creation_error(self, mock_mkdir):
        """Test handling of directory creation errors in settings."""
        mock_mkdir.side_effect = PermissionError("Cannot create directory")
        
        with patch('fazztv.config.settings.load_dotenv'):
            with pytest.raises(PermissionError):
                Settings()


class TestConcurrency:
    """Test concurrent operations and thread safety."""
    
    def test_cache_concurrent_access(self, temp_project_dir):
        """Test cache manager with concurrent access."""
        import threading
        
        cache_mgr = DataCache()
        results = []
        
        def write_cache(key, value):
            cache_mgr.set(key, value)
            results.append((key, value))
        
        # Create multiple threads writing to cache
        threads = []
        for i in range(10):
            t = threading.Thread(target=write_cache, args=(f"key_{i}", f"value_{i}"))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Verify all writes succeeded
        assert len(results) == 10
        for i in range(10):
            assert cache_mgr.get(f"key_{i}") == f"value_{i}"
    
    def test_file_operations_concurrent(self, temp_project_dir):
        """Test concurrent file operations."""
        import threading
        
        results = []
        errors = []
        
        def create_file(index):
            try:
                file_path = temp_project_dir / f"concurrent_{index}.txt"
                file_path.write_text(f"content_{index}")
                results.append(file_path)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads creating files
        threads = []
        for i in range(20):
            t = threading.Thread(target=create_file, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Verify all files were created
        assert len(errors) == 0
        assert len(results) == 20
        
        # Verify all files exist and have correct content
        for i, file_path in enumerate(results):
            assert file_path.exists()


class TestPerformance:
    """Test performance characteristics."""
    
    def test_large_file_operations(self, temp_project_dir):
        """Test operations with large files."""
        # Create a large file (10MB)
        large_file = temp_project_dir / "large.bin"
        large_data = b"0" * (10 * 1024 * 1024)
        large_file.write_bytes(large_data)
        
        # Test file size calculation
        size = file_utils.get_file_size(large_file)
        assert size == len(large_data)
        
        # Test formatted size
        formatted = file_utils.format_file_size(size)
        assert "MB" in formatted
        
        # Test copy performance
        dest = temp_project_dir / "large_copy.bin"
        assert file_utils.copy_file(large_file, dest) is True
        assert dest.stat().st_size == size
        
        # Cleanup
        file_utils.safe_delete(large_file)
        file_utils.safe_delete(dest)
    
    def test_directory_with_many_files(self, temp_project_dir):
        """Test operations on directories with many files."""
        # Create many files
        many_files_dir = temp_project_dir / "many_files"
        many_files_dir.mkdir()
        
        for i in range(100):
            (many_files_dir / f"file_{i:03d}.txt").write_text(f"content_{i}")
        
        # Test find files performance
        files = file_utils.find_files(many_files_dir, "*.txt")
        assert len([f for f in files if f.is_file()]) == 100
        
        # Test directory size calculation
        total_size = file_utils.get_directory_size(many_files_dir)
        assert total_size > 0
        
        # Test cleanup
        deleted = file_utils.cleanup_old_files(many_files_dir, days_old=1, pattern="*.txt")
        assert deleted == 0  # Files are too new
    
    def test_cache_performance(self, temp_project_dir):
        """Test cache performance with many entries."""
        cache_mgr = DataCache()
        
        # Write many cache entries
        for i in range(100):
            cache_mgr.set(f"key_{i}", {"index": i, "data": f"value_{i}" * 100})
        
        # Read all entries
        for i in range(100):
            data = cache_mgr.get(f"key_{i}")
            assert data["index"] == i
        
        # Clear all cache
        cache_mgr.clear()
        
        # Verify cache is empty
        for i in range(100):
            assert cache_mgr.exists(f"key_{i}") is False