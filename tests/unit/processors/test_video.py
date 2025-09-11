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
    
    def test_resize_video_success(self, processor, mock_paths):
        """Test successful video resizing."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.resize_video(
                mock_paths['input'],
                mock_paths['output'],
                width=1920,
                height=1080
            )
            
            assert result is True
            mock_run.assert_called_once()
    
    def test_resize_video_failure(self, processor, mock_paths):
        """Test video resizing failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = processor.resize_video(
                mock_paths['input'],
                mock_paths['output'],
                width=1920,
                height=1080
            )
            
            assert result is False
    
    def test_resize_video_exception(self, processor, mock_paths):
        """Test video resizing with exception."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("FFmpeg error")
            
            result = processor.resize_video(
                mock_paths['input'],
                mock_paths['output'],
                width=1920,
                height=1080
            )
            
            assert result is False
    
    def test_add_audio_track(self, processor, mock_paths):
        """Test adding audio track to video."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.add_audio_track(
                mock_paths['input'],
                mock_paths['audio'],
                mock_paths['output']
            )
            
            assert result is True
    
    def test_extract_frames(self, processor, mock_paths):
        """Test extracting frames from video."""
        output_dir = mock_paths['input'].parent / 'frames'
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.extract_frames(
                mock_paths['input'],
                output_dir,
                fps=1
            )
            
            assert result is True
    
    def test_create_video_from_images(self, processor, mock_paths):
        """Test creating video from images."""
        images_dir = mock_paths['input'].parent / 'images'
        images_dir.mkdir()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.create_video_from_images(
                images_dir,
                mock_paths['output'],
                fps=30
            )
            
            assert result is True
    
    def test_apply_filter(self, processor, mock_paths):
        """Test applying video filter."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.apply_filter(
                mock_paths['input'],
                mock_paths['output'],
                filter_str="scale=1920:1080"
            )
            
            assert result is True
    
    def test_concatenate_videos(self, processor, mock_paths):
        """Test concatenating multiple videos."""
        videos = [
            mock_paths['input'].parent / 'video1.mp4',
            mock_paths['input'].parent / 'video2.mp4'
        ]
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.concatenate_videos(
                videos,
                mock_paths['output']
            )
            
            assert result is True
    
    def test_trim_video(self, processor, mock_paths):
        """Test trimming video."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.trim_video(
                mock_paths['input'],
                mock_paths['output'],
                start_time=10,
                duration=30
            )
            
            assert result is True
    
    def test_change_speed(self, processor, mock_paths):
        """Test changing video speed."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.change_speed(
                mock_paths['input'],
                mock_paths['output'],
                speed_factor=2.0
            )
            
            assert result is True
    
    def test_add_subtitle(self, processor, mock_paths):
        """Test adding subtitle to video."""
        subtitle_file = mock_paths['input'].parent / 'subtitle.srt'
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.add_subtitle(
                mock_paths['input'],
                subtitle_file,
                mock_paths['output']
            )
            
            assert result is True
    
    def test_get_video_info(self, processor, mock_paths):
        """Test getting video information."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='{"streams": [{"width": 1920, "height": 1080}]}'
            )
            
            info = processor.get_video_info(mock_paths['input'])
            
            assert info is not None
    
    def test_convert_format(self, processor, mock_paths):
        """Test converting video format."""
        output_path = mock_paths['input'].parent / 'output.avi'
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.convert_format(
                mock_paths['input'],
                output_path
            )
            
            assert result is True
