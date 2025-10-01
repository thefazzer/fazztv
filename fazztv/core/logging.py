"""Standardized logging for FazzTV."""

import sys
import json
from typing import Any, Dict, Optional, Union, List
from pathlib import Path
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger


class LogLevel(Enum):
    """Log levels."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Log output formats."""
    STANDARD = "standard"
    JSON = "json"
    STRUCTURED = "structured"
    SIMPLE = "simple"


@dataclass
class LogConfig:
    """Configuration for logging setup."""
    level: LogLevel = LogLevel.INFO
    format_type: LogFormat = LogFormat.STANDARD
    file_path: Optional[Path] = None
    rotation: str = "100 MB"
    retention: str = "30 days"
    compression: str = "gz"
    serialize: bool = False
    colorize: bool = True
    diagnose: bool = True
    catch: bool = True
    enqueue: bool = False
    extra_fields: Dict[str, Any] = field(default_factory=dict)


class ComponentLogger:
    """Component-specific logger with standardized formatting."""

    def __init__(self, component: str, config: Optional[LogConfig] = None):
        self.component = component
        self.config = config or LogConfig()
        self._extra_context = {"component": component}

    def _log(self, level: LogLevel, message: str, **context: Any) -> None:
        """Internal logging method."""
        log_context = {**self._extra_context, **context}
        logger.log(level.value, message, **log_context)

    def trace(self, message: str, **context: Any) -> None:
        """Log trace message."""
        self._log(LogLevel.TRACE, message, **context)

    def debug(self, message: str, **context: Any) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **context)

    def info(self, message: str, **context: Any) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, **context)

    def success(self, message: str, **context: Any) -> None:
        """Log success message."""
        self._log(LogLevel.SUCCESS, message, **context)

    def warning(self, message: str, **context: Any) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **context)

    def error(self, message: str, exception: Optional[Exception] = None, **context: Any) -> None:
        """Log error message."""
        if exception:
            context["exception_type"] = type(exception).__name__
            context["exception_message"] = str(exception)
        self._log(LogLevel.ERROR, message, **context)

    def critical(self, message: str, exception: Optional[Exception] = None, **context: Any) -> None:
        """Log critical message."""
        if exception:
            context["exception_type"] = type(exception).__name__
            context["exception_message"] = str(exception)
        self._log(LogLevel.CRITICAL, message, **context)

    def operation_start(self, operation: str, **context: Any) -> None:
        """Log operation start."""
        self.info(f"Starting operation: {operation}", operation=operation, **context)

    def operation_end(self, operation: str, success: bool = True, **context: Any) -> None:
        """Log operation end."""
        if success:
            self.success(f"Completed operation: {operation}", operation=operation, **context)
        else:
            self.error(f"Failed operation: {operation}", operation=operation, **context)

    def performance(self, operation: str, duration: float, **context: Any) -> None:
        """Log performance metrics."""
        self.info(
            f"Performance: {operation} took {duration:.3f}s",
            operation=operation,
            duration=duration,
            performance=True,
            **context
        )

    def api_request(self, method: str, url: str, status_code: Optional[int] = None, **context: Any) -> None:
        """Log API request."""
        self.info(
            f"API Request: {method} {url}",
            api_request=True,
            method=method,
            url=url,
            status_code=status_code,
            **context
        )

    def api_response(self, method: str, url: str, status_code: int, duration: float, **context: Any) -> None:
        """Log API response."""
        level = LogLevel.INFO if 200 <= status_code < 400 else LogLevel.WARNING
        self._log(
            level,
            f"API Response: {method} {url} - {status_code} ({duration:.3f}s)",
            api_response=True,
            method=method,
            url=url,
            status_code=status_code,
            duration=duration,
            **context
        )

    def media_processing(self, operation: str, file_path: str, **context: Any) -> None:
        """Log media processing operation."""
        self.info(
            f"Media Processing: {operation} - {file_path}",
            media_processing=True,
            operation=operation,
            file_path=file_path,
            **context
        )

    def broadcast_event(self, event: str, **context: Any) -> None:
        """Log broadcast event."""
        self.info(
            f"Broadcast Event: {event}",
            broadcast=True,
            event=event,
            **context
        )


