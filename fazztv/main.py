"""
FazzTV Main Entry Point

Orchestrates the video broadcasting pipeline with modular components.
"""

import random
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger

from fazztv.models import MediaItem
from fazztv.broadcasting.serializer import MediaSerializer
from fazztv.broadcaster import RTMPBroadcaster
from fazztv.config.settings import Settings
from fazztv.config import constants
from fazztv.api.openrouter import OpenRouterClient
from fazztv.api.youtube import YouTubeSearchClient
from fazztv.data.shows import FTV_SHOWS
from fazztv.data.artists import SINGERS
from fazztv.utils.ascii_art import print_banner
from fazztv.core.container import DIContainer
from fazztv.core.logging import initialize_logging, get_logger, LogLevel, LogFormat
from fazztv.core.validation import validate_config, ValidationSeverity
from fazztv.core.error_handling import handle_errors, ErrorSeverity
from fazztv.interfaces.media import MediaManagerProtocol
from fazztv.interfaces.api import YouTubeClientProtocol, AIClientProtocol


class FazzTVApplication(MediaManagerProtocol):
    """Main application class for FazzTV broadcasting system."""
    
    def __init__(self, settings: Optional[Settings] = None, container: Optional[DIContainer] = None) -> None:
        """
        Initialize the FazzTV application.

        Args:
            settings: Optional settings (creates default if None)
            container: Optional DI container for dependency injection
        """
        self.settings = settings or Settings()
        self.container = container or DIContainer()
        print_banner('full')  # Display City Driver banner on startup
        self._setup_logging()
        self._validate_configuration()
        self._register_services()
        self._initialize_services()
    
    def _setup_logging(self):
        """Configure logging based on settings."""
        initialize_logging(
            level=LogLevel[self.settings.log_level.upper()],
            format_type=LogFormat.STRUCTURED if self.settings.log_level == "DEBUG" else LogFormat.STANDARD,
            file_path=self.settings.log_file,
            rotation=self.settings.log_max_size
        )
        self.logger = get_logger(__name__)
    
    def _validate_configuration(self):
        """Validate application configuration."""
        result = validate_config(self.settings)
        if not result.is_valid:
            critical_issues = result.get_critical_issues()
            if critical_issues:
                for issue in critical_issues:
                    logger.critical(f"Configuration error: {issue.message}")
                raise ValueError("Invalid configuration: critical issues found")

            for issue in result.warnings:
                logger.warning(f"Configuration warning: {issue.message}")

    def _register_services(self):
        """Register services with DI container."""
        # Register settings as singleton
        self.container.register_singleton(Settings, lambda: self.settings)

        # Register API clients
        self.container.register_singleton(
            OpenRouterClient,
            lambda: OpenRouterClient(self.settings.openrouter_api_key)
        )
        self.container.register_singleton(
            YouTubeSearchClient,
            lambda: YouTubeSearchClient(self.settings.search_limit)
        )

        # Register media processing
        self.container.register_singleton(
            MediaSerializer,
            lambda: MediaSerializer(
                base_res=self.settings.base_resolution,
                fade_length=self.settings.fade_length,
                marquee_duration=self.settings.marquee_duration,
                scroll_speed=self.settings.scroll_speed,
                logo_path="fztv-logo.png" if self.settings.enable_logo else None
            )
        )

        # Register broadcaster
        self.container.register_singleton(
            RTMPBroadcaster,
            lambda: RTMPBroadcaster(rtmp_url=self.settings.rtmp_url)
        )

    def _initialize_services(self):
        """Initialize all service dependencies from DI container."""
        # Resolve services from container
        self.api_client = self.container.resolve(OpenRouterClient)
        self.youtube_client = self.container.resolve(YouTubeSearchClient)
        self.serializer = self.container.resolve(MediaSerializer)
        self.broadcaster = self.container.resolve(RTMPBroadcaster)
    
    @handle_errors("media_creation", "FazzTVApplication")
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
    
    @handle_errors("media_collection", "FazzTVApplication")
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
            length_percent = (
                random.randint(50, 100) if randomize_length else 100
            )
            media_item = self.create_media_item(artist, length_percent)
            
            if media_item:
                media_items.append(media_item)
                logger.info(f"Created media item for {artist}")
            else:
                logger.warning(f"Failed to create media item for {artist}")
        
        logger.info(f"Created {len(media_items)}/{len(artists)} media items")
        return media_items
    
    @handle_errors("serialization", "FazzTVApplication")
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
            if self.serializer.serialize_media_item(
                    item, ftv_shows=shows
            ):
                serialized_items.append(item)
                logger.info(
                    f"Serialized media item for {item.artist}"
                )
            else:
                logger.warning(
                    f"Failed to serialize media item for {item.artist}"
                )
        
        logger.info(
            f"Serialized {len(serialized_items)}/{len(media_items)} "
            "media items"
        )
        return serialized_items
    
    @handle_errors("broadcasting", "FazzTVApplication")
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
            def filter_func(item):
                return True  # Accept all items by default
        
        results = self.broadcaster.broadcast_filtered_collection(
            media_items, filter_func
        )
        
        successful = sum(1 for _, success in results if success)
        logger.info(
            f"Successfully broadcast {successful}/{len(results)} "
            "media items"
        )
        
        return results
    
    def process_collection(self, media_items: List[MediaItem], **kwargs: Any) -> List[MediaItem]:
        """
        Process a collection of media items.

        Implements the MediaManagerProtocol requirement.

        Args:
            media_items: List of MediaItem instances to process
            **kwargs: Additional processing options

        Returns:
            List of processed MediaItem instances
        """
        include_shows = kwargs.get('include_shows', True)
        return self.serialize_collection(media_items, include_shows=include_shows)

    @handle_errors("pipeline_execution", "FazzTVApplication")
    def run(self, artists: Optional[List[str]] = None):
        """
        Run the full broadcast pipeline.
        
        Args:
            artists: Optional list of artists (uses default if not provided)
        """
        self.logger.info("=== Starting FazzTV broadcast ===")
        self.logger.info(f"Mode: {'Production' if self.settings.is_production() else 'Development'}")
        
        # Use provided artists or default list
        artists = artists or SINGERS
        
        # Create media collection
        media_items = self.create_media_collection(artists)
        
        if not media_items:
            self.logger.error("No media items created, aborting broadcast")
            return
        
        # Serialize media items
        serialized_items = self.serialize_collection(media_items)
        
        if not serialized_items:
            self.logger.error("No media items serialized, aborting broadcast")
            return
        
        # Broadcast media items
        self.broadcast_collection(serialized_items)
        
        self.logger.info("=== Finished FazzTV broadcast ===")


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


def main() -> None:
    """Main entry point for the application."""
    from fazztv.core.factory import create_application

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
        settings.rtmp_url = constants.DEFAULT_RTMP_URL

    if args.no_logo:
        settings.enable_logo = False

    if args.cache_dir:
        settings.cache_dir = Path(args.cache_dir)
        settings.cache_dir.mkdir(parents=True, exist_ok=True)

    # Create application using factory pattern with DI container
    app = create_application(settings=settings)
    app.run(artists=args.artists)


if __name__ == "__main__":
    main()