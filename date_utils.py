"""
Date utility functions for handling various date formats including Excel serial dates
"""
from datetime import datetime, timedelta
from typing import Optional, Union
import re


def excel_serial_to_date(serial: Union[int, float]) -> Optional[datetime]:
    """
    Convert Excel serial date to Python datetime.
    Excel stores dates as numbers (days since 1900-01-01).
    
    Args:
        serial: Excel serial date number
        
    Returns:
        datetime object or None if invalid
    """
    try:
        # Excel's epoch starts at 1900-01-01, but has a bug counting 1900 as a leap year
        # We use 1899-12-30 as the base to account for this
        excel_epoch = datetime(1899, 12, 30)
        days = int(serial)
        
        # Handle fractional days (time component)
        fraction = serial - days
        seconds = int(fraction * 86400)  # 86400 seconds in a day
        
        result = excel_epoch + timedelta(days=days, seconds=seconds)
        return result
    except (ValueError, TypeError, OverflowError):
        return None


def parse_date(date_value: Union[str, int, float, datetime, None]) -> Optional[str]:
    """
    Parse various date formats and return ISO format string (YYYY-MM-DD).
    Handles:
    - ISO strings (2024-01-15, 2024-01-15T10:30:00)
    - Excel serial dates (45372.22928240741)
    - Timestamps
    - datetime objects
    
    Args:
        date_value: Date in various formats
        
    Returns:
        ISO format date string (YYYY-MM-DD) or None if invalid
    """
    if not date_value:
        return None
    
    try:
        # Handle datetime objects
        if isinstance(date_value, datetime):
            return date_value.strftime('%Y-%m-%d')
        
        # Handle numeric values (Excel serial dates or timestamps)
        if isinstance(date_value, (int, float)):
            # Check if it's an Excel serial date (typically < 100000)
            if date_value < 100000:
                dt = excel_serial_to_date(date_value)
                if dt:
                    return dt.strftime('%Y-%m-%d')
            else:
                # Treat as Unix timestamp (milliseconds)
                dt = datetime.fromtimestamp(date_value / 1000 if date_value > 10000000000 else date_value)
                return dt.strftime('%Y-%m-%d')
        
        # Handle string values
        if isinstance(date_value, str):
            date_str = date_value.strip()
            
            if not date_str:
                return None
            
            # Try to parse as ISO format
            if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
                # Already in ISO format, validate it
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00').split('T')[0])
                return dt.strftime('%Y-%m-%d')
            
            # Try common date formats
            date_formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S',
            ]
            
            for fmt in date_formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # Try parsing with dateutil if available
            try:
                from dateutil import parser
                dt = parser.parse(date_str)
                return dt.strftime('%Y-%m-%d')
            except (ImportError, ValueError):
                pass
        
        return None
        
    except (ValueError, TypeError, OverflowError) as e:
        print(f"Warning: Failed to parse date '{date_value}': {e}")
        return None


def format_date_for_display(date_value: Union[str, int, float, datetime, None]) -> str:
    """
    Format date for human-readable display.
    
    Args:
        date_value: Date in various formats
        
    Returns:
        Formatted date string (e.g., "Jan 15, 2024") or "Not set"
    """
    iso_date = parse_date(date_value)
    if not iso_date:
        return "Not set"
    
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime('%b %d, %Y')
    except ValueError:
        return "Not set"


def validate_date_string(date_str: Optional[str]) -> bool:
    """
    Validate if a string is a valid date.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if valid, False otherwise
    """
    return parse_date(date_str) is not None


def days_until_date(date_value: Union[str, int, float, datetime, None], 
                   from_date: Optional[datetime] = None) -> Optional[int]:
    """
    Calculate days until a given date.
    
    Args:
        date_value: Target date in various formats
        from_date: Starting date (defaults to now)
        
    Returns:
        Number of days (negative if past) or None if invalid
    """
    iso_date = parse_date(date_value)
    if not iso_date:
        return None
    
    try:
        target = datetime.fromisoformat(iso_date)
        start = from_date or datetime.now()
        
        # Remove time component for day calculation
        target = target.replace(hour=0, minute=0, second=0, microsecond=0)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        delta = target - start
        return delta.days
    except ValueError:
        return None
