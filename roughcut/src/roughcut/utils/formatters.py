"""Utility functions for formatting data for display.

Provides number formatting, asset count formatting, and other
display utilities used across the application.
"""

from typing import Dict


__all__ = ['format_number', 'format_asset_counts']


def format_number(n: int) -> str:
    """Format number with thousands separator.
    
    Args:
        n: Number to format (must be non-negative integer)
        
    Returns:
        Formatted string with commas
        
    Raises:
        TypeError: If n is not an integer
        ValueError: If n is negative
        
    Example:
        >>> format_number(12437)
        '12,437'
        >>> format_number(8291)
        '8,291'
        >>> format_number(1000000)
        '1,000,000'
    """
    if isinstance(n, bool):
        raise TypeError(f"Expected int, got bool")
    if not isinstance(n, int):
        raise TypeError(f"Expected int, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"Asset counts cannot be negative, got {n}")
    return f"{n:,}"


def format_asset_counts(music: int, sfx: int, vfx: int) -> Dict[str, str]:
    """Format all asset counts for display.
    
    Args:
        music: Number of music assets (must be non-negative int)
        sfx: Number of SFX assets (must be non-negative int)
        vfx: Number of VFX assets (must be non-negative int)
        
    Returns:
        Dictionary with formatted counts including total
        
    Raises:
        TypeError: If any count is not an integer
        ValueError: If any count is negative
        
    Example:
        >>> format_asset_counts(12437, 8291, 3102)
        {
            'music': '12,437',
            'sfx': '8,291', 
            'vfx': '3,102',
            'total': '23,830'
        }
    """
    # Validate all inputs are integers
    params = [('music', music), ('sfx', sfx), ('vfx', vfx)]
    for name, value in params:
        if not isinstance(value, int):
            raise TypeError(f"{name} must be int, got {type(value).__name__}")
        if value < 0:
            raise ValueError(f"{name} count cannot be negative, got {value}")
    
    # Check for potential overflow (defensive)
    total = music + sfx + vfx
    if total > 2_147_483_647:  # Max int32
        # Still format but could indicate data issue
        pass
    
    return {
        'music': format_number(music),
        'sfx': format_number(sfx),
        'vfx': format_number(vfx),
        'total': format_number(total)
    }
