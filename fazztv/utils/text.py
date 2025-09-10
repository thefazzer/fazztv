"""Text manipulation utilities for FazzTV."""

import re
from typing import Optional, Tuple


def sanitize_for_ffmpeg(text: str) -> str:
    """
    Sanitize text for use in FFmpeg filters.
    
    Args:
        text: Raw text string
        
    Returns:
        Sanitized text safe for FFmpeg
    """
    if not text:
        return ""
    
    # Replace newlines and carriage returns
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    # Escape special characters for FFmpeg
    text = text.replace("'", "\\'")
    text = text.replace(':', '\\:')
    text = text.replace(',', '\\,')
    text = text.replace(';', '\\;')
    text = text.replace('=', '\\=')
    text = text.replace('[', '\\[')
    text = text.replace(']', '\\]')
    text = text.replace('@', '\\@')
    
    # Remove any backslashes not part of escape sequences
    text = re.sub(r'[\\](?![\'[\]=,@:;])', '', text)
    
    return text


def extract_title_parts(title: str, delimiter: str = ":") -> Tuple[str, str]:
    """
    Extract main title and subtitle from a title string.
    
    Args:
        title: Full title string
        delimiter: Delimiter to split on
        
    Returns:
        Tuple of (main_title, subtitle)
    """
    if delimiter in title:
        parts = title.split(delimiter, 1)
        return parts[0].strip(), parts[1].strip()
    return title.strip(), ""


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    if max_length <= len(suffix):
        return suffix[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


def extract_song_info(title: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract song, album, and date information from a title.
    
    Args:
        title: Title string containing song information
        
    Returns:
        Tuple of (song_name, album, date_str)
    """
    # Pattern: "Song Name (Album Name) - Date"
    pattern = r"^(.*?)\s*(?:\((.*?)\))?\s*(?:-\s*(.*))?$"
    match = re.match(pattern, title)
    
    if match:
        song = match.group(1).strip() if match.group(1) else None
        album = match.group(2).strip() if match.group(2) else None
        date = match.group(3).strip() if match.group(3) else None
        return song, album, date
    
    return title, None, None


def clean_filename(filename: str, replacement: str = "_") -> str:
    """
    Clean a string to be safe for use as a filename.
    
    Args:
        filename: Raw filename
        replacement: Character to replace invalid characters with
        
    Returns:
        Cleaned filename
    """
    # Remove or replace invalid filename characters
    invalid_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(invalid_chars, replacement, filename)
    
    # Remove leading/trailing dots and spaces
    cleaned = cleaned.strip('. ')
    
    # Ensure it's not empty
    if not cleaned:
        cleaned = "unnamed"
    
    return cleaned


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "1:23:45" or "45:23")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def parse_resolution(resolution: str) -> Tuple[int, int]:
    """
    Parse resolution string to width and height.
    
    Args:
        resolution: Resolution string (e.g., "1920x1080")
        
    Returns:
        Tuple of (width, height)
        
    Raises:
        ValueError: If resolution format is invalid
    """
    match = re.match(r"(\d+)x(\d+)", resolution)
    if not match:
        raise ValueError(f"Invalid resolution format: {resolution}")
    
    return int(match.group(1)), int(match.group(2))