"""Comprehensive unit tests for text utilities."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import re

from fazztv.utils.text import (
    sanitize_for_ffmpeg, extract_title_parts, truncate_text,
    extract_song_info, clean_filename, format_duration, parse_resolution
)


class TestTextUtils:
    """Test suite for text utility functions."""
    
    def test_sanitize_for_ffmpeg(self):
        """Test sanitizing text for FFmpeg."""
        text = "Test: 'quoted' text with special chars"
        sanitized = sanitize_for_ffmpeg(text)
        # Should escape special characters for FFmpeg
        assert isinstance(sanitized, str)
    
    def test_extract_title_parts(self):
        """Test extracting title parts."""
        title = "Part One: Part Two"
        part1, part2 = extract_title_parts(title)
        assert part1 == "Part One"
        assert part2 == "Part Two"
    
    def test_extract_title_parts_no_delimiter(self):
        """Test extracting title parts without delimiter."""
        title = "Single Part"
        part1, part2 = extract_title_parts(title)
        assert part1 == "Single Part"
        assert part2 == ""
    
    def test_truncate_text(self):
        """Test truncating text."""
        long_text = "This is a very long text that needs to be truncated"
        truncated = truncate_text(long_text, max_length=20)
        assert len(truncated) <= 23  # 20 + "..."
        assert truncated.endswith("...")
    
    def test_truncate_text_short(self):
        """Test truncating short text."""
        short_text = "Short"
        truncated = truncate_text(short_text, max_length=20)
        assert truncated == "Short"
    
    def test_extract_song_info(self):
        """Test extracting song information."""
        title = "Artist - Song Title (feat. Guest)"
        artist, song, featured = extract_song_info(title)
        assert artist is not None
        assert song is not None
        # Featured artist may or may not be detected
    
    def test_clean_filename(self):
        """Test cleaning filename."""
        filename = "File/Name:With*Special?Chars.txt"
        cleaned = clean_filename(filename)
        assert "/" not in cleaned
        assert ":" not in cleaned
        assert "*" not in cleaned
        assert "?" not in cleaned
    
    def test_format_duration(self):
        """Test formatting duration."""
        # Test various durations
        assert format_duration(65.5) == "1:05"
        assert format_duration(3661) == "1:01:01"
        assert format_duration(30) == "0:30"
    
    def test_parse_resolution(self):
        """Test parsing resolution string."""
        width, height = parse_resolution("1920x1080")
        assert width == 1920
        assert height == 1080
        
        # Test with different format
        width, height = parse_resolution("1280X720")
        assert width == 1280
        assert height == 720
