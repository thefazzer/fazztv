"""Audio processing functionality for FazzTV."""

import subprocess
from typing import Optional, List
from pathlib import Path
from loguru import logger

from fazztv.config import constants


class AudioProcessor:
    """Handles audio processing operations using FFmpeg."""
    
    def normalize_audio(
        self,
        input_path: Path,
        output_path: Path,
        target_level: float = -23.0
    ) -> bool:
        """
        Normalize audio levels.
        
        Args:
            input_path: Input audio file
            output_path: Output audio file
            target_level: Target loudness in LUFS
            
        Returns:
            True if successful, False otherwise
        """
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-af", f"loudnorm=I={target_level}:TP=-1.5:LRA=11",
            "-c:a", constants.AUDIO_CODEC,
            "-b:a", constants.AUDIO_BITRATE,
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Audio normalization error: {e}")
            return False
    
    def add_fade(
        self,
        input_path: Path,
        output_path: Path,
        fade_in: float = 0,
        fade_out: float = 0
    ) -> bool:
        """
        Add fade in/out to audio.
        
        Args:
            input_path: Input audio file
            output_path: Output audio file
            fade_in: Fade in duration in seconds
            fade_out: Fade out duration in seconds
            
        Returns:
            True if successful, False otherwise
        """
        filters = []
        
        if fade_in > 0:
            filters.append(f"afade=in:d={fade_in}")
        
        if fade_out > 0:
            # Get audio duration first
            duration = self._get_audio_duration(input_path)
            if duration:
                filters.append(f"afade=out:st={duration - fade_out}:d={fade_out}")
        
        if not filters:
            # No effects to add
            import shutil
            shutil.copy(input_path, output_path)
            return True
        
        filter_str = ",".join(filters)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-af", filter_str,
            "-c:a", constants.AUDIO_CODEC,
            "-b:a", constants.AUDIO_BITRATE,
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Audio fade error: {e}")
            return False
    
    def mix_audio(
        self,
        inputs: List[Path],
        output_path: Path,
        weights: Optional[List[float]] = None
    ) -> bool:
        """
        Mix multiple audio tracks.
        
        Args:
            inputs: List of input audio files
            output_path: Output audio file
            weights: Optional mixing weights for each input
            
        Returns:
            True if successful, False otherwise
        """
        if not inputs:
            logger.error("No input files provided for mixing")
            return False
        
        if len(inputs) == 1:
            # Single input, just copy
            import shutil
            shutil.copy(inputs[0], output_path)
            return True
        
        # Build FFmpeg command
        cmd = ["ffmpeg", "-y"]
        
        # Add all inputs
        for input_file in inputs:
            cmd.extend(["-i", str(input_file)])
        
        # Build mixing filter
        if weights and len(weights) == len(inputs):
            weight_str = ":".join([f"{w}" for w in weights])
            filter_str = f"amix=inputs={len(inputs)}:weights='{weight_str}'"
        else:
            filter_str = f"amix=inputs={len(inputs)}"
        
        cmd.extend([
            "-filter_complex", filter_str,
            "-c:a", constants.AUDIO_CODEC,
            "-b:a", constants.AUDIO_BITRATE,
            str(output_path)
        ])
        
        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Audio mixing error: {e}")
            return False
    
    def extract_segment(
        self,
        input_path: Path,
        output_path: Path,
        start_time: float = 0,
        duration: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> bool:
        """
        Extract a segment from audio.
        
        Args:
            input_path: Input audio file
            output_path: Output audio file
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
            "-c:a", constants.AUDIO_CODEC,
            "-b:a", constants.AUDIO_BITRATE,
            str(output_path)
        ])
        
        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Audio segment extraction error: {e}")
            return False
    
    def apply_effects(
        self,
        input_path: Path,
        output_path: Path,
        effects: List[str]
    ) -> bool:
        """
        Apply audio effects.
        
        Args:
            input_path: Input audio file
            output_path: Output audio file
            effects: List of FFmpeg audio filter effects
            
        Returns:
            True if successful, False otherwise
        """
        if not effects:
            import shutil
            shutil.copy(input_path, output_path)
            return True
        
        filter_str = ",".join(effects)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-af", filter_str,
            "-c:a", constants.AUDIO_CODEC,
            "-b:a", constants.AUDIO_BITRATE,
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Audio effects error: {e}")
            return False
    
    def _get_audio_duration(self, audio_path: Path) -> Optional[float]:
        """Get duration of audio in seconds."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
        
        return None