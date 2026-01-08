"""
Unit tests for utils/text_utils.py
Tests shared text processing utilities
"""

import pytest
from datetime import date, datetime, timedelta
from utils.text_utils import normalize_text, parse_date, within_days


class TestNormalizeText:
    """Test normalize_text function"""
    
    def test_basic_normalization(self):
        """Test basic text normalization"""
        assert normalize_text("  HELLO  WORLD  ") == "hello world"
    
    def test_empty_string(self):
        """Test empty string handling"""
        assert normalize_text("") == ""
        assert normalize_text(None) == ""
    
    def test_multiple_spaces(self):
        """Test multiple space reduction"""
        assert normalize_text("  Multiple    Spaces   Here  ") == "multiple spaces here"
    
    def test_case_conversion(self):
        """Test case conversion to lowercase"""
        assert normalize_text("UPPER CASE") == "upper case"
        assert normalize_text("Mixed Case") == "mixed case"
    
    def test_special_characters(self):
        """Test special characters are preserved"""
        assert normalize_text("  Hello! @World#  ") == "hello! @world#"


class TestParseDate:
    """Test parse_date function"""
    
    def test_iso_format(self):
        """Test ISO date format"""
        result = parse_date("2025-01-15")
        assert result == date(2025, 1, 15)
    
    def test_slash_format(self):
        """Test slash-separated date format"""
        result = parse_date("2025/01/15")
        assert result == date(2025, 1, 15)
    
    def test_with_time(self):
        """Test date with time component"""
        result = parse_date("2025-01-15T10:30:00")
        assert result == date(2025, 1, 15)
    
    def test_month_name_format(self):
        """Test month name format"""
        result = parse_date("15 January 2025")
        assert result == date(2025, 1, 15)
    
    def test_short_month_name(self):
        """Test short month name format"""
        result = parse_date("15 Jan 2025")
        assert result == date(2025, 1, 15)
    
    def test_empty_string(self):
        """Test empty string handling"""
        assert parse_date("") is None
        assert parse_date(None) is None
    
    def test_invalid_format(self):
        """Test invalid date format"""
        assert parse_date("not a date") is None
    
    def test_tbc(self):
        """Test TBC (to be confirmed) handling"""
        assert parse_date("TBC") is None
        assert parse_date("tbc") is None


class TestWithinDays:
    """Test within_days function"""
    
    def test_within_range(self):
        """Test dates within specified range"""
        a = date(2025, 1, 15)
        b = date(2025, 1, 18)
        assert within_days(a, b, days=5) == True
    
    def test_exactly_at_limit(self):
        """Test dates exactly at limit"""
        a = date(2025, 1, 15)
        b = date(2025, 1, 20)
        assert within_days(a, b, days=5) == True
    
    def test_one_day_over(self):
        """Test dates one day over limit"""
        a = date(2025, 1, 15)
        b = date(2025, 1, 21)
        assert within_days(a, b, days=5) == False
    
    def test_far_apart(self):
        """Test dates far apart"""
        a = date(2025, 1, 15)
        b = date(2025, 2, 15)
        assert within_days(a, b, days=5) == False
    
    def test_none_values(self):
        """Test None value handling"""
        assert within_days(None, date(2025, 1, 15), days=5) == False
        assert within_days(date(2025, 1, 15), None, days=5) == False
        assert within_days(None, None, days=5) == False
    
    def test_same_day(self):
        """Test same day"""
        a = date(2025, 1, 15)
        b = date(2025, 1, 15)
        assert within_days(a, b, days=5) == True
    
    def test_zero_days(self):
        """Test zero days parameter"""
        a = date(2025, 1, 15)
        b = date(2025, 1, 15)
        assert within_days(a, b, days=0) == True
        
        b = date(2025, 1, 16)
        assert within_days(a, b, days=0) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
