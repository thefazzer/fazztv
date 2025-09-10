"""YouTube downloader implementation for FazzTV."""

import os
import random
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from loguru import logger
import yt_dlp

from fazztv.downloaders.base import BaseDownloader
from fazztv.config import constants


class YouTubeDownloader(BaseDownloader):
    """YouTube video/audio downloader using yt-dlp."""
    
    def __init__(self, max_duration: Optional[int] = None):
        """
        Initialize YouTube downloader.
        
        Args:
            max_duration: Maximum duration in seconds for downloads
        """
        self.max_duration = max_duration or constants.ELAPSED_TUNE_SECONDS
        
    def download(self, url: str, output_path: Path,
                 options: Optional[Dict[str, Any]] = None) -> bool:
        """Download complete media from YouTube."""
        logger.debug(f"Downloading media from {url} to {output_path}")
        
        ydl_opts = self._build_options(output_path, options)
        ydl_opts.update({
            "format": "best[ext=mp4]/best",
        })
        
        return self._execute_download(url, ydl_opts)
    
    def download_audio(self, url: str, output_path: Path,
                      options: Optional[Dict[str, Any]] = None) -> bool:
        """Download only audio from YouTube."""
        logger.debug(f"Downloading audio from {url} to {output_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create base output path without extension
        base_output = str(output_path.with_suffix(''))
        
        ydl_opts = self._build_options(Path(base_output), options)
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": constants.DEFAULT_AUDIO_FORMAT,
                "preferredquality": constants.DEFAULT_AUDIO_QUALITY,
            }]
        })
        
        success = self._execute_download(url, ydl_opts)
        
        if success:
            # Find the actual output file
            actual_file = self._find_output_file(base_output, constants.AUDIO_EXTENSIONS)
            if actual_file and actual_file != output_path:
                # Rename to expected output path
                actual_file.rename(output_path)
                logger.debug(f"Renamed {actual_file} to {output_path}")
        
        return success and output_path.exists()
    
    def download_video(self, url: str, output_path: Path,
                      options: Optional[Dict[str, Any]] = None) -> bool:
        """Download only video from YouTube."""
        logger.debug(f"Downloading video from {url} to {output_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        ydl_opts = self._build_options(output_path, options)
        ydl_opts.update({
            "format": "bestvideo[ext=mp4]",
        })
        
        return self._execute_download(url, ydl_opts)
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search YouTube for videos matching query."""
        logger.debug(f"Searching YouTube for: {query}")
        
        ydl_opts = {
            "quiet": True,
            "default_search": "ytsearch",
            "noplaylist": True,
            "max_downloads": limit,
            "extract_flat": False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
                videos = info.get("entries", [])
                
                results = []
                for video in videos:
                    results.append({
                        "title": video.get("title", "Unknown"),
                        "url": video.get("webpage_url", ""),
                        "duration": video.get("duration", 0),
                        "id": video.get("id", ""),
                        "uploader": video.get("uploader", "Unknown")
                    })
                
                logger.info(f"Found {len(results)} results for query: {query}")
                return results
                
        except Exception as e:
            logger.error(f"Search error for '{query}': {e}")
            return []
    
    def get_random_result(self, query: str, limit: int = 5) -> Optional[Tuple[str, str]]:
        """
        Search and return a random result.
        
        Returns:
            Tuple of (url, title) or None if no results
        """
        results = self.search(query, limit)
        if not results:
            return None
        
        choice = random.choice(results)
        return choice["url"], choice["title"]
    
    def _build_options(self, output_path: Path, 
                      custom_options: Optional[Dict[str, Any]] = None) -> dict:
        """Build yt-dlp options dictionary."""
        options = {
            "outtmpl": str(output_path) + ".%(ext)s" if output_path.suffix == '' else str(output_path),
            "quiet": False,
            "verbose": True,
            "overwrites": True,
            "continuedl": False,
            "nopart": True,
            "no_resume": True,
            "fragment_retries": constants.FRAGMENT_RETRIES,
        }
        
        if self.max_duration:
            options["max_duration"] = self.max_duration
        
        if custom_options:
            options.update(custom_options)
        
        return options
    
    def _execute_download(self, url: str, options: dict) -> bool:
        """Execute the actual download with yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    logger.error(f"No information extracted for URL: {url}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False
    
    def _find_output_file(self, base_path: str, extensions: list) -> Optional[Path]:
        """Find the actual output file with any of the given extensions."""
        base = Path(base_path)
        
        # Check for files with expected extensions
        for ext in extensions:
            potential_file = base.with_suffix(ext)
            if potential_file.exists() and potential_file.stat().st_size > 0:
                logger.debug(f"Found output file: {potential_file}")
                return potential_file
        
        # Check for compound extensions (e.g., .aac.m4a)
        parent_dir = base.parent
        base_name = base.name
        
        for file in parent_dir.iterdir():
            if file.name.startswith(base_name) and file.is_file() and file.stat().st_size > 0:
                logger.debug(f"Found alternative output file: {file}")
                return file
        
        logger.error(f"No valid output file found for {base_path}")
        return None