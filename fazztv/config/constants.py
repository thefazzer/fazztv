"""Application-wide constants for FazzTV."""

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
SCROLL_SPEED = 40

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

# Media Duration
DEFAULT_MEDIA_DURATION = 10  # seconds
ELAPSED_TUNE_SECONDS = 10  # Default duration for media clips

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
DEFAULT_RTMP_URL = "rtmp://127.0.0.1:1935/live/test"
YOUTUBE_RTMP_BASE = "rtmp://a.rtmp.youtube.com/live2/"

# API Settings
API_TIMEOUT = 30  # seconds
API_MAX_RETRIES = 3