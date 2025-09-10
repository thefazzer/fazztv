"""
FazzTV - Automated Video Broadcasting System

A modular Python framework for automated video broadcasting to RTMP endpoints,
featuring dynamic content generation, overlay management, and media processing.

Key Components:
    - Broadcasting: RTMP streaming and media serialization
    - API Integration: OpenRouter and YouTube API clients
    - Media Processing: Video downloading, caching, and transformation
    - Configuration: Flexible settings management with environment support
    - Data Management: Persistent storage and caching layers
"""

__version__ = "1.0.0"
__author__ = "FazzTV Development Team"

from fazztv.models import MediaItem
from fazztv.broadcaster import RTMPBroadcaster
from fazztv.serializer import MediaSerializer
from fazztv.config.settings import Settings

__all__ = [
    "MediaItem",
    "RTMPBroadcaster", 
    "MediaSerializer",
    "Settings",
]