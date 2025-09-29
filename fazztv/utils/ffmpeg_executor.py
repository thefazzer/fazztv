"""Centralized FFmpeg command executor with standardized error handling."""

import json
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class FFmpegExecutor:
    """Centralized FFmpeg command executor with standardized error handling."""

    DEFAULT_TIMEOUT = 300  # 5 minutes

    def __init__(self, timeout: Optional[int] = None):
        """Initialize FFmpeg executor.

        Args:
            timeout: Command timeout in seconds (default: 300)
        """
        self.timeout = timeout or self.DEFAULT_TIMEOUT

    def execute(
        self,
        command: List[str],
        check: bool = True,
        capture_output: bool = True,
        text: bool = True,
        timeout: Optional[int] = None
    ) -> subprocess.CompletedProcess:
        """Execute FFmpeg command with standardized error handling.

        Args:
            command: Command arguments as list
            check: Whether to check return code
            capture_output: Whether to capture stdout/stderr
            text: Whether to decode output as text
            timeout: Override default timeout

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: If command fails
            subprocess.TimeoutExpired: If command times out
        """
        timeout = timeout or self.timeout

        logger.debug(f"Executing FFmpeg command: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                check=check,
                capture_output=capture_output,
                text=text,
                timeout=timeout
            )

            if result.returncode == 0:
                logger.debug("FFmpeg command completed successfully")
            else:
                logger.warning(f"FFmpeg command returned code {result.returncode}")

            return result

        except subprocess.TimeoutExpired as e:
            logger.error(f"FFmpeg command timed out after {timeout}s: {e}")
            raise

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed: {e}")
            if e.stderr:
                logger.error(f"FFmpeg stderr: {e.stderr}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error executing FFmpeg: {e}")
            raise

    def get_duration(self, file_path: Union[str, Path]) -> float:
        """Extract media duration using ffprobe.

        Args:
            file_path: Path to media file

        Returns:
            Duration in seconds

        Raises:
            ValueError: If duration cannot be extracted
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        command = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(file_path)
        ]

        try:
            result = self.execute(command, check=True)
            data = json.loads(result.stdout)

            if "format" in data and "duration" in data["format"]:
                return float(data["format"]["duration"])
            else:
                raise ValueError(f"Could not extract duration from {file_path}")

        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Failed to get duration for {file_path}: {e}")

    def probe_format(self, file_path: Union[str, Path]) -> dict:
        """Probe media format using ffprobe.

        Args:
            file_path: Path to media file

        Returns:
            Format information dictionary

        Raises:
            ValueError: If format cannot be probed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        command = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path)
        ]

        try:
            result = self.execute(command, check=True)
            return json.loads(result.stdout)

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to probe format for {file_path}: {e}")

    def validate_output(self, output_path: Union[str, Path]) -> bool:
        """Validate that output file was created successfully.

        Args:
            output_path: Path to output file

        Returns:
            True if valid, False otherwise
        """
        output_path = Path(output_path)

        if not output_path.exists():
            logger.error(f"Output file not created: {output_path}")
            return False

        if output_path.stat().st_size == 0:
            logger.error(f"Output file is empty: {output_path}")
            return False

        try:
            # Try to probe the file to ensure it's valid
            self.probe_format(output_path)
            return True
        except Exception as e:
            logger.error(f"Output file validation failed: {e}")
            return False

    @staticmethod
    def escape_text(text: str) -> str:
        """Escape text for FFmpeg filter arguments.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for FFmpeg filters
        """
        # Escape special characters for FFmpeg
        replacements = [
            ("\\", "\\\\"),
            ("'", "\\'"),
            ('"', '\\"'),
            (":", "\\:"),
            ("\n", "\\n"),
            ("\r", "\\r"),
            ("\t", "\\t"),
            ("=", "\\="),
            (",", "\\,"),
            ("[", "\\["),
            ("]", "\\]"),
            (";", "\\;")
        ]

        for old, new in replacements:
            text = text.replace(old, new)

        return text

    def check_codec_support(self, codec: str) -> bool:
        """Check if codec is supported by FFmpeg.

        Args:
            codec: Codec name to check

        Returns:
            True if supported, False otherwise
        """
        command = ["ffmpeg", "-codecs"]

        try:
            result = self.execute(command, check=True, timeout=10)
            return codec in result.stdout
        except Exception:
            return False