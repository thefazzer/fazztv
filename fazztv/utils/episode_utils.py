"""Utility functions for episode processing and validation."""

import os
import re
from typing import Dict, Any, Optional, List
from loguru import logger


def extract_song_name(title: str) -> str:
    """
    Extract song name from episode title.

    Args:
        title: Episode title containing song information

    Returns:
        Extracted song name or "Unknown Song" if extraction fails
    """
    song_match = re.match(r"^(.*?)\s*\(", title)
    return song_match.group(1).strip() if song_match else "Unknown Song"


def validate_episode_data(episode: Dict[str, Any], required_fields: Optional[List[str]] = None) -> bool:
    """
    Validate that an episode contains required fields.

    Args:
        episode: Episode dictionary to validate
        required_fields: List of required field names (defaults to ['title'])

    Returns:
        True if all required fields are present and non-empty
    """
    if required_fields is None:
        required_fields = ['title']

    for field in required_fields:
        if field not in episode or not str(episode.get(field, '')).strip():
            logger.warning(f"Episode missing or has empty required field: {field}")
            return False
    return True


def sanitize_text_for_overlay(text: str) -> str:
    """
    Sanitize text for use in video overlays.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text safe for video processing
    """
    return text.replace("'", r"\\'")


def get_episode_defaults(episode: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply default values for missing optional episode fields.

    Args:
        episode: Episode dictionary

    Returns:
        Episode dictionary with defaults applied
    """
    defaults = {
        'war_title': 'Unknown Historical Event',
        'commentary': 'No commentary available',
        'music_url': '',
        'video_url': '',
        'audio_file': '',
        'video_file': ''
    }

    for key, default_value in defaults.items():
        if key not in episode:
            episode[key] = default_value

    return episode


def validate_media_file(file_path: str) -> bool:
    """
    Validate that a media file exists and is not empty.

    Args:
        file_path: Path to the media file

    Returns:
        True if file exists and has non-zero size
    """
    if not file_path or not os.path.exists(file_path):
        return False

    return os.path.getsize(file_path) > 0


def get_alternative_url(episode: Dict[str, Any], url_type: str) -> Optional[str]:
    """
    Get alternative URL for media if available.

    Args:
        episode: Episode dictionary
        url_type: Type of URL ('music' or 'video')

    Returns:
        Alternative URL if available, None otherwise
    """
    alternative_key = f'alternative_{url_type}_url'
    return episode.get(alternative_key) if episode.get(alternative_key, '').strip() else None