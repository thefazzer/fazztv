"""Unit tests for RTMP broadcasting module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import subprocess

from fazztv.broadcasting.rtmp import RTMPBroadcaster
from fazztv.models import MediaItem, BroadcastError


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.rtmp_url = "rtmp://test.server/live/stream"
    return settings


@pytest.fixture
def rtmp_broadcaster(mock_settings):
    """Create RTMPBroadcaster instance for testing."""
    with patch('fazztv.broadcasting.rtmp.get_settings', return_value=mock_settings):
        return RTMPBroadcaster()


@pytest.fixture
def serialized_media_item(tmp_path):
    """Create a media item with serialized file."""
    video_file = tmp_path / "test_video.mp4"
    video_file.touch()  # Create empty file
    
    item = MediaItem(
        artist="Test Artist",
        song="Test Song",
        url="https://youtube.com/watch?v=test",
        taxprompt="Test tax info",
        duration=120,
        serialized=video_file
    )
    return item


@pytest.fixture
def unserialized_media_item():
    """Create a media item without serialized file."""
    return MediaItem(
        artist="Test Artist",
        song="Test Song",
        url="https://youtube.com/watch?v=test",
        taxprompt="Test tax info"
    )


class TestRTMPBroadcasterInit:
    """Test RTMPBroadcaster initialization."""
    
    def test_init_with_default_url(self, mock_settings):
        """Test initialization with default URL from settings."""
        with patch('fazztv.broadcasting.rtmp.get_settings', return_value=mock_settings):
            broadcaster = RTMPBroadcaster()
            
        assert broadcaster.rtmp_url == "rtmp://test.server/live/stream"
        assert broadcaster.total_broadcast_count == 0
        assert broadcaster.successful_broadcast_count == 0
        assert broadcaster.failed_broadcast_count == 0
    
    def test_init_with_custom_url(self, mock_settings):
        """Test initialization with custom URL."""
        with patch('fazztv.broadcasting.rtmp.get_settings', return_value=mock_settings):
            broadcaster = RTMPBroadcaster("rtmp://custom.server/live")
            
        assert broadcaster.rtmp_url == "rtmp://custom.server/live"


class TestBroadcastItem:
    """Test broadcasting individual items."""
    
    def test_broadcast_unserialized_item(self, rtmp_broadcaster, unserialized_media_item):
        """Test broadcasting fails for unserialized item."""
        with pytest.raises(BroadcastError, match="is not serialized"):
            rtmp_broadcaster.broadcast_item(unserialized_media_item)
        
        assert rtmp_broadcaster.total_broadcast_count == 1
        assert rtmp_broadcaster.failed_broadcast_count == 1
        assert rtmp_broadcaster.successful_broadcast_count == 0
    
    def test_broadcast_nonexistent_file(self, rtmp_broadcaster):
        """Test broadcasting fails when serialized file doesn't exist."""
        item = MediaItem(
            artist="Test",
            song="Song",
            url="https://youtube.com/test",
            taxprompt="Tax",
            serialized=Path("/nonexistent/video.mp4")
        )
        
        with pytest.raises(BroadcastError, match="does not exist"):
            rtmp_broadcaster.broadcast_item(item)
        
        assert rtmp_broadcaster.failed_broadcast_count == 1
    
    @patch('subprocess.run')
    def test_broadcast_successful(self, mock_run, rtmp_broadcaster, serialized_media_item):
        """Test successful broadcasting."""
        mock_run.return_value = Mock(returncode=0, stderr=b'')
        
        result = rtmp_broadcaster.broadcast_item(serialized_media_item)
        
        assert result is True
        assert rtmp_broadcaster.total_broadcast_count == 1
        assert rtmp_broadcaster.successful_broadcast_count == 1
        assert rtmp_broadcaster.failed_broadcast_count == 0
        
        # Verify ffmpeg command
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert str(serialized_media_item.serialized) in cmd
        assert rtmp_broadcaster.rtmp_url in cmd
    
    @patch('subprocess.run')
    def test_broadcast_ffmpeg_failure(self, mock_run, rtmp_broadcaster, serialized_media_item):
        """Test broadcasting fails when ffmpeg returns error."""
        mock_run.return_value = Mock(returncode=1, stderr=b'FFmpeg error')
        
        result = rtmp_broadcaster.broadcast_item(serialized_media_item)
        
        assert result is False
        assert rtmp_broadcaster.failed_broadcast_count == 1
        assert rtmp_broadcaster.successful_broadcast_count == 0
    
    @patch('subprocess.run')
    def test_broadcast_timeout(self, mock_run, rtmp_broadcaster, serialized_media_item):
        """Test broadcasting timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired('ffmpeg', 240)
        
        with pytest.raises(BroadcastError, match="timeout"):
            rtmp_broadcaster.broadcast_item(serialized_media_item)
        
        assert rtmp_broadcaster.failed_broadcast_count == 1
    
    @patch('subprocess.run')
    def test_broadcast_exception(self, mock_run, rtmp_broadcaster, serialized_media_item):
        """Test broadcasting handles unexpected exceptions."""
        mock_run.side_effect = Exception("Unexpected error")
        
        with pytest.raises(BroadcastError, match="Unexpected error"):
            rtmp_broadcaster.broadcast_item(serialized_media_item)
        
        assert rtmp_broadcaster.failed_broadcast_count == 1


class TestBroadcastCollection:
    """Test broadcasting collections of items."""
    
    @patch('subprocess.run')
    def test_broadcast_collection_all_successful(self, mock_run, rtmp_broadcaster, tmp_path):
        """Test broadcasting collection when all succeed."""
        mock_run.return_value = Mock(returncode=0, stderr=b'')
        
        # Create multiple media items
        items = []
        for i in range(3):
            video_file = tmp_path / f"video_{i}.mp4"
            video_file.touch()
            item = MediaItem(
                artist=f"Artist {i}",
                song=f"Song {i}",
                url=f"https://youtube.com/{i}",
                taxprompt="Tax",
                serialized=video_file
            )
            items.append(item)
        
        results = rtmp_broadcaster.broadcast_collection(items)
        
        assert len(results) == 3
        assert all(success for _, success in results)
        assert rtmp_broadcaster.successful_broadcast_count == 3
        assert rtmp_broadcaster.failed_broadcast_count == 0
    
    @patch('subprocess.run')
    def test_broadcast_collection_with_failures(self, mock_run, rtmp_broadcaster, tmp_path):
        """Test broadcasting collection with some failures."""
        # First succeeds, second fails, third succeeds
        mock_run.side_effect = [
            Mock(returncode=0, stderr=b''),
            Mock(returncode=1, stderr=b'Error'),
            Mock(returncode=0, stderr=b'')
        ]
        
        items = []
        for i in range(3):
            video_file = tmp_path / f"video_{i}.mp4"
            video_file.touch()
            item = MediaItem(
                artist=f"Artist {i}",
                song=f"Song {i}",
                url=f"https://youtube.com/{i}",
                taxprompt="Tax",
                serialized=video_file
            )
            items.append(item)
        
        results = rtmp_broadcaster.broadcast_collection(items)
        
        assert len(results) == 3
        assert results[0][1] is True
        assert results[1][1] is False
        assert results[2][1] is True
        assert rtmp_broadcaster.successful_broadcast_count == 2
        assert rtmp_broadcaster.failed_broadcast_count == 1
    
    @patch('subprocess.run')
    def test_broadcast_collection_stop_on_failure(self, mock_run, rtmp_broadcaster, tmp_path):
        """Test broadcasting stops on first failure when configured."""
        mock_run.side_effect = [
            Mock(returncode=0, stderr=b''),
            Mock(returncode=1, stderr=b'Error')
        ]
        
        items = []
        for i in range(3):
            video_file = tmp_path / f"video_{i}.mp4"
            video_file.touch()
            item = MediaItem(
                artist=f"Artist {i}",
                song=f"Song {i}",
                url=f"https://youtube.com/{i}",
                taxprompt="Tax",
                serialized=video_file
            )
            items.append(item)
        
        results = rtmp_broadcaster.broadcast_collection(items, stop_on_failure=True)
        
        assert len(results) == 2  # Should stop after second item fails
        assert rtmp_broadcaster.successful_broadcast_count == 1
        assert rtmp_broadcaster.failed_broadcast_count == 1
    
    @patch('subprocess.run')
    def test_broadcast_collection_with_callbacks(self, mock_run, rtmp_broadcaster, tmp_path):
        """Test broadcasting with success and failure callbacks."""
        mock_run.side_effect = [
            Mock(returncode=0, stderr=b''),
            Mock(returncode=1, stderr=b'Error')
        ]
        
        success_items = []
        failed_items = []
        
        def on_success(item):
            success_items.append(item)
        
        def on_failure(item, exc):
            failed_items.append((item, str(exc)))
        
        items = []
        for i in range(2):
            video_file = tmp_path / f"video_{i}.mp4"
            video_file.touch()
            item = MediaItem(
                artist=f"Artist {i}",
                song=f"Song {i}",
                url=f"https://youtube.com/{i}",
                taxprompt="Tax",
                serialized=video_file
            )
            items.append(item)
        
        rtmp_broadcaster.broadcast_collection(
            items,
            on_success=on_success,
            on_failure=on_failure
        )
        
        assert len(success_items) == 1
        assert success_items[0] == items[0]
        assert len(failed_items) == 1
        assert failed_items[0][0] == items[1]
    
    @patch('subprocess.run')
    def test_broadcast_collection_with_exception(self, mock_run, rtmp_broadcaster, tmp_path):
        """Test broadcasting handles exceptions in collection."""
        mock_run.side_effect = Exception("Unexpected error")
        
        video_file = tmp_path / "video.mp4"
        video_file.touch()
        item = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com/test",
            taxprompt="Tax",
            serialized=video_file
        )
        
        results = rtmp_broadcaster.broadcast_collection([item])
        
        assert len(results) == 1
        assert results[0][1] is False
        assert rtmp_broadcaster.failed_broadcast_count == 1


class TestBroadcastFiltered:
    """Test filtered broadcasting."""
    
    @patch('subprocess.run')
    def test_broadcast_filtered(self, mock_run, rtmp_broadcaster, tmp_path):
        """Test broadcasting with filter function."""
        mock_run.return_value = Mock(returncode=0, stderr=b'')
        
        items = []
        for i in range(5):
            video_file = tmp_path / f"video_{i}.mp4"
            video_file.touch()
            item = MediaItem(
                artist=f"Artist {i}",
                song=f"Song {i}",
                url=f"https://youtube.com/{i}",
                taxprompt="Tax",
                length_percent=20 + i * 20,  # 20, 40, 60, 80, 100
                serialized=video_file
            )
            items.append(item)
        
        # Filter for items with length_percent > 50
        def filter_func(item):
            return item.length_percent > 50
        
        results = rtmp_broadcaster.broadcast_filtered(items, filter_func)
        
        assert len(results) == 3  # Should broadcast items with 60, 80, 100
        assert all(success for _, success in results)
        assert rtmp_broadcaster.successful_broadcast_count == 3
    
    def test_broadcast_filtered_empty_result(self, rtmp_broadcaster, tmp_path):
        """Test broadcasting when filter excludes all items."""
        items = []
        for i in range(3):
            video_file = tmp_path / f"video_{i}.mp4"
            video_file.touch()
            item = MediaItem(
                artist=f"Artist {i}",
                song=f"Song {i}",
                url=f"https://youtube.com/{i}",
                taxprompt="Tax",
                serialized=video_file
            )
            items.append(item)
        
        # Filter that excludes everything
        def filter_func(item):
            return False
        
        results = rtmp_broadcaster.broadcast_filtered(items, filter_func)
        
        assert len(results) == 0
        assert rtmp_broadcaster.total_broadcast_count == 0


class TestTestConnection:
    """Test RTMP connection testing."""
    
    @patch('subprocess.run')
    def test_connection_successful(self, mock_run, rtmp_broadcaster):
        """Test successful connection test."""
        mock_run.return_value = Mock(returncode=0)
        
        result = rtmp_broadcaster.test_connection()
        
        assert result is True
        
        # Verify test command
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert "testsrc" in cmd
        assert rtmp_broadcaster.rtmp_url in cmd
    
    @patch('subprocess.run')
    def test_connection_failed(self, mock_run, rtmp_broadcaster):
        """Test failed connection test."""
        mock_run.return_value = Mock(returncode=1, stderr=b'Connection refused')
        
        result = rtmp_broadcaster.test_connection()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_connection_timeout(self, mock_run, rtmp_broadcaster):
        """Test connection test timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('ffmpeg', 10)
        
        result = rtmp_broadcaster.test_connection()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_connection_exception(self, mock_run, rtmp_broadcaster):
        """Test connection test with exception."""
        mock_run.side_effect = Exception("Network error")
        
        result = rtmp_broadcaster.test_connection()
        
        assert result is False


