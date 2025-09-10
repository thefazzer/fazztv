"""Episode model for FazzTV."""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

from fazztv.models.exceptions import ValidationError


@dataclass
class Episode:
    """Represents a broadcast episode."""
    
    title: str
    music_url: str
    guid: str = field(default_factory=lambda: str(uuid.uuid4()))
    war_title: Optional[str] = None
    war_url: Optional[str] = None
    commentary: Optional[str] = None
    alternative_music_url: Optional[str] = None
    release_date: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate episode after initialization."""
        if not self.title:
            raise ValidationError("Episode title is required")
        
        if not self.music_url:
            raise ValidationError("Music URL is required")
        
        if not self._is_valid_url(self.music_url):
            raise ValidationError(f"Invalid music URL: {self.music_url}")
        
        if self.alternative_music_url and not self._is_valid_url(self.alternative_music_url):
            raise ValidationError(f"Invalid alternative music URL: {self.alternative_music_url}")
        
        if self.war_url and not self._is_valid_url(self.war_url):
            raise ValidationError(f"Invalid war URL: {self.war_url}")
    
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Check if URL is valid."""
        return url.startswith(("http://", "https://"))
    
    def get_song_name(self) -> str:
        """Extract song name from title."""
        import re
        match = re.match(r"^(.*?)\s*\(", self.title)
        return match.group(1) if match else self.title
    
    def get_album_name(self) -> Optional[str]:
        """Extract album name from title."""
        import re
        match = re.search(r"\((.*?)\)", self.title)
        return match.group(1) if match else None
    
    def get_release_date_parsed(self) -> Optional[datetime]:
        """Parse release date string to datetime."""
        if not self.release_date:
            return None
        
        from fazztv.utils.datetime import parse_date
        date_obj = parse_date(self.release_date)
        
        if date_obj:
            return datetime.combine(date_obj, datetime.min.time())
        return None
    
    def calculate_days_old(self) -> int:
        """Calculate how many days old the episode is."""
        from fazztv.utils.datetime import calculate_days_old
        
        if self.release_date:
            return calculate_days_old(self.release_date)
        
        # Try to extract date from title
        import re
        date_match = re.search(r'- ([A-Za-z]+ \d{1,2} \d{4})$', self.title)
        if date_match:
            return calculate_days_old(date_match.group(1))
        
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "guid": self.guid,
            "title": self.title,
            "music_url": self.music_url,
            "war_title": self.war_title,
            "war_url": self.war_url,
            "commentary": self.commentary,
            "alternative_music_url": self.alternative_music_url,
            "release_date": self.release_date,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Episode":
        """Create Episode from dictionary."""
        return cls(
            guid=data.get("guid", str(uuid.uuid4())),
            title=data.get("title", ""),
            music_url=data.get("music_url", ""),
            war_title=data.get("war_title"),
            war_url=data.get("war_url"),
            commentary=data.get("commentary"),
            alternative_music_url=data.get("alternative_music_url"),
            release_date=data.get("release_date"),
            metadata=data.get("metadata", {})
        )
    
    def update_metadata(self, key: str, value: Any):
        """Update metadata field."""
        self.metadata[key] = value
        self.metadata["last_updated"] = datetime.now().isoformat()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)
    
    def __str__(self) -> str:
        """Return string representation."""
        return f"Episode: {self.title} (GUID: {self.guid[:8]}...)"
    
    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"Episode(title='{self.title[:30]}...', "
            f"guid='{self.guid[:8]}...', "
            f"war_title='{self.war_title[:20] if self.war_title else 'None'}...')"
        )