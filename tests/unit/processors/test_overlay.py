"""Comprehensive unit tests for overlay module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from abc import ABC

from fazztv.processors.overlay import (
    Overlay, TextOverlay, ImageOverlay, VideoOverlay, OverlayManager
)


class TestOverlay:
    """Test suite for Overlay base class."""
    
    def test_abstract_base_class(self):
        """Test Overlay is an abstract base class."""
        # Cannot instantiate abstract class
        with pytest.raises(TypeError):
            Overlay()


class TestTextOverlay:
    """Test suite for TextOverlay class."""
    
    def test_initialization(self):
        """Test TextOverlay initialization."""
        overlay = TextOverlay(
            text="Test",
            position=(10, 20),
            font_size=24,
            font_color="white"
        )
        assert overlay.text == "Test"
        assert overlay.position == (10, 20)
        assert overlay.font_size == 24
        assert overlay.font_color == "white"
    
    def test_build_filter(self):
        """Test build_filter method."""
        overlay = TextOverlay("Test", (0, 0))
        filter_str = overlay.build_filter()
        assert "drawtext" in filter_str
        assert "Test" in filter_str
    
    def test_custom_font(self):
        """Test custom font settings."""
        overlay = TextOverlay(
            text="Custom",
            position=(50, 50),
            font_path="/usr/share/fonts/truetype/custom.ttf",
            font_size=32
        )
        filter_str = overlay.build_filter()
        assert "fontfile=" in filter_str
        assert "fontsize=32" in filter_str


class TestImageOverlay:
    """Test suite for ImageOverlay class."""
    
    def test_initialization(self):
        """Test ImageOverlay initialization."""
        overlay = ImageOverlay(
            image_path=Path("/tmp/test.png"),
            position=(100, 200),
            scale=0.5
        )
        assert overlay.image_path == Path("/tmp/test.png")
        assert overlay.position == (100, 200)
        assert overlay.scale == 0.5
    
    def test_build_filter(self):
        """Test build_filter method."""
        overlay = ImageOverlay(Path("/tmp/overlay.png"), (0, 0))
        filter_str = overlay.build_filter()
        assert "overlay" in filter_str
    
    def test_with_opacity(self):
        """Test overlay with opacity."""
        overlay = ImageOverlay(
            Path("/tmp/test.png"),
            position=(0, 0),
            opacity=0.7
        )
        filter_str = overlay.build_filter()
        # Check for opacity handling
        assert overlay.opacity == 0.7


class TestVideoOverlay:
    """Test suite for VideoOverlay class."""
    
    def test_initialization(self):
        """Test VideoOverlay initialization."""
        overlay = VideoOverlay(
            video_path=Path("/tmp/video.mp4"),
            position=(50, 50),
            scale=0.8,
            loop=True
        )
        assert overlay.video_path == Path("/tmp/video.mp4")
        assert overlay.position == (50, 50)
        assert overlay.scale == 0.8
        assert overlay.loop is True
    
    def test_build_filter(self):
        """Test build_filter method."""
        overlay = VideoOverlay(Path("/tmp/overlay.mp4"), (10, 10))
        filter_str = overlay.build_filter()
        assert isinstance(filter_str, str)
    
    def test_no_loop(self):
        """Test video overlay without looping."""
        overlay = VideoOverlay(
            Path("/tmp/video.mp4"),
            position=(0, 0),
            loop=False
        )
        assert overlay.loop is False


class TestOverlayManager:
    """Test suite for OverlayManager class."""
    
    def test_initialization(self):
        """Test OverlayManager initialization."""
        manager = OverlayManager()
        assert manager.overlays == []
    
    def test_add_overlay(self):
        """Test adding overlays."""
        manager = OverlayManager()
        text_overlay = TextOverlay("Test", (0, 0))
        manager.add_overlay(text_overlay)
        assert len(manager.overlays) == 1
        assert manager.overlays[0] == text_overlay
    
    def test_add_multiple_overlays(self):
        """Test adding multiple overlays."""
        manager = OverlayManager()
        text = TextOverlay("Text", (0, 0))
        image = ImageOverlay(Path("/tmp/img.png"), (10, 10))
        
        manager.add_overlay(text)
        manager.add_overlay(image)
        
        assert len(manager.overlays) == 2
    
    def test_build_filter_complex(self):
        """Test building filter complex."""
        manager = OverlayManager()
        text = TextOverlay("Test", (0, 0))
        manager.add_overlay(text)
        
        filter_complex = manager.build_filter_complex()
        assert isinstance(filter_complex, str)
    
    def test_clear_overlays(self):
        """Test clearing overlays."""
        manager = OverlayManager()
        manager.add_overlay(TextOverlay("Test", (0, 0)))
        assert len(manager.overlays) == 1
        
        manager.clear()
        assert len(manager.overlays) == 0
    
    def test_apply_overlays(self):
        """Test applying overlays to video."""
        manager = OverlayManager()
        manager.add_overlay(TextOverlay("Test", (0, 0)))
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = manager.apply_overlays(
                Path("/tmp/input.mp4"),
                Path("/tmp/output.mp4")
            )
            
            assert result is True
            mock_run.assert_called_once()
