"""Common error handling utilities for FazzTV."""

import functools
import os
import time
import traceback
from typing import Any, Callable, Optional, Type, TypeVar, Union
from loguru import logger
import requests

T = TypeVar('T')

def log_exceptions(
    return_value: Any = False,
    logger_func: Callable[[str], None] = logger.error,
    reraise: bool = False,
    include_traceback: bool = True
):
    """
    Decorator to handle exceptions with logging.

    Args:
        return_value: Value to return when an exception occurs (default: False)
        logger_func: Logging function to use (default: logger.error)
        reraise: Whether to reraise the exception after logging (default: False)
        include_traceback: Whether to include traceback in log (default: True)

    Returns:
        Decorated function that handles exceptions
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, Any]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Union[T, Any]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Create error message
                error_msg = f"Error in {func.__name__}: {e}"

                if include_traceback:
                    error_msg += f"\nTraceback: {traceback.format_exc()}"

                # Log the error
                logger_func(error_msg)

                # Reraise if requested
                if reraise:
                    raise

                # Return the specified return value
                return return_value

        return wrapper
    return decorator

def safe_execute(
    func: Callable[..., T],
    args: tuple = (),
    kwargs: Optional[dict] = None,
    default_return: Any = None,
    log_errors: bool = True,
    operation_name: Optional[str] = None
) -> Union[T, Any]:
    """
    Safely execute a function with error handling.

    Args:
        func: Function to execute
        args: Arguments to pass to function
        kwargs: Keyword arguments to pass to function
        default_return: Value to return on error (default: None)
        log_errors: Whether to log errors (default: True)
        operation_name: Name for the operation in logs (default: function name)

    Returns:
        Function result or default_return on error
    """
    if kwargs is None:
        kwargs = {}

    operation = operation_name or func.__name__

    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error in {operation}: {e}")
            logger.debug(f"Traceback for {operation}: {traceback.format_exc()}")
        return default_return

def validate_file_exists(file_path: str, operation_name: str = "file operation") -> bool:
    """
    Validate that a file exists and log error if not.

    Args:
        file_path: Path to file to check
        operation_name: Name of operation for logging

    Returns:
        True if file exists, False otherwise
    """
    if not file_path:
        logger.error(f"{operation_name}: No file path provided")
        return False

    if not os.path.exists(file_path):
        logger.error(f"{operation_name}: File does not exist: {file_path}")
        return False

    if os.path.getsize(file_path) == 0:
        logger.error(f"{operation_name}: File is empty: {file_path}")
        return False

    return True

def handle_subprocess_result(
    result,
    operation_name: str,
    success_message: Optional[str] = None
) -> bool:
    """
    Handle subprocess result with standardized logging.

    Args:
        result: subprocess.CompletedProcess result
        operation_name: Name of the operation for logging
        success_message: Optional success message to log

    Returns:
        True if successful, False otherwise
    """
    try:
        if result.returncode != 0:
            error_output = result.stderr.decode('utf-8', 'ignore') if result.stderr else "No error output"
            logger.error(f"{operation_name} failed (exit code {result.returncode}): {error_output}")
            return False

        if success_message:
            logger.info(success_message)

        return True

    except Exception as e:
        logger.error(f"Error processing {operation_name} result: {e}")
        return False

class ErrorContext:
    """Context manager for handling errors in a block of code."""

    def __init__(
        self,
        operation_name: str,
        reraise: bool = False,
        return_value: Any = None,
        log_success: bool = False
    ):
        """
        Initialize error context.

        Args:
            operation_name: Name of the operation for logging
            reraise: Whether to reraise exceptions
            return_value: Value to return if exception occurs
            log_success: Whether to log success message
        """
        self.operation_name = operation_name
        self.reraise = reraise
        self.return_value = return_value
        self.log_success = log_success
        self.success = False

    def __enter__(self):
        logger.debug(f"Starting {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.success = True
            if self.log_success:
                logger.info(f"Successfully completed {self.operation_name}")
            return True

        # Log the exception
        logger.error(f"Error in {self.operation_name}: {exc_val}")
        logger.debug(f"Traceback for {self.operation_name}: {traceback.format_exc()}")

        if self.reraise:
            return False  # Let exception propagate

        return True  # Suppress exception

    def get_result(self, success_value: Any = True) -> Any:
        """Get the result based on success/failure."""
        return success_value if self.success else self.return_value


def safe_file_operation(operation_name: str) -> Callable:
    """Decorator for safe file operations with consistent error handling.

    Args:
        operation_name: Descriptive name for the operation being performed

    Returns:
        Decorated function with error handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                logger.error(f"{operation_name} failed - file not found: {e}")
                return None
            except PermissionError as e:
                logger.error(f"{operation_name} failed - permission denied: {e}")
                return None
            except IOError as e:
                logger.error(f"{operation_name} failed - I/O error: {e}")
                return None
            except Exception as e:
                logger.error(f"{operation_name} failed with unexpected error: {e}")
                return None
        return wrapper
    return decorator


def safe_api_call(
    provider_name: str,
    max_retries: int = 3,
    backoff_factor: float = 2.0
) -> Callable:
    """Decorator for API calls with timeout and request exception handling.

    Args:
        provider_name: Name of the API provider
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier

    Returns:
        Decorated function with API error handling and retries
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.Timeout as e:
                    last_exception = e
                    wait_time = backoff_factor ** attempt
                    logger.warning(
                        f"{provider_name} API timeout (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                except requests.exceptions.ConnectionError as e:
                    last_exception = e
                    logger.error(f"{provider_name} API connection error: {e}")
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        time.sleep(wait_time)
                except requests.exceptions.RequestException as e:
                    logger.error(f"{provider_name} API request failed: {e}")
                    return None
                except Exception as e:
                    logger.error(f"{provider_name} API unexpected error: {e}")
                    return None

            logger.error(
                f"{provider_name} API failed after {max_retries} attempts: {last_exception}"
            )
            return None
        return wrapper
    return decorator


def retry_on_exception(
    exceptions: Union[Type[Exception], tuple],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0
) -> Callable:
    """Retry decorator for specific exceptions.

    Args:
        exceptions: Exception type(s) to retry on
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries
        backoff: Delay multiplier for each retry

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed for {func.__name__}: {e}"
                        )

            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def handle_and_convert(
    exception_type: Type[Exception],
    target_exception: Type[Exception],
    message_prefix: str = ""
) -> Callable:
    """Convert one exception type to another with optional message prefix.

    Args:
        exception_type: Exception type to catch
        target_exception: Exception type to raise instead
        message_prefix: Optional prefix for the new exception message

    Returns:
        Decorated function with exception conversion
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except exception_type as e:
                new_message = f"{message_prefix}{str(e)}" if message_prefix else str(e)
                raise target_exception(new_message) from e
        return wrapper
    return decorator