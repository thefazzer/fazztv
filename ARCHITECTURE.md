# FazzTV Architecture Documentation

## Overview
FazzTV is a media broadcasting system that combines video and audio content with overlays and effects, then streams to RTMP endpoints. The system supports multiple content types including Madonna music videos with war documentary overlays and tax evasion information displays.

## Module Structure

### Core Modules

#### 1. **config/** - Configuration Management
- `settings.py` - Central configuration with environment variable support
- `constants.py` - Application-wide constants
- `__init__.py` - Configuration module initialization

#### 2. **models/** - Data Models  
- `media_item.py` - MediaItem class for representing media content
- `episode.py` - Episode data model for Madonna content
- `exceptions.py` - Custom exception classes
- `__init__.py` - Models module initialization

#### 3. **downloaders/** - Media Download Services
- `base.py` - Abstract base downloader class
- `youtube.py` - YouTube video/audio downloader using yt-dlp
- `cache.py` - Download caching functionality
- `__init__.py` - Downloaders module initialization

#### 4. **processors/** - Media Processing
- `video.py` - Video processing and effects (FFmpeg operations)
- `audio.py` - Audio processing functionality
- `overlay.py` - Text and image overlay management
- `equalizer.py` - Audio visualizer/equalizer generation
- `__init__.py` - Processors module initialization

#### 5. **api/** - External API Clients
- `openrouter.py` - OpenRouter API client for AI services
- `youtube.py` - YouTube API integration
- `__init__.py` - API module initialization

#### 6. **broadcasting/** - Stream Broadcasting
- `rtmp.py` - RTMP broadcast functionality
- `serializer.py` - Media serialization for broadcast
- `__init__.py` - Broadcasting module initialization

#### 7. **data/** - Data Management
- `loader.py` - JSON data loading and management
- `storage.py` - Persistent storage handling
- `cache.py` - Cache management utilities
- `__init__.py` - Data module initialization

#### 8. **utils/** - Utility Functions
- `text.py` - Text manipulation and sanitization
- `file.py` - File system operations
- `logging.py` - Logging configuration
- `datetime.py` - Date/time utilities
- `__init__.py` - Utils module initialization

#### 9. **apps/** - Application Entry Points
- `madonna_app.py` - Madonna broadcast application
- `tax_app.py` - Tax evasion broadcast application
- `__init__.py` - Apps module initialization

### File Organization

```
fazztv/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── constants.py
├── models/
│   ├── __init__.py
│   ├── media_item.py
│   ├── episode.py
│   └── exceptions.py
├── downloaders/
│   ├── __init__.py
│   ├── base.py
│   ├── youtube.py
│   └── cache.py
├── processors/
│   ├── __init__.py
│   ├── video.py
│   ├── audio.py
│   ├── overlay.py
│   └── equalizer.py
├── api/
│   ├── __init__.py
│   ├── openrouter.py
│   └── youtube.py
├── broadcasting/
│   ├── __init__.py
│   ├── rtmp.py
│   └── serializer.py
├── data/
│   ├── __init__.py
│   ├── loader.py
│   ├── storage.py
│   └── cache.py
├── utils/
│   ├── __init__.py
│   ├── text.py
│   ├── file.py
│   ├── logging.py
│   └── datetime.py
├── apps/
│   ├── __init__.py
│   ├── madonna_app.py
│   └── tax_app.py
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_downloaders.py
    ├── test_processors.py
    ├── test_broadcasting.py
    └── test_utils.py
```

## Design Principles

### 1. **Separation of Concerns**
- Each module has a single, well-defined responsibility
- Business logic is separated from data access and presentation

### 2. **Dependency Injection**
- Components receive dependencies through constructors
- Allows for easy testing and flexibility

### 3. **Interface Segregation**
- Small, focused interfaces for each component
- Abstract base classes define contracts

### 4. **Error Handling**
- Custom exceptions for domain-specific errors
- Comprehensive error logging and recovery

