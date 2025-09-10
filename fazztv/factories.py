"""
Factory patterns for creating FazzTV objects.
"""

from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger

from fazztv.models import MediaItem
from fazztv.config.settings import Settings
from fazztv.broadcaster import RTMPBroadcaster
from fazztv.serializer import MediaSerializer
from fazztv.api.openrouter import OpenRouterClient
from fazztv.api.youtube import YouTubeSearchClient
from fazztv.exceptions import ConfigurationError, ValidationError


class MediaItemFactory:
    """Factory for creating MediaItem instances."""
    
    @staticmethod
    def create_from_dict(data: Dict[str, Any]) -> MediaItem:
        """
        Create a MediaItem from a dictionary.
        
        Args:
            data: Dictionary containing media item data
            
        Returns:
            MediaItem instance
            
        Raises:
            ValidationError: If required fields are missing
        """
        required_fields = ['artist', 'song', 'url', 'taxprompt']
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(
                    f"Missing required field: {field}",
                    field=field
                )
        
        return MediaItem(
            artist=data['artist'],
            song=data['song'],
            url=data['url'],
            taxprompt=data['taxprompt'],
            length_percent=data.get('length_percent', 100),
            duration=data.get('duration'),
            serialized=data.get('serialized'),
            source_path=data.get('source_path'),
            metadata=data.get('metadata', {})
        )
    
    @staticmethod
    def create_from_search_result(
        artist: str,
        search_result: Dict[str, Any],
        tax_info: str,
        length_percent: int = 100,
        duration: Optional[int] = None
    ) -> MediaItem:
        """
        Create a MediaItem from a YouTube search result.
        
        Args:
            artist: Artist name
            search_result: YouTube search result dictionary
            tax_info: Tax information text
            length_percent: Percentage of media to use
            duration: Optional duration limit
            
        Returns:
            MediaItem instance
        """
        return MediaItem(
            artist=artist,
            song=search_result.get('title', 'Unknown'),
            url=search_result.get('url', ''),
            taxprompt=tax_info,
            length_percent=length_percent,
            duration=duration,
            metadata={
                'youtube_id': search_result.get('id'),
                'original_duration': search_result.get('duration'),
                'view_count': search_result.get('view_count'),
                'upload_date': search_result.get('upload_date')
            }
        )


class ServiceFactory:
    """Factory for creating service instances."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the service factory.
        
        Args:
            settings: Settings instance (creates default if not provided)
        """
        self.settings = settings or Settings()
        self._validate_settings()
    
    def _validate_settings(self):
        """Validate settings for service creation."""
        if not self.settings.validate():
            raise ConfigurationError("Invalid settings configuration")
    
    def create_api_client(self) -> OpenRouterClient:
        """
        Create an OpenRouter API client.
        
        Returns:
            Configured OpenRouterClient instance
            
        Raises:
            ConfigurationError: If API key is not configured
        """
        if not self.settings.openrouter_api_key:
            raise ConfigurationError("OpenRouter API key not configured")
        
        return OpenRouterClient(self.settings.openrouter_api_key)
    
    def create_youtube_client(self) -> YouTubeSearchClient:
        """
        Create a YouTube search client.
        
        Returns:
            Configured YouTubeSearchClient instance
        """
        return YouTubeSearchClient(self.settings.search_limit)
    
    def create_serializer(self, logo_path: Optional[str] = None) -> MediaSerializer:
        """
        Create a media serializer.
        
        Args:
            logo_path: Optional path to logo file
            
        Returns:
            Configured MediaSerializer instance
        """
        if logo_path is None and self.settings.enable_logo:
            logo_path = "fztv-logo.png"
        elif not self.settings.enable_logo:
            logo_path = None
        
        return MediaSerializer(
            base_res=self.settings.base_resolution,
            fade_length=self.settings.fade_length,
            marquee_duration=self.settings.marquee_duration,
            scroll_speed=self.settings.scroll_speed,
            logo_path=logo_path
        )
    
    def create_broadcaster(self, rtmp_url: Optional[str] = None) -> RTMPBroadcaster:
        """
        Create an RTMP broadcaster.
        
        Args:
            rtmp_url: Optional RTMP URL (uses settings default if not provided)
            
        Returns:
            Configured RTMPBroadcaster instance
        """
        url = rtmp_url or self.settings.rtmp_url
        return RTMPBroadcaster(rtmp_url=url)
    
    def create_all_services(self) -> Dict[str, Any]:
        """
        Create all services at once.
        
        Returns:
            Dictionary containing all service instances
            
        Raises:
            ConfigurationError: If any service cannot be created
        """
        try:
            services = {
                'api_client': self.create_api_client(),
                'youtube_client': self.create_youtube_client(),
                'serializer': self.create_serializer(),
                'broadcaster': self.create_broadcaster()
            }
            
            logger.info("All services created successfully")
            return services
            
        except Exception as e:
            logger.error(f"Failed to create services: {e}")
            raise ConfigurationError(f"Service creation failed: {e}")


class ApplicationFactory:
    """Factory for creating the main application."""
    
    @staticmethod
    def create_from_args(args) -> 'FazzTVApplication':
        """
        Create application from command-line arguments.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Configured FazzTVApplication instance
        """
        from fazztv.main import FazzTVApplication
        
        # Create settings with command-line overrides
        settings = Settings(env_file=getattr(args, 'env_file', None))
        
        # Apply command-line overrides
        if hasattr(args, 'stream_key') and args.stream_key:
            settings.stream_key = args.stream_key
            settings.rtmp_url = settings._build_rtmp_url()
        
        if hasattr(args, 'log_level') and args.log_level:
            settings.log_level = args.log_level
        
        if hasattr(args, 'test_mode') and args.test_mode:
            settings.stream_key = None
            settings.rtmp_url = "rtmp://127.0.0.1:1935/live/test"
        
        if hasattr(args, 'no_logo') and args.no_logo:
            settings.enable_logo = False
        
        if hasattr(args, 'cache_dir') and args.cache_dir:
            settings.cache_dir = Path(args.cache_dir)
            settings.cache_dir.mkdir(parents=True, exist_ok=True)
        
        return FazzTVApplication(settings)
    
    @staticmethod
    def create_for_testing() -> 'FazzTVApplication':
        """
        Create application configured for testing.
        
        Returns:
            FazzTVApplication configured for testing
        """
        from fazztv.main import FazzTVApplication
        
        settings = Settings()
        settings.stream_key = None
        settings.rtmp_url = "rtmp://127.0.0.1:1935/live/test"
        settings.log_level = "DEBUG"
        settings.cache_dir = Path("/tmp/fazztv_test")
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        
        return FazzTVApplication(settings)