"""Unit tests for main module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import argparse
from pathlib import Path

from fazztv.main import FazzTVApplication, create_parser, main
from fazztv.models import MediaItem, Episode
from fazztv.config.settings import Settings


class TestFazzTVApplication:
    """Test the FazzTV application class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.log_file = "test.log"
        settings.log_max_size = "10MB"
        settings.log_level = "INFO"
        settings.openrouter_api_key = "test-key"
        settings.search_limit = 5
        settings.base_resolution = "1280x720"
        settings.fade_length = 10
        settings.marquee_duration = 100
        settings.scroll_speed = 100
        settings.enable_logo = True
        settings.rtmp_url = "rtmp://test.server/live"
        settings.test_run = False
        return settings

    @pytest.fixture
    def app(self, mock_settings):
        """Create application instance with mocks."""
        with patch('fazztv.main.print_banner'), \
             patch('fazztv.main.logger'), \
             patch('fazztv.main.OpenRouterClient'), \
             patch('fazztv.main.YouTubeSearchClient'), \
             patch('fazztv.main.MediaSerializer'), \
             patch('fazztv.main.RTMPBroadcaster'):
            app = FazzTVApplication(mock_settings)
            return app

    def test_initialization(self, mock_settings):
        """Test application initialization."""
        with patch('fazztv.main.print_banner') as mock_banner, \
             patch('fazztv.main.logger') as mock_logger, \
             patch('fazztv.main.OpenRouterClient') as mock_api, \
             patch('fazztv.main.YouTubeSearchClient') as mock_yt, \
             patch('fazztv.main.MediaSerializer') as mock_serializer, \
             patch('fazztv.main.RTMPBroadcaster') as mock_broadcaster:

            app = FazzTVApplication(mock_settings)

            mock_banner.assert_called_once_with('full')
            mock_api.assert_called_once_with(mock_settings.openrouter_api_key)
            mock_yt.assert_called_once_with(mock_settings.search_limit)
            mock_broadcaster.assert_called_once_with(rtmp_url=mock_settings.rtmp_url)

    def test_create_media_item_success(self, app):
        """Test successful media item creation."""
        app.youtube_client.search_music_video = Mock(return_value=("http://test.url", "Test Song"))
        app.api_client = Mock()
        app.api_client.chat = Mock(return_value="Test tax info")

        with patch('fazztv.main.MediaItem') as mock_media_item_class:
            mock_media_item = Mock(spec=MediaItem)
            mock_media_item_class.return_value = mock_media_item

            result = app.create_media_item("Test Artist", 20)

            assert result == mock_media_item
            app.youtube_client.search_music_video.assert_called_once_with("Test Artist")

    def test_create_media_item_no_video(self, app):
        """Test media item creation when no video is found."""
        app.youtube_client.search_music_video = Mock(return_value=None)
        result = app.create_media_item("Unknown Artist")
        assert result is None


class TestCreateParser:
    """Test command line argument parsing."""

    def test_create_parser_default(self):
        """Test default argument parsing."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.mode == 'fazzio'
        assert not args.test

    def test_create_parser_ftv_mode(self):
        """Test ftv mode argument."""
        parser = create_parser()
        args = parser.parse_args(['--mode', 'ftv'])
        assert args.mode == 'ftv'

    def test_create_parser_test_flag(self):
        """Test test flag."""
        parser = create_parser()
        args = parser.parse_args(['--test'])
        assert args.test is True


class TestMainFunction:
    """Test the main entry point function."""

    def test_main_success(self):
        """Test successful main execution."""
        with patch('fazztv.main.create_parser') as mock_parse, \
             patch('fazztv.main.Settings') as mock_settings_class, \
             patch('fazztv.main.FazzTVApplication') as mock_app_class:

            mock_parser = Mock()
            mock_args = Mock()
            mock_args.mode = 'fazzio'
            mock_args.test = False
            mock_parser.parse_args.return_value = mock_args
            mock_parse.return_value = mock_parser

            mock_settings = Mock()
            mock_settings_class.return_value = mock_settings

            mock_app = Mock()
            mock_app_class.return_value = mock_app

            result = main()

            assert result == 0
            mock_app.run.assert_called_once_with(mode='fazzio')

    def test_main_keyboard_interrupt(self):
        """Test main with keyboard interrupt."""
        with patch('fazztv.main.create_parser') as mock_parse, \
             patch('fazztv.main.Settings') as mock_settings_class, \
             patch('fazztv.main.FazzTVApplication') as mock_app_class, \
             patch('fazztv.main.logger') as mock_logger:

            mock_parser = Mock()
            mock_args = Mock()
            mock_args.mode = 'fazzio'
            mock_args.test = False
            mock_parser.parse_args.return_value = mock_args
            mock_parse.return_value = mock_parser

            mock_app = Mock()
            mock_app.run.side_effect = KeyboardInterrupt()
            mock_app_class.return_value = mock_app

            result = main()

            assert result == 0
            mock_logger.info.assert_called_with("Application interrupted by user")
