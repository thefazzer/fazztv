"""Comprehensive unit tests for EqualizerGenerator."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from fazztv.processors.equalizer import EqualizerGenerator


class TestEqualizerGenerator:
    """Test suite for EqualizerGenerator class."""
    
    def test_init_default_params(self):
        """Test initialization with default parameters."""
        gen = EqualizerGenerator()
        
        assert gen.bands == 4
        assert gen.height == 200
        assert gen.width == 1280
        assert gen.colors == ["0xFFFFFFFF"] * 4
        assert len(gen.frequencies) == 4
        assert gen.frequencies[0] == (40, 20)
        assert gen.frequencies[1] == (155, 95)
        assert gen.frequencies[2] == (375, 125)
        assert gen.frequencies[3] == (1250, 750)
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        colors = ["0xFF0000FF", "0x00FF00FF", "0x0000FFFF"]
        gen = EqualizerGenerator(
            bands=3,
            height=400,
            width=1920,
            colors=colors
        )
        
        assert gen.bands == 3
        assert gen.height == 400
        assert gen.width == 1920
        assert gen.colors == colors
        assert len(gen.frequencies) == 4  # Still has 4 frequencies defined
    
    def test_build_filter_complex_default(self):
        """Test build_filter_complex with default parameters."""
        gen = EqualizerGenerator()
        result = gen.build_filter_complex()
        
        # Check that result is a non-empty string
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Check for expected filter components
        assert "bandpass" in result
        assert "showvolume" in result
        assert "hstack" in result
        assert "scale=" in result
        assert "color=black" in result
        assert "overlay" in result
        assert "vstack" in result
        assert "[final]" in result
    
    def test_build_filter_complex_custom_io(self):
        """Test build_filter_complex with custom input/output."""
        gen = EqualizerGenerator()
        result = gen.build_filter_complex(
            audio_input="2:a",
            video_output="video_main"
        )
        
        assert "[2:a]" in result
        assert "[video_main]" in result
    
    def test_build_filter_complex_structure(self):
        """Test the structure of generated filter complex."""
        gen = EqualizerGenerator(bands=2)
        result = gen.build_filter_complex()
        
        # Should have multiple filter sections separated by semicolons
        sections = result.split(";")
        assert len(sections) > 5
        
        # Check for band outputs
        assert "band0" in result
        assert "band1" in result
        
        # Check for stacking operations
        assert "hstack=inputs=2" in result
    
    def test_build_band_filter(self):
        """Test _build_band_filter method."""
        gen = EqualizerGenerator()
        result = gen._build_band_filter(
            audio_input="1:a",
            band_index=0,
            frequency=100,
            bandwidth=50,
            color="0xFF0000FF"
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Check for expected filter components
        assert "bandpass=frequency=100:width=50" in result
        assert "showvolume" in result
        assert "0xFF0000FF" in result
        assert "crop" in result
        assert "scale" in result
        assert "smartblur" in result
        assert "minterpolate" in result
        assert "vflip" in result
        assert "vstack" in result
        assert "format=rgba" in result
        assert "pad" in result
        assert "[band0]" in result
    
    def test_build_band_filter_different_indices(self):
        """Test _build_band_filter with different band indices."""
        gen = EqualizerGenerator()
        
        result1 = gen._build_band_filter("1:a", 0, 100, 50, "0xFF0000FF")
        result2 = gen._build_band_filter("1:a", 1, 200, 100, "0x00FF00FF")
        result3 = gen._build_band_filter("1:a", 2, 300, 150, "0x0000FFFF")
        
        # Check unique labels for each band
        assert "[b0" in result1 and "[band0]" in result1
        assert "[b1" in result2 and "[band1]" in result2
        assert "[b2" in result3 and "[band2]" in result3
        
        # Check different frequencies
        assert "frequency=100" in result1
        assert "frequency=200" in result2
        assert "frequency=300" in result3
    
    def test_build_simple_visualizer_line(self):
        """Test build_simple_visualizer with line style."""
        gen = EqualizerGenerator()
        result = gen.build_simple_visualizer(
            audio_input="1:a",
            style="line"
        )
        
        assert isinstance(result, str)
        assert "showwaves" in result
        assert f"s={gen.width}x{gen.height}" in result
        assert "mode=line" in result
        assert "rate=25" in result
        assert "colors=white" in result
        assert "[viz]" in result
    
    def test_build_simple_visualizer_bar(self):
        """Test build_simple_visualizer with bar style."""
        gen = EqualizerGenerator()
        result = gen.build_simple_visualizer(
            audio_input="2:a",
            style="bar"
        )
        
        assert isinstance(result, str)
        assert "showfreqs" in result
        assert f"s={gen.width}x{gen.height}" in result
        assert "mode=bar" in result
        assert "cmode=separate" in result
        assert "colors=white" in result
        assert "[viz]" in result
    
    def test_build_simple_visualizer_dot(self):
        """Test build_simple_visualizer with dot style."""
        gen = EqualizerGenerator()
        result = gen.build_simple_visualizer(
            audio_input="3:a",
            style="dot"
        )
        
        assert isinstance(result, str)
        assert "showwaves" in result
        assert f"s={gen.width}x{gen.height}" in result
        assert "mode=point" in result
        assert "rate=25" in result
        assert "colors=white" in result
        assert "[viz]" in result
    
    def test_build_simple_visualizer_unknown_style(self):
        """Test build_simple_visualizer with unknown style."""
        gen = EqualizerGenerator()
        
        with patch('fazztv.processors.equalizer.logger') as mock_logger:
            result = gen.build_simple_visualizer(
                audio_input="1:a",
                style="unknown"
            )
            
            # Should log warning
            mock_logger.warning.assert_called_once_with(
                "Unknown visualizer style: unknown, using line"
            )
            
            # Should fall back to line style
            assert "showwaves" in result
            assert "mode=line" in result
    
    def test_build_simple_visualizer_custom_dimensions(self):
        """Test build_simple_visualizer with custom dimensions."""
        gen = EqualizerGenerator(width=1920, height=1080)
        result = gen.build_simple_visualizer(style="line")
        
        assert "s=1920x1080" in result
    
    def test_multiple_bands_filter_complex(self):
        """Test filter complex generation with different band counts."""
        gen2 = EqualizerGenerator(bands=2)
        gen4 = EqualizerGenerator(bands=4)
        
        result2 = gen2.build_filter_complex()
        result4 = gen4.build_filter_complex()
        
        assert "hstack=inputs=2" in result2
        assert "hstack=inputs=4" in result4
        
        # Check band outputs  
        assert "band0" in result2 and "band1" in result2
        # Only check up to band3 since generator only defines 4 frequency bands
        assert all(f"band{i}" in result4 for i in range(4))
    
    def test_color_cycling(self):
        """Test color cycling when bands exceed colors."""
        colors = ["0xFF0000FF", "0x00FF00FF"]
        gen = EqualizerGenerator(bands=5, colors=colors)
        
        # When building filter, colors should cycle
        result = gen.build_filter_complex()
        
        # Check that all bands are generated
        for i in range(5):
            assert f"band{i}" in result
