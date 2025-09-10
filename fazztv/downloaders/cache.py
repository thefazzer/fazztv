"""Cached downloader implementation for FazzTV."""

import shutil
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger

from fazztv.downloaders.base import BaseDownloader
from fazztv.config import get_settings, constants


class CachedDownloader(BaseDownloader):
    """Downloader wrapper that implements caching."""
    
    def __init__(self, downloader: BaseDownloader, cache_dir: Optional[Path] = None):
        """
        Initialize cached downloader.
        
        Args:
            downloader: The underlying downloader to wrap
            cache_dir: Optional cache directory path
        """
        self.downloader = downloader
        self.settings = get_settings()
        self.cache_dir = cache_dir or self.settings.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def download(self, url: str, output_path: Path,
                 options: Optional[Dict[str, Any]] = None) -> bool:
        """Download with caching support."""
        cache_key = self._get_cache_key(url, "full", options)
        cached_file = self._get_cached_file(cache_key)
        
        if cached_file:
            logger.info(f"Using cached file for {url}")
            shutil.copy(cached_file, output_path)
            return True
        
        # Download using underlying downloader
        success = self.downloader.download(url, output_path, options)
        
        if success and output_path.exists():
            self._cache_file(output_path, cache_key)
        
        return success
    
    def download_audio(self, url: str, output_path: Path,
                      options: Optional[Dict[str, Any]] = None) -> bool:
        """Download audio with caching support."""
        # Use GUID if provided in options
        guid = options.get('guid') if options else None
        
        if guid:
            cache_key = f"{guid}_audio.aac"
        else:
            cache_key = self._get_cache_key(url, "audio", options)
        
        cached_file = self._get_cached_file(cache_key)
        
        if cached_file:
            logger.info(f"Using cached audio file: {cache_key}")
            shutil.copy(cached_file, output_path)
            return True
        
        # Download using underlying downloader
        success = self.downloader.download_audio(url, output_path, options)
        
        if success and output_path.exists():
            self._cache_file(output_path, cache_key)
        
        return success
    
    def download_video(self, url: str, output_path: Path,
                      options: Optional[Dict[str, Any]] = None) -> bool:
        """Download video with caching support."""
        # Use GUID if provided in options
        guid = options.get('guid') if options else None
        
        if guid:
            cache_key = f"{guid}_video.mp4"
        else:
            cache_key = self._get_cache_key(url, "video", options)
        
        cached_file = self._get_cached_file(cache_key)
        
        if cached_file:
            logger.info(f"Using cached video file: {cache_key}")
            shutil.copy(cached_file, output_path)
            return True
        
        # Download using underlying downloader
        success = self.downloader.download_video(url, output_path, options)
        
        if success and output_path.exists():
            self._cache_file(output_path, cache_key)
        
        return success
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Pass through search to underlying downloader."""
        return self.downloader.search(query, limit)
    
    def clear_cache(self, older_than_days: Optional[int] = None):
        """
        Clear cache files older than specified days.
        
        Args:
            older_than_days: Clear files older than this many days.
                           If None, uses default from constants.
        """
        days = older_than_days or constants.CACHE_EXPIRY_DAYS
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cleared_count = 0
        for cache_file in self.cache_dir.iterdir():
            if cache_file.is_file():
                file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_time < cutoff_date:
                    cache_file.unlink()
                    cleared_count += 1
                    logger.debug(f"Removed old cache file: {cache_file}")
        
        logger.info(f"Cleared {cleared_count} cache files older than {days} days")
    
    def get_cache_size(self) -> int:
        """Get total size of cache in bytes."""
        total_size = 0
        for cache_file in self.cache_dir.iterdir():
            if cache_file.is_file():
                total_size += cache_file.stat().st_size
        return total_size
    
    def _get_cache_key(self, url: str, media_type: str, 
                      options: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for the given parameters."""
        import hashlib
        
        # Create a unique key based on URL and options
        key_parts = [url, media_type]
        
        if options:
            # Add relevant options to the key
            for key in sorted(options.keys()):
                if key not in ['guid', 'output_path']:  # Exclude non-relevant options
                    key_parts.append(f"{key}={options[key]}")
        
        key_string = "|".join(key_parts)
        hash_digest = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        # Determine extension based on media type
        ext = ".mp4" if media_type == "video" else ".aac" if media_type == "audio" else ".media"
        
        return f"{hash_digest}_{media_type}{ext}"
    
    def _get_cached_file(self, cache_key: str) -> Optional[Path]:
        """Check if a cached file exists and is valid."""
        cache_path = self.cache_dir / cache_key
        
        if cache_path.exists() and cache_path.stat().st_size > 0:
            # Check if cache is enabled
            if not self.settings.enable_caching:
                return None
            
            # Check if file is not too old
            file_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
            if file_age.days <= constants.CACHE_EXPIRY_DAYS:
                return cache_path
            else:
                logger.debug(f"Cache file {cache_key} is too old, will re-download")
        
        return None
    
    def _cache_file(self, source_path: Path, cache_key: str):
        """Copy a file to cache."""
        if not self.settings.enable_caching:
            return
        
        cache_path = self.cache_dir / cache_key
        try:
            shutil.copy(source_path, cache_path)
            logger.debug(f"Cached file to {cache_key}")
        except Exception as e:
            logger.error(f"Failed to cache file: {e}")