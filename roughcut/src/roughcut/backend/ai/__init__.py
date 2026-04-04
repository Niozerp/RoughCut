# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

#!/usr/bin/env python3
"""AI module for RoughCut.

Provides AI-powered tag generation and related utilities.
"""

from .openai_client import OpenAIClient, TagResult
from .tagger import MediaTagger

__all__ = [
    'OpenAIClient',
    'TagResult',
    'MediaTagger'
]
