"""Common error handling utilities for FazzTV."""

import functools
import os
import traceback
from typing import Any, Callable, Optional, TypeVar, Union
from loguru import logger

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