"""Application-wide constants for FazzTV."""

import os

# Video Processing Constants
BASE_RESOLUTION = "640x360"
DEFAULT_FADE_LENGTH = 3
DEFAULT_FPS = 30
VIDEO_CODEC = "libx264"
VIDEO_PRESET = "fast"
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "128k"

# Marquee Settings
MARQUEE_DURATION = 86400  # 24 hours in seconds
SCROLL_SPEED = 65

# Download Settings
SEARCH_LIMIT = 5
MAX_DOWNLOAD_RETRIES = 3
FRAGMENT_RETRIES = 999
DEFAULT_AUDIO_QUALITY = "192"
DEFAULT_AUDIO_FORMAT = "aac"

# Cache Settings
CACHE_DIR_NAME = "fazztv"
CACHE_EXPIRY_DAYS = 7

# Logging
LOG_FILE = "fazztv.log"
LOG_MAX_SIZE = "10 MB"
LOG_LEVEL = "DEBUG"
MADONNA_LOG_FILE = "madonna_broadcast.log"

# Media Duration
DEFAULT_MEDIA_DURATION = 10  # seconds
ELAPSED_TUNE_SECONDS = 60  # Default duration for media clips in seconds

# File Extensions
AUDIO_EXTENSIONS = ['.aac', '.m4a', '.mp3', '.wav']
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.webm']

# Font Settings
DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
TITLE_FONT_SIZE = 50
SUBTITLE_FONT_SIZE = 40
BYLINE_FONT_SIZE = 26
MARQUEE_FONT_SIZE = 24

# Colors
COLOR_RED = "red"
COLOR_YELLOW = "yellow"
COLOR_WHITE = "white"
COLOR_BLACK = "black"

# Overlay Positions
OVERLAY_PADDING = 10
LOGO_SIZE = 120
LOGO_POSITION = (20, 20)

# RTMP Settings
DEFAULT_RTMP_URL = os.getenv("RTMP_URL", "rtmp://127.0.0.1:1935/live/test")
YOUTUBE_RTMP_BASE = "rtmp://a.rtmp.youtube.com/live2/"

def get_rtmp_url(stream_key: str = None) -> str:
    """
    Get the appropriate RTMP URL based on stream key.

    Args:
        stream_key: Optional YouTube stream key

    Returns:
        RTMP URL string
    """
    if stream_key:
        return f"{YOUTUBE_RTMP_BASE}{stream_key}"
    return DEFAULT_RTMP_URL

# API Settings
API_TIMEOUT = 30  # seconds
API_MAX_RETRIES = 3

# Subprocess Settings
SUBPROCESS_TIMEOUT = 120  # seconds (2 minutes default)
FFMPEG_TIMEOUT = 300  # seconds (5 minutes for FFmpeg operations)

# Download Settings for Madonna
AGE_LIMIT_UNRESTRICTED = 99  # Allow age-restricted content
FRAGMENT_RETRIES_MAX = 999
AUDIO_PREFERRED_QUALITY = "192"
AUDIO_PREFERRED_CODEC = "aac"
VIDEO_PREFERRED_FORMAT = "bestvideo[ext=mp4]"

# Cache File Suffixes
AUDIO_CACHE_SUFFIX = "_audio.aac"
VIDEO_CACHE_SUFFIX = "_video.mp4"
OUTPUT_CACHE_SUFFIX = "_output.mp4"

# FFmpeg Video Processing
FFMPEG_VIDEO_CODEC_HW = "h264_nvenc"  # Hardware-accelerated H.264
FFMPEG_VIDEO_PRESET = "fast"
FFMPEG_AUDIO_BITRATE = "128k"

# File Extensions for Audio Search
AUDIO_SEARCH_EXTENSIONS = ['.aac', '.m4a', '.aac.m4a', '.aac.mp4', '.mp3']

# Default Files
DEFAULT_VIDEO_FILE = "madonna-rotator.mp4"
DEFAULT_LIGHTBULB_IMAGE = "didyouknow-lightbulb.png"
DEFAULT_LOGO_FILE = "fztv-logo.png"

# Search Query Templates
MADONNA_SEARCH_TEMPLATE = "Madonna {song_name} official music video"