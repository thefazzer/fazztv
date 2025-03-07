import random
import os
import subprocess
from typing import List, Optional

def serialize_media_item(self, media_item: MediaItem, output_file: Optional[str] = None,
                        ftv_shows: Optional[List[dict]] = None) -> bool:
    """
    Serialize a media item to a file or memory buffer.
    
    Args:
        media_item: The MediaItem to serialize
        output_file: Optional output file path. If None, serializes to a temporary file.
        ftv_shows: Optional list of show dictionaries with title and byline
        
    Returns:
        bool: True if serialization was successful
    """
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Download the video
        if not self.download_video(media_item, temp_path):
            logger.error(f"Failed to download video for {media_item}")
            return False
        
        # Get the original duration
        original_duration = self.get_video_duration(temp_path)
        if original_duration <= 0:
            logger.error(f"Invalid duration for {media_item}")
            return False
        
        # Calculate the target duration based on length_percent
        target_duration = original_duration * (media_item.length_percent / 100.0)
        
        # Create a temporary file for the marquee text
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as marquee_file:
            marquee_path = marquee_file.name
            # Flatten multiline to single line
            marquee_text = media_item.taxprompt.replace("\n", " ").replace("\r", " ")
            marquee_file.write(marquee_text)
        
        # Determine output path
        final_output = output_file if output_file else tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        
        # Select a random show if ftv_shows is provided
        show_title = ""
        show_byline = ""
        if ftv_shows and len(ftv_shows) > 0:
            show = random.choice(ftv_shows)
            show_title = show.get("title", "")
            show_byline = show.get("byline", "")
        
        # Prepare FFmpeg command with artist, song, and show information
        cmd = self._build_ffmpeg_command(
            temp_path, 
            marquee_path, 
            final_output, 
            target_duration,
            artist=media_item.artist,
            song=media_item.song,
            show_title=show_title,
            show_byline=show_byline
        )
        
        # Add the -t parameter to limit the output duration
        cmd.insert(-1, "-t")
        cmd.insert(-1, str(target_duration))
        
        # Run FFmpeg
        logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr.decode('utf-8', 'ignore')}")
            return False
        
        # Store the serialized path in the media item
        media_item.serialized = final_output
        return True
        
    except Exception as e:
        logger.error(f"Serialization error: {e}")
        return False
    finally:
        # Clean up temporary files
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(marquee_path):
            os.remove(marquee_path)