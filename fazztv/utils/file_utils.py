"""File validation and utility functions for FazzTV."""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Union
from loguru import logger

from fazztv.config import constants


def is_valid_file(file_path: Union[str, Path], operation_name: str = "file operation") -> bool:
    """
    Validate that a file exists, is readable, and has content.

    Args:
        file_path: Path to file to check
        operation_name: Name of operation for logging

    Returns:
        True if file is valid, False otherwise
    """
    if not file_path:
        logger.error(f"{operation_name}: No file path provided")
        return False

    path = Path(file_path) if isinstance(file_path, str) else file_path

    if not path.exists():
        logger.error(f"{operation_name}: File does not exist: {path}")
        return False

    if not path.is_file():
        logger.error(f"{operation_name}: Path is not a file: {path}")
        return False

    if path.stat().st_size == 0:
        logger.error(f"{operation_name}: File is empty: {path}")
        return False

    try:
        # Test if file is readable
        with path.open('rb') as f:
            f.read(1)
    except (IOError, OSError) as e:
        logger.error(f"{operation_name}: File is not readable: {path}, Error: {e}")
        return False

    return True


def is_valid_audio_file(file_path: Union[str, Path]) -> bool:
    """
    Validate that a file is a valid audio file.

    Args:
        file_path: Path to audio file

    Returns:
        True if file is a valid audio file, False otherwise
    """
    path = Path(file_path) if isinstance(file_path, str) else file_path

    if not is_valid_file(path, "Audio validation"):
        return False

    # Check file extension
    if path.suffix.lower() not in constants.AUDIO_EXTENSIONS:
        logger.error(f"Audio validation: Invalid audio file extension: {path.suffix}")
        return False

    return True


def is_valid_video_file(file_path: Union[str, Path]) -> bool:
    """
    Validate that a file is a valid video file.

    Args:
        file_path: Path to video file

    Returns:
        True if file is a valid video file, False otherwise
    """
    path = Path(file_path) if isinstance(file_path, str) else file_path

    if not is_valid_file(path, "Video validation"):
        return False

    # Check file extension
    if path.suffix.lower() not in constants.VIDEO_EXTENSIONS:
        logger.error(f"Video validation: Invalid video file extension: {path.suffix}")
        return False

    return True


def ensure_directory_exists(directory: Union[str, Path]) -> bool:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory: Path to directory

    Returns:
        True if directory exists or was created successfully, False otherwise
    """
    path = Path(directory) if isinstance(directory, str) else directory

    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directory ensured: {path}")
        return True
    except (OSError, IOError) as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False


def safe_copy_file(src: Union[str, Path], dst: Union[str, Path],
                   overwrite: bool = False) -> bool:
    """
    Safely copy a file with validation.

    Args:
        src: Source file path
        dst: Destination file path
        overwrite: Whether to overwrite existing destination

    Returns:
        True if copy was successful, False otherwise
    """
    src_path = Path(src) if isinstance(src, str) else src
    dst_path = Path(dst) if isinstance(dst, str) else dst

    if not is_valid_file(src_path, "File copy source"):
        return False

    if dst_path.exists() and not overwrite:
        logger.error(f"File copy: Destination exists and overwrite=False: {dst_path}")
        return False

    try:
        # Ensure destination directory exists
        if not ensure_directory_exists(dst_path.parent):
            return False

        shutil.copy2(src_path, dst_path)
        logger.debug(f"File copied: {src_path} -> {dst_path}")
        return True
    except (OSError, IOError) as e:
        logger.error(f"File copy failed: {src_path} -> {dst_path}, Error: {e}")
        return False


def safe_move_file(src: Union[str, Path], dst: Union[str, Path],
                   overwrite: bool = False) -> bool:
    """
    Safely move a file with validation.

    Args:
        src: Source file path
        dst: Destination file path
        overwrite: Whether to overwrite existing destination

    Returns:
        True if move was successful, False otherwise
    """
    src_path = Path(src) if isinstance(src, str) else src
    dst_path = Path(dst) if isinstance(dst, str) else dst

    if not is_valid_file(src_path, "File move source"):
        return False

    if dst_path.exists() and not overwrite:
        logger.error(f"File move: Destination exists and overwrite=False: {dst_path}")
        return False

    try:
        # Ensure destination directory exists
        if not ensure_directory_exists(dst_path.parent):
            return False

        # Remove destination if it exists and overwrite is True
        if dst_path.exists() and overwrite:
            dst_path.unlink()

        shutil.move(str(src_path), str(dst_path))
        logger.debug(f"File moved: {src_path} -> {dst_path}")
        return True
    except (OSError, IOError) as e:
        logger.error(f"File move failed: {src_path} -> {dst_path}, Error: {e}")
        return False


def find_files_by_extension(directory: Union[str, Path],
                           extensions: List[str]) -> List[Path]:
    """
    Find all files in directory with specific extensions.

    Args:
        directory: Directory to search
        extensions: List of extensions to match (including dot)

    Returns:
        List of Path objects for matching files
    """
    dir_path = Path(directory) if isinstance(directory, str) else directory

    if not dir_path.exists() or not dir_path.is_dir():
        logger.error(f"Find files: Invalid directory: {dir_path}")
        return []

    matching_files = []
    for extension in extensions:
        pattern = f"*{extension}"
        matching_files.extend(dir_path.glob(pattern))

    # Filter for valid files only
    valid_files = []
    for file_path in matching_files:
        if is_valid_file(file_path, "File search"):
            valid_files.append(file_path)

    logger.debug(f"Found {len(valid_files)} valid files with extensions {extensions} in {dir_path}")
    return valid_files


def get_file_size_mb(file_path: Union[str, Path]) -> Optional[float]:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to file

    Returns:
        File size in MB or None if file doesn't exist
    """
    path = Path(file_path) if isinstance(file_path, str) else file_path

    if not path.exists():
        return None

    try:
        size_bytes = path.stat().st_size
        return size_bytes / (1024 * 1024)  # Convert to MB
    except (OSError, IOError):
        return None


def cleanup_temp_files(temp_dir: Union[str, Path],
                      pattern: str = "*",
                      max_age_hours: Optional[int] = None) -> int:
    """
    Clean up temporary files in a directory.

    Args:
        temp_dir: Temporary directory to clean
        pattern: File pattern to match (default: all files)
        max_age_hours: Only delete files older than this many hours

    Returns:
        Number of files deleted
    """
    dir_path = Path(temp_dir) if isinstance(temp_dir, str) else temp_dir

    if not dir_path.exists() or not dir_path.is_dir():
        logger.error(f"Cleanup: Invalid temp directory: {dir_path}")
        return 0

    files_deleted = 0

    try:
        for file_path in dir_path.glob(pattern):
            if not file_path.is_file():
                continue

            should_delete = True

            if max_age_hours:
                import time
                file_age_hours = (time.time() - file_path.stat().st_mtime) / 3600
                should_delete = file_age_hours > max_age_hours

            if should_delete:
                try:
                    file_path.unlink()
                    files_deleted += 1
                    logger.debug(f"Deleted temp file: {file_path}")
                except (OSError, IOError) as e:
                    logger.warning(f"Failed to delete temp file {file_path}: {e}")

        logger.info(f"Cleaned up {files_deleted} temporary files from {dir_path}")
        return files_deleted

    except Exception as e:
        logger.error(f"Error during cleanup of {dir_path}: {e}")
        return files_deleted