"""
FazzTV Main Entry Point

Orchestrates the video broadcasting pipeline with modular components.
"""

import random
import argparse
from typing import List, Optional
from loguru import logger

from fazztv.models import MediaItem
from fazztv.serializer import MediaSerializer
from fazztv.broadcaster import RTMPBroadcaster
from fazztv.config.settings import Settings
from fazztv.api.openrouter import OpenRouterClient
from fazztv.api.youtube import YouTubeSearchClient
from fazztv.data.shows import FTV_SHOWS
from fazztv.data.artists import SINGERS
from fazztv.utils.ascii_art import print_banner


class FazzTVApplication:
    """Main application class for FazzTV broadcasting system."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the FazzTV application.

        Args:
            settings: Optional settings instance (creates default if not provided)
        """
        self.settings = settings or Settings()
        print_banner('full')  # Display City Driver banner on startup
        self._setup_logging()
        self._initialize_services()
    
    def _setup_logging(self):
        """Configure logging based on settings."""
        logger.add(
            self.settings.log_file,
            rotation=self.settings.log_max_size,
            level=self.settings.log_level
        )
    
    def _initialize_services(self):
        """Initialize all service dependencies."""
        # API Clients
        self.api_client = OpenRouterClient(self.settings.openrouter_api_key)
        self.youtube_client = YouTubeSearchClient(self.settings.search_limit)
        
        # Media Processing
        self.serializer = MediaSerializer(
            base_res=self.settings.base_resolution,
            fade_length=self.settings.fade_length,
            marquee_duration=self.settings.marquee_duration,
            scroll_speed=self.settings.scroll_speed,
            logo_path="fztv-logo.png" if self.settings.enable_logo else None
        )
        
        # Broadcasting
        self.broadcaster = RTMPBroadcaster(rtmp_url=self.settings.rtmp_url)
    
    def create_media_item(
        self,
        artist: str,
        length_percent: int = 10
    ) -> Optional[MediaItem]:
        """
        Create a MediaItem for the given artist.
        
        Args:
            artist: The artist name
            length_percent: Percentage of original media to use
            
        Returns:
            MediaItem instance or None if creation failed
        """
        # Search for music video
        result = self.youtube_client.search_music_video(artist)
        if not result:
            logger.error(f"Could not find music video for {artist}")
            return None
        
        url, song = result
        
        # Get tax information
        taxprompt = self._get_safe_tax_info(artist)
        
        try:
            media_item = MediaItem(
                artist=artist,
                song=song,
                url=url,
                taxprompt=taxprompt,
                length_percent=length_percent
            )
            return media_item
        except ValueError as e:
            logger.error(f"Error creating MediaItem for {artist}: {e}")
            return None
    
    def _get_safe_tax_info(self, artist: str) -> str:
        """
        Safely get tax information for an artist.
        
        Args:
            artist: The artist name
            
        Returns:
            Tax information string or error message
        """
        logger.debug(f"Requesting tax info for {artist}...")
        try:
            return self.api_client.get_tax_info(artist)
        except Exception as e:
            logger.error(f"Error getting tax info for {artist}: {e}")
            return "Tax information unavailable."
    
    def create_media_collection(
        self,
        artists: List[str],
        randomize_length: bool = True
    ) -> List[MediaItem]:
        """
        Create a collection of media items for multiple artists.
        
        Args:
            artists: List of artist names
            randomize_length: Whether to randomize clip lengths
            
        Returns:
            List of successfully created MediaItem instances
        """
        media_items = []
        
        for artist in artists:
            length_percent = random.randint(50, 100) if randomize_length else 100
            media_item = self.create_media_item(artist, length_percent)
            
            if media_item:
                media_items.append(media_item)
                logger.info(f"Created media item for {artist}")
            else:
                logger.warning(f"Failed to create media item for {artist}")
        
        logger.info(f"Created {len(media_items)}/{len(artists)} media items")
        return media_items
    
    def serialize_collection(
        self,
        media_items: List[MediaItem],
        include_shows: bool = True
    ) -> List[MediaItem]:
        """
        Serialize a collection of media items.
        
        Args:
            media_items: List of MediaItem instances to serialize
            include_shows: Whether to include show information
            
        Returns:
            List of successfully serialized MediaItem instances
        """
        serialized_items = []
        shows = FTV_SHOWS if include_shows else None
        
        for item in media_items:
            if self.serializer.serialize_media_item(item, ftv_shows=shows):
                serialized_items.append(item)
                logger.info(f"Serialized media item for {item.artist}")
            else:
                logger.warning(f"Failed to serialize media item for {item.artist}")
        
        logger.info(f"Serialized {len(serialized_items)}/{len(media_items)} media items")
        return serialized_items
    
    def broadcast_collection(
        self,
        media_items: List[MediaItem],
        filter_func=None
    ) -> List[tuple]:
        """
        Broadcast a collection of media items.
        
        Args:
            media_items: List of MediaItem instances to broadcast
            filter_func: Optional filter function for items
            
        Returns:
            List of (MediaItem, success) tuples
        """
        if filter_func is None:
            filter_func = lambda item: True  # Accept all items by default
        
        results = self.broadcaster.broadcast_filtered_collection(media_items, filter_func)
        
        successful = sum(1 for _, success in results if success)
        logger.info(f"Successfully broadcast {successful}/{len(results)} media items")
        
        return results
    
    def run(self, artists: Optional[List[str]] = None):
        """
        Run the full broadcast pipeline.
        
        Args:
            artists: Optional list of artists (uses default if not provided)
        """
        logger.info("=== Starting FazzTV broadcast ===")
        logger.info(f"Mode: {'Production' if self.settings.is_production() else 'Development'}")
        
        # Use provided artists or default list
        artists = artists or SINGERS
        
        # Create media collection
        media_items = self.create_media_collection(artists)
        
        if not media_items:
            logger.error("No media items created, aborting broadcast")
            return
        
        # Serialize media items
        serialized_items = self.serialize_collection(media_items)
        
        if not serialized_items:
            logger.error("No media items serialized, aborting broadcast")
            return
        
        # Broadcast media items
        self.broadcast_collection(serialized_items)
        
        logger.info("=== Finished FazzTV broadcast ===")


