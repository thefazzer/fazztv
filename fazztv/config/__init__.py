"""Configuration module for FazzTV."""

from fazztv.config.settings import Settings
from fazztv.config.constants import (
    # Video Processing Constants
    BASE_RESOLUTION, DEFAULT_FADE_LENGTH, DEFAULT_FPS, VIDEO_CODEC,
    VIDEO_PRESET, AUDIO_CODEC, AUDIO_BITRATE,
    # Marquee Settings
    MARQUEE_DURATION, SCROLL_SPEED,
    # Download Settings
    SEARCH_LIMIT, MAX_DOWNLOAD_RETRIES, FRAGMENT_RETRIES,
    DEFAULT_AUDIO_QUALITY, DEFAULT_AUDIO_FORMAT,
    # Cache Settings
    CACHE_DIR_NAME, CACHE_EXPIRY_DAYS,
    # Logging
    LOG_FILE, LOG_MAX_SIZE, LOG_LEVEL, MADONNA_LOG_FILE,
    # Media Duration
    DEFAULT_MEDIA_DURATION, ELAPSED_TUNE_SECONDS,
    # File Extensions
    AUDIO_EXTENSIONS, VIDEO_EXTENSIONS,
    # Font Settings
    DEFAULT_FONT, TITLE_FONT_SIZE, SUBTITLE_FONT_SIZE,
    BYLINE_FONT_SIZE, MARQUEE_FONT_SIZE,
    # Colors
    COLOR_RED, COLOR_YELLOW, COLOR_WHITE, COLOR_BLACK,
    # Overlay Positions
    OVERLAY_PADDING, LOGO_SIZE, LOGO_POSITION,
    # RTMP Settings
    DEFAULT_RTMP_URL, YOUTUBE_RTMP_BASE,
    # API Settings
    API_TIMEOUT, API_MAX_RETRIES,
    # Subprocess Settings
    SUBPROCESS_TIMEOUT, FFMPEG_TIMEOUT,
    # Download Settings for Madonna
    AGE_LIMIT_UNRESTRICTED, FRAGMENT_RETRIES_MAX,
    AUDIO_PREFERRED_QUALITY, AUDIO_PREFERRED_CODEC,
    VIDEO_PREFERRED_FORMAT,
    # Cache File Suffixes
    AUDIO_CACHE_SUFFIX, VIDEO_CACHE_SUFFIX, OUTPUT_CACHE_SUFFIX,
    # FFmpeg Video Processing
    FFMPEG_VIDEO_CODEC_HW, FFMPEG_VIDEO_PRESET, FFMPEG_AUDIO_BITRATE,
    # File Extensions for Audio Search
    AUDIO_SEARCH_EXTENSIONS,
    # Default Files
    DEFAULT_VIDEO_FILE, DEFAULT_LIGHTBULB_IMAGE, DEFAULT_LOGO_FILE,
    # Search Query Templates
    MADONNA_SEARCH_TEMPLATE,
    # Functions
    get_rtmp_url
)

__all__ = ['Settings', 'get_settings']

_settings = None

def get_settings() -> Settings:
    """Get the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings