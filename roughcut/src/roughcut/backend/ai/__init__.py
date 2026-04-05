# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

#!/usr/bin/env python3
"""AI module for RoughCut.

Provides AI-powered tag generation and rough cut generation utilities.
"""

from .chunk import (
    AssembledRoughCut,
    ChunkBoundary,
    ChunkConfig,
    ChunkContext,
    ChunkProgress,
    ChunkResult,
    TranscriptChunk,
)
from .chunker import ContextChunker, PROVIDER_TOKEN_LIMITS, estimate_token_count
from .asset_filter import AssetFilter
from .chunked_orchestrator import ChunkedOrchestrator, ChunkProgressTracker
from .data_bundle import (
    DataBundle,
    DataBundleBuilder,
    FormatRules,
    MediaAssetMetadata,
    MediaIndexSubset,
    TranscriptData,
)
from .document_models import (
    AssetSuggestion,
    AssetType,
    ConfidenceLevel,
    DocumentValidationResult,
    MusicSuggestion,
    RoughCutDocument,
    RoughCutSection,
    SFXSuggestion,
    TranscriptSegment,
    VFXSuggestion,
)
from .openai_client import OpenAIClient, TagResult
from .prompt_engine import PromptBuilder, PromptConfig
from .rough_cut_orchestrator import RoughCutOrchestrator
from .tagger import MediaTagger
from .tag_storage import TagStorage, TaggedAsset

__all__ = [
    # Chunk data structures
    'AssembledRoughCut',
    'ChunkBoundary',
    'ChunkConfig',
    'ChunkContext',
    'ChunkProgress',
    'ChunkResult',
    'TranscriptChunk',
    # Chunk processing
    'ContextChunker',
    'PROVIDER_TOKEN_LIMITS',
    'estimate_token_count',
    # Asset filtering
    'AssetFilter',
    # Chunked orchestration
    'ChunkedOrchestrator',
    'ChunkProgressTracker',
    # Data bundle
    'DataBundle',
    'DataBundleBuilder',
    'FormatRules',
    'MediaAssetMetadata',
    'MediaIndexSubset',
    'TranscriptData',
    # Document models
    'AssetSuggestion',
    'AssetType',
    'ConfidenceLevel',
    'DocumentValidationResult',
    'MusicSuggestion',
    'RoughCutDocument',
    'RoughCutSection',
    'SFXSuggestion',
    'TranscriptSegment',
    'VFXSuggestion',
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
