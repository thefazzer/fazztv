"""Comprehensive unit tests for madonna.py module."""

import os
import sys
import json
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import subprocess
from datetime import datetime, date

# We need to mock the imports that don't exist
sys.modules['fazztv.serializer'] = MagicMock()
sys.modules['fazztv.broadcaster'] = MagicMock()

import fazztv.madonna as madonna


class TestMadonnaConfiguration:
    """Test configuration and constants."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        assert madonna.SEARCH_LIMIT == 5
        assert madonna.BASE_RES == "640x360"
        assert madonna.FADE_LENGTH == 3
        assert madonna.MARQUEE_DURATION == 86400
        assert madonna.SCROLL_SPEED == 65
        assert madonna.ELAPSED_TUNE_SECONDS == 60
        assert madonna.DEFAULT_VIDEO == "madonna-rotator.mp4"
        assert madonna.DEV_MODE is True
    
    def test_paths_configuration(self):
        """Test path configurations."""
        assert madonna.TEMP_DIR == "/tmp/fazztv"
        assert madonna.DATA_FILE.endswith("madonna_data.json")
        assert madonna.LOG_FILE == "madonna_broadcast.log"


class TestMediaItemCreation:
    """Test MediaItem creation and management."""
    
    @patch('fazztv.madonna.load_ftv_shows')
    def test_load_media_items(self, mock_load_shows):
        """Test loading media items from JSON."""
        mock_load_shows.return_value = [
            {
                "artist": "Test Artist",
                "song": "Test Song",
                "url": "https://youtube.com/test",
                "taxprompt": "Test prompt"
            }
        ]
        
        items = madonna.load_media_items()
        assert len(items) == 1
        assert items[0].artist == "Test Artist"
        assert items[0].song == "Test Song"
    
    @patch('builtins.open', new_callable=mock_open, read_data='[{"artist": "Test"}]')
    def test_load_ftv_shows(self, mock_file):
        """Test loading FTV shows from JSON file."""
        shows = madonna.load_ftv_shows()
        assert len(shows) == 1
        assert shows[0]["artist"] == "Test"
    
    @patch('os.path.exists')
    def test_load_ftv_shows_file_not_exists(self, mock_exists):
        """Test loading FTV shows when file doesn't exist."""
        mock_exists.return_value = False
        shows = madonna.load_ftv_shows()
        assert shows == []


class TestOpenRouterIntegration:
    """Test OpenRouter API integration."""
    
    @patch('requests.post')
    def test_get_marquee_from_openrouter_success(self, mock_post):
        """Test successful marquee generation from OpenRouter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Test marquee text'
                }
            }]
        }
        mock_post.return_value = mock_response
        
        result = madonna.get_marquee_from_openrouter("Test prompt")
        assert result == "Test marquee text"
    
    @patch('requests.post')
    def test_get_marquee_from_openrouter_failure(self, mock_post):
        """Test failed marquee generation from OpenRouter."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        result = madonna.get_marquee_from_openrouter("Test prompt")
        assert result == ""
    
    @patch('requests.post')
    def test_get_marquee_from_openrouter_exception(self, mock_post):
        """Test exception handling in OpenRouter call."""
        mock_post.side_effect = Exception("Network error")
        
        result = madonna.get_marquee_from_openrouter("Test prompt")
        assert result == ""


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_get_guid_with_env(self):
        """Test getting GUID from environment."""
        with patch.dict(os.environ, {'FAZZTV_GUID': 'test-guid'}):
            assert madonna.get_guid() == 'test-guid'
    
    def test_get_guid_default(self):
        """Test getting default GUID."""
        with patch.dict(os.environ, {}, clear=True):
            assert madonna.get_guid() == madonna.DEFAULT_GUID
    
    def test_detect_format(self):
        """Test format detection from URL."""
        # YouTube URL
        assert madonna.detect_format("https://youtube.com/watch?v=test") == "bestvideo+bestaudio/best"
        assert madonna.detect_format("https://youtu.be/test") == "bestvideo+bestaudio/best"
        
        # Other URLs
        assert madonna.detect_format("https://example.com/video.mp4") == "best"
    
    def test_should_download_new_media(self):
        """Test logic for determining if new media should be downloaded."""
        # Should download initially
        assert madonna.should_download_new_media(None, None) is True
        
        # Should download after 2 hours
        old_time = datetime.now().timestamp() - 7300  # More than 2 hours
        assert madonna.should_download_new_media(old_time, "test.mp4") is True
        
        # Should not download if recent and file exists
        recent_time = datetime.now().timestamp() - 3600  # 1 hour ago
        with patch('os.path.exists', return_value=True):
            assert madonna.should_download_new_media(recent_time, "test.mp4") is False
    
    @patch('os.makedirs')
    def test_ensure_temp_dir(self, mock_makedirs):
        """Test ensuring temp directory exists."""
        with patch('os.path.exists', return_value=False):
            madonna.ensure_temp_dir()
            mock_makedirs.assert_called_once_with(madonna.TEMP_DIR)
    
    def test_cleanup_old_files(self):
        """Test cleanup of old temporary files."""
        with patch('os.listdir', return_value=['old.mp4', 'new.mp4']):
            with patch('os.path.getmtime', side_effect=[100, 200]):
                with patch('os.remove') as mock_remove:
                    with patch('time.time', return_value=7300):  # Current time
                        madonna.cleanup_old_files()
                        # Should remove the old file (mtime=100, more than 2 hours old)
                        mock_remove.assert_called_once()


