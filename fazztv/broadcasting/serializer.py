"""Media serialization for broadcasting."""

import tempfile
import random
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger

from fazztv.models import MediaItem, ProcessingError
from fazztv.processors import VideoProcessor
from fazztv.downloaders import YouTubeDownloader, CachedDownloader
from fazztv.config import get_settings
from fazztv.utils.file import get_temp_path, safe_delete


class MediaSerializer:
    """Handles serialization of MediaItems for broadcasting."""
    
    def __init__(
        self,
        base_res: Optional[str] = None,
        fade_length: Optional[int] = None,
        logo_path: Optional[Path] = None
    ):
        """
        Initialize media serializer.
        
        Args:
            base_res: Base resolution for videos
            fade_length: Fade effect duration in seconds
            logo_path: Path to logo image
        """
        settings = get_settings()
        self.base_res = base_res or settings.base_resolution
        self.fade_length = fade_length or settings.fade_length
        self.logo_path = Path(logo_path) if logo_path else None
        
        # Initialize components
        self.video_processor = VideoProcessor()
        self.downloader = CachedDownloader(YouTubeDownloader())
    
    def serialize_media_item(
        self,
        media_item: MediaItem,
        show_info: Optional[Dict[str, str]] = None,
        output_dir: Optional[Path] = None
    ) -> bool:
        """
        Serialize a media item for broadcasting.
        
        Args:
            media_item: MediaItem to serialize
            show_info: Optional show information for overlays
            output_dir: Optional output directory
            
        Returns:
            True if serialization successful
        """
        try:
            # Generate output path
            output_dir = output_dir or Path(tempfile.gettempdir())
            output_path = output_dir / f"{media_item.get_filename_safe_title()}.mp4"
            
            logger.info(f"Serializing {media_item} to {output_path}")
            
            # Download media
            audio_path = get_temp_path(suffix=".aac")
            video_path = get_temp_path(suffix=".mp4")
            
            logger.debug(f"Downloading audio from {media_item.url}")
            if not self.downloader.download_audio(media_item.url, audio_path):
                raise ProcessingError(f"Failed to download audio for {media_item}")
            
            logger.debug(f"Downloading video from {media_item.url}")
            if not self.downloader.download_video(media_item.url, video_path):
                # Try alternative source or use default video
                logger.warning("Using default video due to download failure")
                video_path = self._create_default_video()
            
            # Apply length percentage if needed
            if media_item.length_percent < 100:
                audio_path = self._trim_media(
                    audio_path,
                    media_item.length_percent,
                    media_item.duration
                )
            
            # Process video with overlays
            title = show_info.get("title", "") if show_info else media_item.get_display_title()
            subtitle = show_info.get("byline", "") if show_info else ""
            marquee = media_item.taxprompt
            
            success = self.video_processor.combine_audio_video(
                audio_path=audio_path,
                video_path=video_path,
                output_path=output_path,
                title=title,
                subtitle=subtitle,
                marquee_text=marquee,
                logo_path=self.logo_path,
                enable_equalizer=get_settings().enable_equalizer
            )
            
            # Clean up temporary files
            safe_delete(audio_path)
            safe_delete(video_path)
            
            if success:
                media_item.serialized = output_path
                logger.info(f"Successfully serialized {media_item}")
                return True
            else:
                raise ProcessingError(f"Video processing failed for {media_item}")
                
        except Exception as e:
            logger.error(f"Serialization error for {media_item}: {e}")
            return False
    
    def serialize_collection(
        self,
        media_items: List[MediaItem],
        show_data: Optional[List[Dict[str, str]]] = None,
        randomize_shows: bool = True
    ) -> List[MediaItem]:
        """
        Serialize a collection of media items.
        
        Args:
            media_items: List of MediaItems to serialize
            show_data: Optional list of show information
            randomize_shows: Whether to randomize show assignment
            
        Returns:
            List of successfully serialized MediaItems
        """
        serialized = []
        
        # Prepare show data
        if show_data and randomize_shows:
            show_data = show_data.copy()
            random.shuffle(show_data)
        
        for i, item in enumerate(media_items):
            # Get show info for this item
            show_info = None
            if show_data:
                show_info = show_data[i % len(show_data)]
            
            if self.serialize_media_item(item, show_info):
                serialized.append(item)
            else:
                logger.warning(f"Failed to serialize {item}")
        
        logger.info(f"Serialized {len(serialized)}/{len(media_items)} items")
        return serialized
    
    def _trim_media(
        self,
        media_path: Path,
        length_percent: int,
        max_duration: Optional[int] = None
    ) -> Path:
        """
        Trim media file to specified length.
        
        Args:
            media_path: Path to media file
            length_percent: Percentage of original length to keep
            max_duration: Maximum duration in seconds
            
        Returns:
            Path to trimmed media file
        """
        from fazztv.processors import AudioProcessor
        
        # Get media duration
        audio_proc = AudioProcessor()
        duration = audio_proc._get_audio_duration(media_path)
        
        if not duration:
            logger.warning(f"Could not determine duration for {media_path}")
            return media_path
        
        # Calculate target duration
        target_duration = duration * (length_percent / 100)
        
        if max_duration:
            target_duration = min(target_duration, max_duration)
        
        # Create trimmed version
        trimmed_path = get_temp_path(suffix=media_path.suffix)
        
        if audio_proc.extract_segment(
            media_path,
            trimmed_path,
            start_time=0,
            duration=target_duration
        ):
            safe_delete(media_path)
            return trimmed_path
        else:
            logger.warning(f"Failed to trim {media_path}, using original")
            return media_path
    
    def _create_default_video(self) -> Path:
        """
        Create a default video when download fails.
        
        Returns:
            Path to default video file
        """
        import subprocess
        
        output_path = get_temp_path(suffix=".mp4")
        
        # Create a simple test pattern video
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={self.base_res}:r=30:d=30",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"Created default video at {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create default video: {e}")
            raise ProcessingError("Could not create default video")
    
    def cleanup_serialized(self, media_items: List[MediaItem]) -> int:
        """
        Clean up serialized files for media items.
        
        Args:
            media_items: List of MediaItems with serialized files
            
        Returns:
            Number of files cleaned up
        """
        cleaned = 0
        
        for item in media_items:
            if item.serialized and item.serialized.exists():
                if safe_delete(item.serialized):
                    item.serialized = None
                    cleaned += 1
        
        logger.info(f"Cleaned up {cleaned} serialized files")
        return cleaned