"""Unit tests for formatters utility module.

Tests number formatting and asset count formatting functions.
"""

import pytest
from roughcut.utils.formatters import format_number, format_asset_counts


class TestFormatNumber:
    """Test suite for format_number function."""
    
    def test_format_small_number(self):
        """Test formatting small numbers."""
        assert format_number(0) == "0"
        assert format_number(5) == "5"
        assert format_number(42) == "42"
        assert format_number(999) == "999"
    
    def test_format_thousands(self):
        """Test formatting numbers in thousands."""
        assert format_number(1000) == "1,000"
        assert format_number(1234) == "1,234"
        assert format_number(9999) == "9,999"
    
    def test_format_ten_thousands(self):
        """Test formatting numbers in ten thousands (AC #3 scenario)."""
        assert format_number(12437) == "12,437"
        assert format_number(8291) == "8,291"
        assert format_number(3102) == "3,102"
    
    def test_format_hundred_thousands(self):
        """Test formatting numbers in hundred thousands."""
        assert format_number(100000) == "100,000"
        assert format_number(123456) == "123,456"
        assert format_number(999999) == "999,999"
    
    def test_format_millions(self):
        """Test formatting numbers in millions."""
        assert format_number(1000000) == "1,000,000"
        assert format_number(1234567) == "1,234,567"
        assert format_number(12345678) == "12,345,678"
    
    def test_format_negative_numbers_raises_error(self):
        """Test that negative numbers raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            format_number(-1)
        with pytest.raises(ValueError, match="cannot be negative"):
            format_number(-1000)
        with pytest.raises(ValueError, match="cannot be negative"):
            format_number(-1234567)
    
    def test_format_non_integer_raises_type_error(self):
        """Test that non-integer types raise TypeError."""
        with pytest.raises(TypeError, match="Expected int, got float"):
            format_number(1234.56)
        with pytest.raises(TypeError, match="Expected int, got str"):
            format_number("1234")
        with pytest.raises(TypeError, match="Expected int, got NoneType"):
            format_number(None)
    
    def test_format_bool_raises_type_error(self):
        """Test that booleans raise TypeError (not integers)."""
        with pytest.raises(TypeError, match="Expected int, got bool"):
            format_number(True)
        with pytest.raises(TypeError, match="Expected int, got bool"):
            format_number(False)


class TestFormatAssetCounts:
    """Test suite for format_asset_counts function."""
    
    def test_format_all_zero(self):
        """Test formatting when all counts are zero."""
        result = format_asset_counts(0, 0, 0)
        
        assert result['music'] == "0"
        assert result['sfx'] == "0"
        assert result['vfx'] == "0"
        assert result['total'] == "0"
    
    def test_format_single_categories(self):
        """Test formatting with single category counts."""
        result = format_asset_counts(100, 0, 0)
        assert result['music'] == "100"
        assert result['sfx'] == "0"
        assert result['vfx'] == "0"
        assert result['total'] == "100"
        
        result = format_asset_counts(0, 50, 0)
        assert result['music'] == "0"
        assert result['sfx'] == "50"
        assert result['vfx'] == "0"
        assert result['total'] == "50"
        
        result = format_asset_counts(0, 0, 25)
        assert result['music'] == "0"
        assert result['sfx'] == "0"
        assert result['vfx'] == "25"
        assert result['total'] == "25"
    
    def test_format_mixed_categories(self):
        """Test formatting with mixed category counts."""
        result = format_asset_counts(12437, 8291, 3102)
        
        assert result['music'] == "12,437"
        assert result['sfx'] == "8,291"
        assert result['vfx'] == "3,102"
        assert result['total'] == "23,830"
    
    def test_format_large_numbers(self):
        """Test formatting with large numbers."""
        result = format_asset_counts(1000000, 500000, 250000)
        
        assert result['music'] == "1,000,000"
        assert result['sfx'] == "500,000"
        assert result['vfx'] == "250,000"
        assert result['total'] == "1,750,000"
    
    def test_result_structure(self):
        """Test that result has correct structure with all expected keys."""
        result = format_asset_counts(1, 2, 3)
        
        assert 'music' in result
        assert 'sfx' in result
        assert 'vfx' in result
        assert 'total' in result
        assert len(result) == 4
    
    def test_format_asset_counts_type_validation(self):
        """Test that format_asset_counts validates input types."""
        with pytest.raises(TypeError, match="music must be int"):
            format_asset_counts("100", 0, 0)
        with pytest.raises(TypeError, match="sfx must be int"):
            format_asset_counts(0, "50", 0)
        with pytest.raises(TypeError, match="vfx must be int"):
            format_asset_counts(0, 0, "25")
    
    def test_format_asset_counts_negative_validation(self):
        """Test that format_asset_counts validates non-negative counts."""
        with pytest.raises(ValueError, match="music count cannot be negative"):
            format_asset_counts(-1, 0, 0)
        with pytest.raises(ValueError, match="sfx count cannot be negative"):
            format_asset_counts(0, -50, 0)
        with pytest.raises(ValueError, match="vfx count cannot be negative"):
            format_asset_counts(0, 0, -25)
    
    def test_format_asset_counts_with_floats_raises_error(self):
        """Test that float inputs raise TypeError."""
        with pytest.raises(TypeError):
            format_asset_counts(10.5, 0, 0)
        with pytest.raises(TypeError):
            format_asset_counts(0, 20.5, 0)
        with pytest.raises(TypeError):
            format_asset_counts(0, 0, 30.5)
