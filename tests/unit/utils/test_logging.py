"""Comprehensive unit tests for logging utilities."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import logging
from pathlib import Path

from fazztv.utils.logging import (
    setup_logging, get_logger, log_exception, log_performance, LogContext, create_audit_logger
)
from loguru import logger


class TestLoggingUtils:
    """Test suite for logging utility functions."""
    
    def test_setup_logging(self, tmp_path):
        """Test setting up logging."""
        log_dir = tmp_path / "logs"
        setup_logging(log_dir=log_dir, level="DEBUG")
        assert log_dir.exists()
    
    def test_get_logger(self):
        """Test getting logger."""
        test_logger = get_logger("test_module")
        assert test_logger is not None
        # Loguru logger is a singleton
        assert test_logger == logger
    
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
        with LogContext("test_operation", {"user": "test"}):
            # Context should be set
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