def create_parser() -> argparse.ArgumentParser:
    """
    Create command-line argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="FazzTV - Automated Video Broadcasting System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--artists",
        nargs="+",
        help="List of artists to broadcast (uses default if not specified)"
    )
    
    parser.add_argument(
        "--stream-key",
        help="YouTube stream key for live broadcasting"
    )
    
    parser.add_argument(
        "--env-file",
        help="Path to environment file (defaults to .env)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode (local RTMP server)"
    )
    
    parser.add_argument(
        "--no-logo",
        action="store_true",
        help="Disable logo overlay"
    )
    
    parser.add_argument(
        "--cache-dir",
        help="Directory for caching downloaded media"
    )
    
    return parser


def main():
    """Main entry point for the application."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Create settings with command-line overrides
    settings = Settings(env_file=args.env_file)
    
    # Apply command-line overrides
    if args.stream_key:
        settings.stream_key = args.stream_key
        settings.rtmp_url = settings._build_rtmp_url()
    
    if args.log_level:
        settings.log_level = args.log_level
    
    if args.test_mode:
        settings.stream_key = None
        settings.rtmp_url = "rtmp://127.0.0.1:1935/live/test"
    
    if args.no_logo:
        settings.enable_logo = False
    
    if args.cache_dir:
        from pathlib import Path
        settings.cache_dir = Path(args.cache_dir)
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Create and run application
    app = FazzTVApplication(settings)
    app.run(artists=args.artists)


if __name__ == "__main__":
    main()