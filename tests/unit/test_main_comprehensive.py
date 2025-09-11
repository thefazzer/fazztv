"""Comprehensive unit tests for main.py module."""

import sys
import argparse
from unittest.mock import Mock, patch, MagicMock, call
import pytest
from loguru import logger

# Mock the imports that don't exist in main.py
sys.modules['fazztv.serializer'] = MagicMock()
sys.modules['fazztv.broadcaster'] = MagicMock()

from fazztv.main import FazzTVApplication


class TestFazzTVApplication:
    """Test the FazzTVApplication class."""
    
    @patch('fazztv.main.Settings')
    def test_initialization_with_default_settings(self, mock_settings):
        """Test app initialization with default settings."""
        mock_settings_instance = Mock()
        mock_settings.return_value = mock_settings_instance
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            with patch.object(FazzTVApplication, '_initialize_services'):
                app = FazzTVApplication()
                
                assert app.settings == mock_settings_instance
                app._setup_logging.assert_called_once()
                app._initialize_services.assert_called_once()
    
    def test_initialization_with_custom_settings(self):
        """Test app initialization with custom settings."""
        custom_settings = Mock()
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            with patch.object(FazzTVApplication, '_initialize_services'):
                app = FazzTVApplication(settings=custom_settings)
                
                assert app.settings == custom_settings
    
    @patch('fazztv.main.logger')
    def test_setup_logging(self, mock_logger):
        """Test logging setup."""
        settings = Mock()
        settings.log_file = "test.log"
        settings.log_max_size = "10MB"
        settings.log_level = "DEBUG"
        
        with patch.object(FazzTVApplication, '_initialize_services'):
            app = FazzTVApplication(settings=settings)
            
            mock_logger.add.assert_called_once_with(
                "test.log",
                rotation="10MB",
                level="DEBUG"
            )
    
    @patch('fazztv.main.OpenRouterClient')
    @patch('fazztv.main.YouTubeSearchClient')
    @patch('fazztv.main.MediaSerializer')
    @patch('fazztv.main.RTMPBroadcaster')
    def test_initialize_services(self, mock_broadcaster, mock_serializer,
                                  mock_youtube, mock_openrouter):
        """Test service initialization."""
        settings = Mock()
        settings.openrouter_api_key = "test-key"
        settings.search_limit = 5
        settings.rtmp_url = "rtmp://test"
        settings.stream_key = "stream-key"
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            app = FazzTVApplication(settings=settings)
            
            mock_openrouter.assert_called_once_with("test-key")
            mock_youtube.assert_called_once_with(5)
            mock_serializer.assert_called_once()
            mock_broadcaster.assert_called_once()
    
    def test_load_media_items_from_file(self):
        """Test loading media items from file."""
        settings = Mock()
        
        mock_data = [
            {
                "artist": "Artist1",
                "song": "Song1",
                "url": "https://youtube.com/1",
                "taxprompt": "Tax1"
            },
            {
                "artist": "Artist2",
                "song": "Song2",
                "url": "https://youtube.com/2",
                "taxprompt": "Tax2"
            }
        ]
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            with patch.object(FazzTVApplication, '_initialize_services'):
                with patch('fazztv.main.FTV_SHOWS', mock_data):
                    app = FazzTVApplication(settings=settings)
                    items = app.load_media_items()
                    
                    assert len(items) == 2
                    assert items[0].artist == "Artist1"
                    assert items[1].artist == "Artist2"
    
    def test_search_and_create_media_items(self):
        """Test searching and creating media items from artists."""
        settings = Mock()
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            with patch.object(FazzTVApplication, '_initialize_services'):
                app = FazzTVApplication(settings=settings)
                
                # Mock the YouTube client
                app.youtube_client = Mock()
                app.youtube_client.search_videos.return_value = [
                    {"url": "https://youtube.com/1"},
                    {"url": "https://youtube.com/2"}
                ]
                
                # Mock the API client for tax prompts
                app.api_client = Mock()
                app.api_client.generate_tax_prompt.return_value = "Generated tax prompt"
                
                items = app.search_and_create_media_items(["Artist1", "Artist2"])
                
                assert len(items) > 0
                app.youtube_client.search_videos.assert_called()
                app.api_client.generate_tax_prompt.assert_called()
    
    def test_process_media_items(self):
        """Test processing media items."""
        settings = Mock()
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            with patch.object(FazzTVApplication, '_initialize_services'):
                app = FazzTVApplication(settings=settings)
                
                # Mock the serializer
                app.serializer = Mock()
                app.serializer.serialize_collection.return_value = ["item1", "item2"]
                
                media_items = [Mock(), Mock()]
                result = app.process_media_items(media_items)
                
                app.serializer.serialize_collection.assert_called_once_with(media_items)
                assert result == ["item1", "item2"]
    
    def test_broadcast_media_items(self):
        """Test broadcasting media items."""
        settings = Mock()
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            with patch.object(FazzTVApplication, '_initialize_services'):
                app = FazzTVApplication(settings=settings)
                
                # Mock the broadcaster
                app.broadcaster = Mock()
                app.broadcaster.broadcast_collection.return_value = [
                    (Mock(), True),
                    (Mock(), False)
                ]
                
                media_items = [Mock(), Mock()]
                results = app.broadcast_media_items(media_items)
                
                app.broadcaster.broadcast_collection.assert_called_once_with(media_items)
                assert len(results) == 2
                assert results[0][1] is True
                assert results[1][1] is False
    
    @patch('fazztv.main.random.shuffle')
    def test_run_with_shuffle(self, mock_shuffle):
        """Test running the application with shuffle enabled."""
        settings = Mock()
        settings.shuffle = True
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            with patch.object(FazzTVApplication, '_initialize_services'):
                with patch.object(FazzTVApplication, 'load_media_items') as mock_load:
                    with patch.object(FazzTVApplication, 'process_media_items') as mock_process:
                        with patch.object(FazzTVApplication, 'broadcast_media_items') as mock_broadcast:
                            
                            mock_load.return_value = [Mock(), Mock()]
                            mock_process.return_value = [Mock(), Mock()]
                            
                            app = FazzTVApplication(settings=settings)
                            app.run(shuffle=True)
                            
                            mock_shuffle.assert_called_once()
                            mock_load.assert_called_once()
                            mock_process.assert_called_once()
                            mock_broadcast.assert_called_once()
    
    def test_run_with_limit(self):
        """Test running the application with item limit."""
        settings = Mock()
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            with patch.object(FazzTVApplication, '_initialize_services'):
                with patch.object(FazzTVApplication, 'load_media_items') as mock_load:
                    with patch.object(FazzTVApplication, 'process_media_items') as mock_process:
                        with patch.object(FazzTVApplication, 'broadcast_media_items'):
                            
                            # Return 5 items but limit to 2
                            mock_load.return_value = [Mock() for _ in range(5)]
                            
                            app = FazzTVApplication(settings=settings)
                            app.run(limit=2)
                            
                            # Should only process 2 items
                            called_items = mock_process.call_args[0][0]
                            assert len(called_items) == 2
    
    def test_run_with_no_media_items(self):
        """Test running when no media items are available."""
        settings = Mock()
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            with patch.object(FazzTVApplication, '_initialize_services'):
                with patch.object(FazzTVApplication, 'load_media_items') as mock_load:
                    
                    mock_load.return_value = []
                    
                    app = FazzTVApplication(settings=settings)
                    
                    with pytest.raises(SystemExit):
                        app.run()
    
    def test_run_continuous_mode(self):
        """Test running in continuous mode."""
        settings = Mock()
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            with patch.object(FazzTVApplication, '_initialize_services'):
                with patch.object(FazzTVApplication, 'load_media_items') as mock_load:
                    with patch.object(FazzTVApplication, 'process_media_items'):
                        with patch.object(FazzTVApplication, 'broadcast_media_items'):
                            
                            mock_load.return_value = [Mock()]
                            
                            app = FazzTVApplication(settings=settings)
                            
                            # Mock to run only twice then stop
                            with patch('time.sleep') as mock_sleep:
                                mock_sleep.side_effect = [None, KeyboardInterrupt]
                                
                                app.run(continuous=True)
                                
                                assert mock_load.call_count >= 1
    
    def test_cleanup(self):
        """Test cleanup method."""
        settings = Mock()
        
        with patch.object(FazzTVApplication, '_setup_logging'):
            with patch.object(FazzTVApplication, '_initialize_services'):
                app = FazzTVApplication(settings=settings)
                
                # Create mock services with cleanup methods
                app.serializer = Mock()
                app.broadcaster = Mock()
                app.api_client = Mock()
                app.youtube_client = Mock()
                
                app.cleanup()
                
                app.serializer.cleanup.assert_called_once()
                app.broadcaster.cleanup.assert_called_once()


