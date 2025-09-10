"""Overlay management for video processing."""

from typing import Optional, Tuple, List, Any
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod

from fazztv.config import constants


@dataclass
class Overlay(ABC):
    """Base class for video overlays."""
    position: Tuple[Optional[int], Optional[int]]  # (x, y) where None means center
    
    @abstractmethod
    def to_filter_string(self, input_label: str, output_label: str) -> str:
        """Convert overlay to FFmpeg filter string."""
        pass


@dataclass
class TextOverlay(Overlay):
    """Text overlay for video."""
    text: str
    font_size: int = 24
    color: str = "white"
    border_color: str = "black"
    border_width: int = 2
    font_path: str = constants.DEFAULT_FONT
    
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


@dataclass
class ImageOverlay(Overlay):
    """Image overlay for video."""
    image_path: Path
    size: Optional[Tuple[int, int]] = None  # (width, height)
    opacity: float = 1.0
    
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


@dataclass
class VideoOverlay(Overlay):
    """Video overlay for video (picture-in-picture)."""
    video_path: Path
    size: Tuple[int, int]  # Required for video overlay
    loop: bool = True
    
    def to_filter_string(self, input_label: str, output_label: str) -> str:
        """Convert video overlay to FFmpeg filter."""
        # Build position string
        x_pos = f"{self.position[0]}" if self.position[0] is not None else "(W-w)/2"
        y_pos = f"{self.position[1]}" if self.position[1] is not None else "(H-h)/2"
        
        # Loop setting
        loop_str = ",setpts=PTS-STARTPTS" if self.loop else ""
        
        filter_str = (
            f"[2:v]scale={self.size[0]}:{self.size[1]}{loop_str}[pip];"
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