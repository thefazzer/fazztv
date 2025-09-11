"""Unit tests for media serializer module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import subprocess

from fazztv.broadcasting.serializer import MediaSerializer
from fazztv.models import MediaItem, ProcessingError


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.base_resolution = "1920x1080"
    settings.fade_length = 2
    settings.enable_equalizer = True
    return settings


@pytest.fixture
def media_serializer(mock_settings):
    """Create MediaSerializer instance for testing."""
    with patch('fazztv.broadcasting.serializer.get_settings', return_value=mock_settings):
        with patch('fazztv.broadcasting.serializer.VideoProcessor') as mock_vp:
            with patch('fazztv.broadcasting.serializer.CachedDownloader') as mock_dl:
                serializer = MediaSerializer()
                return serializer


@pytest.fixture
def sample_media_item():
    """Create a sample media item."""
    return MediaItem(
        artist="Test Artist",
        song="Test Song",
        url="https://youtube.com/watch?v=test",
        taxprompt="Test tax information",
        length_percent=75,
        duration=180
    )


class TestMediaSerializerInit:
    """Test MediaSerializer initialization."""
    
    def test_init_with_defaults(self, mock_settings):
        """Test initialization with default settings."""
        with patch('fazztv.broadcasting.serializer.get_settings', return_value=mock_settings):
            with patch('fazztv.broadcasting.serializer.VideoProcessor'):
                with patch('fazztv.broadcasting.serializer.CachedDownloader'):
                    serializer = MediaSerializer()
                    
        assert serializer.base_res == "1920x1080"
        assert serializer.fade_length == 2
        assert serializer.logo_path is None
    
    def test_init_with_custom_params(self, mock_settings):
        """Test initialization with custom parameters."""
        logo_path = Path("/path/to/logo.png")
        
        with patch('fazztv.broadcasting.serializer.get_settings', return_value=mock_settings):
            with patch('fazztv.broadcasting.serializer.VideoProcessor'):
                with patch('fazztv.broadcasting.serializer.CachedDownloader'):
                    serializer = MediaSerializer(
                        base_res="1280x720",
                        fade_length=3,
                        logo_path=logo_path
                    )
                    
        assert serializer.base_res == "1280x720"
        assert serializer.fade_length == 3
        assert serializer.logo_path == logo_path


class TestSerializeMediaItem:
    """Test serializing individual media items."""
    
    @patch('fazztv.broadcasting.serializer.get_temp_path')
    @patch('fazztv.broadcasting.serializer.safe_delete')
    def test_serialize_successful(self, mock_delete, mock_temp_path, media_serializer, sample_media_item, tmp_path):
        """Test successful media item serialization."""
        # Setup mocks
        audio_path = tmp_path / "temp_audio.aac"
        video_path = tmp_path / "temp_video.mp4"
        mock_temp_path.side_effect = [audio_path, video_path]
        
        media_serializer.downloader.download_audio.return_value = True
        media_serializer.downloader.download_video.return_value = True
        media_serializer.video_processor.combine_audio_video.return_value = True
        
        # Execute
        result = media_serializer.serialize_media_item(sample_media_item, output_dir=tmp_path)
        
        # Verify
        assert result is True
        assert sample_media_item.serialized is not None
        assert sample_media_item.serialized.parent == tmp_path
        
        # Verify downloads were called
        media_serializer.downloader.download_audio.assert_called_once_with(
            sample_media_item.url, audio_path
        )
        media_serializer.downloader.download_video.assert_called_once_with(
            sample_media_item.url, video_path
        )
        
        # Verify cleanup
        assert mock_delete.call_count == 2
    
    @patch('fazztv.broadcasting.serializer.get_temp_path')
    def test_serialize_audio_download_failure(self, mock_temp_path, media_serializer, sample_media_item, tmp_path):
        """Test serialization fails when audio download fails."""
        audio_path = tmp_path / "temp_audio.aac"
        mock_temp_path.return_value = audio_path
        
        media_serializer.downloader.download_audio.return_value = False
        
        result = media_serializer.serialize_media_item(sample_media_item)
        
        assert result is False
        assert sample_media_item.serialized is None
    
    @patch('fazztv.broadcasting.serializer.get_temp_path')
    def test_serialize_video_download_failure_uses_default(self, mock_temp_path, media_serializer, sample_media_item, tmp_path):
        """Test serialization uses default video when download fails."""
        audio_path = tmp_path / "temp_audio.aac"
        video_path = tmp_path / "temp_video.mp4"
        default_video = tmp_path / "default.mp4"
        mock_temp_path.side_effect = [audio_path, video_path]
        
        media_serializer.downloader.download_audio.return_value = True
        media_serializer.downloader.download_video.return_value = False
        media_serializer._create_default_video = Mock(return_value=default_video)
        media_serializer.video_processor.combine_audio_video.return_value = True
        
        result = media_serializer.serialize_media_item(sample_media_item, output_dir=tmp_path)
        
        assert result is True
        media_serializer._create_default_video.assert_called_once()
    
    @patch('fazztv.broadcasting.serializer.get_temp_path')
    @patch('fazztv.broadcasting.serializer.safe_delete')
    def test_serialize_with_trim(self, mock_delete, mock_temp_path, media_serializer, tmp_path):
        """Test serialization with length trimming."""
        audio_path = tmp_path / "temp_audio.aac"
        video_path = tmp_path / "temp_video.mp4"
        trimmed_path = tmp_path / "trimmed_audio.aac"
        mock_temp_path.side_effect = [audio_path, video_path]
        
        media_item = MediaItem(
            artist="Artist",
            song="Song",
            url="https://youtube.com/test",
            taxprompt="Tax",
            length_percent=50,  # Should trigger trimming
            duration=120
        )
        
        media_serializer.downloader.download_audio.return_value = True
        media_serializer.downloader.download_video.return_value = True
        media_serializer._trim_media = Mock(return_value=trimmed_path)
        media_serializer.video_processor.combine_audio_video.return_value = True
        
        result = media_serializer.serialize_media_item(media_item, output_dir=tmp_path)
        
        assert result is True
        media_serializer._trim_media.assert_called_once_with(audio_path, 50, 120)
    
    @patch('fazztv.broadcasting.serializer.get_temp_path')
    def test_serialize_with_show_info(self, mock_temp_path, media_serializer, sample_media_item, tmp_path):
        """Test serialization with show information."""
        audio_path = tmp_path / "temp_audio.aac"
        video_path = tmp_path / "temp_video.mp4"
        mock_temp_path.side_effect = [audio_path, video_path]
        
        show_info = {
            "title": "Show Title",
            "byline": "Show Byline"
        }
        
        media_serializer.downloader.download_audio.return_value = True
        media_serializer.downloader.download_video.return_value = True
        media_serializer.video_processor.combine_audio_video.return_value = True
        
        result = media_serializer.serialize_media_item(
            sample_media_item,
            show_info=show_info,
            output_dir=tmp_path
        )
        
        assert result is True
        
        # Verify show info was passed to video processor
        call_args = media_serializer.video_processor.combine_audio_video.call_args
        assert call_args.kwargs['title'] == "Show Title"
        assert call_args.kwargs['subtitle'] == "Show Byline"
        assert call_args.kwargs['marquee_text'] == sample_media_item.taxprompt
    
    @patch('fazztv.broadcasting.serializer.get_temp_path')
    def test_serialize_video_processing_failure(self, mock_temp_path, media_serializer, sample_media_item, tmp_path):
        """Test serialization fails when video processing fails."""
        audio_path = tmp_path / "temp_audio.aac"
        video_path = tmp_path / "temp_video.mp4"
        mock_temp_path.side_effect = [audio_path, video_path]
        
        media_serializer.downloader.download_audio.return_value = True
        media_serializer.downloader.download_video.return_value = True
        media_serializer.video_processor.combine_audio_video.return_value = False
        
        result = media_serializer.serialize_media_item(sample_media_item)
        
        assert result is False
        assert sample_media_item.serialized is None


class TestSerializeCollection:
    """Test serializing collections of media items."""
    
    def test_serialize_collection_all_successful(self, media_serializer):
        """Test serializing collection when all succeed."""
        items = [
            MediaItem(artist=f"Artist{i}", song=f"Song{i}", 
                     url=f"https://youtube.com/{i}", taxprompt="Tax")
            for i in range(3)
        ]
        
        media_serializer.serialize_media_item = Mock(return_value=True)
        
        result = media_serializer.serialize_collection(items)
        
        assert len(result) == 3
        assert media_serializer.serialize_media_item.call_count == 3
    
    def test_serialize_collection_with_failures(self, media_serializer):
        """Test serializing collection with some failures."""
        items = [
            MediaItem(artist=f"Artist{i}", song=f"Song{i}",
                     url=f"https://youtube.com/{i}", taxprompt="Tax")
            for i in range(3)
        ]
        
        # First and third succeed, second fails
        media_serializer.serialize_media_item = Mock(side_effect=[True, False, True])
        
        result = media_serializer.serialize_collection(items)
        
        assert len(result) == 2
        assert items[0] in result
        assert items[2] in result
        assert items[1] not in result
    
    def test_serialize_collection_with_show_data(self, media_serializer):
        """Test serializing collection with show data."""
        items = [
            MediaItem(artist=f"Artist{i}", song=f"Song{i}",
                     url=f"https://youtube.com/{i}", taxprompt="Tax")
            for i in range(2)
        ]
        
        show_data = [
            {"title": "Show1", "byline": "Byline1"},
            {"title": "Show2", "byline": "Byline2"}
        ]
        
        media_serializer.serialize_media_item = Mock(return_value=True)
        
        result = media_serializer.serialize_collection(
            items,
            show_data=show_data,
            randomize_shows=False
        )
        
        # Verify show data was passed correctly
        calls = media_serializer.serialize_media_item.call_args_list
        assert calls[0][0][1] == show_data[0]
        assert calls[1][0][1] == show_data[1]
    
    @patch('random.shuffle')
    def test_serialize_collection_randomize_shows(self, mock_shuffle, media_serializer):
        """Test that show data is randomized when configured."""
        items = [MediaItem(artist="A", song="S", url="https://yt.com", taxprompt="T")]
        show_data = [{"title": "Show1"}, {"title": "Show2"}]
        
        media_serializer.serialize_media_item = Mock(return_value=True)
        
        media_serializer.serialize_collection(
            items,
            show_data=show_data,
            randomize_shows=True
        )
        
        mock_shuffle.assert_called_once()
    
    def test_serialize_collection_empty(self, media_serializer):
        """Test serializing empty collection."""
        result = media_serializer.serialize_collection([])
        
        assert result == []
        media_serializer.serialize_media_item.assert_not_called()


class TestTrimMedia:
    """Test media trimming functionality."""
    
    @patch('fazztv.broadcasting.serializer.AudioProcessor')
    @patch('fazztv.broadcasting.serializer.get_temp_path')
    @patch('fazztv.broadcasting.serializer.safe_delete')
    def test_trim_media_successful(self, mock_delete, mock_temp_path, mock_audio_proc, media_serializer, tmp_path):
        """Test successful media trimming."""
        input_path = tmp_path / "input.mp3"
        trimmed_path = tmp_path / "trimmed.mp3"
        mock_temp_path.return_value = trimmed_path
        
        # Mock audio processor
        audio_proc_instance = Mock()
        audio_proc_instance._get_audio_duration.return_value = 100  # 100 seconds
        audio_proc_instance.extract_segment.return_value = True
        mock_audio_proc.return_value = audio_proc_instance
        
        result = media_serializer._trim_media(input_path, 50, None)
        
        assert result == trimmed_path
        audio_proc_instance.extract_segment.assert_called_once_with(
            input_path, trimmed_path, start_time=0, duration=50
        )
        mock_delete.assert_called_once_with(input_path)
    
    @patch('fazztv.broadcasting.serializer.AudioProcessor')
    def test_trim_media_no_duration(self, mock_audio_proc, media_serializer, tmp_path):
        """Test trim returns original when duration cannot be determined."""
        input_path = tmp_path / "input.mp3"
        
        audio_proc_instance = Mock()
        audio_proc_instance._get_audio_duration.return_value = None
        mock_audio_proc.return_value = audio_proc_instance
        
        result = media_serializer._trim_media(input_path, 50, None)
        
        assert result == input_path
    
    @patch('fazztv.broadcasting.serializer.AudioProcessor')
    @patch('fazztv.broadcasting.serializer.get_temp_path')
    def test_trim_media_with_max_duration(self, mock_temp_path, mock_audio_proc, media_serializer, tmp_path):
        """Test trimming respects maximum duration."""
        input_path = tmp_path / "input.mp3"
        trimmed_path = tmp_path / "trimmed.mp3"
        mock_temp_path.return_value = trimmed_path
        
        audio_proc_instance = Mock()
        audio_proc_instance._get_audio_duration.return_value = 200
        audio_proc_instance.extract_segment.return_value = True
        mock_audio_proc.return_value = audio_proc_instance
        
        # 75% of 200s = 150s, but max is 100s
        result = media_serializer._trim_media(input_path, 75, max_duration=100)
        
        # Should use max_duration (100) instead of percentage (150)
        audio_proc_instance.extract_segment.assert_called_once_with(
            input_path, trimmed_path, start_time=0, duration=100
        )


class TestCreateDefaultVideo:
    """Test default video creation."""
    
    @patch('subprocess.run')
    @patch('fazztv.broadcasting.serializer.get_temp_path')
    def test_create_default_video_successful(self, mock_temp_path, mock_run, media_serializer, tmp_path):
        """Test successful default video creation."""
        output_path = tmp_path / "default.mp4"
        mock_temp_path.return_value = output_path
        mock_run.return_value = Mock(returncode=0)
        
        result = media_serializer._create_default_video()
        
        assert result == output_path
        
        # Verify ffmpeg command
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert media_serializer.base_res in str(cmd)
        assert str(output_path) in cmd
    
    @patch('subprocess.run')
    @patch('fazztv.broadcasting.serializer.get_temp_path')
    def test_create_default_video_failure(self, mock_temp_path, mock_run, media_serializer, tmp_path):
        """Test default video creation failure."""
        output_path = tmp_path / "default.mp4"
        mock_temp_path.return_value = output_path
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")
        
        with pytest.raises(ProcessingError, match="Could not create default video"):
            media_serializer._create_default_video()


class TestCleanupSerialized:
    """Test cleanup of serialized files."""
    
    @patch('fazztv.broadcasting.serializer.safe_delete')
    def test_cleanup_serialized_files(self, mock_delete, media_serializer, tmp_path):
        """Test cleaning up serialized files."""
        # Create media items with serialized files
        items = []
        for i in range(3):
            file_path = tmp_path / f"video_{i}.mp4"
            file_path.touch()  # Create the file
            item = MediaItem(
                artist=f"Artist{i}",
                song=f"Song{i}",
                url=f"https://youtube.com/{i}",
                taxprompt="Tax",
                serialized=file_path
            )
            items.append(item)
        
        mock_delete.return_value = True
        
        cleaned = media_serializer.cleanup_serialized(items)
        
        assert cleaned == 3
        assert mock_delete.call_count == 3
        
        # Verify serialized paths were reset
        for item in items:
            assert item.serialized is None
    
    @patch('fazztv.broadcasting.serializer.safe_delete')
    def test_cleanup_with_nonexistent_files(self, mock_delete, media_serializer):
        """Test cleanup handles non-existent files."""
        items = [
            MediaItem(
                artist="Artist",
                song="Song",
                url="https://youtube.com/test",
                taxprompt="Tax",
                serialized=Path("/nonexistent/video.mp4")
            )
        ]
        
        cleaned = media_serializer.cleanup_serialized(items)
        
        assert cleaned == 0
        mock_delete.assert_not_called()
    
    def test_cleanup_empty_list(self, media_serializer):
        """Test cleanup with empty list."""
        cleaned = media_serializer.cleanup_serialized([])
        
        assert cleaned == 0