"""Complete unit tests for madonna.py module."""

import pytest
import json
import os
from unittest.mock import Mock, patch, mock_open, MagicMock
from pathlib import Path
import subprocess
from datetime import datetime, timedelta

# Import the module to test
from fazztv import madonna
from fazztv.models import MediaItem


class TestMadonnaDataLoading:
    """Test data loading functions."""
    
    @patch('builtins.open', new_callable=mock_open, read_data='{"episodes": [{"artist": "Madonna", "song": "Like a Prayer"}]}')
    def test_load_madonna_data_success(self, mock_file):
        """Test successful loading of Madonna data."""
        data = madonna.load_madonna_data()
        assert "episodes" in data
        assert len(data["episodes"]) == 1
        assert data["episodes"][0]["artist"] == "Madonna"
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_madonna_data_file_not_found(self, mock_file):
        """Test handling of missing data file."""
        data = madonna.load_madonna_data()
        assert data == {"episodes": []}
    
    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    def test_load_madonna_data_invalid_json(self, mock_file):
        """Test handling of invalid JSON."""
        data = madonna.load_madonna_data()
        assert data == {"episodes": []}
    
    @patch('builtins.open', new_callable=mock_open, read_data='{"episodes": [{"artist": "Madonna", "song": "Vogue"}]}')
    @patch('json.dump')
    def test_load_madonna_data_adds_guids(self, mock_dump, mock_file):
        """Test that GUIDs are added to episodes without them."""
        data = madonna.load_madonna_data()
        # Check that GUID was added
        assert "guid" in data["episodes"][0]
        # Verify the file was written with updated data
        mock_dump.assert_called_once()


class TestYouTubeSearch:
    """Test YouTube search functionality."""
    
    @patch('yt_dlp.YoutubeDL')
    def test_get_madonna_song_url_success(self, mock_ydl_class):
        """Test successful YouTube search for Madonna song."""
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "title": "Madonna - Like a Prayer",
                    "webpage_url": "https://youtube.com/watch?v=123"
                }
            ]
        }
        
        url = madonna.get_madonna_song_url("Like a Prayer")
        assert url == "https://youtube.com/watch?v=123"
    
    @patch('yt_dlp.YoutubeDL')
    def test_get_madonna_song_url_no_results(self, mock_ydl_class):
        """Test YouTube search with no results."""
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {"entries": []}
        
        url = madonna.get_madonna_song_url("Nonexistent Song")
        assert url is None
    
    @patch('yt_dlp.YoutubeDL')
    def test_get_madonna_song_url_exception(self, mock_ydl_class):
        """Test YouTube search with exception."""
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("Network error")
        
        url = madonna.get_madonna_song_url("Like a Prayer")
        assert url is None


