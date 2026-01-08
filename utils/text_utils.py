"""
Shared text and date utility functions.

This module consolidates common utility functions used across
duplicate detection, validation, and other modules.
"""

import re
from datetime import date
from typing import Optional
from dateutil import parser as date_parser


def normalize_text(value: str) -> str:
    """
    Normalize text for comparison.
    
    Args:
        value: Text to normalize
        
    Returns:
        Normalized text (lowercase, stripped, single spaces)
    """
    value = (value or "").strip().lower()
    value = re.sub(r'\s+', ' ', value)
    return value


def parse_date(value: str) -> Optional[date]:
    """
    Parse date string to date object.
    
    Args:
        value: Date string to parse
        
    Returns:
        Date object or None if parsing fails
    """
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date_parser.parse(value).date()
    except:
        return None


def within_days(a: Optional[date], b: Optional[date], *, days: int) -> bool:
    """
    Check if two dates are within specified days of each other.
    
    Args:
        a: First date
        b: Second date
        days: Maximum days difference
        
    Returns:
        True if dates are within specified days, False otherwise
    """
    if a is None or b is None:
        return False
    delta = abs((a - b).days)
    return delta <= days
