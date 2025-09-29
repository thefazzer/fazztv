"""Unit tests for MediaSerializer module."""

from unittest.mock import Mock, patch
from pathlib import Path
from fazztv.broadcasting.serializer import MediaSerializer
from fazztv.models import MediaItem


class TestMediaSerializer:
    """Test suite for MediaSerializer class."""

    @patch("fazztv.broadcasting.serializer.get_settings")
    def test_initialization(self, mock_settings):
        """Test MediaSerializer initialization."""
        mock_settings.return_value = Mock(
            base_resolution="1920x1080",
            fade_length=2,
            enable_equalizer=False
        )

        serializer = MediaSerializer()
        assert serializer is not None
        assert serializer.base_res == "1920x1080"
        assert serializer.fade_length == 2

    @patch("fazztv.broadcasting.serializer.get_settings")
    @patch("fazztv.broadcasting.serializer.VideoProcessor")
    @patch("fazztv.broadcasting.serializer.CachedDownloader")
    def test_serialize_media_item_success(self, mock_downloader_cls, mock_processor_cls, mock_settings):
        """Test successful media item serialization."""
        # Setup mocks
        mock_settings.return_value = Mock(
            base_resolution="1920x1080",
            fade_length=2,
            enable_equalizer=False
        )

        mock_downloader = Mock()
        mock_downloader.download_audio.return_value = True
        mock_downloader.download_video.return_value = True
        mock_downloader_cls.return_value = mock_downloader

        mock_processor = Mock()
        mock_processor.combine_audio_video.return_value = True
        mock_processor_cls.return_value = mock_processor

        # Create test media item
        media_item = MediaItem(
            artist="Madonna",
            song="Like a Prayer",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test prompt"
        )

        # Test serialization
        serializer = MediaSerializer()
        with patch("fazztv.broadcasting.serializer.get_temp_path") as mock_temp:
            mock_temp.side_effect = [Path("/tmp/audio.aac"), Path("/tmp/video.mp4")]
            result = serializer.serialize_media_item(media_item)

        assert result is True
        assert mock_downloader.download_audio.called
        assert mock_downloader.download_video.called
        assert mock_processor.combine_audio_video.called

    @patch("fazztv.broadcasting.serializer.get_settings")
    @patch("fazztv.broadcasting.serializer.VideoProcessor")
    @patch("fazztv.broadcasting.serializer.CachedDownloader")
    def test_serialize_media_item_failure(self, mock_downloader_cls, mock_processor_cls, mock_settings):
        """Test failed media item serialization."""
        # Setup mocks
        mock_settings.return_value = Mock(
            base_resolution="1920x1080",
            fade_length=2,
            enable_equalizer=False
        )

        mock_downloader = Mock()
        mock_downloader.download_audio.return_value = False
        mock_downloader_cls.return_value = mock_downloader

        mock_processor = Mock()
        mock_processor_cls.return_value = mock_processor

        # Create test media item
        media_item = MediaItem(
            artist="Madonna",
            song="Like a Prayer",
            url="https://youtube.com/watch?v=test",
            taxprompt="Test prompt"
        )

        # Test serialization
        serializer = MediaSerializer()
        with patch("fazztv.broadcasting.serializer.get_temp_path") as mock_temp:
            mock_temp.side_effect = [Path("/tmp/audio.aac"), Path("/tmp/video.mp4")]
            result = serializer.serialize_media_item(media_item)

        assert result is False
        assert mock_downloader.download_audio.called

    @patch("fazztv.broadcasting.serializer.get_settings")
    @patch("fazztv.broadcasting.serializer.VideoProcessor")
    @patch("fazztv.broadcasting.serializer.CachedDownloader")
    def test_serialize_collection(self, mock_downloader_cls, mock_processor_cls, mock_settings):
        """Test serializing a collection of media items."""
        # Setup mocks
        mock_settings.return_value = Mock(
            base_resolution="1920x1080",
            fade_length=2,
            enable_equalizer=False
        )

        mock_downloader = Mock()
        mock_downloader.download_audio.return_value = True
        mock_downloader.download_video.return_value = True
        mock_downloader_cls.return_value = mock_downloader

        mock_processor = Mock()
        mock_processor.combine_audio_video.return_value = True
        mock_processor_cls.return_value = mock_processor

        # Create test media items
        media_items = [
            MediaItem(
                artist="Madonna",
                song="Like a Prayer",
                url="https://youtube.com/watch?v=test1",
                taxprompt="Test prompt 1"
            ),
            MediaItem(
                artist="Madonna",
                song="Vogue",
                url="https://youtube.com/watch?v=test2",
                taxprompt="Test prompt 2"
            )
        ]

        # Test collection serialization
        serializer = MediaSerializer()
        with patch("fazztv.broadcasting.serializer.get_temp_path") as mock_temp:
            mock_temp.side_effect = [
                Path("/tmp/audio1.aac"), Path("/tmp/video1.mp4"),
                Path("/tmp/audio2.aac"), Path("/tmp/video2.mp4")
            ]
            result = serializer.serialize_collection(media_items)

        assert len(result) == 2
        assert mock_downloader.download_audio.call_count == 2
        assert mock_downloader.download_video.call_count == 2
        assert mock_processor.combine_audio_video.call_count == 2

    @patch("fazztv.broadcasting.serializer.get_settings")
    @patch("fazztv.broadcasting.serializer.AudioProcessor")
    def test_trim_media(self, mock_audio_proc_cls, mock_settings):
        """Test media trimming functionality."""
        mock_settings.return_value = Mock(
            base_resolution="1920x1080",
            fade_length=2
        )

        mock_audio_proc = Mock()
        mock_audio_proc._get_audio_duration.return_value = 100
        mock_audio_proc.extract_segment.return_value = True
        mock_audio_proc_cls.return_value = mock_audio_proc

        serializer = MediaSerializer()

        with patch("fazztv.broadcasting.serializer.get_temp_path") as mock_temp:
            with patch("fazztv.broadcasting.serializer.safe_delete") as mock_delete:
                mock_temp.return_value = Path("/tmp/trimmed.aac")
                result = serializer._trim_media(Path("/tmp/original.aac"), 50)

        assert result == Path("/tmp/trimmed.aac")
        assert mock_audio_proc.extract_segment.called

        # Check that duration calculation is correct
        call_args = mock_audio_proc.extract_segment.call_args
        # extract_segment(input, output, start_time=0, duration=target_duration)
        assert call_args[0][0] == Path("/tmp/original.aac")  # input
        assert call_args[0][1] == Path("/tmp/trimmed.aac")  # output
        assert call_args[1]["start_time"] == 0  # start_time
        assert call_args[1]["duration"] == 50  # duration (50% of 100)

    @patch("fazztv.broadcasting.serializer.get_settings")
    def test_cleanup_serialized(self, mock_settings):
        """Test cleanup of serialized files."""
        mock_settings.return_value = Mock(
            base_resolution="1920x1080",
            fade_length=2
        )

        # Create media items with mock serialized paths
        media_items = [
            MediaItem(
                artist="Madonna",
                song="Like a Prayer",
                url="https://youtube.com/watch?v=test1",
                taxprompt="Test prompt 1"
            ),
            MediaItem(
                artist="Madonna",
                song="Vogue",
                url="https://youtube.com/watch?v=test2",
                taxprompt="Test prompt 2"
            )
        ]

        # Set serialized paths
        media_items[0].serialized = Mock()
        media_items[0].serialized.exists.return_value = True
        media_items[1].serialized = Mock()
        media_items[1].serialized.exists.return_value = True

        serializer = MediaSerializer()

        with patch("fazztv.broadcasting.serializer.safe_delete") as mock_delete:
            mock_delete.return_value = True
            cleaned = serializer.cleanup_serialized(media_items)

        assert cleaned == 2
        assert mock_delete.call_count == 2
        assert media_items[0].serialized is None
        assert media_items[1].serialized is None