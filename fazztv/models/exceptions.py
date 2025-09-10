"""Custom exceptions for FazzTV."""


class FazzTVException(Exception):
    """Base exception for all FazzTV errors."""
    pass


class ConfigurationError(FazzTVException):
    """Raised when configuration is invalid or missing."""
    pass


class DownloadError(FazzTVException):
    """Raised when media download fails."""
    pass


class ProcessingError(FazzTVException):
    """Raised when media processing fails."""
    pass


class BroadcastError(FazzTVException):
    """Raised when broadcasting fails."""
    pass


class DataError(FazzTVException):
    """Raised when data operations fail."""
    pass


class APIError(FazzTVException):
    """Raised when external API calls fail."""
    pass


class CacheError(FazzTVException):
    """Raised when cache operations fail."""
    pass


class ValidationError(FazzTVException):
    """Raised when data validation fails."""
    pass


class MediaError(FazzTVException):
    """Raised for media-related errors."""
    pass


class FileSystemError(FazzTVException):
    """Raised for file system operations errors."""
    pass


class NetworkError(FazzTVException):
    """Raised for network-related errors."""
    pass


class AuthenticationError(FazzTVException):
    """Raised when authentication fails."""
    pass


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    pass


class TimeoutError(NetworkError):
    """Raised when operation times out."""
    pass