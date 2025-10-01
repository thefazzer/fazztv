"""Component factory for FazzTV."""

from typing import Dict, Any, Optional, Type, TypeVar
from pathlib import Path

from fazztv.config.settings import Settings
from fazztv.core.container import DIContainer
from fazztv.core.logging import get_logger, ComponentLogger
from fazztv.providers.base import ProviderConfig
from fazztv.interfaces.providers import ProviderProtocol

T = TypeVar('T')


class ComponentFactory:
    """Factory for creating FazzTV components with proper dependency injection."""

    def __init__(self, container: DIContainer, settings: Settings):
        self.container = container
        self.settings = settings
        self.logger = get_logger("ComponentFactory")

    def create_provider(
        self,
        provider_class: Type[T],
        provider_id: str,
        **config_overrides: Any
    ) -> T:
        """Create a provider with configuration."""
        config_data = {
            "provider_id": provider_id,
            "timeout": self.settings.timeout if hasattr(self.settings, 'timeout') else 60,
            "max_retries": 3,
            **config_overrides
        }

        config = ProviderConfig(**config_data)
        return provider_class(config)

    def create_api_client(
        self,
        client_class: Type[T],
        api_key: Optional[str] = None,
        **kwargs: Any
    ) -> T:
        """Create an API client."""
        if api_key is None:
            # Try to get API key from settings based on client type
            client_name = client_class.__name__.lower()
            if "openrouter" in client_name:
                api_key = self.settings.openrouter_api_key
            elif "openai" in client_name:
                api_key = self.settings.openai_api_key

        return client_class(api_key, **kwargs)

    def create_media_serializer(self, **overrides: Any) -> Any:
        """Create a media serializer with settings."""
        from fazztv.broadcasting.serializer import MediaSerializer

        config = {
            "base_res": self.settings.base_resolution,
            "fade_length": self.settings.fade_length,
            "marquee_duration": self.settings.marquee_duration,
            "scroll_speed": self.settings.scroll_speed,
            "logo_path": "fztv-logo.png" if self.settings.enable_logo else None,
            **overrides
        }

        return MediaSerializer(**config)

    def create_broadcaster(self, rtmp_url: Optional[str] = None) -> Any:
        """Create a broadcaster."""
        from fazztv.broadcaster import RTMPBroadcaster

        url = rtmp_url or self.settings.rtmp_url
        return RTMPBroadcaster(rtmp_url=url)

    def create_youtube_client(self, search_limit: Optional[int] = None) -> Any:
        """Create a YouTube client."""
        from fazztv.api.youtube import YouTubeSearchClient

        limit = search_limit or self.settings.search_limit
        return YouTubeSearchClient(search_limit=limit)

    def create_application(self, **overrides: Any) -> Any:
        """Create the main FazzTV application."""
        from fazztv.main import FazzTVApplication

        # Setup container with all dependencies
        self._register_dependencies()

        return FazzTVApplication(
            settings=self.settings,
            container=self.container,
            **overrides
        )

    def _register_dependencies(self) -> None:
        """Register all standard dependencies in the container."""
        # Settings
        self.container.register_singleton(Settings, lambda: self.settings)

        # API Clients
        from fazztv.api.openrouter import OpenRouterClient
        from fazztv.api.youtube import YouTubeSearchClient

        self.container.register_singleton(
            OpenRouterClient,
            lambda: self.create_api_client(OpenRouterClient)
        )

        self.container.register_singleton(
            YouTubeSearchClient,
            lambda: self.create_youtube_client()
        )

        # Media Processing
        from fazztv.broadcasting.serializer import MediaSerializer
        from fazztv.broadcaster import RTMPBroadcaster

        self.container.register_singleton(
            MediaSerializer,
            lambda: self.create_media_serializer()
        )

        self.container.register_singleton(
            RTMPBroadcaster,
            lambda: self.create_broadcaster()
        )

        self.logger.info("All dependencies registered in container")


def create_application(
    settings: Optional[Settings] = None,
    container: Optional[DIContainer] = None,
    **config_overrides: Any
) -> Any:
    """Convenience function to create a fully configured FazzTV application."""
    settings = settings or Settings()

    # Apply any configuration overrides
    for key, value in config_overrides.items():
        if hasattr(settings, key):
            setattr(settings, key, value)

    container = container or DIContainer()
    factory = ComponentFactory(container, settings)

    return factory.create_application()


def create_provider_factory(settings: Settings) -> ComponentFactory:
    """Create a factory specifically for creating providers."""
    container = DIContainer()
    return ComponentFactory(container, settings)


def setup_development_environment() -> Dict[str, Any]:
    """Setup a development environment with all components."""
    # Create settings with development defaults
    settings = Settings()
    settings.log_level = "DEBUG"
    settings.enable_caching = True
    settings.rtmp_url = "rtmp://localhost/live/test"

    # Create container and factory
    container = DIContainer()
    factory = ComponentFactory(container, settings)

    # Create main components
    app = factory.create_application()

    return {
        "application": app,
        "settings": settings,
        "container": container,
        "factory": factory,
        "logger": get_logger("Development")
    }


def setup_production_environment(
    stream_key: str,
    openrouter_api_key: Optional[str] = None,
    **config_overrides: Any
) -> Dict[str, Any]:
    """Setup a production environment."""
    settings = Settings()
    settings.stream_key = stream_key
    settings.rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"

    if openrouter_api_key:
        settings.openrouter_api_key = openrouter_api_key

    # Apply overrides
    for key, value in config_overrides.items():
        if hasattr(settings, key):
            setattr(settings, key, value)

    container = DIContainer()
    factory = ComponentFactory(container, settings)

    app = factory.create_application()

    return {
        "application": app,
        "settings": settings,
        "container": container,
        "factory": factory,
        "logger": get_logger("Production")
    }