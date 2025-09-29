"""File system utilities for FazzTV."""

import shutil
from pathlib import Path
from typing import Optional, List, Union
from loguru import logger

from fazztv.config import constants


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        The path object
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_delete(path: Path) -> bool:
    """
    Safely delete a file or directory.
    
    Args:
        path: Path to delete
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        if path.is_file():
            path.unlink()
            logger.debug(f"Deleted file: {path}")
            return True
        elif path.is_dir():
            shutil.rmtree(path)
            logger.debug(f"Deleted directory: {path}")
            return True
        else:
            logger.warning(f"Path does not exist: {path}")
            return False
    except Exception as e:
        logger.error(f"Error deleting {path}: {e}")
        return False


def get_file_size(path: Path) -> int:
    """
    Get file size in bytes.
    
    Args:
        path: File path
        
    Returns:
        File size in bytes, or 0 if file doesn't exist
    """
    if path.exists() and path.is_file():
        return path.stat().st_size
    return 0


def format_file_size(size_bytes: int) -> str:
    """
    Format file size to human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def copy_file(source: Path, destination: Path, overwrite: bool = False) -> bool:
    """
    Copy a file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite if destination exists
        
    Returns:
        True if copied successfully, False otherwise
    """
    try:
        if destination.exists() and not overwrite:
            logger.warning(f"Destination already exists: {destination}")
            return False
        
        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source, destination)
        logger.debug(f"Copied {source} to {destination}")
        return True
    except Exception as e:
        logger.error(f"Error copying file: {e}")
        return False


def move_file(source: Path, destination: Path, overwrite: bool = False) -> bool:
    """
    Move a file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite if destination exists
        
    Returns:
        True if moved successfully, False otherwise
    """
    try:
        if destination.exists() and not overwrite:
            logger.warning(f"Destination already exists: {destination}")
            return False
        
        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(str(source), str(destination))
        logger.debug(f"Moved {source} to {destination}")
        return True
    except Exception as e:
        logger.error(f"Error moving file: {e}")
        return False


def find_files(
    directory: Path,
    pattern: str = "*",
    recursive: bool = True
) -> List[Path]:
    """
    Find files matching a pattern in directory.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern to match
        recursive: Whether to search recursively
        
    Returns:
        List of matching file paths
    """
    if not directory.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return []
    
    if recursive:
        return list(directory.rglob(pattern))
    else:
        return list(directory.glob(pattern))


def get_temp_path(prefix: str = "fazztv_", suffix: str = "") -> Path:
    """
    Get a temporary file path.
    
    Args:
        prefix: Prefix for the temp file
        suffix: Suffix/extension for the temp file
        
    Returns:
        Path to temporary file
    """
    import tempfile
    
    temp_file = tempfile.NamedTemporaryFile(
        prefix=prefix,
        suffix=suffix,
        delete=False
    )
    temp_path = Path(temp_file.name)
    temp_file.close()
    
    return temp_path


def cleanup_old_files(
    directory: Path,
    days_old: int,
    pattern: str = "*"
) -> int:
    """
    Clean up files older than specified days.
    
    Args:
        directory: Directory to clean
        days_old: Age threshold in days
        pattern: File pattern to match
        
    Returns:
        Number of files deleted
    """
    from datetime import datetime, timedelta
    
    if not directory.exists():
        return 0
    
    cutoff_time = datetime.now() - timedelta(days=days_old)
    deleted_count = 0
    
    for file_path in directory.glob(pattern):
        if file_path.is_file():
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_time < cutoff_time:
                if safe_delete(file_path):
                    deleted_count += 1
    
    logger.info(f"Deleted {deleted_count} files older than {days_old} days from {directory}")
    return deleted_count


def get_directory_size(directory: Path) -> int:
    """
    Get total size of all files in directory.

    Args:
        directory: Directory path

    Returns:
        Total size in bytes
    """
    total_size = 0

    if not directory.exists():
        return 0

    for file_path in directory.rglob("*"):
        if file_path.is_file():
            total_size += file_path.stat().st_size

    return total_size


def find_downloaded_file(base_path: str, extensions: Optional[List[str]] = None) -> Optional[Path]:
    """
    Find a downloaded file with any of the given extensions.

    Args:
        base_path: Base path without extension
        extensions: List of extensions to check (without dot)

    Returns:
        Path to the found file, or None if not found
    """
    if extensions is None:
        extensions = ['mp3', 'm4a', 'mp4', 'webm', 'opus', 'mkv', 'avi']

    base = Path(base_path)

    # Check with each extension
    for ext in extensions:
        file_path = base.with_suffix(f'.{ext}')
        if file_path.exists():
            logger.debug(f"Found file: {file_path}")
            return file_path

    # Check if base path itself exists (might have extension already)
    if base.exists() and base.is_file():
        logger.debug(f"Found file: {base}")
        return base

    # Try to find files with similar names in the same directory
    if base.parent.exists():
        pattern = f"{base.stem}.*"
        for file_path in base.parent.glob(pattern):
            if file_path.is_file() and file_path.suffix[1:] in extensions:
                logger.debug(f"Found file with pattern: {file_path}")
                return file_path

    logger.warning(f"No file found for base path: {base_path}")
    return None


def safe_file_copy(source: Path, destination: Path, overwrite: bool = False) -> bool:
    """
    Safely copy a file with error handling.

    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite if destination exists

    Returns:
        True if copied successfully, False otherwise
    """
    return copy_file(source, destination, overwrite)


def safe_file_delete(path: Path) -> bool:
    """
    Safely delete a file with error handling.

    Args:
        path: File path to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    return safe_delete(path)


def safe_mkdir(path: Path) -> Path:
    """
    Safely create a directory with error handling.

    Args:
        path: Directory path to create

    Returns:
        The path object
    """
    return ensure_directory(path)


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


def find_files_by_extension(directory: Union[str, Path], extensions: List[str]) -> List[Path]:
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