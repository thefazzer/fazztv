import re
import os
from dataclasses import dataclass, field
from typing import Optional, Union, BinaryIO
from loguru import logger

@dataclass
class MediaItem:
    """Structured representation of a media item for streaming."""
    artist: str
    song: str
    url: str
    taxprompt: str
    length_percent: int = 100
    _serialized: Optional[Union[bytes, str, BinaryIO]] = None
    
    def __post_init__(self):
        """Validate the MediaItem after initialization."""
        if not self.artist or not isinstance(self.artist, str):
            raise ValueError("Artist must be a non-empty string")
        
        if not self.song or not isinstance(self.song, str):
            raise ValueError("Song must be a non-empty string")
        
        # Basic YouTube URL validation
        youtube_pattern = r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$'
        if not re.match(youtube_pattern, self.url):
            raise ValueError(f"Invalid YouTube URL: {self.url}")
        
        if not self.taxprompt or not isinstance(self.taxprompt, str):
            raise ValueError("Tax prompt must be a non-empty string")
        
        if not isinstance(self.length_percent, int) or self.length_percent <= 0 or self.length_percent > 100:
            raise ValueError("Length percentage must be an integer between 1 and 100")
    
    @property
    def serialized(self):
        """Get the serialized stream data."""
        return self._serialized
    
    @serialized.setter
    def serialized(self, value):
        """Set the serialized stream data."""
        self._serialized = value
    
    def is_serialized(self) -> bool:
        """Check if the media item has been serialized."""
        return self._serialized is not None
    
    def __str__(self):
        return f"{self.artist} - {self.song} ({self.length_percent}%)"