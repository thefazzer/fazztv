import subprocess
from typing import List, Callable, Tuple
from loguru import logger

from fazztv.models import MediaItem
from fazztv.config import constants
from fazztv.core.error_handling import handle_errors
from fazztv.utils.error_handling import handle_subprocess_result, validate_file_exists

class RTMPBroadcaster:
    """Handles broadcasting of serialized MediaItems to RTMP endpoints."""
    
    def __init__(self, rtmp_url: str = constants.DEFAULT_RTMP_URL):
        """
        Initialize the broadcaster with an RTMP URL.
        
        Args:
            rtmp_url: The RTMP URL to broadcast to
        """
        self.rtmp_url = rtmp_url
    
    @handle_errors(operation="broadcast_item", component="broadcaster", return_value=False)
    def broadcast_item(self, media_item: MediaItem) -> bool:
        """
        Broadcast a single media item to the RTMP endpoint.
        
        Args:
            media_item: The MediaItem to broadcast
            
        Returns:
            bool: True if broadcasting was successful
        """
        if not media_item.is_serialized():
            logger.error(f"Media item {media_item} is not serialized")
            return False

        serialized_path = media_item.serialized
        if not validate_file_exists(serialized_path, "Broadcasting"):
            return False
        
        cmd = [
            "ffmpeg", "-y", "-re",
            "-i", serialized_path,
            "-c", "copy",
            "-f", "flv",
            self.rtmp_url
        ]
        
        logger.debug(f"Broadcasting {media_item} to {self.rtmp_url}")
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=constants.FFMPEG_TIMEOUT)
            return handle_subprocess_result(result, f"Broadcasting {media_item}")
        except Exception as e:
            logger.error(f"Broadcasting exception: {e}")
            return False
    
    def broadcast_filtered_collection(self, 
                                     media_items: List[MediaItem], 
                                     filter_func: Callable[[MediaItem], bool]) -> List[Tuple[MediaItem, bool]]:
        """
        Broadcast a filtered collection of media items.
        
        Args:
            media_items: List of MediaItems to potentially broadcast
            filter_func: Lambda function to filter media items
            
        Returns:
            List of tuples (MediaItem, broadcast_success)
        """
        filtered_items = [item for item in media_items if filter_func(item)]
        logger.info(f"Broadcasting {len(filtered_items)} items after filtering from {len(media_items)} total")
        
        results = []
        for item in filtered_items:
            success = self.broadcast_item(item)
            results.append((item, success))
        
        return results