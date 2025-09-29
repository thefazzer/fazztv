"""Download utilities for FazzTV media processing."""

import os
import tempfile
from typing import Optional, List, Dict, Any
from pathlib import Path
import yt_dlp
from loguru import logger

from fazztv.config import constants
from fazztv.utils.file_utils import is_valid_file, safe_copy_file, ensure_directory_exists
from fazztv.utils.error_handling import log_exceptions, safe_execute


def get_cache_file_path(temp_dir: str, guid: str, file_type: str) -> str:
    """
    Get the cache file path for a given GUID and file type.

    Args:
        temp_dir: Temporary directory for cache files
        guid: Unique identifier for the episode
        file_type: Type of file ('audio' or 'video')

    Returns:
        Cache file path
    """
    if file_type == 'audio':
        suffix = constants.AUDIO_CACHE_SUFFIX
    elif file_type == 'video':
        suffix = constants.VIDEO_CACHE_SUFFIX
    elif file_type == 'output':
        suffix = constants.OUTPUT_CACHE_SUFFIX
    else:
        raise ValueError(f"Invalid file type: {file_type}")

    return os.path.join(temp_dir, f"{guid}{suffix}")


@log_exceptions(return_value=False)
def get_cached_file(guid: Optional[str], output_file: str, temp_dir: str, file_type: str) -> bool:
    """
    Check for and use cached file if available.

    Args:
        guid: Unique identifier for the episode
        output_file: Target output file path
        temp_dir: Temporary directory for cache files
        file_type: Type of file ('audio' or 'video')

    Returns:
        True if cached file was used successfully, False otherwise
    """
    if not guid:
        return False

    cached_file = get_cache_file_path(temp_dir, guid, file_type)

    if is_valid_file(cached_file, f"Cached {file_type} check"):
        logger.info(f"Using cached {file_type} file for GUID {guid}")
        return safe_copy_file(cached_file, output_file, overwrite=True)

    return False


@log_exceptions(return_value=None)
def cache_file(output_file: str, guid: Optional[str], temp_dir: str, file_type: str) -> None:
    """
    Cache file for future use.

    Args:
        output_file: Source file to cache
        guid: Unique identifier for the episode
        temp_dir: Temporary directory for cache files
        file_type: Type of file ('audio' or 'video')
    """
    if not guid or not is_valid_file(output_file, f"{file_type.title()} caching"):
        return

    cached_file = get_cache_file_path(temp_dir, guid, file_type)
    logger.debug(f"Caching {file_type} file to {cached_file}")
    safe_copy_file(output_file, cached_file, overwrite=True)


def get_yt_dlp_audio_options(base_output: str) -> Dict[str, Any]:
    """
    Get yt-dlp options for audio download.

    Args:
        base_output: Base output path without extension

    Returns:
        Dictionary of yt-dlp options
    """
    return {
        "format": "bestaudio/best",
        "max_duration": constants.ELAPSED_TUNE_SECONDS,
        "outtmpl": f"{base_output}.%(ext)s",
        "quiet": False,
        "verbose": True,
        "overwrites": True,
        "continuedl": False,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": constants.AUDIO_PREFERRED_CODEC,
            "preferredquality": constants.AUDIO_PREFERRED_QUALITY,
        }]
    }


def get_yt_dlp_video_options(output_file: str) -> Dict[str, Any]:
    """
    Get yt-dlp options for video download.

    Args:
        output_file: Output file path

    Returns:
        Dictionary of yt-dlp options
    """
    return {
        "format": constants.VIDEO_PREFERRED_FORMAT,
        "max_duration": constants.ELAPSED_TUNE_SECONDS,
        "outtmpl": output_file,
        "quiet": True,
        "overwrites": True,
        "continuedl": False,
        "age_limit": constants.AGE_LIMIT_UNRESTRICTED
    }


@log_exceptions(return_value=None)
def find_downloaded_audio_file(base_output: str) -> Optional[str]:
    """
    Find the audio file created by yt-dlp.

    Args:
        base_output: Base output path without extension

    Returns:
        Path to found audio file or None if not found
    """
    # Try standard extensions first
    for ext in constants.AUDIO_SEARCH_EXTENSIONS:
        potential_file = f"{base_output}{ext}"
        if os.path.exists(potential_file) and os.path.getsize(potential_file) > 0:
            logger.debug(f"Found audio file: {potential_file} ({os.path.getsize(potential_file)} bytes)")
            return potential_file

    # Try directory search if standard approach fails
    dir_path = os.path.dirname(base_output)
    base_name = os.path.basename(base_output)
    logger.debug(f"Searching directory {dir_path} for files starting with {base_name}")

    try:
        for file in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file)
            if file.startswith(base_name) and os.path.getsize(file_path) > 0:
                logger.debug(f"Found alternative audio file: {file_path}")
                return file_path
    except OSError as e:
        logger.error(f"Error searching directory {dir_path}: {e}")

    return None


@log_exceptions(return_value=False)
def move_audio_to_output(found_file: str, output_file: str) -> bool:
    """
    Move downloaded audio file to expected location.

    Args:
        found_file: Path to found audio file
        output_file: Target output file path

    Returns:
        True if move was successful, False otherwise
    """
    if found_file == output_file:
        return True

    logger.debug(f"Renaming {found_file} to {output_file}")

    try:
        if os.path.exists(output_file):
            os.remove(output_file)
        os.rename(found_file, output_file)
        return True
    except OSError as e:
        logger.error(f"Failed to move audio file from {found_file} to {output_file}: {e}")
        return False


@log_exceptions(return_value=False)
def prepare_output_directory(output_file: str) -> bool:
    """
    Ensure output directory exists.

    Args:
        output_file: Output file path

    Returns:
        True if directory preparation was successful, False otherwise
    """
    output_dir = os.path.dirname(output_file)
    if output_dir:
        return ensure_directory_exists(output_dir)
    return True


def prepare_base_output_path(output_file: str) -> str:
    """
    Create base output path without extension for yt-dlp.

    Args:
        output_file: Target output file path

    Returns:
        Base output path suitable for yt-dlp
    """
    base_output = os.path.splitext(output_file)[0]
    if base_output.endswith('.aac'):
        base_output = base_output[:-4]
    return base_output


@log_exceptions(return_value=False)
def download_with_yt_dlp(url: str, yt_dlp_opts: Dict[str, Any], operation_name: str) -> bool:
    """
    Download media using yt-dlp with given options.

    Args:
        url: URL to download from
        yt_dlp_opts: yt-dlp options dictionary
        operation_name: Name of operation for logging

    Returns:
        True if download was successful, False otherwise
    """
    try:
        with yt_dlp.YoutubeDL(yt_dlp_opts) as ydl:
            if "extract_info" in operation_name.lower():
                info = ydl.extract_info(url, download=True)
                if not info:
                    logger.error(f"No information extracted for URL: {url}")
                    return False
            else:
                ydl.download([url])
        return True
    except Exception as e:
        logger.error(f"Error in {operation_name}: {e}")
        return False