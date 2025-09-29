"""Utility functions for GUID management in episodes."""

import uuid
from typing import Dict, Any
from loguru import logger


def ensure_guid(episode: Dict[str, Any]) -> str:
    """
    Ensure an episode has a GUID, generating one if needed.

    Args:
        episode: Episode dictionary to check/update

    Returns:
        The episode's GUID (existing or newly generated)
    """
    if 'guid' not in episode or not episode['guid']:
        episode['guid'] = str(uuid.uuid4())
        logger.info(f"Generated new GUID {episode['guid']} for episode '{episode.get('title', 'Unknown')}'")
    return episode['guid']


def validate_guid_format(guid: str) -> bool:
    """
    Validate if a string is a properly formatted UUID.

    Args:
        guid: String to validate

    Returns:
        True if valid UUID format, False otherwise
    """
    try:
        uuid.UUID(str(guid))
        return True
    except (ValueError, TypeError):
        return False


def generate_unique_id(prefix: str = "") -> str:
    """
    Generate a unique identifier with optional prefix.

    Args:
        prefix: Optional prefix for the generated ID

    Returns:
        Unique identifier string
    """
    unique_id = str(uuid.uuid4())
    return f"{prefix}_{unique_id}" if prefix else unique_id