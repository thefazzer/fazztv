"""Overlay management for video processing."""

from typing import Optional, Tuple, List
from pathlib import Path
from abc import ABC, abstractmethod

from fazztv.config import constants


class Overlay(ABC):
    """Base class for video overlays."""

    def __init__(self, position: Tuple[Optional[int], Optional[int]]):
        self.position = position

    @abstractmethod
    def to_filter_string(self, input_label: str, output_label: str) -> str:
        """Convert overlay to FFmpeg filter string."""
        pass


class TextOverlay(Overlay):
    """Text overlay for video."""

    def __init__(self, text: str, position: Tuple[Optional[int], Optional[int]],
                 font_size: int = 24, font_color: str = "white", **kwargs):
        super().__init__(position)
        self.text = text
        self.font_size = font_size
        self.font_color = font_color
        self.color = font_color  # Keep sync
        self.border_color = kwargs.get('border_color', 'black')
        self.border_width = kwargs.get('border_width', 2)
        self.font_path = kwargs.get('font_path', None)
        self.__post_init__()

    def __post_init__(self):
        """Post initialization to handle font_color alias and default font."""
        # Handle font_color alias
        if hasattr(self, 'font_color') and self.font_color != "white":
            self.color = self.font_color
        elif hasattr(self, 'color') and self.color != "white":
            self.font_color = self.color

        # Set default font path
        if self.font_path is None:
            self.font_path = getattr(constants, 'DEFAULT_FONT', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')

    def build_filter(self) -> str:
        """Build filter string for text overlay."""
        return self.to_filter_string("0", "out")

    def to_filter_string(self, input_label: str, output_label: str) -> str:
        """Convert text overlay to FFmpeg filter."""
        # Sanitize text
        safe_text = self._sanitize_text(self.text)
        
        # Build position string
        x_pos = f"{self.position[0]}" if self.position[0] is not None else "(w-text_w)/2"
        y_pos = f"{self.position[1]}" if self.position[1] is not None else "(h-text_h)/2"
        
        filter_str = (
            f"[{input_label}]drawtext="
            f"text='{safe_text}':"
            f"fontfile={self.font_path}:"
            f"fontsize={self.font_size}:"
            f"fontcolor={self.color}:"
            f"bordercolor={self.border_color}:"
            f"borderw={self.border_width}:"
            f"x={x_pos}:"
            f"y={y_pos}"
            f"[{output_label}]"
        )
        
        return filter_str
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text for FFmpeg."""
        if not text:
            return ""
        
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = text.replace("'", "\\'")
        text = text.replace(':', '\\:')
        text = text.replace(',', '\\,')
        text = text.replace(';', '\\;')
        text = text.replace('=', '\\=')
        
        return text


class ImageOverlay(Overlay):
    """Image overlay for video."""

    def __init__(self, image_path: Path, position: Tuple[Optional[int], Optional[int]],
                 scale: float = 1.0, **kwargs):
        super().__init__(position)
        self.image_path = image_path
        self.scale = scale
        self.size = kwargs.get('size', None)
        self.opacity = kwargs.get('opacity', 1.0)

    def build_filter(self) -> str:
        """Build filter string for image overlay."""
        return self.to_filter_string("0", "out")

    def to_filter_string(self, input_label: str, output_label: str) -> str:
        """Convert image overlay to FFmpeg filter."""
        # Build position string
        x_pos = f"{self.position[0]}" if self.position[0] is not None else "(W-w)/2"
        y_pos = f"{self.position[1]}" if self.position[1] is not None else "(H-h)/2"
        
        # Scale if size is specified
        scale_str = ""
        if self.size:
            scale_str = f"scale={self.size[0]}:{self.size[1]},"
        
        # Apply opacity if needed
        opacity_str = ""
        if self.opacity < 1.0:
            opacity_str = f"format=rgba,colorchannelmixer=aa={self.opacity},"
        
        filter_str = (
            f"[1:v]{scale_str}{opacity_str}[logo];"
            f"[{input_label}][logo]overlay={x_pos}:{y_pos}[{output_label}]"
        )
        
        return filter_str


class VideoOverlay(Overlay):
    """Video overlay for video (picture-in-picture)."""

    def __init__(self, video_path: Path, position: Tuple[Optional[int], Optional[int]],
                 scale: float = 1.0, loop: bool = True, **kwargs):
        super().__init__(position)
        self.video_path = video_path
        self.scale = scale
        self.loop = loop
        self.size = kwargs.get('size', None)

    def build_filter(self) -> str:
        """Build filter string for video overlay."""
        return self.to_filter_string("0", "out")

    def to_filter_string(self, input_label: str, output_label: str) -> str:
        """Convert video overlay to FFmpeg filter."""
        # Build position string
        x_pos = f"{self.position[0]}" if self.position[0] is not None else "(W-w)/2"
        y_pos = f"{self.position[1]}" if self.position[1] is not None else "(H-h)/2"

        # Loop setting
        loop_str = ",setpts=PTS-STARTPTS" if self.loop else ""

        # Scale setting
        if self.size:
            scale_str = f"scale={self.size[0]}:{self.size[1]}"
        elif self.scale != 1.0:
            scale_str = f"scale=iw*{self.scale}:ih*{self.scale}"
        else:
            scale_str = ""

        scale_with_comma = f"{scale_str}," if scale_str else ""

        filter_str = (
            f"[2:v]{scale_with_comma}{loop_str.lstrip(',')}[pip];"
            f"[{input_label}][pip]overlay={x_pos}:{y_pos}[{output_label}]"
        )

        return filter_str


class OverlayManager:
    """Manages multiple overlays for video processing."""
    
    def __init__(self):
        """Initialize overlay manager."""
        self.overlays: List[Overlay] = []
    
    def add_overlay(self, overlay: Overlay):
        """Add an overlay to the manager."""
        self.overlays.append(overlay)
    
    def remove_overlay(self, overlay: Overlay):
        """Remove an overlay from the manager."""
        if overlay in self.overlays:
            self.overlays.remove(overlay)
    
    def clear(self):
        """Clear all overlays."""
        self.overlays.clear()
    
    def build_filter_complex(self, input_label: str = "0:v") -> str:
        """
        Build FFmpeg filter complex for all overlays.
        
        Args:
            input_label: Label of the input stream
            
        Returns:
            Filter complex string
        """
        if not self.overlays:
            return ""
        
        filter_parts = []
        current_input = input_label
        
        for i, overlay in enumerate(self.overlays):
            output_label = f"overlay{i}"
            filter_part = overlay.to_filter_string(current_input, output_label)
            filter_parts.append(filter_part)
            current_input = output_label
        
        # Rename final output to standard label
        filter_parts.append(f"[{current_input}]copy[overlayed]")
        
        return ";".join(filter_parts)
    
    def get_input_files(self) -> List[Path]:
        """Get list of additional input files needed for overlays."""
        input_files = []

        for overlay in self.overlays:
            if isinstance(overlay, ImageOverlay):
                input_files.append(overlay.image_path)
            elif isinstance(overlay, VideoOverlay):
                input_files.append(overlay.video_path)

        return input_files

    def apply_overlays(self, input_path: Path, output_path: Path) -> bool:
        """
        Apply overlays to a video file using FFmpeg.

        Args:
            input_path: Path to input video file
            output_path: Path to output video file

        Returns:
            True if successful, False otherwise
        """
        import subprocess

        if not self.overlays:
            return False

        filter_complex = self.build_filter_complex()
        if not filter_complex:
            return False

        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-filter_complex', filter_complex,
            '-map', '[overlayed]',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-y',  # Overwrite output
            str(output_path)
        ]

        # Add input files for image/video overlays
        input_files = self.get_input_files()
        for i, file_path in enumerate(input_files, 1):
            cmd.insert(3 + i*2, '-i')
            cmd.insert(4 + i*2, str(file_path))

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False