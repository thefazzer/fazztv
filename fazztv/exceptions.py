"""
Custom exceptions for FazzTV broadcasting system.
"""


class FazzTVException(Exception):
    """Base exception for all FazzTV errors."""
    pass


class ConfigurationError(FazzTVException):
    """Raised when there's a configuration problem."""
    pass


class MediaDownloadError(FazzTVException):
    """Raised when media download fails."""
    pass


class MediaSerializationError(FazzTVException):
    """Raised when media serialization fails."""
    pass


class BroadcastError(FazzTVException):
    """Raised when broadcasting fails."""
    pass


class APIError(FazzTVException):
    """Raised when API calls fail."""
    
    def __init__(self, message: str, api_name: str = None, status_code: int = None):
        """
        Initialize API error.
        
        Args:
            message: Error message
            api_name: Name of the API that failed
            status_code: HTTP status code if applicable
        """
        super().__init__(message)
        self.api_name = api_name
        self.status_code = status_code


class ValidationError(FazzTVException):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: str = None, value: any = None):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            value: Value that was invalid
        """
        super().__init__(message)
        self.field = field
        self.value = value


class CacheError(FazzTVException):
    """Raised when cache operations fail."""
    pass


class ProcessingError(FazzTVException):
    """Raised when media processing fails."""
    pass


class DataError(FazzTVException):
    """Raised when data operations fail."""
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


class DownloadError(FazzTVException):
    """Raised when media download fails."""
    pass