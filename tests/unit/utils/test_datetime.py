"""Comprehensive unit tests for datetime utilities."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import time

from fazztv.utils.datetime import (
    calculate_days_old, parse_date, format_date, get_time_ago,
    add_business_days, is_weekend, get_date_range
)
from datetime import date, datetime, timedelta


class TestDateTimeUtils:
    """Test suite for datetime utility functions."""
    
    def test_calculate_days_old(self):
        """Test calculating days old."""
        # Test with a date 10 days ago
        past_date = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
        days = calculate_days_old(past_date)
        assert days == 10
    
    def test_calculate_days_old_with_reference(self):
        """Test calculating days old with reference date."""
        ref_date = date(2024, 1, 15)
        days = calculate_days_old("2024-01-01", ref_date)
        assert days == 14
    
    def test_parse_date(self):
        """Test parsing date string."""
        result = parse_date("2024-01-01")
        assert isinstance(result, date)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
    
    def test_parse_date_invalid(self):
        """Test parsing invalid date string."""
        result = parse_date("invalid-date")
        assert result is None
    
    def test_format_date(self):
        """Test formatting date."""
        date_obj = date(2024, 1, 15)
        formatted = format_date(date_obj)
        assert "January 15 2024" == formatted
    
    def test_format_date_custom(self):
        """Test formatting date with custom format."""
        date_obj = date(2024, 1, 15)
        formatted = format_date(date_obj, "%Y-%m-%d")
        assert "2024-01-15" == formatted
    
    def test_get_time_ago(self):
        """Test getting time ago string."""
        past = date.today() - timedelta(days=5)
        result = get_time_ago(past)
        assert "5 days ago" in result
    
    def test_add_business_days(self):
        """Test adding business days."""
        # Start on Monday
        start = date(2024, 1, 1)  # Monday
        result = add_business_days(start, 5)
        # Should skip weekend, ending on next Monday
        assert result == date(2024, 1, 8)
    
    def test_is_weekend(self):
        """Test weekend check."""
        saturday = date(2024, 1, 6)
        sunday = date(2024, 1, 7)
        monday = date(2024, 1, 8)
        
        assert is_weekend(saturday) is True
        assert is_weekend(sunday) is True
        assert is_weekend(monday) is False
    
    def test_get_date_range(self):
        """Test getting date range."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)
        date_range = get_date_range(start, end)
        
        assert len(date_range) == 5
        assert date_range[0] == start
        assert date_range[-1] == end
