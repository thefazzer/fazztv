"""Comprehensive unit tests for logging utilities."""


from fazztv.utils.logging import (
    setup_logging, get_logger, log_exception, log_performance, LogContext, create_audit_logger
)


class TestLoggingUtils:
    """Test suite for logging utility functions."""
    
    def test_setup_logging(self, tmp_path):
        """Test setting up logging."""
        log_file = tmp_path / "logs" / "test.log"
        setup_logging(log_file=log_file, log_level="DEBUG")
        assert log_file.parent.exists()
    
    def test_get_logger(self):
        """Test getting logger."""
        test_logger = get_logger("test_module")
        assert test_logger is not None
        # Should be a bound logger with the name
        assert hasattr(test_logger, '_core')  # Loguru logger attribute
    
    def test_log_exception(self):
        """Test logging exception."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            # Should not raise
            log_exception(e, "test context")
    
    def test_log_performance(self):
        """Test performance logging."""
        # Log with duration under threshold (should not log)
        log_performance("fast_func", 0.5, threshold=1.0)
        
        # Log with duration over threshold (should log)
        log_performance("slow_func", 2.0, threshold=1.0)
    
    def test_log_context(self):
        """Test LogContext manager."""
        with LogContext("DEBUG"):
            # Context should set temporary log level
            pass
        # Context should be cleared after exiting
    
    def test_create_audit_logger(self, tmp_path):
        """Test creating audit logger."""
        audit_file = tmp_path / "audit.log"
        audit_logger = create_audit_logger(audit_file)
        
        # Logger should be created
        assert audit_logger is not None
        
        # Test logging to audit
        audit_logger.info("Audit message")
        
        # File should be created
        assert audit_file.exists()
