"""Unit tests for custom exceptions."""

import pytest
from fazztv.models.exceptions import (
    FazzTVException,
    ConfigurationError,
    DownloadError,
    ProcessingError,
    BroadcastError,
    DataError,
    APIError,
    CacheError,
    ValidationError,
    MediaError,
    FileSystemError,
    NetworkError,
    AuthenticationError,
    RateLimitError,
    TimeoutError
)


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""
    
    def test_base_exception(self):
        """Test base FazzTVException."""
        exc = FazzTVException("Test error")
        assert str(exc) == "Test error"
        assert isinstance(exc, Exception)
    
    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from FazzTVException."""
        exceptions = [
            ConfigurationError,
            DownloadError,
            ProcessingError,
            BroadcastError,
            DataError,
            APIError,
            CacheError,
            ValidationError,
            MediaError,
            FileSystemError,
            NetworkError,
            AuthenticationError
        ]
        
        for exc_class in exceptions:
            exc = exc_class("Test")
            assert isinstance(exc, FazzTVException)
            assert isinstance(exc, Exception)
    
    def test_rate_limit_error_inheritance(self):
        """Test RateLimitError inherits from APIError."""
        exc = RateLimitError("Rate limit exceeded")
        assert isinstance(exc, APIError)
        assert isinstance(exc, FazzTVException)
        assert isinstance(exc, Exception)
    
    def test_timeout_error_inheritance(self):
        """Test TimeoutError inherits from NetworkError."""
        exc = TimeoutError("Operation timed out")
        assert isinstance(exc, NetworkError)
        assert isinstance(exc, FazzTVException)
        assert isinstance(exc, Exception)


class TestExceptionMessages:
    """Test exception message handling."""
    
    def test_exception_with_message(self):
        """Test exceptions with custom messages."""
        message = "Custom error message"
        
        exceptions = [
            FazzTVException(message),
            ConfigurationError(message),
            DownloadError(message),
            ProcessingError(message),
            BroadcastError(message),
            DataError(message),
            APIError(message),
            CacheError(message),
            ValidationError(message),
            MediaError(message),
            FileSystemError(message),
            NetworkError(message),
            AuthenticationError(message),
            RateLimitError(message),
            TimeoutError(message)
        ]
        
        for exc in exceptions:
            assert str(exc) == message
    
    def test_exception_without_message(self):
        """Test exceptions without messages."""
        exc = FazzTVException()
        assert str(exc) == ""
    
    def test_exception_with_multiple_args(self):
        """Test exceptions with multiple arguments."""
        exc = ValidationError("Field", "is invalid")
        # Python exceptions concatenate args with space
        assert "Field" in str(exc)


class TestExceptionRaising:
    """Test raising and catching exceptions."""
    
    def test_raise_base_exception(self):
        """Test raising base FazzTVException."""
        with pytest.raises(FazzTVException) as exc_info:
            raise FazzTVException("Base error")
        
        assert str(exc_info.value) == "Base error"
    
    def test_raise_configuration_error(self):
        """Test raising ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Missing API key")
        
        assert "Missing API key" in str(exc_info.value)
    
    def test_raise_download_error(self):
        """Test raising DownloadError."""
        with pytest.raises(DownloadError) as exc_info:
            raise DownloadError("Failed to download video")
        
        assert "Failed to download video" in str(exc_info.value)
    
    def test_raise_processing_error(self):
        """Test raising ProcessingError."""
        with pytest.raises(ProcessingError) as exc_info:
            raise ProcessingError("FFmpeg processing failed")
        
        assert "FFmpeg processing failed" in str(exc_info.value)
    
    def test_raise_broadcast_error(self):
        """Test raising BroadcastError."""
        with pytest.raises(BroadcastError) as exc_info:
            raise BroadcastError("RTMP connection failed")
        
        assert "RTMP connection failed" in str(exc_info.value)
    
    def test_raise_data_error(self):
        """Test raising DataError."""
        with pytest.raises(DataError) as exc_info:
            raise DataError("Database connection failed")
        
        assert "Database connection failed" in str(exc_info.value)
    
    def test_raise_api_error(self):
        """Test raising APIError."""
        with pytest.raises(APIError) as exc_info:
            raise APIError("YouTube API error")
        
        assert "YouTube API error" in str(exc_info.value)
    
    def test_raise_cache_error(self):
        """Test raising CacheError."""
        with pytest.raises(CacheError) as exc_info:
            raise CacheError("Cache write failed")
        
        assert "Cache write failed" in str(exc_info.value)
    
    def test_raise_validation_error(self):
        """Test raising ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Invalid input format")
        
        assert "Invalid input format" in str(exc_info.value)
    
    def test_raise_media_error(self):
        """Test raising MediaError."""
        with pytest.raises(MediaError) as exc_info:
            raise MediaError("Unsupported media format")
        
        assert "Unsupported media format" in str(exc_info.value)
    
    def test_raise_filesystem_error(self):
        """Test raising FileSystemError."""
        with pytest.raises(FileSystemError) as exc_info:
            raise FileSystemError("Permission denied")
        
        assert "Permission denied" in str(exc_info.value)
    
    def test_raise_network_error(self):
        """Test raising NetworkError."""
        with pytest.raises(NetworkError) as exc_info:
            raise NetworkError("Connection refused")
        
        assert "Connection refused" in str(exc_info.value)
    
    def test_raise_authentication_error(self):
        """Test raising AuthenticationError."""
        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("Invalid credentials")
        
        assert "Invalid credentials" in str(exc_info.value)
    
    def test_raise_rate_limit_error(self):
        """Test raising RateLimitError."""
        with pytest.raises(RateLimitError) as exc_info:
            raise RateLimitError("API rate limit exceeded")
        
        assert "API rate limit exceeded" in str(exc_info.value)
    
    def test_raise_timeout_error(self):
        """Test raising TimeoutError."""
        with pytest.raises(TimeoutError) as exc_info:
            raise TimeoutError("Request timed out after 30s")
        
        assert "Request timed out after 30s" in str(exc_info.value)


class TestExceptionCatching:
    """Test catching exceptions with proper hierarchy."""
    
    def test_catch_specific_exception(self):
        """Test catching specific exception type."""
        try:
            raise ValidationError("Test validation error")
        except ValidationError as e:
            assert "Test validation error" in str(e)
        except FazzTVException:
            pytest.fail("Should catch ValidationError specifically")
    
    def test_catch_base_exception(self):
        """Test catching base exception catches all derived."""
        exceptions_to_test = [
            ConfigurationError("config"),
            DownloadError("download"),
            ValidationError("validation")
        ]
        
        for exc in exceptions_to_test:
            try:
                raise exc
            except FazzTVException as e:
                assert str(e) in ["config", "download", "validation"]
            else:
                pytest.fail(f"Failed to catch {type(exc).__name__}")
    
    def test_catch_api_error_catches_rate_limit(self):
        """Test catching APIError also catches RateLimitError."""
        try:
            raise RateLimitError("Rate limited")
        except APIError as e:
            assert "Rate limited" in str(e)
        except Exception:
            pytest.fail("Should catch as APIError")
    
    def test_catch_network_error_catches_timeout(self):
        """Test catching NetworkError also catches TimeoutError."""
        try:
            raise TimeoutError("Timed out")
        except NetworkError as e:
            assert "Timed out" in str(e)
        except Exception:
            pytest.fail("Should catch as NetworkError")
    
    def test_exception_chaining(self):
        """Test exception chaining with cause."""
        original = ValueError("Original error")
        
        try:
            try:
                raise original
            except ValueError as e:
                raise ProcessingError("Processing failed") from e
        except ProcessingError as e:
            assert "Processing failed" in str(e)
            assert e.__cause__ is original


class TestExceptionUsagePatterns:
    """Test common usage patterns for exceptions."""
    
    def test_configuration_error_usage(self):
        """Test typical ConfigurationError usage."""
        def load_config():
            api_key = None
            if not api_key:
                raise ConfigurationError("API key not found in environment")
        
        with pytest.raises(ConfigurationError, match="API key not found"):
            load_config()
    
    def test_validation_error_usage(self):
        """Test typical ValidationError usage."""
        def validate_url(url):
            if not url.startswith(("http://", "https://")):
                raise ValidationError(f"Invalid URL scheme: {url}")
        
        with pytest.raises(ValidationError, match="Invalid URL scheme"):
            validate_url("ftp://example.com")
    
    def test_rate_limit_error_usage(self):
        """Test typical RateLimitError usage."""
        def api_call(retry_after=None):
            if retry_after:
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")
        
        with pytest.raises(RateLimitError, match="Retry after 60s"):
            api_call(retry_after=60)
    
    def test_timeout_error_usage(self):
        """Test typical TimeoutError usage."""
        def download_with_timeout(timeout=30):
            # Simulate timeout
            raise TimeoutError(f"Download timed out after {timeout} seconds")
        
        with pytest.raises(TimeoutError, match="timed out after 30 seconds"):
            download_with_timeout()
    
    def test_nested_exception_handling(self):
        """Test nested exception handling pattern."""
        def inner_function():
            raise ValidationError("Invalid data")
        
        def middle_function():
            try:
                inner_function()
            except ValidationError as e:
                raise ProcessingError("Cannot process invalid data") from e
        
        def outer_function():
            try:
                middle_function()
            except ProcessingError as e:
                raise BroadcastError("Cannot broadcast due to processing error") from e
        
        with pytest.raises(BroadcastError) as exc_info:
            outer_function()
        
        # Check the exception chain
        assert "Cannot broadcast" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ProcessingError)
        assert isinstance(exc_info.value.__cause__.__cause__, ValidationError)