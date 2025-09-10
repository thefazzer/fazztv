"""RTMP broadcasting functionality for FazzTV."""

import subprocess
from typing import List, Tuple, Optional, Callable
from pathlib import Path
from loguru import logger

from fazztv.models import MediaItem, BroadcastError
from fazztv.config import get_settings


class RTMPBroadcaster:
    """Handles broadcasting of serialized MediaItems to RTMP endpoints."""
    
    def __init__(self, rtmp_url: Optional[str] = None):
        """
        Initialize the broadcaster with an RTMP URL.
        
        Args:
            rtmp_url: The RTMP URL to broadcast to (uses settings if None)
        """
        settings = get_settings()
        self.rtmp_url = rtmp_url or settings.rtmp_url
        self.total_broadcast_count = 0
        self.successful_broadcast_count = 0
        self.failed_broadcast_count = 0
    
    def broadcast_item(self, media_item: MediaItem) -> bool:
        """
        Broadcast a single media item to the RTMP endpoint.
        
        Args:
            media_item: The MediaItem to broadcast
            
        Returns:
            True if broadcasting was successful
            
        Raises:
            BroadcastError: If broadcasting fails
        """
        self.total_broadcast_count += 1
        
        if not media_item.is_serialized():
            error_msg = f"Media item {media_item} is not serialized"
            logger.error(error_msg)
            self.failed_broadcast_count += 1
            raise BroadcastError(error_msg)
        
        serialized_path = media_item.serialized
        if not serialized_path.exists():
            error_msg = f"Serialized file {serialized_path} does not exist"
            logger.error(error_msg)
            self.failed_broadcast_count += 1
            raise BroadcastError(error_msg)
        
        cmd = [
            "ffmpeg", "-y", "-re",
            "-i", str(serialized_path),
            "-c", "copy",
            "-f", "flv",
            self.rtmp_url
        ]
        
        logger.info(f"Broadcasting {media_item} to {self.rtmp_url}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=media_item.duration * 2 if media_item.duration else None
            )
            
            if result.returncode != 0:
                error_msg = f"Broadcasting failed: {result.stderr.decode('utf-8', 'ignore')}"
                logger.error(error_msg)
                self.failed_broadcast_count += 1
                return False
            
            logger.info(f"Successfully broadcast {media_item}")
            self.successful_broadcast_count += 1
            return True
            
        except subprocess.TimeoutExpired:
            error_msg = f"Broadcasting timeout for {media_item}"
            logger.error(error_msg)
            self.failed_broadcast_count += 1
            raise BroadcastError(error_msg)
        except Exception as e:
            error_msg = f"Broadcasting exception: {e}"
            logger.error(error_msg)
            self.failed_broadcast_count += 1
            raise BroadcastError(error_msg)
    
    def broadcast_collection(
        self,
        media_items: List[MediaItem],
        on_success: Optional[Callable[[MediaItem], None]] = None,
        on_failure: Optional[Callable[[MediaItem, Exception], None]] = None,
        stop_on_failure: bool = False
    ) -> List[Tuple[MediaItem, bool]]:
        """
        Broadcast a collection of media items.
        
        Args:
            media_items: List of MediaItems to broadcast
            on_success: Optional callback for successful broadcasts
            on_failure: Optional callback for failed broadcasts
            stop_on_failure: Whether to stop on first failure
            
        Returns:
            List of tuples (MediaItem, success_status)
        """
        results = []
        
        logger.info(f"Starting broadcast of {len(media_items)} items")
        
        for i, item in enumerate(media_items, 1):
            logger.info(f"Broadcasting item {i}/{len(media_items)}: {item}")
            
            try:
                success = self.broadcast_item(item)
                results.append((item, success))
                
                if success and on_success:
                    on_success(item)
                elif not success and on_failure:
                    on_failure(item, BroadcastError("Broadcast failed"))
                
                if not success and stop_on_failure:
                    logger.warning("Stopping broadcast due to failure")
                    break
                    
            except Exception as e:
                results.append((item, False))
                
                if on_failure:
                    on_failure(item, e)
                
                if stop_on_failure:
                    logger.warning(f"Stopping broadcast due to exception: {e}")
                    break
        
        logger.info(
            f"Broadcast complete: {self.successful_broadcast_count} successful, "
            f"{self.failed_broadcast_count} failed"
        )
        
        return results
    
    def broadcast_filtered(
        self,
        media_items: List[MediaItem],
        filter_func: Callable[[MediaItem], bool]
    ) -> List[Tuple[MediaItem, bool]]:
        """
        Broadcast filtered media items.
        
        Args:
            media_items: List of MediaItems to potentially broadcast
            filter_func: Function to filter items
            
        Returns:
            List of tuples (MediaItem, success_status)
        """
        filtered_items = [item for item in media_items if filter_func(item)]
        
        logger.info(
            f"Broadcasting {len(filtered_items)} items after filtering "
            f"from {len(media_items)} total"
        )
        
        return self.broadcast_collection(filtered_items)
    
    def test_connection(self) -> bool:
        """
        Test RTMP connection.
        
        Returns:
            True if connection is successful
        """
        # Create a small test video
        test_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac",
            "-f", "flv",
            "-t", "1",
            self.rtmp_url
        ]
        
        try:
            logger.info(f"Testing RTMP connection to {self.rtmp_url}")
            result = subprocess.run(test_cmd, capture_output=True, timeout=10)
            
            if result.returncode == 0:
                logger.info("RTMP connection test successful")
                return True
            else:
                logger.error(f"RTMP connection test failed: {result.stderr.decode('utf-8', 'ignore')}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("RTMP connection test timed out")
            return False
        except Exception as e:
            logger.error(f"RTMP connection test error: {e}")
            return False
    
    def get_stats(self) -> dict:
        """
        Get broadcasting statistics.
        
        Returns:
            Dictionary of statistics
        """
        success_rate = 0
        if self.total_broadcast_count > 0:
            success_rate = (
                self.successful_broadcast_count / self.total_broadcast_count * 100
            )
        
        return {
            "rtmp_url": self.rtmp_url,
            "total_broadcasts": self.total_broadcast_count,
            "successful": self.successful_broadcast_count,
            "failed": self.failed_broadcast_count,
            "success_rate": round(success_rate, 2)
        }
    
    def reset_stats(self):
        """Reset broadcasting statistics."""
        self.total_broadcast_count = 0
        self.successful_broadcast_count = 0
        self.failed_broadcast_count = 0
        logger.info("Broadcasting statistics reset")