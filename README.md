# FazzTV - Modular Media Broadcasting System

FazzTV is a highly modular Python application for creating and broadcasting media content with overlays, effects, and real-time streaming to RTMP endpoints. The system is designed for maximum flexibility and maintainability.

## Features

- **YouTube Integration**: Download and process videos/audio from YouTube
- **Advanced Video Processing**: Add overlays, text, logos, and audio visualizers
- **RTMP Broadcasting**: Stream content to YouTube Live or other RTMP servers
- **Intelligent Caching**: Multi-level caching for downloads and processed media
- **Modular Architecture**: Clean separation of concerns with dedicated modules
- **AI Integration**: OpenRouter API for content generation
- **Comprehensive Error Handling**: Custom exceptions and robust error recovery

## Architecture

FazzTV follows a clean, modular architecture. See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation.

### Core Modules

- **`config/`** - Configuration management with environment variables
- **`models/`** - Data models and custom exceptions
- **`downloaders/`** - Media download services with caching
- **`processors/`** - Video/audio processing with FFmpeg
- **`api/`** - External API clients (OpenRouter, YouTube)
- **`broadcasting/`** - RTMP streaming and serialization
- **`data/`** - Data management and storage
- **`utils/`** - Utility functions and helpers
- **`apps/`** - Application entry points

## Installation

### Prerequisites

- Python 3.8+
- FFmpeg (with libx264 and AAC support)
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/fazztv.git
cd fazztv
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

### Environment Variables

Create a `.env` file with the following variables:

```env
# API Keys
OPENROUTER_API_KEY=your_openrouter_key
STREAM_KEY=your_youtube_stream_key

# Paths
DATA_DIR=./data
CACHE_DIR=/tmp/fazztv
LOG_DIR=./logs

# Video Settings
BASE_RESOLUTION=1280x720
FPS=30
FADE_LENGTH=3

# Features
ENABLE_EQUALIZER=true
ENABLE_CACHING=true
ENABLE_LOGO=true

# API Settings
API_TIMEOUT=30
```

## Usage

### Basic Example

```python
from fazztv.models import MediaItem
from fazztv.broadcasting import RTMPBroadcaster, MediaSerializer
from fazztv.config import get_settings

# Initialize settings
settings = get_settings()

# Create a media item
media_item = MediaItem(
    artist="Madonna",
    song="Like a Prayer",
    url="https://youtube.com/watch?v=...",
    taxprompt="Historical context about the song",
    length_percent=100
)

# Serialize the media item
serializer = MediaSerializer()
serializer.serialize_media_item(media_item)

# Broadcast to RTMP
broadcaster = RTMPBroadcaster()
broadcaster.broadcast_item(media_item)
```

### Madonna Broadcast Application

```python
from fazztv.apps.madonna_app import MadonnaBroadcastApp

app = MadonnaBroadcastApp()
app.run()
```

### Tax Evasion Show Application

```python
from fazztv.apps.tax_app import TaxEvasionApp

app = TaxEvasionApp()
app.run()
```

## Module Documentation

### Configuration Module

```python
from fazztv.config import get_settings

settings = get_settings()
print(settings.to_dict())  # View current configuration
```

### Downloaders

```python
from fazztv.downloaders import YouTubeDownloader, CachedDownloader

# Basic downloader
downloader = YouTubeDownloader()
downloader.download_audio(url, output_path)

# With caching
cached_downloader = CachedDownloader(downloader)
cached_downloader.download_video(url, output_path, {'guid': 'unique_id'})
```

### Video Processing

```python
from fazztv.processors import VideoProcessor

processor = VideoProcessor()
processor.combine_audio_video(
    audio_path=audio_file,
    video_path=video_file,
    output_path=output_file,
    title="Video Title",
    subtitle="Subtitle Text",
    marquee_text="Scrolling text",
    enable_equalizer=True
)
```

### API Clients

```python
from fazztv.api import OpenRouterClient, YouTubeSearchClient

# AI content generation
ai_client = OpenRouterClient()
commentary = ai_client.generate_commentary("Topic", style="humorous")

# YouTube search
yt_client = YouTubeSearchClient()
videos = yt_client.search_music_video("Madonna", "Vogue")
```

### Data Management

```python
from fazztv.data import DataLoader, DataStorage, DataCache

# Load JSON data
loader = DataLoader()
episodes = loader.load_episodes("madonna_data.json")

# Store data
storage = DataStorage()
storage.store("key", data, format="json")

# In-memory cache
cache = DataCache()
cache.set("key", value, ttl=3600)
```

## Testing

Run the test suite:

```bash
# Unit tests
python -m pytest tests/

# Integration tests
python -m pytest tests/integration/

# Test coverage
python -m pytest --cov=fazztv tests/
```

## Development

### Project Structure

```
fazztv/
├── __init__.py
├── config/           # Configuration management
├── models/           # Data models and exceptions
├── downloaders/      # Media download services
├── processors/       # Media processing
├── api/             # External API clients
├── broadcasting/     # RTMP broadcasting
├── data/            # Data management
├── utils/           # Utility functions
├── apps/            # Application entry points
└── tests/           # Test suite
```

### Adding New Features

1. Create a new module in the appropriate directory
2. Define interfaces and data models
3. Implement with error handling
4. Add unit tests
5. Update documentation

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Add docstrings to all classes and methods
- Keep functions focused and small
- Use meaningful variable names

## Error Handling

FazzTV uses custom exceptions for better error management:

```python
from fazztv.models import (
    ConfigurationError,
    DownloadError,
    ProcessingError,
    BroadcastError
)

try:
    # Your code here
    pass
except DownloadError as e:
    logger.error(f"Download failed: {e}")
except ProcessingError as e:
    logger.error(f"Processing failed: {e}")
```

## Performance Optimization

### Caching Strategy

- Downloads are cached with GUID-based keys
- Processed media is cached for reuse
- In-memory cache for frequently accessed data

### Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor
from fazztv.downloaders import YouTubeDownloader

downloader = YouTubeDownloader()
urls = ["url1", "url2", "url3"]

with ThreadPoolExecutor(max_workers=3) as executor:
    results = executor.map(downloader.download_audio, urls)
```

## Troubleshooting

### Common Issues

1. **FFmpeg not found**
   - Install FFmpeg: `sudo apt-get install ffmpeg`
   - Verify installation: `ffmpeg -version`

2. **API rate limits**
   - Implement exponential backoff
   - Use caching to reduce API calls

3. **RTMP connection failures**
   - Test connection: `broadcaster.test_connection()`
   - Verify stream key and URL

### Debug Mode

Enable debug logging:

```python
from fazztv.utils.logging import setup_logging

setup_logging(log_level="DEBUG")
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [https://github.com/yourusername/fazztv/issues](https://github.com/yourusername/fazztv/issues)
- Documentation: [ARCHITECTURE.md](ARCHITECTURE.md)

## Acknowledgments

- FFmpeg for media processing
- yt-dlp for YouTube integration
- OpenRouter for AI capabilities
- loguru for logging