class TestStatistics:
    """Test broadcasting statistics."""
    
    def test_get_stats_initial(self, rtmp_broadcaster):
        """Test getting initial statistics."""
        stats = rtmp_broadcaster.get_stats()
        
        assert stats["rtmp_url"] == rtmp_broadcaster.rtmp_url
        assert stats["total_broadcasts"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0
    
    @patch('subprocess.run')
    def test_get_stats_after_broadcasts(self, mock_run, rtmp_broadcaster, serialized_media_item):
        """Test statistics after some broadcasts."""
        # Simulate 3 successful and 2 failed broadcasts
        mock_run.side_effect = [
            Mock(returncode=0, stderr=b''),
            Mock(returncode=0, stderr=b''),
            Mock(returncode=1, stderr=b'Error'),
            Mock(returncode=0, stderr=b''),
            Mock(returncode=1, stderr=b'Error')
        ]
        
        for _ in range(5):
            try:
                rtmp_broadcaster.broadcast_item(serialized_media_item)
            except BroadcastError:
                pass
        
        stats = rtmp_broadcaster.get_stats()
        
        assert stats["total_broadcasts"] == 5
        assert stats["successful"] == 3
        assert stats["failed"] == 2
        assert stats["success_rate"] == 60.0
    
    def test_reset_stats(self, rtmp_broadcaster):
        """Test resetting statistics."""
        # Set some initial values
        rtmp_broadcaster.total_broadcast_count = 10
        rtmp_broadcaster.successful_broadcast_count = 7
        rtmp_broadcaster.failed_broadcast_count = 3
        
        rtmp_broadcaster.reset_stats()
        
        assert rtmp_broadcaster.total_broadcast_count == 0
        assert rtmp_broadcaster.successful_broadcast_count == 0
        assert rtmp_broadcaster.failed_broadcast_count == 0
        
        stats = rtmp_broadcaster.get_stats()
        assert stats["total_broadcasts"] == 0
        assert stats["success_rate"] == 0