"""
Media item models for FazzTV broadcasting system.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import os


@dataclass
class MediaItem:
    """
    Represents a media item to be broadcast.
    
    Attributes:
        artist: The artist name
        song: The song title
        url: The URL to the media
        taxprompt: The tax information to display
        length_percent: The percentage of the original media to use (1-100)
        duration: Explicit duration in seconds to limit the clip to
        serialized: Path to the serialized media file
        source_path: Path to the source media file
        metadata: Additional metadata for the media item
    """
    
    artist: str
    song: str
    url: str
    taxprompt: str
    length_percent: int = 100
    duration: Optional[int] = None
    serialized: Optional[str] = None
    source_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not 1 <= self.length_percent <= 100:
            raise ValueError(f"length_percent must be between 1 and 100, got {self.length_percent}")
        
        if self.duration is not None and self.duration <= 0:
            raise ValueError(f"duration must be positive, got {self.duration}")
    
    def is_serialized(self) -> bool:
        """
        Check if the media item has been serialized.
        
        Returns:
            True if the item has been serialized and the file exists
        """
        return self.serialized is not None and os.path.exists(self.serialized)
    
    def is_downloaded(self) -> bool:
        """
        Check if the source media has been downloaded.
        
        Returns:
            True if the source file exists
        """
        return self.source_path is not None and os.path.exists(self.source_path)
    
    def get_effective_duration(self, original_duration: float) -> float:
        """
        Calculate the effective duration for this media item.
        
        Args:
            original_duration: The original duration of the media in seconds
            
        Returns:
            The effective duration considering length_percent and duration limit
        """
        if self.duration is not None:
            return min(self.duration, original_duration)
        return original_duration * (self.length_percent / 100.0)
    
    def cleanup(self) -> None:
        """Remove temporary files associated with this media item."""
        for path_attr in ['serialized', 'source_path']:
            path = getattr(self, path_attr, None)
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    setattr(self, path_attr, None)
                except OSError as e:
                    from loguru import logger
                    logger.warning(f"Could not remove {path}: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the media item to a dictionary.
        
        Returns:
            Dictionary representation of the media item
        """
        return {
            "artist": self.artist,
            "song": self.song,
            "url": self.url,
            "taxprompt": self.taxprompt[:100] + "..." if len(self.taxprompt) > 100 else self.taxprompt,
            "length_percent": self.length_percent,
            "duration": self.duration,
            "is_serialized": self.is_serialized(),
            "is_downloaded": self.is_downloaded(),
            "metadata": self.metadata
        }
    
    def __str__(self) -> str:
        """Return a string representation of the MediaItem."""
        return f"{self.artist} - {self.song}"
    
    def __repr__(self) -> str:
        """Return a detailed string representation of the MediaItem."""
        return (
            f"MediaItem(artist='{self.artist}', song='{self.song}', "
            f"length_percent={self.length_percent}, "
            f"serialized={self.is_serialized()})"
        )