class LogManager:
    """Centralized logging management."""

    def __init__(self):
        self._loggers: Dict[str, ComponentLogger] = {}
        self._config: Optional[LogConfig] = None
        self._initialized = False

    def initialize(self, config: LogConfig) -> None:
        """Initialize logging system."""
        if self._initialized:
            logger.warning("Log manager already initialized")
            return

        self._config = config
        self._setup_loguru(config)
        self._initialized = True
        logger.info("Logging system initialized", config=self._config_to_dict(config))

    def _setup_loguru(self, config: LogConfig) -> None:
        """Setup loguru with configuration."""
        # Remove default handler
        logger.remove()

        # Console handler
        console_format = self._get_format(config.format_type, console=True)
        logger.add(
            sys.stderr,
            format=console_format,
            level=config.level.value,
            colorize=config.colorize and sys.stderr.isatty(),
            diagnose=config.diagnose,
            catch=config.catch,
            enqueue=config.enqueue
        )

        # File handler if specified
        if config.file_path:
            file_format = self._get_format(config.format_type, console=False)
            logger.add(
                config.file_path,
                format=file_format,
                level=config.level.value,
                rotation=config.rotation,
                retention=config.retention,
                compression=config.compression,
                serialize=config.serialize,
                diagnose=config.diagnose,
                catch=config.catch,
                enqueue=config.enqueue
            )

    def _get_format(self, format_type: LogFormat, console: bool = True) -> str:
        """Get format string based on format type."""
        timestamp = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>" if console else "{time:YYYY-MM-DD HH:mm:ss.SSS}"
        level = "<level>{level: <8}</level>" if console else "{level: <8}"
        component = "<cyan>{extra[component]: <15}</cyan>" if console else "{extra[component]: <15}"
        message = "<level>{message}</level>" if console else "{message}"

        if format_type == LogFormat.SIMPLE:
            return f"{level} | {message}"
        elif format_type == LogFormat.JSON:
            return "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name} | {message} | {extra}"
        elif format_type == LogFormat.STRUCTURED:
            return f"{timestamp} | {level} | {component} | {message} | {{extra}}"
        else:  # STANDARD
            return f"{timestamp} | {level} | {component} | {message}"

    def get_logger(self, component: str) -> ComponentLogger:
        """Get or create a component logger."""
        if component not in self._loggers:
            self._loggers[component] = ComponentLogger(component, self._config)
        return self._loggers[component]

    def set_level(self, level: LogLevel) -> None:
        """Change logging level globally."""
        if self._config:
            self._config.level = level
            logger.info(f"Logging level changed to {level.value}")

    def add_context(self, **context: Any) -> None:
        """Add global context to all loggers."""
        logger.configure(extra=context)

    def _config_to_dict(self, config: LogConfig) -> Dict[str, Any]:
        """Convert config to dictionary for logging."""
        return {
            "level": config.level.value,
            "format": config.format_type.value,
            "file_path": str(config.file_path) if config.file_path else None,
            "rotation": config.rotation,
            "retention": config.retention,
            "compression": config.compression
        }


# Global log manager instance
_log_manager = LogManager()


def initialize_logging(
    level: LogLevel = LogLevel.INFO,
    format_type: LogFormat = LogFormat.STANDARD,
    file_path: Optional[Union[str, Path]] = None,
    **kwargs: Any
) -> None:
    """Initialize the logging system."""
    config = LogConfig(
        level=level,
        format_type=format_type,
        file_path=Path(file_path) if file_path else None,
        **kwargs
    )
    _log_manager.initialize(config)


def get_logger(component: str) -> ComponentLogger:
    """Get a component-specific logger."""
    return _log_manager.get_logger(component)


def set_log_level(level: LogLevel) -> None:
    """Set global logging level."""
    _log_manager.set_level(level)


def add_global_context(**context: Any) -> None:
    """Add global context to all log messages."""
    _log_manager.add_context(**context)


# Convenience function for backward compatibility
def setup_logging(
    log_file: Optional[str] = None,
    log_level: str = "INFO",
    log_format: str = "standard"
) -> None:
    """Setup logging with simple parameters."""
    level = LogLevel(log_level.upper())
    format_type = LogFormat(log_format.lower())
    initialize_logging(level=level, format_type=format_type, file_path=log_file)