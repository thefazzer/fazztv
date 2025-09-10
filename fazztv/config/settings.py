"""Settings management for FazzTV."""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

from fazztv.config import constants


class Settings:
    """Centralized settings management with environment variable support."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize settings from environment variables.
        
        Args:
            env_file: Optional path to .env file
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        # API Keys
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.stream_key = os.getenv("STREAM_KEY", "")
        
        # Paths
        self.data_dir = Path(os.getenv("DATA_DIR", "./data"))
        self.cache_dir = Path(os.getenv("CACHE_DIR", f"/tmp/{constants.CACHE_DIR_NAME}"))
        self.log_dir = Path(os.getenv("LOG_DIR", "./logs"))
        
        # Video Settings
        self.base_resolution = os.getenv("BASE_RESOLUTION", constants.BASE_RESOLUTION)
        self.fade_length = int(os.getenv("FADE_LENGTH", str(constants.DEFAULT_FADE_LENGTH)))
        self.fps = int(os.getenv("FPS", str(constants.DEFAULT_FPS)))
        
        # Download Settings
        self.search_limit = int(os.getenv("SEARCH_LIMIT", str(constants.SEARCH_LIMIT)))
        self.media_duration = int(os.getenv("MEDIA_DURATION", str(constants.DEFAULT_MEDIA_DURATION)))
        
        # Marquee Settings
        self.marquee_duration = int(os.getenv("MARQUEE_DURATION", str(constants.MARQUEE_DURATION)))
        self.scroll_speed = int(os.getenv("SCROLL_SPEED", str(constants.SCROLL_SPEED)))
        
        # RTMP Settings
        self.rtmp_url = self._build_rtmp_url()
        
        # Logging
        self.log_file = self.log_dir / os.getenv("LOG_FILE", constants.LOG_FILE)
        self.log_level = os.getenv("LOG_LEVEL", constants.LOG_LEVEL)
        self.log_max_size = os.getenv("LOG_MAX_SIZE", constants.LOG_MAX_SIZE)
        
        # Feature Flags
        self.enable_equalizer = os.getenv("ENABLE_EQUALIZER", "false").lower() == "true"
        self.enable_caching = os.getenv("ENABLE_CACHING", "true").lower() == "true"
        self.enable_logo = os.getenv("ENABLE_LOGO", "true").lower() == "true"
        
        # Create necessary directories
        self._ensure_directories()
    
    def _build_rtmp_url(self) -> str:
        """Build the RTMP URL based on stream key."""
        if self.stream_key:
            return f"{constants.YOUTUBE_RTMP_BASE}{self.stream_key}"
        return constants.DEFAULT_RTMP_URL
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        for directory in [self.data_dir, self.cache_dir, self.log_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_cache_path(self, filename: str) -> Path:
        """Get the full path for a cached file."""
        return self.cache_dir / filename
    
    def get_data_file(self, filename: str) -> Path:
        """Get the full path for a data file."""
        return self.data_dir / filename
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return bool(self.stream_key)
    
    def validate(self) -> bool:
        """
        Validate the current settings.
        
        Returns:
            True if settings are valid, False otherwise
        """
        if self.is_production() and not self.stream_key:
            return False
        
        # Check if required API keys are present for certain features
        # This can be expanded based on requirements
        
        return True
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary for logging/debugging."""
        return {
            "api_keys_configured": {
                "openrouter": bool(self.openrouter_api_key),
                "openai": bool(self.openai_api_key),
                "stream": bool(self.stream_key)
            },
            "paths": {
                "data": str(self.data_dir),
                "cache": str(self.cache_dir),
                "log": str(self.log_dir)
            },
            "video": {
                "resolution": self.base_resolution,
                "fade_length": self.fade_length,
                "fps": self.fps
            },
            "features": {
                "equalizer": self.enable_equalizer,
                "caching": self.enable_caching,
                "logo": self.enable_logo
            },
            "mode": "production" if self.is_production() else "development"
        }