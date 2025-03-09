class MediaItem:
    """Represents a media item to be broadcast."""
    
    def __init__(self, artist: str, song: str, url: str, taxprompt: str, 
                 length_percent: int = 100, duration: Optional[int] = None):
        """
        Initialize a MediaItem.
        
        Args:
            artist: The artist name
            song: The song title
            url: The URL to the media
            taxprompt: The tax information to display
            length_percent: The percentage of the original media to use (1-100)
            duration: Explicit duration in seconds to limit the clip to
        """
        self.artist = artist
        self.song = song
        self.url = url
        self.taxprompt = taxprompt
        self.serialized = None
        
        if not 1 <= length_percent <= 100:
            raise ValueError("length_percent must be between 1 and 100")
        self.length_percent = length_percent
        
        self.duration = duration
    
    def is_serialized(self) -> bool:
        """Check if the media item has been serialized."""
        return self.serialized is not None and os.path.exists(self.serialized)
    
    def __str__(self) -> str:
        """Return a string representation of the MediaItem."""
        return f"{self.artist} - {self.song}"