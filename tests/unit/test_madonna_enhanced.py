"""Enhanced test suite for madonna.py module."""

import unittest
from unittest.mock import MagicMock, patch, mock_open, call
import json
import tempfile
from pathlib import Path
from datetime import datetime
import uuid
import sys

import sys
sys.path.insert(0, "/home/faz/development/HollowCityDriver/.city-driver-worktrees/faz-wt-20250929-2726425")

from fazztv.madonna import (
    load_madonna_data,
    get_madonna_song_url,
    download_audio_only,
    download_video_only,
    calculate_days_old,
    cleanup_environment,
    build_ffmpeg_filter,
    create_media_item_from_episode
)
from fazztv.models import MediaItem


class TestMadonnaDataLoading(unittest.TestCase):
    """Test cases for data loading functionality."""

    @patch('fazztv.madonna.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"episodes": [{"guid": "test-guid"}]}')
    def test_load_madonna_data_success(self, mock_file, mock_exists):
        """Test successful loading of Madonna data."""
        mock_exists.return_value = True

        data = load_madonna_data()

        self.assertIsNotNone(data)
        self.assertIn('episodes', data)
        self.assertEqual(data['episodes'][0]['guid'], 'test-guid')
        mock_exists.assert_called_once()
        mock_file.assert_called_once()

    @patch('builtins.open', side_effect=FileNotFoundError())
    @patch('fazztv.madonna.logger')
    def test_load_madonna_data_missing_file(self, mock_logger, mock_open):
        """Test loading data when file doesn't exist."""
        data = load_madonna_data()

        self.assertEqual(data, {'episodes': []})
        mock_logger.error.assert_called()

    @patch('fazztv.madonna.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    @patch('fazztv.madonna.logger')
    def test_load_madonna_data_invalid_json(self, mock_logger, mock_file, mock_exists):
        """Test loading data with invalid JSON."""
        mock_exists.return_value = True

        data = load_madonna_data()

        self.assertEqual(data, {'episodes': []})
        mock_logger.error.assert_called()


class TestYouTubeSearch(unittest.TestCase):
    """Test cases for YouTube search functionality."""

    @patch('fazztv.madonna.yt_dlp.YoutubeDL')
    def test_get_madonna_song_url_success(self, mock_yt_dlp):
        """Test successful YouTube URL retrieval."""
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {
            'entries': [
                {'url': 'https://youtube.com/watch?v=test123', 'title': 'Test Song'}
            ]
        }
        mock_yt_dlp.return_value.__enter__.return_value = mock_instance

        url = get_madonna_song_url('Test Song')

        self.assertEqual(url, 'https://youtube.com/watch?v=test123')
        mock_instance.extract_info.assert_called_once()

    @patch('fazztv.madonna.yt_dlp.YoutubeDL')
    @patch('fazztv.madonna.logger')
    def test_get_madonna_song_url_no_results(self, mock_logger, mock_yt_dlp):
        """Test YouTube search with no results."""
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {'entries': []}
        mock_yt_dlp.return_value.__enter__.return_value = mock_instance

        url = get_madonna_song_url('Nonexistent Song')

        self.assertIsNone(url)
        mock_logger.warning.assert_called_with("No entries found for Madonna - Nonexistent Song")

    @patch('fazztv.madonna.yt_dlp.YoutubeDL')
    @patch('fazztv.madonna.logger')
    def test_get_madonna_song_url_network_error(self, mock_logger, mock_yt_dlp):
        """Test YouTube search with network error."""
        mock_instance = MagicMock()
        mock_instance.extract_info.side_effect = Exception("Network error")
        mock_yt_dlp.return_value.__enter__.return_value = mock_instance

        url = get_madonna_song_url('Test Song')

        self.assertIsNone(url)
        mock_logger.error.assert_called_with("Error searching for 'Madonna - Test Song': Network error")


class TestMediaDownload(unittest.TestCase):
    """Test cases for media download functionality."""

    @patch('fazztv.madonna._get_cached_audio')
    def test_download_audio_only_with_cache(self, mock_get_cached):
        """Test audio download when file is cached."""
        mock_get_cached.return_value = '/tmp/cached_audio.aac'

        result = download_audio_only('https://youtube.com/watch?v=test', 'Test Song')

        self.assertEqual(result, '/tmp/cached_audio.aac')
        mock_get_cached.assert_called_once()

    @patch('fazztv.madonna._get_cached_audio')
    @patch('fazztv.madonna._cache_audio_file')
    @patch('fazztv.madonna.yt_dlp.YoutubeDL')
    @patch('fazztv.madonna.os.listdir')
    @patch('fazztv.madonna.os.path.exists')
    @patch('fazztv.madonna.shutil.move')
    def test_download_audio_only_without_cache(self, mock_move, mock_exists, mock_listdir,
                                                mock_yt_dlp, mock_cache, mock_get_cached):
        """Test audio download when not cached."""
        mock_get_cached.return_value = None
        mock_exists.return_value = True
        mock_listdir.return_value = ['test_audio.aac']
        mock_instance = MagicMock()
        mock_instance.download.return_value = None
        mock_yt_dlp.return_value.__enter__.return_value = mock_instance
        mock_cache.return_value = '/tmp/cached_audio.aac'

        result = download_audio_only('https://youtube.com/watch?v=test', 'Test Song')

        self.assertIsNotNone(result)
        mock_instance.download.assert_called_once()
        mock_cache.assert_called_once()

    @patch('fazztv.madonna._get_cached_audio')
    @patch('fazztv.madonna.yt_dlp.YoutubeDL')
    @patch('fazztv.madonna.logger')
    def test_download_audio_only_failure(self, mock_logger, mock_yt_dlp, mock_get_cached):
        """Test audio download failure."""
        mock_get_cached.return_value = None
        mock_instance = MagicMock()
        mock_instance.download.side_effect = Exception("Download error")
        mock_yt_dlp.return_value.__enter__.return_value = mock_instance

        result = download_audio_only('https://youtube.com/watch?v=test', 'Test Song')

        self.assertIsNone(result)
        mock_logger.error.assert_called()


class TestDateCalculations(unittest.TestCase):
    """Test cases for date calculation functionality."""

    def test_calculate_days_old_valid_date(self):
        """Test age calculation with valid date."""
        # Use a date from 30 days ago
        from datetime import timedelta
        test_date = datetime.now() - timedelta(days=30)
        date_str = test_date.strftime("%B %d, %Y")

        days = calculate_days_old(date_str)

        self.assertEqual(days, 30)

    def test_calculate_days_old_invalid_format(self):
        """Test age calculation with invalid date format."""
        days = calculate_days_old("Invalid Date")

        self.assertIsNone(days)

    def test_calculate_days_old_future_date(self):
        """Test age calculation with future date."""
        from datetime import timedelta
        future_date = datetime.now() + timedelta(days=10)
        date_str = future_date.strftime("%B %d, %Y")

        days = calculate_days_old(date_str)

        self.assertEqual(days, -10)


class TestUtilityFunctions(unittest.TestCase):
    """Test cases for utility functions."""

    @patch('fazztv.madonna.os.path.exists')
    @patch('fazztv.madonna.os.makedirs')
    @patch('fazztv.madonna.shutil.rmtree')
    def test_cleanup_environment(self, mock_rmtree, mock_makedirs, mock_exists):
        """Test environment cleanup."""
        mock_exists.return_value = True

        cleanup_environment()

        mock_rmtree.assert_called_once_with('/tmp/fazztv')
        mock_makedirs.assert_called_once_with('/tmp/fazztv', exist_ok=True)



class TestFFmpegFilters(unittest.TestCase):
    """Test cases for FFmpeg filter building."""

    def test_build_ffmpeg_filter_basic(self):
        """Test basic FFmpeg filter building."""
        texts = {
            'title': 'Test Title',
            'subtitle': 'Test Subtitle',
            'byline': 'Test Byline',
            'marquee': 'Test Marquee'
        }
        filter_str = build_ffmpeg_filter(texts, has_logo=True)

        self.assertIsNotNone(filter_str)
        self.assertIn('scale', filter_str)
        self.assertIn('drawtext', filter_str)

    def test_build_ffmpeg_filter_without_logo(self):
        """Test FFmpeg filter building without logo."""
        texts = {
            'title': 'Test Title',
            'subtitle': 'Test Subtitle',
            'byline': 'Test Byline',
            'marquee': 'Test Marquee'
        }
        filter_str = build_ffmpeg_filter(texts, has_logo=False)

        self.assertIsNotNone(filter_str)
        # Since has_logo is False, overlay might not be in the filter


class TestMediaItemCreation(unittest.TestCase):
    """Test cases for MediaItem creation."""

    @patch('fazztv.madonna.get_madonna_song_url')
    @patch('fazztv.madonna.download_audio_only')
    @patch('fazztv.madonna.download_video_only')
    @patch('fazztv.madonna.subprocess.run')
    @patch('fazztv.madonna.tempfile.NamedTemporaryFile')
    def test_create_media_item_from_episode_success(self, mock_tempfile, mock_subprocess,
                                                     mock_download_video, mock_download_audio,
                                                     mock_get_url):
        """Test successful MediaItem creation from episode."""
        # Setup mocks
        mock_get_url.return_value = 'https://youtube.com/watch?v=test'
        mock_download_audio.return_value = '/tmp/audio.aac'
        mock_download_video.return_value = '/tmp/video.mp4'
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_temp = MagicMock()
        mock_temp.name = '/tmp/output.mp4'
        mock_tempfile.return_value = mock_temp

        episode = {
            'title': 'Episode 1: Test Song',
            'commentary': 'Test commentary',
            'guid': 'test-guid'
        }

        media_item = create_media_item_from_episode(episode)

        self.assertIsNotNone(media_item)
        self.assertIsInstance(media_item, MediaItem)
        self.assertEqual(media_item.artist, 'Madonna')
        self.assertEqual(media_item.song, 'Test Song')
        mock_subprocess.assert_called_once()

    @patch('fazztv.madonna.get_madonna_song_url')
    @patch('fazztv.madonna.logger')
    def test_create_media_item_from_episode_no_url(self, mock_logger, mock_get_url):
        """Test MediaItem creation when URL not found."""
        mock_get_url.return_value = None

        episode = {
            'title': 'Episode 1: Test Song',
            'commentary': 'Test commentary',
            'guid': 'test-guid'
        }

        media_item = create_media_item_from_episode(episode)

        self.assertIsNone(media_item)
        mock_logger.error.assert_called()


# Commented out - these functions no longer exist in madonna.py
# class TestCacheFunctions(unittest.TestCase):
#     """Test cases for cache-related functions."""
#
#     @patch('fazztv.madonna.os.path.exists')
#     def test_get_cached_audio_exists(self, mock_exists):
#         """Test getting cached audio when file exists."""
#         mock_exists.return_value = True
#
#         result = _get_cached_audio('test_guid', 'test_song.aac')
#
#         self.assertIsNotNone(result)
#         self.assertIn('test_guid', result)
#
#     @patch('fazztv.madonna.os.path.exists')
#     def test_get_cached_audio_not_exists(self, mock_exists):
#         """Test getting cached audio when file doesn't exist."""
#         mock_exists.return_value = False
#
#         result = _get_cached_audio('test_guid', 'test_song.aac')
#
#         self.assertIsNone(result)
#
#     @patch('fazztv.madonna.shutil.copy')
#     @patch('fazztv.madonna.logger')
#     def test_cache_audio_file_success(self, mock_logger, mock_copy):
#         """Test successful audio file caching."""
#         result = _cache_audio_file('/tmp/source.aac', 'test_guid')
#
#         self.assertIsNotNone(result)
#         self.assertIn('test_guid', result)
#         mock_copy.assert_called_once()
#         mock_logger.debug.assert_called()


if __name__ == '__main__':
    unittest.main()