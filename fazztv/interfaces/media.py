"""Media processing interface protocols for FazzTV."""

from typing import Protocol, List, Tuple, Callable, Optional, Any, Dict
from abc import abstractmethod
from pathlib import Path

from fazztv.models import MediaItem


class MediaProcessorProtocol(Protocol):
    """Protocol for media processing components."""

    @abstractmethod
    def process_media(self, media_item: MediaItem, **kwargs: Any) -> bool:
        """Process a media item."""
        ...

    @abstractmethod
    def validate_media(self, media_item: MediaItem) -> bool:
        """Validate a media item."""
        ...


class SerializerProtocol(Protocol):
    """Protocol for media serialization."""

    @abstractmethod
    def serialize_media_item(
        self,
        media_item: MediaItem,
        **kwargs: Any
    ) -> bool:
        """Serialize a media item."""
        ...

    @abstractmethod
    def get_output_path(self, media_item: MediaItem) -> Path:
        """Get the output path for a serialized media item."""
        ...

    @abstractmethod
    def validate_output(self, output_path: Path) -> bool:
        """Validate the serialized output."""
        ...


class BroadcasterProtocol(Protocol):
    """Protocol for broadcasting components."""

    @abstractmethod
    def broadcast_item(self, media_item: MediaItem) -> bool:
        """Broadcast a single media item."""
        ...

    @abstractmethod
    def broadcast_collection(
        self,
        media_items: List[MediaItem],
        filter_func: Optional[Callable[[MediaItem], bool]] = None
    ) -> List[Tuple[MediaItem, bool]]:
        """Broadcast a collection of media items."""
        ...

    @abstractmethod
    def check_broadcast_status(self) -> bool:
        """Check if broadcaster is ready."""
        ...


class DownloaderProtocol(Protocol):
    """Protocol for media downloading components."""

    @abstractmethod
    def download(self, url: str, output_path: Path) -> bool:
        """Download media from URL."""
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for media."""
        ...

    @abstractmethod
    def get_random_result(self, query: str, limit: int = 5) -> Optional[Tuple[str, str]]:
        """Get random search result."""
        ...


class CacheProtocol(Protocol):
    """Protocol for caching components."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        ...


class MediaManagerProtocol(Protocol):
    """Protocol for comprehensive media management."""

    @abstractmethod
    def create_media_item(
        self,
        artist: str,
        length_percent: int = 10,
        **kwargs: Any
    ) -> Optional[MediaItem]:
        """Create a media item."""
        ...

    @abstractmethod
    def create_media_collection(
        self,
        artists: List[str],
        randomize_length: bool = True,
        **kwargs: Any
    ) -> List[MediaItem]:
        """Create a collection of media items."""
        ...

    @abstractmethod
    def process_collection(
        self,
        media_items: List[MediaItem],
        **kwargs: Any
    ) -> List[MediaItem]:
        """Process a collection of media items."""
        ...


class PlaylistProtocol(Protocol):
    """Protocol for playlist management."""

    @abstractmethod
    def add_item(self, media_item: MediaItem) -> None:
        """Add item to playlist."""
        ...

    @abstractmethod
    def remove_item(self, media_item: MediaItem) -> bool:
        """Remove item from playlist."""
        ...

    @abstractmethod
    def get_items(self) -> List[MediaItem]:
        """Get all items in playlist."""
        ...

    @abstractmethod
    def shuffle(self) -> None:
        """Shuffle playlist order."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear playlist."""
        ...