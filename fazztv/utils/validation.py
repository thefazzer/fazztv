"""Validation utilities for common patterns."""

from typing import Any, TypeVar, Optional, Callable

T = TypeVar('T')


def validate_not_none(value: Optional[T], error_message: str = "Value cannot be None") -> T:
    """
    Validate that a value is not None.

    Args:
        value: Value to validate
        error_message: Error message if validation fails

    Returns:
        The value if not None

    Raises:
        ValueError: If value is None
    """
    if value is None:
        raise ValueError(error_message)
    return value


def validate_not_empty(value: str, error_message: str = "Value cannot be empty") -> str:
    """
    Validate that a string value is not empty.

    Args:
        value: String value to validate
        error_message: Error message if validation fails

    Returns:
        The value if not empty

    Raises:
        ValueError: If value is empty or None
    """
    if not value or not value.strip():
        raise ValueError(error_message)
    return value


def validate_positive(value: float, error_message: str = "Value must be positive") -> float:
    """
    Validate that a numeric value is positive.

    Args:
        value: Numeric value to validate
        error_message: Error message if validation fails

    Returns:
        The value if positive

    Raises:
        ValueError: If value is not positive
    """
    if value <= 0:
        raise ValueError(error_message)
    return value


def validate_in_range(value: float, min_val: float, max_val: float,
                     error_message: Optional[str] = None) -> float:
    """
    Validate that a numeric value is within a range.

    Args:
        value: Numeric value to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        error_message: Custom error message if validation fails

    Returns:
        The value if within range

    Raises:
        ValueError: If value is outside the range
    """
    if not min_val <= value <= max_val:
        msg = error_message or f"Value must be between {min_val} and {max_val}"
        raise ValueError(msg)
    return value


def validate_file_extension(filename: str, allowed_extensions: list[str],
                           error_message: Optional[str] = None) -> str:
    """
    Validate that a filename has an allowed extension.

    Args:
        filename: Filename to validate
        allowed_extensions: List of allowed extensions (with dots, e.g., ['.mp4', '.avi'])
        error_message: Custom error message if validation fails

    Returns:
        The filename if valid

    Raises:
        ValueError: If filename doesn't have an allowed extension
    """
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        msg = error_message or f"File must have one of these extensions: {allowed_extensions}"
        raise ValueError(msg)
    return filename


def guard_clause(condition: bool, return_value: T,
                log_message: Optional[str] = None,
                logger: Optional[Callable] = None) -> Optional[T]:
    """
    Helper for guard clause pattern.

    Args:
        condition: Condition to check
        return_value: Value to return if condition is True
        log_message: Optional message to log
        logger: Optional logger function

    Returns:
        return_value if condition is True, None otherwise
    """
    if condition:
        if log_message and logger:
            logger(log_message)
        return return_value
    return None


def validate_with_predicate(value: T, predicate: Callable[[T], bool],
                           error_message: str = "Validation failed") -> T:
    """
    Validate using a custom predicate function.

    Args:
        value: Value to validate
        predicate: Function that returns True if valid
        error_message: Error message if validation fails

    Returns:
        The value if valid

    Raises:
        ValueError: If predicate returns False
    """
    if not predicate(value):
        raise ValueError(error_message)
    return value