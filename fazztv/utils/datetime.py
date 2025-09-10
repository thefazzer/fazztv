"""Date and time utilities for FazzTV."""

import re
from datetime import datetime, date, timedelta
from typing import Optional


def calculate_days_old(date_str: str, reference_date: Optional[date] = None) -> int:
    """
    Calculate how many days old something is from a date string.
    
    Args:
        date_str: Date string to parse
        reference_date: Reference date to calculate from (default: today)
        
    Returns:
        Number of days between dates
    """
    if reference_date is None:
        reference_date = date.today()
    
    parsed_date = parse_date(date_str)
    if parsed_date:
        return (reference_date - parsed_date).days
    
    return 0


def parse_date(date_str: str) -> Optional[date]:
    """
    Parse various date formats from string.
    
    Args:
        date_str: Date string to parse
        
    Returns:
        Parsed date or None if parsing fails
    """
    if not date_str:
        return None
    
    # Common date formats to try
    formats = [
        "%B %d %Y",      # January 15 2024
        "%B %d, %Y",     # January 15, 2024
        "%d %B %Y",      # 15 January 2024
        "%Y-%m-%d",      # 2024-01-15
        "%m/%d/%Y",      # 01/15/2024
        "%d/%m/%Y",      # 15/01/2024
        "%Y/%m/%d",      # 2024/01/15
        "%b %d %Y",      # Jan 15 2024
        "%b %d, %Y",     # Jan 15, 2024
        "%d %b %Y",      # 15 Jan 2024
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    
    # Try extracting date from longer string
    # Pattern: Month Day Year
    pattern = r'([A-Za-z]+)\s+(\d{1,2})\s+(\d{4})'
    match = re.search(pattern, date_str)
    if match:
        try:
            month_str = match.group(1)
            day = int(match.group(2))
            year = int(match.group(3))
            
            # Try to parse month name
            for month_num in range(1, 13):
                month_date = date(2000, month_num, 1)
                if month_date.strftime('%B').lower().startswith(month_str.lower()) or \
                   month_date.strftime('%b').lower() == month_str.lower():
                    return date(year, month_num, day)
        except (ValueError, AttributeError):
            pass
    
    return None


def format_date(date_obj: date, format_str: str = "%B %d %Y") -> str:
    """
    Format date object to string.
    
    Args:
        date_obj: Date to format
        format_str: Format string
        
    Returns:
        Formatted date string
    """
    return date_obj.strftime(format_str)


def get_time_ago(past_date: date) -> str:
    """
    Get human-readable time ago string.
    
    Args:
        past_date: Date in the past
        
    Returns:
        Human-readable string (e.g., "5 days ago", "2 months ago")
    """
    today = date.today()
    delta = today - past_date
    
    if delta.days == 0:
        return "today"
    elif delta.days == 1:
        return "yesterday"
    elif delta.days < 7:
        return f"{delta.days} days ago"
    elif delta.days < 30:
        weeks = delta.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif delta.days < 365:
        months = delta.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = delta.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"


def add_business_days(start_date: date, days: int) -> date:
    """
    Add business days to a date (excluding weekends).
    
    Args:
        start_date: Starting date
        days: Number of business days to add
        
    Returns:
        Result date
    """
    current = start_date
    remaining = abs(days)
    delta = 1 if days > 0 else -1
    
    while remaining > 0:
        current += timedelta(days=delta)
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            remaining -= 1
    
    return current


def is_weekend(date_obj: date) -> bool:
    """
    Check if a date falls on a weekend.
    
    Args:
        date_obj: Date to check
        
    Returns:
        True if weekend, False otherwise
    """
    return date_obj.weekday() >= 5  # Saturday = 5, Sunday = 6


def get_date_range(start: date, end: date) -> list:
    """
    Get list of dates between start and end (inclusive).
    
    Args:
        start: Start date
        end: End date
        
    Returns:
        List of dates
    """
    if start > end:
        start, end = end, start
    
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    
    return dates