class TestMainFunction:
    """Test the main entry point function."""
    
    @patch('sys.argv', ['fazztv', '--dev', '--limit', '5'])
    @patch('fazztv.main.FazzTVApplication')
    def test_main_with_arguments(self, mock_app_class):
        """Test main function with command line arguments."""
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        
        from fazztv.main import main
        
        with patch('fazztv.main.parse_arguments') as mock_parse:
            mock_args = Mock()
            mock_args.dev = True
            mock_args.limit = 5
            mock_args.shuffle = False
            mock_args.continuous = False
            mock_parse.return_value = mock_args
            
            main()
            
            mock_app.run.assert_called_once_with(
                shuffle=False,
                limit=5,
                continuous=False
            )
    
    @patch('fazztv.main.FazzTVApplication')
    def test_main_handles_keyboard_interrupt(self, mock_app_class):
        """Test main function handles keyboard interrupt."""
        mock_app = Mock()
        mock_app.run.side_effect = KeyboardInterrupt
        mock_app_class.return_value = mock_app
        
        from fazztv.main import main
        
        with patch('fazztv.main.parse_arguments') as mock_parse:
            mock_args = Mock()
            mock_parse.return_value = mock_args
            
            # Should exit cleanly without raising
            main()
            
            mock_app.cleanup.assert_called_once()
    
    @patch('fazztv.main.FazzTVApplication')
    def test_main_handles_exception(self, mock_app_class):
        """Test main function handles general exceptions."""
        mock_app = Mock()
        mock_app.run.side_effect = Exception("Test error")
        mock_app_class.return_value = mock_app
        
        from fazztv.main import main
        
        with patch('fazztv.main.parse_arguments') as mock_parse:
            mock_args = Mock()
            mock_parse.return_value = mock_args
            
            with pytest.raises(SystemExit):
                main()
            
            mock_app.cleanup.assert_called_once()


class TestArgumentParsing:
    """Test command line argument parsing."""
    
    def test_parse_arguments_defaults(self):
        """Test default argument values."""
        from fazztv.main import parse_arguments
        
        with patch('sys.argv', ['fazztv']):
            args = parse_arguments()
            
            assert args.dev is False
            assert args.limit is None
            assert args.shuffle is False
            assert args.continuous is False
    
    def test_parse_arguments_all_options(self):
        """Test parsing all command line options."""
        from fazztv.main import parse_arguments
        
        with patch('sys.argv', ['fazztv', '--dev', '--limit', '10', 
                                 '--shuffle', '--continuous']):
            args = parse_arguments()
            
            assert args.dev is True
            assert args.limit == 10
            assert args.shuffle is True
            assert args.continuous is True