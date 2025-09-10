"""Audio equalizer/visualizer generation for FazzTV."""

from typing import List, Tuple
from loguru import logger

from fazztv.config import constants


class EqualizerGenerator:
    """Generates audio visualizer/equalizer effects."""
    
    def __init__(
        self,
        bands: int = 4,
        height: int = 200,
        width: int = 1280,
        colors: List[str] = None
    ):
        """
        Initialize equalizer generator.
        
        Args:
            bands: Number of frequency bands
            height: Height of visualizer
            width: Width of visualizer
            colors: List of colors for bands
        """
        self.bands = bands
        self.height = height
        self.width = width
        self.colors = colors or ["0xFFFFFFFF"] * bands  # Default white
        
        # Frequency ranges for bands
        self.frequencies = [
            (40, 20),      # Low
            (155, 95),     # Mid-low
            (375, 125),    # Mid-high
            (1250, 750)    # High
        ]
    
    def build_filter_complex(
        self,
        audio_input: str = "1:a",
        video_output: str = "main"
    ) -> str:
        """
        Build FFmpeg filter complex for equalizer visualization.
        
        Args:
            audio_input: Audio input stream label
            video_output: Video stream to overlay onto
            
        Returns:
            Filter complex string
        """
        filter_parts = []
        band_outputs = []
        
        # Generate each frequency band visualization
        for i, (freq, width) in enumerate(self.frequencies):
            band_filter = self._build_band_filter(
                audio_input=audio_input,
                band_index=i,
                frequency=freq,
                bandwidth=width,
                color=self.colors[i % len(self.colors)]
            )
            filter_parts.append(band_filter)
            band_outputs.append(f"band{i}")
        
        # Stack bands horizontally
        stack_filter = f"[{']['.join(band_outputs)}]hstack=inputs={self.bands}[eq_raw]"
        filter_parts.append(stack_filter)
        
        # Scale to desired width
        scale_filter = f"[eq_raw]scale={self.width}:{self.height}[eq_scaled]"
        filter_parts.append(scale_filter)
        
        # Create background for equalizer
        bg_filter = f"color=black:s={self.width}x{self.height}[eq_bg]"
        filter_parts.append(bg_filter)
        
        # Overlay equalizer on background
        overlay_filter = "[eq_bg][eq_scaled]overlay=0:0[eq_final]"
        filter_parts.append(overlay_filter)
        
        # Stack with main video
        final_filter = f"[{video_output}][eq_final]vstack=inputs=2[final]"
        filter_parts.append(final_filter)
        
        return ";".join(filter_parts)
    
    def _build_band_filter(
        self,
        audio_input: str,
        band_index: int,
        frequency: int,
        bandwidth: int,
        color: str
    ) -> str:
        """
        Build filter for a single frequency band.
        
        Args:
            audio_input: Audio input stream
            band_index: Index of this band
            frequency: Center frequency
            bandwidth: Bandwidth
            color: Color for visualization
            
        Returns:
            Filter string for this band
        """
        # Generate unique labels for this band
        base = f"b{band_index}"
        
        filters = [
            # Bandpass filter
            f"[{audio_input}]bandpass=frequency={frequency}:width={bandwidth}:width_type=h[{base}0]",
            
            # Show volume
            f"[{base}0]showvolume=b=0:c={color}:ds=log:f=0:h=100:m=p:o=v:p=1:rate=15:s=0:t=0:v=0:w=200[{base}1]",
            
            # Crop to half height
            f"[{base}1]crop=h=ih/2:w=25:x=0:y=0[{base}2]",
            
            # Scale height
            f"[{base}2]scale=h={self.height}:w=-1[{base}3]",
            
            # Apply smoothing
            f"[{base}3]smartblur[{base}4]",
            
            # Interpolate for smoother motion
            f"[{base}4]minterpolate=fps=30:me_mode=bidir:mi_mode=mci[{base}5]",
            
            # More smoothing
            f"[{base}5]smartblur[{base}6]",
            
            # Split for mirroring
            f"[{base}6]split=2[{base}7][{base}8]",
            
            # Flip one copy
            f"[{base}7]vflip[{base}9]",
            
            # Stack vertically for mirror effect
            f"[{base}8][{base}9]vstack[{base}10]",
            
            # Format to RGBA
            f"[{base}10]format=rgba[{base}11]",
            
            # Add padding
            f"[{base}11]pad=color=black@0:height=0:width=100:x=25:y=0[band{band_index}]"
        ]
        
        return ";".join(filters)
    
    def build_simple_visualizer(
        self,
        audio_input: str = "1:a",
        style: str = "line"
    ) -> str:
        """
        Build a simpler audio visualizer.
        
        Args:
            audio_input: Audio input stream
            style: Visualization style ('line', 'bar', 'dot')
            
        Returns:
            Filter complex string
        """
        if style == "line":
            return (
                f"[{audio_input}]showwaves=s={self.width}x{self.height}:"
                f"mode=line:rate=25:colors=white[viz]"
            )
        elif style == "bar":
            return (
                f"[{audio_input}]showfreqs=s={self.width}x{self.height}:"
                f"mode=bar:cmode=separate:colors=white[viz]"
            )
        elif style == "dot":
            return (
                f"[{audio_input}]showwaves=s={self.width}x{self.height}:"
                f"mode=point:rate=25:colors=white[viz]"
            )
        else:
            logger.warning(f"Unknown visualizer style: {style}, using line")
            return self.build_simple_visualizer(audio_input, "line")