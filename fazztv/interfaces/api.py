"""API interface protocols for FazzTV."""

from typing import Protocol, List, Dict, Any, Optional, Tuple
from abc import abstractmethod


class APIClientProtocol(Protocol):
    """Protocol for API client components."""

    @abstractmethod
    def make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Make an API request."""
        ...

    @abstractmethod
    def check_health(self) -> bool:
        """Check API health/availability."""
        ...

    @abstractmethod
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get rate limit information."""
        ...


class SearchClientProtocol(Protocol):
    """Protocol for search client components."""

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for content."""
        ...

    @abstractmethod
    def search_videos(
        self,
        query: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for videos."""
        ...

    @abstractmethod
    def get_random_video(
        self,
        query: str,
        limit: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a random video from search results."""
        ...


class ContentClientProtocol(Protocol):
    """Protocol for content retrieval clients."""

    @abstractmethod
    def get_content(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get content by identifier."""
        ...

    @abstractmethod
    def get_metadata(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get metadata for content."""
        ...

    @abstractmethod
    def validate_content(self, identifier: str) -> bool:
        """Validate that content exists and is accessible."""
        ...


class YouTubeClientProtocol(SearchClientProtocol, ContentClientProtocol):
    """Protocol specific to YouTube API clients."""

    @abstractmethod
    def search_music_video(
        self,
        artist: str,
        song: Optional[str] = None,
        official_only: bool = True
    ) -> Optional[Tuple[str, str]]:
        """Search for music videos."""
        ...

    @abstractmethod
    def search_documentary(
        self,
        topic: str,
        min_duration: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Search for documentaries."""
        ...

    @abstractmethod
    def search_by_category(
        self,
        category: str,
        artist: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search by content category."""
        ...

    @abstractmethod
    def get_video_url_by_id(self, video_id: str) -> str:
        """Get YouTube URL from video ID."""
        ...

    @abstractmethod
    def search_playlist(
        self,
        query: str,
        playlist_type: str = "playlist"
    ) -> List[Dict[str, Any]]:
        """Search for playlists."""
        ...

    @abstractmethod
    def get_trending_music(
        self,
        region: str = "US",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get trending music videos."""
        ...

    @abstractmethod
    def search_by_year(
        self,
        artist: str,
        year: int
    ) -> List[Dict[str, Any]]:
        """Search for content from specific year."""
        ...

    @abstractmethod
    def find_similar_videos(
        self,
        reference_title: str,
        exclude_artist: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find similar videos."""
        ...


class AIClientProtocol(Protocol):
    """Protocol for AI service clients."""

    @abstractmethod
    def generate_content(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> Optional[str]:
        """Generate content using AI."""
        ...

    @abstractmethod
    def get_tax_info(self, artist: str) -> str:
        """Get tax information for an artist."""
        ...

    @abstractmethod
    def analyze_content(
        self,
        content: str,
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """Analyze content."""
        ...


class OpenRouterClientProtocol(AIClientProtocol):
    """Protocol specific to OpenRouter API clients."""

    @abstractmethod
    def list_available_models(self) -> List[str]:
        """List available models."""
        ...

    @abstractmethod
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        ...


class ClientManagerProtocol(Protocol):
    """Protocol for managing multiple API clients."""

    @abstractmethod
    def register_client(self, name: str, client: APIClientProtocol) -> None:
        """Register an API client."""
        ...

    @abstractmethod
    def get_client(self, name: str) -> Optional[APIClientProtocol]:
        """Get a registered client."""
        ...

    @abstractmethod
    def list_clients(self) -> List[str]:
        """List all registered client names."""
        ...

    @abstractmethod
    def check_all_clients(self) -> Dict[str, bool]:
        """Check health of all clients."""
        ...