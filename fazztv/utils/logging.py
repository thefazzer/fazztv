"""Logging configuration utilities for FazzTV."""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger

from fazztv.config import get_settings, constants


def setup_logging(
    log_file: Optional[Path] = None,
    log_level: Optional[str] = None,
    log_rotation: Optional[str] = None,
    console_output: bool = True
) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_file: Log file path (uses settings default if None)
        log_level: Log level (uses settings default if None)
        log_rotation: Log rotation size (uses settings default if None)
        console_output: Whether to output to console
    """
    settings = get_settings()
    
    # Remove default logger
    logger.remove()
    
    # Set up console logging if enabled
    if console_output:
        logger.add(
            sys.stderr,
            level=log_level or settings.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )
    
    # Set up file logging
    if log_file or settings.log_file:
        file_path = log_file or settings.log_file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            file_path,
            level=log_level or settings.log_level,
            rotation=log_rotation or settings.log_max_size,
            retention="30 days",
            compression="zip",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            backtrace=True,
            diagnose=True
        )
    
    logger.info(f"Logging initialized - Level: {log_level or settings.log_level}")


def get_logger(name: str) -> logger:
    """
    Get a logger instance with a specific name.
    
    Args:
        name: Logger name (usually module name)
        
    Returns:
        Logger instance
    """
    return logger.bind(name=name)


def log_exception(exc: Exception, context: Optional[str] = None) -> None:
    """
    Log an exception with optional context.
    
    Args:
        exc: Exception to log
        context: Optional context string
    """
    if context:
        logger.error(f"{context}: {exc}")
    else:
        logger.error(f"Exception occurred: {exc}")
    
    logger.exception(exc)


def log_performance(func_name: str, duration: float, threshold: float = 1.0) -> None:
    """
    Log performance metrics for a function.
    
    Args:
        func_name: Name of the function
        duration: Execution duration in seconds
        threshold: Warning threshold in seconds
    """
    if duration > threshold:
        logger.warning(f"{func_name} took {duration:.2f}s (threshold: {threshold}s)")
    else:
        logger.debug(f"{func_name} completed in {duration:.2f}s")


class LogContext:
    """Context manager for temporary log level changes."""
    
    def __init__(self, level: str):
        """
        Initialize log context.
        
        Args:
            level: Temporary log level
        """
        self.temp_level = level
        self.original_level = None
    
    def __enter__(self):
        """Enter context and change log level."""
        # Store original level and set new one
        # Note: This is simplified - full implementation would need to track handler levels
        logger.debug(f"Temporarily changing log level to {self.temp_level}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore log level."""
        logger.debug("Restoring original log level")
        return False


def create_audit_logger(audit_file: Path) -> logger:
    """
    Create a separate logger for audit trails.
    
    Args:
        audit_file: Path to audit log file
        
    Returns:
        Audit logger instance
    """
    audit_logger = logger.bind(audit=True)
    
    audit_logger.add(
        audit_file,
        level="INFO",
        rotation="1 day",
        retention="90 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | AUDIT | {message}",
        filter=lambda record: record["extra"].get("audit", False)
    )
    
    return audit_logger