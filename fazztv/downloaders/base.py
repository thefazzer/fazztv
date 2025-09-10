"""Base downloader interface for FazzTV."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path


class BaseDownloader(ABC):
    """Abstract base class for media downloaders."""
    
    @abstractmethod
    def download(self, url: str, output_path: Path, 
                 options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Download media from URL to output path.
        
        Args:
            url: Source URL
            output_path: Destination file path
            options: Optional download options
            
        Returns:
            True if download successful, False otherwise
        """
        pass
    
    @abstractmethod
    def download_audio(self, url: str, output_path: Path,
                      options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Download only audio from URL.
        
        Args:
            url: Source URL
            output_path: Destination file path
            options: Optional download options
            
        Returns:
            True if download successful, False otherwise
        """
        pass
    
    @abstractmethod
    def download_video(self, url: str, output_path: Path,
                      options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Download only video from URL.
        
        Args:
            url: Source URL
            output_path: Destination file path
            options: Optional download options
            
        Returns:
            True if download successful, False otherwise
        """
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list:
        """
        Search for media matching query.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        pass