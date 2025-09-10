"""Media item model for FazzTV."""

from typing import Optional
from pathlib import Path
from dataclasses import dataclass

from fazztv.models.exceptions import ValidationError


@dataclass
class MediaItem:
    """Represents a media item to be broadcast."""
    
    artist: str
    song: str
    url: str
    taxprompt: str
    length_percent: int = 100
    duration: Optional[int] = None
    serialized: Optional[Path] = None
    
    def __post_init__(self):
        """Validate media item after initialization."""
        if not 1 <= self.length_percent <= 100:
            raise ValidationError(f"length_percent must be between 1 and 100, got {self.length_percent}")
        
        if not self.artist:
            raise ValidationError("Artist name is required")
        
        if not self.song:
            raise ValidationError("Song title is required")
        
        if not self.url:
            raise ValidationError("URL is required")
        
        # Convert serialized to Path if it's a string
        if self.serialized and not isinstance(self.serialized, Path):
            self.serialized = Path(self.serialized)
    
    def is_serialized(self) -> bool:
        """Check if the media item has been serialized."""
        return self.serialized is not None and self.serialized.exists()
    
    def get_display_title(self) -> str:
        """Get formatted display title."""
        return f"{self.artist} - {self.song}"
    
    def get_filename_safe_title(self) -> str:
        """Get title safe for use as filename."""
        import re
        title = self.get_display_title()
        # Remove or replace invalid filename characters
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        return safe_title.strip('. ')
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "artist": self.artist,
            "song": self.song,
            "url": self.url,
            "taxprompt": self.taxprompt,
            "length_percent": self.length_percent,
            "duration": self.duration,
            "serialized": str(self.serialized) if self.serialized else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MediaItem":
        """Create MediaItem from dictionary."""
        return cls(
            artist=data.get("artist", ""),
            song=data.get("song", ""),
            url=data.get("url", ""),
            taxprompt=data.get("taxprompt", ""),
            length_percent=data.get("length_percent", 100),
            duration=data.get("duration"),
            serialized=Path(data["serialized"]) if data.get("serialized") else None
        )
    
    def __str__(self) -> str:
        """Return string representation."""
        return self.get_display_title()
    
    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"MediaItem(artist='{self.artist}', song='{self.song}', "
            f"url='{self.url[:30]}...', length={self.length_percent}%)"
        )