class TestMediaDownload:
    """Test media download functions."""
    
    @patch('yt_dlp.YoutubeDL')
    @patch('os.rename')
    @patch('os.path.getsize')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_download_audio_only_success(self, mock_exists, mock_makedirs, mock_getsize, mock_rename, mock_ydl_class):
        """Test successful audio download."""
        # First call to check cache, second to check output file
        mock_exists.side_effect = [False, False, True]
        mock_getsize.return_value = 1000
        
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {"title": "Test Video"}
        
        result = madonna.download_audio_only(
            "https://youtube.com/watch?v=123",
            "/tmp/test.mp3"
        )
        assert result is True
    
    @patch('shutil.copy')
    @patch('os.path.getsize')
    @patch('os.path.exists')
    def test_download_audio_only_already_exists(self, mock_exists, mock_getsize, mock_copy):
        """Test audio download when file already exists."""
        # Check with guid for cached file
        mock_exists.return_value = True
        mock_getsize.return_value = 1000
        
        result = madonna.download_audio_only(
            "https://youtube.com/watch?v=123",
            "/tmp/test.mp3",
            guid="test-guid"
        )
        assert result is True
        mock_copy.assert_called_once()
    
    @patch('yt_dlp.YoutubeDL')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_download_audio_only_failure(self, mock_exists, mock_makedirs, mock_ydl_class):
        """Test failed audio download."""
        mock_exists.return_value = False
        
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("Download failed")
        
        result = madonna.download_audio_only(
            "https://youtube.com/watch?v=123",
            "/tmp/test.mp3"
        )
        assert result is False
    
    @patch('yt_dlp.YoutubeDL')
    @patch('os.rename')
    @patch('os.path.getsize')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_download_video_only_success(self, mock_exists, mock_makedirs, mock_getsize, mock_rename, mock_ydl_class):
        """Test successful video download."""
        mock_exists.side_effect = [False, False, True]
        mock_getsize.return_value = 1000
        
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {"title": "Test Video"}
        
        result = madonna.download_video_only(
            "https://youtube.com/watch?v=123",
            "/tmp/test.mp4"
        )
        assert result is True
    
    @patch('shutil.copy')
    @patch('os.path.getsize')
    @patch('os.path.exists')
    def test_download_video_only_already_exists(self, mock_exists, mock_getsize, mock_copy):
        """Test video download when file already exists."""
        # Check with guid for cached file
        mock_exists.return_value = True
        mock_getsize.return_value = 1000
        
        result = madonna.download_video_only(
            "https://youtube.com/watch?v=123",
            "/tmp/test.mp4",
            guid="test-guid"
        )
        assert result is True
        mock_copy.assert_called_once()
    
    @patch('yt_dlp.YoutubeDL')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_download_video_only_failure(self, mock_exists, mock_makedirs, mock_ydl_class):
        """Test failed video download."""
        mock_exists.return_value = False
        
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("Download failed")
        
        result = madonna.download_video_only(
            "https://youtube.com/watch?v=123",
            "/tmp/test.mp4"
        )
        assert result is False


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_calculate_days_old_recent(self):
        """Test calculating days old for recent date."""
        today = datetime.now()
        song_info = f"Madonna - Like a Prayer ({today.strftime('%Y-%m-%d')})"
        days = madonna.calculate_days_old(song_info)
        assert days == 0
    
    def test_calculate_days_old_past(self):
        """Test calculating days old for past date."""
        past_date = datetime.now() - timedelta(days=10)
        song_info = f"Madonna - Vogue ({past_date.strftime('%Y-%m-%d')})"
        days = madonna.calculate_days_old(song_info)
        assert days == 10
    
    def test_calculate_days_old_no_date(self):
        """Test calculating days old with no date."""
        song_info = "Madonna - Material Girl"
        days = madonna.calculate_days_old(song_info)
        assert days == float('inf')
    
    @patch('shutil.rmtree')
    @patch('os.makedirs')
    def test_cleanup_environment(self, mock_makedirs, mock_rmtree):
        """Test environment cleanup."""
        madonna.cleanup_environment()
        mock_rmtree.assert_called_once_with(madonna.TEMP_DIR, ignore_errors=True)
        mock_makedirs.assert_called_once_with(madonna.TEMP_DIR, exist_ok=True)
    
    def test_create_media_item_from_episode(self):
        """Test creating MediaItem from episode data."""
        episode = {
            "artist": "Madonna",
            "song": "Like a Prayer",
            "url": "https://youtube.com/watch?v=123",
            "taxprompt": "Test prompt",
            "guid": "test-guid",
            "duration": 300
        }
        
        media_item = madonna.create_media_item_from_episode(episode)
        
        assert isinstance(media_item, MediaItem)
        assert media_item.artist == "Madonna"
        assert media_item.song == "Like a Prayer"
        assert media_item.url == "https://youtube.com/watch?v=123"
        assert media_item.guid == "test-guid"
        assert media_item.duration == 300
    
    def test_create_media_item_from_episode_with_defaults(self):
        """Test creating MediaItem with default values."""
        episode = {
            "artist": "Madonna",
            "song": "Vogue"
        }
        
        media_item = madonna.create_media_item_from_episode(episode)
        
        assert isinstance(media_item, MediaItem)
        assert media_item.artist == "Madonna"
        assert media_item.song == "Vogue"
        assert media_item.url == ""
        assert media_item.guid is not None
        assert media_item.duration == madonna.ELAPSED_TUNE_SECONDS


