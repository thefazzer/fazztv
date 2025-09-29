"""Comprehensive unit tests for VideoProcessor."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import subprocess

from fazztv.processors.video import VideoProcessor
from fazztv.config import constants


class TestVideoProcessor:
    """Test suite for VideoProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create VideoProcessor instance."""
        return VideoProcessor()
    
    @pytest.fixture
    def mock_paths(self, tmp_path):
        """Create test paths."""
        return {
            'input': tmp_path / 'input.mp4',
            'output': tmp_path / 'output.mp4',
            'audio': tmp_path / 'audio.mp3',
            'image': tmp_path / 'image.png'
        }
    
    def test_initialization(self, processor):
        """Test VideoProcessor initialization."""
        assert processor is not None
    
    def test_scale_video_success(self, processor, mock_paths):
        """Test successful video scaling."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = processor.scale_video(
                mock_paths['input'],
                mock_paths['output'],
                resolution="1920x1080"
            )

            assert result is True
            mock_run.assert_called_once()
    
    def test_scale_video_failure(self, processor, mock_paths):
        """Test video scaling failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)

            result = processor.scale_video(
                mock_paths['input'],
                mock_paths['output'],
                resolution="1920x1080"
            )

            assert result is False
    
    def test_scale_video_exception(self, processor, mock_paths):
        """Test video scaling with exception."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("FFmpeg error")

            result = processor.scale_video(
                mock_paths['input'],
                mock_paths['output'],
                resolution="1920x1080"
            )

            assert result is False
    
    def test_combine_audio_video(self, processor, mock_paths):
        """Test combining audio and video."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = processor.combine_audio_video(
                mock_paths['audio'],
                mock_paths['input'],
                mock_paths['output']
            )

            assert result is True
    
    def test_add_fade_effects(self, processor, mock_paths):
        """Test adding fade effects to video."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = processor.add_fade_effects(
                mock_paths['input'],
                mock_paths['output'],
                fade_in=2,
                fade_out=2
            )

            assert result is True
    
    def test_extract_clip(self, processor, mock_paths):
        """Test extracting clip from video."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = processor.extract_clip(
                mock_paths['input'],
                mock_paths['output'],
                start_time=10,
                duration=30
            )

            assert result is True
    
    def test_get_video_duration(self, processor, mock_paths):
        """Test getting video duration."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="120.5"
            )

            duration = processor._get_video_duration(mock_paths['input'])

            assert duration == 120.5
    
    def test_sanitize_text(self, processor):
        """Test text sanitization."""
        test_text = "Hello: world, with = problematic; chars"
        result = processor._sanitize_text(test_text)

        assert "\\:" in result  # Colon should be escaped
        assert "\\," in result  # Comma should be escaped
        assert "\\=" in result  # Equals should be escaped
        assert "\\;" in result  # Semicolon should be escaped
    