class TestMediaProcessing:
    """Test media processing functions."""
    
    @patch('subprocess.run')
    def test_download_media_success(self, mock_run):
        """Test successful media download."""
        mock_run.return_value = Mock(returncode=0)
        
        result = madonna.download_media("https://youtube.com/test", "/tmp/test.mp4")
        assert result == "/tmp/test.mp4"
    
    @patch('subprocess.run')
    def test_download_media_failure(self, mock_run):
        """Test failed media download."""
        mock_run.return_value = Mock(returncode=1)
        
        result = madonna.download_media("https://youtube.com/test", "/tmp/test.mp4")
        assert result is None
    
    @patch('subprocess.run')
    def test_create_final_video_success(self, mock_run):
        """Test successful final video creation."""
        mock_run.return_value = Mock(returncode=0, stdout=b'Duration: 00:01:00')
        
        with patch('os.path.exists', return_value=True):
            result = madonna.create_final_video(
                "/tmp/input.mp4",
                "/tmp/output.mp4",
                "Test Marquee",
                30
            )
            assert result == "/tmp/output.mp4"
    
    @patch('subprocess.run')
    def test_get_video_dimensions(self, mock_run):
        """Test getting video dimensions."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=b'640\n360\n'
        )
        
        width, height = madonna.get_video_dimensions("/tmp/video.mp4")
        assert width == 640
        assert height == 360
    
    @patch('subprocess.run')
    def test_get_video_duration(self, mock_run):
        """Test getting video duration."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=b'60.5'
        )
        
        duration = madonna.get_video_duration("/tmp/video.mp4")
        assert duration == 60.5


class TestBroadcasting:
    """Test broadcasting functions."""
    
    @patch('subprocess.run')
    def test_broadcast_video_success(self, mock_run):
        """Test successful video broadcast."""
        mock_run.return_value = Mock(returncode=0)
        
        with patch('os.path.exists', return_value=True):
            result = madonna.broadcast_video("/tmp/video.mp4", "rtmp://test")
            assert result is True
    
    @patch('subprocess.run')
    def test_broadcast_video_failure(self, mock_run):
        """Test failed video broadcast."""
        mock_run.return_value = Mock(returncode=1)
        
        with patch('os.path.exists', return_value=True):
            result = madonna.broadcast_video("/tmp/video.mp4", "rtmp://test")
            assert result is False
    
    def test_broadcast_video_file_not_exists(self):
        """Test broadcasting when file doesn't exist."""
        with patch('os.path.exists', return_value=False):
            result = madonna.broadcast_video("/tmp/nonexistent.mp4", "rtmp://test")
            assert result is False


class TestMainExecution:
    """Test main execution flow."""
    
    @patch('fazztv.madonna.load_media_items')
    @patch('fazztv.madonna.MediaSerializer')
    @patch('fazztv.madonna.RTMPBroadcaster')
    @patch('os.getenv')
    def test_main_no_stream_key(self, mock_getenv, mock_broadcaster, mock_serializer, mock_load):
        """Test main execution without stream key."""
        mock_getenv.return_value = None
        
        with pytest.raises(SystemExit):
            madonna.main()
    
    @patch('fazztv.madonna.load_media_items')
    @patch('fazztv.madonna.MediaSerializer')
    @patch('fazztv.madonna.RTMPBroadcaster')
    @patch('os.getenv')
    def test_main_no_media_items(self, mock_getenv, mock_broadcaster, mock_serializer, mock_load):
        """Test main execution with no media items."""
        mock_getenv.return_value = "test-key"
        mock_load.return_value = []
        
        with pytest.raises(SystemExit):
            madonna.main()
    
    @patch('fazztv.madonna.parse_arguments')
    def test_parse_arguments(self, mock_parse):
        """Test argument parsing."""
        mock_args = Mock()
        mock_args.dev = True
        mock_args.limit = 10
        mock_args.shuffle = True
        mock_parse.return_value = mock_args
        
        args = madonna.parse_arguments()
        assert args.dev is True
        assert args.limit == 10
        assert args.shuffle is True


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_format_duration(self):
        """Test duration formatting."""
        # Test various duration formats
        assert madonna.format_duration(60) == "00:01:00"
        assert madonna.format_duration(3661) == "01:01:01"
        assert madonna.format_duration(90.5) == "00:01:30"
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert madonna.sanitize_filename("Test File.mp4") == "Test_File.mp4"
        assert madonna.sanitize_filename("Test/File\\Name.mp4") == "Test_File_Name.mp4"
        assert madonna.sanitize_filename("Test:File*Name?.mp4") == "Test_File_Name_.mp4"
    
    def test_get_cache_path(self):
        """Test getting cache path for media."""
        path = madonna.get_cache_path("Artist", "Song")
        assert path.startswith(madonna.TEMP_DIR)
        assert "Artist" in path
        assert "Song" in path
        assert path.endswith(".mp4")
    
    @patch('uuid.uuid4')
    def test_generate_session_id(self, mock_uuid):
        """Test session ID generation."""
        mock_uuid.return_value = Mock(hex="test123")
        session_id = madonna.generate_session_id()
        assert session_id == "test123"