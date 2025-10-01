"""Enhanced error handling for FazzTV."""

import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from loguru import logger

T = TypeVar('T')


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    NETWORK = "network"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    PROVIDER = "provider"
    MEDIA_PROCESSING = "media_processing"
    BROADCASTING = "broadcasting"
    API = "api"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"


@dataclass
class ErrorContext:
    """Context information for an error."""
    operation: str
    component: str
    timestamp: datetime = field(default_factory=datetime.now)
    user_data: Dict[str, Any] = field(default_factory=dict)
    system_data: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class FazzTVError:
    """Structured error representation."""
    exception: Exception
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    traceback_str: str = field(default="")
    retry_after: Optional[int] = None
    user_message: Optional[str] = None
    technical_message: Optional[str] = None
    recovery_suggestions: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Generate traceback string."""
        if not self.traceback_str:
            self.traceback_str = traceback.format_exc()

        if not self.technical_message:
            self.technical_message = str(self.exception)


class ErrorRegistry:
    """Registry for error patterns and handling strategies."""

    def __init__(self):
        self._handlers: Dict[Type[Exception], Callable[[Exception, ErrorContext], FazzTVError]] = {}
        self._patterns: Dict[str, Dict[str, Any]] = {}

    def register_handler(
        self,
        exception_type: Type[Exception],
        handler: Callable[[Exception, ErrorContext], FazzTVError]
    ) -> None:
        """Register an error handler for a specific exception type."""
        self._handlers[exception_type] = handler
        logger.debug(f"Registered error handler for {exception_type.__name__}")

    def register_pattern(
        self,
        pattern_name: str,
        severity: ErrorSeverity,
        category: ErrorCategory,
        user_message: str,
        recovery_suggestions: List[str] = None,
        retry_after: Optional[int] = None
    ) -> None:
        """Register an error pattern."""
        self._patterns[pattern_name] = {
            "severity": severity,
            "category": category,
            "user_message": user_message,
            "recovery_suggestions": recovery_suggestions or [],
            "retry_after": retry_after
        }
        logger.debug(f"Registered error pattern: {pattern_name}")

    def handle_error(self, exception: Exception, context: ErrorContext) -> FazzTVError:
        """Handle an error using registered handlers or patterns."""
        # Try specific handler first
        handler = self._handlers.get(type(exception))
        if handler:
            return handler(exception, context)

        # Try to match patterns
        exception_str = str(exception).lower()
        for pattern_name, pattern_data in self._patterns.items():
            if pattern_name.lower() in exception_str:
                return FazzTVError(
                    exception=exception,
                    severity=pattern_data["severity"],
                    category=pattern_data["category"],
                    context=context,
                    user_message=pattern_data["user_message"],
                    recovery_suggestions=pattern_data["recovery_suggestions"],
                    retry_after=pattern_data.get("retry_after")
                )

        # Default handling
        return self._create_default_error(exception, context)

    def _create_default_error(self, exception: Exception, context: ErrorContext) -> FazzTVError:
        """Create a default error when no specific handler is found."""
        # Classify by exception type
        if isinstance(exception, (ConnectionError, TimeoutError)):
            severity = ErrorSeverity.MEDIUM
            category = ErrorCategory.NETWORK
        elif isinstance(exception, ValueError):
            severity = ErrorSeverity.LOW
            category = ErrorCategory.VALIDATION
        elif isinstance(exception, PermissionError):
            severity = ErrorSeverity.HIGH
            category = ErrorCategory.AUTHENTICATION
        else:
            severity = ErrorSeverity.MEDIUM
            category = ErrorCategory.SYSTEM

        return FazzTVError(
            exception=exception,
            severity=severity,
            category=category,
            context=context,
            user_message="An unexpected error occurred. Please try again.",
            recovery_suggestions=["Check your configuration", "Retry the operation", "Contact support if issue persists"]
        )


class ErrorHandler:
    """Main error handling coordinator."""

    def __init__(self):
        self.registry = ErrorRegistry()
        self._setup_default_patterns()

    def _setup_default_patterns(self) -> None:
        """Setup default error patterns."""
        patterns = [
            ("timeout", ErrorSeverity.MEDIUM, ErrorCategory.NETWORK, "Request timed out", ["Increase timeout", "Check network connectivity"], 30),
            ("rate limit", ErrorSeverity.LOW, ErrorCategory.RATE_LIMIT, "Rate limit exceeded", ["Wait before retrying", "Check API quotas"], 60),
            ("unauthorized", ErrorSeverity.HIGH, ErrorCategory.AUTHENTICATION, "Authentication failed", ["Check API keys", "Verify credentials"]),
            ("not found", ErrorSeverity.LOW, ErrorCategory.API, "Resource not found", ["Check URL", "Verify resource exists"]),
            ("invalid config", ErrorSeverity.HIGH, ErrorCategory.CONFIGURATION, "Configuration error", ["Check settings", "Validate configuration"]),
            ("ffmpeg", ErrorSeverity.MEDIUM, ErrorCategory.MEDIA_PROCESSING, "Media processing failed", ["Check input file", "Verify FFmpeg installation"]),
            ("broadcast", ErrorSeverity.HIGH, ErrorCategory.BROADCASTING, "Broadcasting failed", ["Check RTMP URL", "Verify stream key"]),
        ]

        for pattern_name, severity, category, message, suggestions, *retry_after in patterns:
            self.registry.register_pattern(
                pattern_name, severity, category, message, suggestions,
                retry_after[0] if retry_after else None
            )

    def handle_error(
        self,
        exception: Exception,
        operation: str,
        component: str,
        **context_data: Any
    ) -> FazzTVError:
        """Handle an error with context."""
        context = ErrorContext(
            operation=operation,
            component=component,
            user_data=context_data.get("user_data", {}),
            system_data=context_data.get("system_data", {}),
            request_id=context_data.get("request_id"),
            session_id=context_data.get("session_id")
        )

        error = self.registry.handle_error(exception, context)
        self._log_error(error)
        return error

    def _log_error(self, error: FazzTVError) -> None:
        """Log an error with appropriate level."""
        log_data = {
            "severity": error.severity.value,
            "category": error.category.value,
            "operation": error.context.operation,
            "component": error.context.component,
            "exception_type": type(error.exception).__name__,
            "user_message": error.user_message,
            "technical_message": error.technical_message
        }

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error in {error.context.component}: {error.technical_message}", **log_data)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error in {error.context.component}: {error.technical_message}", **log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error in {error.context.component}: {error.technical_message}", **log_data)
        else:
            logger.info(f"Low severity error in {error.context.component}: {error.technical_message}", **log_data)


# Global error handler instance
_error_handler = ErrorHandler()


def handle_errors(
    operation: str,
    component: str,
    return_value: Any = None,
    raise_on_critical: bool = True,
    log_errors: bool = True
) -> Callable:
    """Decorator for standardized error handling."""
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, Any]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Union[T, Any]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error = _error_handler.handle_error(e, operation, component)

                if raise_on_critical and error.severity == ErrorSeverity.CRITICAL:
                    raise e

                return return_value
        return wrapper
    return decorator


def log_and_handle_error(
    exception: Exception,
    operation: str,
    component: str,
    **context: Any
) -> FazzTVError:
    """Utility function to log and handle an error."""
    return _error_handler.handle_error(exception, operation, component, **context)


def register_error_handler(
    exception_type: Type[Exception],
    handler: Callable[[Exception, ErrorContext], FazzTVError]
) -> None:
    """Register a custom error handler."""
    _error_handler.registry.register_handler(exception_type, handler)


def register_error_pattern(
    pattern_name: str,
    severity: ErrorSeverity,
    category: ErrorCategory,
    user_message: str,
    recovery_suggestions: List[str] = None,
    retry_after: Optional[int] = None
) -> None:
    """Register a custom error pattern."""
    _error_handler.registry.register_pattern(
        pattern_name, severity, category, user_message, recovery_suggestions, retry_after
    )