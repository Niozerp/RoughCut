# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

#!/usr/bin/env python3
"""AI module for RoughCut.

Provides AI-powered tag generation and rough cut generation utilities.
"""

from .data_bundle import (
    DataBundle,
    DataBundleBuilder,
    FormatRules,
    MediaAssetMetadata,
    MediaIndexSubset,
    TranscriptData,
)
from .openai_client import OpenAIClient, TagResult
from .prompt_engine import PromptBuilder, PromptConfig
from .rough_cut_orchestrator import RoughCutOrchestrator
from .tagger import MediaTagger
from .tag_storage import TagStorage, TaggedAsset

__all__ = [
    # Data bundle
    'DataBundle',
    'DataBundleBuilder',
    'FormatRules',
    'MediaAssetMetadata',
    'MediaIndexSubset',
    'TranscriptData',
    # Client
    'OpenAIClient',
    'TagResult',
    # Prompt
    'PromptBuilder',
    'PromptConfig',
    # Orchestrator
    'RoughCutOrchestrator',
    # Tagging
    'MediaTagger',
    'TagStorage',
    'TaggedAsset'
]
