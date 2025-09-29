"""Subprocess utilities for safe command execution."""
import subprocess
import logging
import shlex
from typing import Optional, List, Union, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


def safe_subprocess_run(
    cmd: Union[str, List[str]],
    timeout: Optional[int] = None,
    check: bool = False,
    capture_output: bool = True,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None
) -> Tuple[int, str, str]:
    """
    Safely execute a subprocess command with proper error handling.

    Args:
        cmd: Command to execute (string or list)
        timeout: Timeout in seconds
        check: Whether to raise exception on non-zero exit code
        capture_output: Whether to capture stdout and stderr
        cwd: Working directory for the command
        env: Environment variables

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        # Convert string commands to list for safer execution
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
            logger.warning("String command converted to list for safer execution")

        result = subprocess.run(
            cmd,
            shell=False,  # Always use shell=False for security
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            check=check,
            cwd=cwd,
            env=env
        )

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout} seconds: {cmd}")
        if e.stdout:
            logger.debug(f"Partial stdout: {e.stdout.decode('utf-8', errors='ignore')}")
        if e.stderr:
            logger.debug(f"Partial stderr: {e.stderr.decode('utf-8', errors='ignore')}")
        raise

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {cmd}")
        if e.stdout:
            logger.debug(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.debug(f"Stderr: {e.stderr}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error running command: {cmd}, Error: {e}")
        raise


def check_command_available(command: str) -> bool:
    """
    Check if a command is available in the system PATH.

    Args:
        command: Name of the command to check

    Returns:
        True if command is available, False otherwise
    """
    try:
        returncode, _, _ = safe_subprocess_run(
            ["which", command],
            capture_output=True
        )
        return returncode == 0
    except Exception:
        return False


def escape_ffmpeg_text(text: str) -> str:
    """
    Escape text for use in FFmpeg filter expressions.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for FFmpeg filters
    """
    # FFmpeg filter text needs special character escaping
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace(",", "\\,")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace("=", "\\=")
    return text