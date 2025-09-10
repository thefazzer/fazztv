"""File system utilities for FazzTV."""

import os
import shutil
from pathlib import Path
from typing import Optional, List
from loguru import logger


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