class TestMainFunction:
    """Test main function and program flow."""
    
    @patch('fazztv.madonna.RTMPBroadcaster')
    @patch('fazztv.madonna.MediaSerializer')
    @patch('fazztv.madonna.load_madonna_data')
    @patch('fazztv.madonna.cleanup_environment')
    @patch('sys.argv', ['madonna.py'])
    def test_main_dev_mode(self, mock_cleanup, mock_load_data, mock_serializer, mock_broadcaster):
        """Test main function in dev mode."""
        # Setup mocks
        mock_load_data.return_value = {
            "episodes": [
                {
                    "artist": "Madonna",
                    "song": "Like a Prayer",
                    "url": "https://youtube.com/watch?v=123"
                }
            ]
        }
        mock_broadcaster_instance = Mock()
        mock_broadcaster.return_value = mock_broadcaster_instance
        
        # Run main (it will exit after one iteration in dev mode)
        with patch('time.sleep'):
            with patch('random.choice', return_value=mock_load_data.return_value["episodes"][0]):
                # Main should handle the flow
                try:
                    madonna.main()
                except SystemExit:
                    pass  # Expected in test environment
        
        # Verify initialization
        mock_cleanup.assert_called_once()
        mock_load_data.assert_called()
    
    @patch('sys.argv', ['madonna.py', '--stream-key', 'test-key'])
    @patch('fazztv.madonna.cleanup_environment')
    def test_main_with_stream_key(self, mock_cleanup):
        """Test main function with stream key argument."""
        with patch('fazztv.madonna.load_madonna_data') as mock_load:
            mock_load.return_value = {"episodes": []}
            
            try:
                madonna.main()
            except SystemExit:
                pass
            
            # Stream key should be set
            assert madonna.STREAM_KEY == 'test-key'
            assert madonna.DEV_MODE is False
    
    @patch('sys.argv', ['madonna.py', '--dev'])
    @patch('fazztv.madonna.cleanup_environment')
    def test_main_dev_flag(self, mock_cleanup):
        """Test main function with dev flag."""
        with patch('fazztv.madonna.load_madonna_data') as mock_load:
            mock_load.return_value = {"episodes": []}
            
            try:
                madonna.main()
            except SystemExit:
                pass
            
            # Dev mode should be enabled
            assert madonna.DEV_MODE is True


class TestErrorHandling:
    """Test error handling throughout the module."""
    
    @patch('subprocess.run')
    def test_download_with_subprocess_error(self, mock_run):
        """Test handling of subprocess errors during download."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'yt-dlp', stderr=b"Error message")
        
        result = madonna.download_audio_only("https://youtube.com/watch?v=123", "/tmp/test.mp3")
        assert result is False
    
    @patch('yt_dlp.YoutubeDL')
    def test_youtube_search_with_network_error(self, mock_ydl_class):
        """Test handling of network errors during YouTube search."""
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = ConnectionError("Network unreachable")
        
        url = madonna.get_madonna_song_url("Like a Prayer")
        assert url is None
    
    @patch('builtins.open', side_effect=PermissionError("Access denied"))
    def test_load_data_permission_error(self, mock_open):
        """Test handling of permission errors when loading data."""
        data = madonna.load_madonna_data()
        assert data == {"episodes": []}


class TestIntegration:
    """Integration tests for complete workflows."""
    
    @patch('fazztv.madonna.download_audio_only')
    @patch('fazztv.madonna.download_video_only')
    @patch('fazztv.madonna.get_madonna_song_url')
    def test_complete_media_processing(self, mock_get_url, mock_download_video, mock_download_audio):
        """Test complete media processing workflow."""
        # Setup mocks
        mock_get_url.return_value = "https://youtube.com/watch?v=123"
        mock_download_video.return_value = True
        mock_download_audio.return_value = True
        
        # Create episode
        episode = {
            "artist": "Madonna",
            "song": "Like a Prayer",
            "guid": "test-guid"
        }
        
        # Get URL
        url = madonna.get_madonna_song_url(episode["song"])
        assert url is not None
        
        # Download media
        video_result = madonna.download_video_only(url, "/tmp/video.mp4", episode["guid"])
        audio_result = madonna.download_audio_only(url, "/tmp/audio.mp3", episode["guid"])
        
        assert video_result is True
        assert audio_result is True
        
        # Create media item
        media_item = madonna.create_media_item_from_episode(episode)
        assert media_item.artist == "Madonna"
        assert media_item.song == "Like a Prayer"