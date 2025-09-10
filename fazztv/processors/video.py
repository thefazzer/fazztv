"""Video processing functionality for FazzTV."""

import subprocess
import tempfile
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from loguru import logger

from fazztv.config import get_settings, constants
from fazztv.processors.overlay import OverlayManager, TextOverlay, ImageOverlay
from fazztv.processors.equalizer import EqualizerGenerator


class VideoProcessor:
    """Handles video processing operations using FFmpeg."""
    
    def __init__(self):
        """Initialize video processor."""
        self.settings = get_settings()
        self.overlay_manager = OverlayManager()
        self.equalizer = EqualizerGenerator()
    
    def combine_audio_video(
        self,
        audio_path: Path,
        video_path: Path,
        output_path: Path,
        title: str = "",
        subtitle: str = "",
        byline: str = "",
        marquee_text: str = "",
        logo_path: Optional[Path] = None,
        enable_equalizer: bool = False,
        additional_overlays: Optional[List[Any]] = None
    ) -> bool:
        """
        Combine audio and video with overlays.
        
        Args:
            audio_path: Path to audio file
            video_path: Path to video file
            output_path: Path for output file
            title: Main title text
            subtitle: Subtitle text
            byline: Byline text
            marquee_text: Scrolling marquee text
            logo_path: Optional logo image path
            enable_equalizer: Whether to add audio visualizer
            additional_overlays: Optional list of additional overlays
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Combining {audio_path} + {video_path} => {output_path}")
        
        # Create temporary files for text overlays
        temp_files = []
        
        try:
            # Prepare text overlays
            if title:
                title_overlay = TextOverlay(
                    text=title,
                    font_size=constants.TITLE_FONT_SIZE,
                    color=constants.COLOR_RED,
                    position=(None, 30)  # Centered horizontally, 30px from top
                )
                self.overlay_manager.add_overlay(title_overlay)
            
            if subtitle:
                subtitle_overlay = TextOverlay(
                    text=subtitle,
                    font_size=constants.SUBTITLE_FONT_SIZE,
                    color=constants.COLOR_YELLOW,
                    position=(None, 90)  # Centered horizontally, 90px from top
                )
                self.overlay_manager.add_overlay(subtitle_overlay)
            
            if byline:
                byline_overlay = TextOverlay(
                    text=byline,
                    font_size=constants.BYLINE_FONT_SIZE,
                    color=constants.COLOR_WHITE,
                    position=(None, 160)  # Centered horizontally, 160px from top
                )
                self.overlay_manager.add_overlay(byline_overlay)
            
            # Add logo if provided
            if logo_path and logo_path.exists():
                logo_overlay = ImageOverlay(
                    image_path=logo_path,
                    position=constants.LOGO_POSITION,
                    size=(constants.LOGO_SIZE, constants.LOGO_SIZE)
                )
                self.overlay_manager.add_overlay(logo_overlay)
            
            # Add additional overlays if provided
            if additional_overlays:
                for overlay in additional_overlays:
                    self.overlay_manager.add_overlay(overlay)
            
            # Build FFmpeg command
            cmd = self._build_ffmpeg_command(
                audio_path=audio_path,
                video_path=video_path,
                output_path=output_path,
                marquee_text=marquee_text,
                enable_equalizer=enable_equalizer
            )
            
            # Execute FFmpeg
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr.decode('utf-8', 'ignore')}")
                return False
            
            logger.info(f"Successfully created video: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Video processing error: {e}")
            return False
        
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()
            
            # Clear overlays for next use
            self.overlay_manager.clear()
    
    def add_fade_effects(
        self,
        input_path: Path,
        output_path: Path,
        fade_in: int = 0,
        fade_out: int = 0
    ) -> bool:
        """
        Add fade in/out effects to video.
        
        Args:
            input_path: Input video path
            output_path: Output video path
            fade_in: Fade in duration in seconds
            fade_out: Fade out duration in seconds
            
        Returns:
            True if successful, False otherwise
        """
        filters = []
        
        if fade_in > 0:
            filters.append(f"fade=in:0:{fade_in * self.settings.fps}")
        
        if fade_out > 0:
            # Need to get video duration first
            duration = self._get_video_duration(input_path)
            if duration:
                start_frame = int((duration - fade_out) * self.settings.fps)
                filters.append(f"fade=out:{start_frame}:{fade_out * self.settings.fps}")
        
        if not filters:
            # No effects to add, just copy
            import shutil
            shutil.copy(input_path, output_path)
            return True
        
        filter_complex = ",".join(filters)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", filter_complex,
            "-c:a", "copy",
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Fade effect error: {e}")
            return False
    
    def scale_video(
        self,
        input_path: Path,
        output_path: Path,
        resolution: Optional[str] = None,
        maintain_aspect: bool = True
    ) -> bool:
        """
        Scale video to specified resolution.
        
        Args:
            input_path: Input video path
            output_path: Output video path
            resolution: Target resolution (e.g., "1280x720")
            maintain_aspect: Whether to maintain aspect ratio
            
        Returns:
            True if successful, False otherwise
        """
        resolution = resolution or self.settings.base_resolution
        width, height = resolution.split('x')
        
        if maintain_aspect:
            scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        else:
            scale_filter = f"scale={width}:{height}"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", scale_filter,
            "-c:a", "copy",
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Scale video error: {e}")
            return False
    
    def extract_clip(
        self,
        input_path: Path,
        output_path: Path,
        start_time: float = 0,
        duration: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> bool:
        """
        Extract a clip from video.
        
        Args:
            input_path: Input video path
            output_path: Output video path
            start_time: Start time in seconds
            duration: Duration in seconds
            end_time: End time in seconds (alternative to duration)
            
        Returns:
            True if successful, False otherwise
        """
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", str(input_path)
        ]
        
        if duration:
            cmd.extend(["-t", str(duration)])
        elif end_time:
            cmd.extend(["-to", str(end_time)])
        
        cmd.extend([
            "-c", "copy",
            str(output_path)
        ])
        
        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Extract clip error: {e}")
            return False
    
    def _build_ffmpeg_command(
        self,
        audio_path: Path,
        video_path: Path,
        output_path: Path,
        marquee_text: str = "",
        enable_equalizer: bool = False
    ) -> List[str]:
        """Build the FFmpeg command for processing."""
        cmd = ["ffmpeg", "-y"]
        
        # Input files
        cmd.extend(["-i", str(video_path)])
        cmd.extend(["-i", str(audio_path)])
        
        # Build filter complex
        filter_parts = []
        
        # Scale video
        filter_parts.append(f"[0:v]scale={self.settings.base_resolution}:force_original_aspect_ratio=decrease,setsar=1[scaled]")
        
        # Add overlays from overlay manager
        current_output = "scaled"
        overlay_filters = self.overlay_manager.build_filter_complex(current_output)
        if overlay_filters:
            filter_parts.append(overlay_filters)
            current_output = "overlayed"
        
        # Add marquee if provided
        if marquee_text:
            marquee_filter = self._build_marquee_filter(marquee_text, current_output)
            filter_parts.append(marquee_filter)
            current_output = "marquee"
        
        # Add equalizer if enabled
        if enable_equalizer and self.settings.enable_equalizer:
            eq_filter = self.equalizer.build_filter_complex(audio_input="1:a", video_output=current_output)
            filter_parts.append(eq_filter)
            current_output = "final"
        else:
            filter_parts.append(f"[{current_output}]copy[final]")
        
        # Join all filters
        filter_complex = ";".join(filter_parts)
        
        cmd.extend(["-filter_complex", filter_complex])
        
        # Map outputs
        cmd.extend(["-map", "[final]"])
        cmd.extend(["-map", "1:a"])
        
        # Output settings
        cmd.extend([
            "-c:v", constants.VIDEO_CODEC,
            "-preset", constants.VIDEO_PRESET,
            "-c:a", constants.AUDIO_CODEC,
            "-b:a", constants.AUDIO_BITRATE,
            "-shortest",
            "-r", str(self.settings.fps),
            "-vsync", "2",
            "-movflags", "+faststart",
            str(output_path)
        ])
        
        return cmd
    
    def _build_marquee_filter(self, text: str, input_label: str) -> str:
        """Build marquee filter for scrolling text."""
        # Sanitize text for FFmpeg
        safe_text = self._sanitize_text(text)
        
        marquee_filter = (
            f"[{input_label}]drawtext="
            f"text='{safe_text}':"
            f"fontfile={constants.DEFAULT_FONT}:"
            f"fontsize={constants.MARQUEE_FONT_SIZE}:"
            f"fontcolor=white:bordercolor=black:borderw=3:"
            f"x=w-mod({self.settings.scroll_speed}*t\\,w+text_w):"
            f"y=h-th-10[marquee]"
        )
        
        return marquee_filter
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text for FFmpeg drawtext filter."""
        if not text:
            return ""
        
        # Replace problematic characters
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = text.replace("'", "\\'")
        text = text.replace(':', '\\:')
        text = text.replace(',', '\\,')
        text = text.replace(';', '\\;')
        text = text.replace('=', '\\=')
        
        return text
    
    def _get_video_duration(self, video_path: Path) -> Optional[float]:
        """Get duration of video in seconds."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Error getting video duration: {e}")
        
        return None