### 5. **Caching Strategy**
- Multi-level caching for downloads and processed media
- Cache invalidation based on content GUIDs

### 6. **Configuration Management**
- Environment-based configuration
- Sensible defaults with override capabilities

## Data Flow

1. **Configuration Loading**
   - Load environment variables and settings
   - Initialize logging and cache directories

2. **Data Loading**
   - Load episode/content data from JSON files
   - Validate and enrich with GUIDs

3. **Media Download**
   - Check cache for existing downloads
   - Download audio/video from sources
   - Store in cache with GUID references

4. **Media Processing**
   - Apply video effects and overlays
   - Generate audio visualizations
   - Combine audio and video streams

5. **Broadcasting**
   - Serialize processed media
   - Stream to RTMP endpoint
   - Clean up temporary files

## Key Interfaces

### MediaItem
```python
class MediaItem:
    artist: str
    song: str
    url: str
    taxprompt: str
    length_percent: int
    duration: Optional[int]
    serialized: Optional[str]
```

### Downloader
```python
class BaseDownloader(ABC):
    def download(url: str, output_path: str, guid: Optional[str]) -> bool
    def download_audio(url: str, output_path: str, guid: Optional[str]) -> bool
    def download_video(url: str, output_path: str, guid: Optional[str]) -> bool
```

### Processor
```python
class VideoProcessor:
    def process(input_path: str, output_path: str, options: Dict) -> bool
    def add_overlay(video_path: str, overlay: Overlay) -> bool
    def combine_audio_video(audio: str, video: str, output: str) -> bool
```

### Broadcaster
```python
class RTMPBroadcaster:
    def broadcast_item(media_item: MediaItem) -> bool
    def broadcast_collection(items: List[MediaItem]) -> List[Tuple[MediaItem, bool]]
```

## Error Handling Strategy

1. **Custom Exceptions**
   - `DownloadError` - Failed media downloads
   - `ProcessingError` - FFmpeg or processing failures
   - `BroadcastError` - RTMP streaming issues
   - `ConfigurationError` - Missing or invalid configuration

2. **Fallback Mechanisms**
   - Alternative download URLs
   - Cache fallbacks for failed downloads
   - Graceful degradation of features

3. **Logging Levels**
   - DEBUG: Detailed execution flow
   - INFO: Key operations and milestones
   - WARNING: Recoverable issues
   - ERROR: Failures requiring attention
   - CRITICAL: System-level failures

## Testing Strategy

1. **Unit Tests**
   - Test individual components in isolation
   - Mock external dependencies
   - Focus on business logic

2. **Integration Tests**
   - Test module interactions
   - Verify data flow between components
   - Test with real FFmpeg operations

3. **End-to-End Tests**
   - Full workflow from data loading to broadcasting
   - Performance testing for media processing
   - Network resilience testing

## Performance Considerations

1. **Caching**
   - Aggressive caching of downloaded media
   - Processed media cache for repeated broadcasts
   - In-memory caching for frequently accessed data

2. **Parallel Processing**
   - Concurrent downloads for multiple media items
   - Parallel video processing where possible
   - Async I/O for file operations

3. **Resource Management**
   - Temporary file cleanup
   - Memory-efficient streaming for large files
   - Connection pooling for API clients

## Security Considerations

1. **Credential Management**
   - Environment variables for sensitive data
   - Never commit credentials to version control
   - Secure storage of API keys

2. **Input Validation**
   - Sanitize all user inputs
   - Validate URLs before downloading
   - Escape special characters in FFmpeg commands

3. **File System Security**
   - Restricted file system access
   - Temporary file permissions
   - Safe path construction

## Deployment Considerations

1. **Dependencies**
   - FFmpeg installation required
   - Python 3.8+ with pip packages
   - Sufficient disk space for cache

2. **Environment Setup**
   - `.env` file for configuration
   - Log directory permissions
   - RTMP endpoint configuration

3. **Monitoring**
   - Log rotation and retention
   - Performance metrics collection
   - Error alerting mechanisms