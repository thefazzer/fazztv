"""Subprocess utilities for safe command execution."""
import subprocess
import logging
import shlex
import sys
from typing import Optional, List, Union, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def safe_subprocess_run(
    cmd: Union[str, List[str]],
    timeout: Optional[int] = None,
    check: bool = False,
    capture_output: bool = True,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
    input: Optional[str] = None
) -> Optional[subprocess.CompletedProcess]:
    """
    Safely execute a subprocess command with proper error handling.

    Args:
        cmd: Command to execute (string or list)
        timeout: Timeout in seconds
        check: Whether to raise exception on non-zero exit code
        capture_output: Whether to capture stdout and stderr
        cwd: Working directory for the command
        env: Environment variables
        input: Input to pass to the subprocess

    Returns:
        CompletedProcess object or None on error
    """
    try:
        # Convert string commands to list for safer execution
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
            logger.warning("String command converted to list for safer execution")

        kwargs: dict[str, Any] = {
            "capture_output": capture_output,
            "text": True,
            "check": check,
            "timeout": timeout
        }

        if cwd is not None:
            kwargs["cwd"] = cwd
        if env is not None:
            kwargs["env"] = env
        if input is not None:
            kwargs["input"] = input

        result = subprocess.run(cmd, **kwargs)
        return result

    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout} seconds: {cmd}")
        return None

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {cmd}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error running command: {cmd}, Error: {e}")
        return None


def check_command_available(command: str) -> bool:
    """
    Check if a command is available in the system PATH.

    Args:
        command: Name of the command to check

    Returns:
        True if command is available, False otherwise
    """
    try:
        # Use 'where' on Windows, 'which' on Unix-like systems
        check_cmd = "where" if sys.platform == "win32" else "which"
        result = safe_subprocess_run(
            [check_cmd, command],
            capture_output=True
        )
        return result is not None and result.returncode == 0
    except Exception:
        return False


def escape_ffmpeg_text(text: Optional[str]) -> str:
    """
    Escape text for use in FFmpeg filter expressions.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for FFmpeg filters
    """
    if text is None:
        return ""

    # FFmpeg filter text needs special character escaping
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace('"', '\\\"')
    text = text.replace(":", "\\:")
    text = text.replace(",", "\\,")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace("=", "\\=")
    text = text.replace("%", "\\%")
    text = text.replace("$", "\\$")
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "\\r")
    return text