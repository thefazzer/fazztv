"""Configuration module for FazzTV."""

from fazztv.config.settings import Settings
from fazztv.config.constants import *

__all__ = ['Settings', 'get_settings']

_settings = None

def get_settings() -> Settings:
    """Get the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings