"""YouTube search API client for FazzTV."""

import random
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from loguru import logger

from fazztv.downloaders.youtube import YouTubeDownloader


class YouTubeSearchClient:
    """Client for YouTube search operations."""
    
    def __init__(self, search_limit: int = 5):
        """
        Initialize YouTube search client.
        
        Args:
            search_limit: Default number of search results
        """
        self.search_limit = search_limit
        self.downloader = YouTubeDownloader()
    
    def search_videos(
        self,
        query: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for videos on YouTube.
        
        Args:
            query: Search query
            limit: Number of results (uses default if None)
            
        Returns:
            List of video information dictionaries
        """
        limit = limit or self.search_limit
        return self.downloader.search(query, limit)
    
    def get_random_video(
        self,
        query: str,
        limit: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search and return a random video.
        
        Args:
            query: Search query
            limit: Number of results to choose from
            
        Returns:
            Random video info or None if no results
        """
        results = self.search_videos(query, limit)
        if results:
            return random.choice(results)
        return None
    
    def search_music_video(
        self,
        artist: str,
        song: Optional[str] = None,
        official_only: bool = True
    ) -> Optional[Tuple[str, str]]:
        """
        Search for a music video.
        
        Args:
            artist: Artist name
            song: Optional song name
            official_only: Whether to search for official videos only
            
        Returns:
            Tuple of (url, title) or None if not found
        """
        query_parts = [artist]
        
        if song:
            query_parts.append(song)
        
        if official_only:
            query_parts.append("official music video")
        else:
            query_parts.append("music video")
        
        query = " ".join(query_parts)
        result = self.downloader.get_random_result(query, self.search_limit)
        
        if result:
            logger.info(f"Found music video for {artist}: {result[1]}")
        else:
            logger.warning(f"No music video found for {artist}")
        
        return result
    
    def search_documentary(
        self,
        topic: str,
        min_duration: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search for documentaries on a topic.
        
        Args:
            topic: Documentary topic
            min_duration: Minimum duration in seconds
            
        Returns:
            Documentary info or None if not found
        """
        query = f"{topic} documentary"
        results = self.search_videos(query, self.search_limit * 2)
        
        if min_duration:
            # Filter by duration
            results = [r for r in results if r.get("duration", 0) >= min_duration]
        
        if results:
            # Prefer longer documentaries
            results.sort(key=lambda x: x.get("duration", 0), reverse=True)
            return results[0]
        
        return None
    
    def search_by_category(
        self,
        category: str,
        artist: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search videos by category.
        
        Args:
            category: Video category (e.g., "live performance", "interview")
            artist: Optional artist filter
            
        Returns:
            List of matching videos
        """
        query_parts = []
        
        if artist:
            query_parts.append(artist)
        
        query_parts.append(category)
        
        query = " ".join(query_parts)
        return self.search_videos(query)
    
    def get_video_url_by_id(self, video_id: str) -> str:
        """
        Get YouTube URL from video ID.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Full YouTube URL
        """
        return f"https://www.youtube.com/watch?v={video_id}"
    
    def search_playlist(
        self,
        query: str,
        playlist_type: str = "playlist"
    ) -> List[Dict[str, Any]]:
        """
        Search for playlists.
        
        Args:
            query: Search query
            playlist_type: Type of playlist to search for
            
        Returns:
            List of playlist information
        """
        full_query = f"{query} {playlist_type}"
        # Note: This returns individual videos, not playlists
        # Full playlist support would require additional implementation
        return self.search_videos(full_query)
    
    def get_trending_music(
        self,
        region: str = "US",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get trending music videos.
        
        Args:
            region: Region code
            limit: Number of results
            
        Returns:
            List of trending music videos
        """
        query = f"trending music {region} {datetime.now().year}"
        return self.search_videos(query, limit)
    
    def search_by_year(
        self,
        artist: str,
        year: int
    ) -> List[Dict[str, Any]]:
        """
        Search for videos from a specific year.
        
        Args:
            artist: Artist name
            year: Year to search
            
        Returns:
            List of videos from that year
        """
        query = f"{artist} {year}"
        return self.search_videos(query)
    
    def find_similar_videos(
        self,
        reference_title: str,
        exclude_artist: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find videos similar to a reference.
        
        Args:
            reference_title: Reference video title
            exclude_artist: Artist to exclude from results
            
        Returns:
            List of similar videos
        """
        # Extract keywords from title
        import re
        keywords = re.findall(r'\b\w+\b', reference_title.lower())
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        keywords = [k for k in keywords if k not in common_words]
        
        # Build search query
        query = " ".join(keywords[:5])  # Use top 5 keywords
        
        results = self.search_videos(query)
        
        # Filter out excluded artist if specified
        if exclude_artist:
            exclude_lower = exclude_artist.lower()
            results = [r for r in results if exclude_lower not in r.get("title", "").lower()]
        
        return results