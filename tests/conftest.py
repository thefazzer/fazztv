"""Pytest configuration and shared fixtures."""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for test files."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def mock_ffmpeg():
    """Mock ffmpeg command."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout=b'', stderr=b'')
        yield mock_run

@pytest.fixture
def mock_yt_dlp():
    """Mock yt-dlp command."""
    with patch('yt_dlp.YoutubeDL') as mock_ytdl:
        instance = Mock()
        instance.download.return_value = 0
        instance.extract_info.return_value = {
            'title': 'Test Video',
            'duration': 180,
            'url': 'https://example.com/video.mp4',
            'ext': 'mp4',
            'formats': []
        }
        mock_ytdl.return_value = instance
        yield mock_ytdl

@pytest.fixture
def sample_media_item():
    """Create a sample MediaItem for testing."""
    from fazztv.models.media_item import MediaItem
    return MediaItem(
        artist="Test Artist",
        song="Test Song",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        taxprompt="Test tax prompt for the artist.",
        length_percent=75
    )

@pytest.fixture
def sample_episode():
    """Create a sample Episode for testing."""
    from fazztv.models.episode import Episode
    return Episode(
        title="Test Episode",
        description="Test episode description",
        artist="Test Artist",
        genre="Test Genre",
        duration=3600,
        air_date="2024-01-01"
    )

@pytest.fixture
def mock_rtmp_server():
    """Mock RTMP server for testing broadcasting."""
    server = Mock()
    server.host = "127.0.0.1"
    server.port = 1935
    server.running = True
    server.start = Mock()
    server.stop = Mock()
    server.is_connected = Mock(return_value=True)
    return server

@pytest.fixture
def mock_openrouter_api():
    """Mock OpenRouter API responses."""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Test AI response'
                }
            }]
        }
        mock_post.return_value = mock_response
        yield mock_post

@pytest.fixture
def mock_youtube_api():
    """Mock YouTube API responses."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [{
                'snippet': {
                    'title': 'Test Video',
                    'description': 'Test Description'
                },
                'contentDetails': {
                    'duration': 'PT3M30S'
                }
            }]
        }
        mock_get.return_value = mock_response
        yield mock_get

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset any singleton instances that might persist between tests
    from fazztv.config.settings import Settings
    if hasattr(Settings, '_instance'):
        delattr(Settings, '_instance')
    yield

@pytest.fixture
def env_setup(monkeypatch):
    """Set up test environment variables."""
    test_env = {
        'FAZZTV_ENV': 'test',
        'FAZZTV_DEBUG': 'true',
        'FAZZTV_LOG_LEVEL': 'DEBUG',
        'RTMP_URL': 'rtmp://localhost:1935/live',
        'STREAM_KEY': 'test_stream_key',
        'YOUTUBE_API_KEY': 'test_api_key',
        'OPENROUTER_API_KEY': 'test_openrouter_key'
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    return test_env