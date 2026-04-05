"""Data bundle construction for AI rough cut generation.

Provides DataBundle dataclass and DataBundleBuilder for constructing
AI request payloads with transcript, format rules, and filtered media index.
Ensures only metadata (never actual media file contents) is included per NFR7.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)

# Constants for token estimation and limits
CHARS_PER_TOKEN = 4  # Rough estimate: 1 token ≈ 4 characters for English text
MAX_BUNDLE_TOKENS = 120000  # Conservative limit for GPT-4 (context window: 128k)
PATH_TRAVERSAL_PATTERNS = {"..", "~", "//", "\\"}  # Patterns indicating potential path traversal


@dataclass
class TranscriptData:
    """Transcript data for AI processing.
    
    Contains text and segment boundaries for preserving timing.
    """
    text: str
    segments: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "segments": self.segments
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptData":
        """Create from dictionary."""
        return cls(
            text=data.get("text", ""),
            segments=data.get("segments", [])
        )


@dataclass
class FormatRules:
    """Format template rules for AI processing.
    
    Contains structure, timing, and asset matching criteria.
    """
    slug: str
    name: str
    segments: List[Dict[str, Any]] = field(default_factory=list)
    asset_groups: List[Dict[str, Any]] = field(default_factory=list)
    rules: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "slug": self.slug,
            "name": self.name,
            "segments": self.segments,
            "asset_groups": self.asset_groups,
            "rules": self.rules
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FormatRules":
        """Create from dictionary."""
        return cls(
            slug=data.get("slug", ""),
            name=data.get("name", ""),
            segments=data.get("segments", []),
            asset_groups=data.get("asset_groups", []),
            rules=data.get("rules", {})
        )


@dataclass
class MediaAssetMetadata:
    """Media asset metadata - METADATA ONLY per NFR7.
    
    Contains file paths, tags, and categories - NEVER actual file contents.
    """
    path: str
    filename: str
    category: str  # "music", "sfx", "vfx"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "path": self.path,
            "filename": self.filename,
            "category": self.category,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaAssetMetadata":
        """Create from dictionary."""
        return cls(
            path=data.get("path", ""),
            filename=data.get("filename", ""),
            category=data.get("category", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class MediaIndexSubset:
    """Filtered media index subset for AI processing.
    
    Contains only relevant assets based on format requirements.
    """
    music: List[MediaAssetMetadata] = field(default_factory=list)
    sfx: List[MediaAssetMetadata] = field(default_factory=list)
    vfx: List[MediaAssetMetadata] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "music": [m.to_dict() for m in self.music],
            "sfx": [m.to_dict() for m in self.sfx],
            "vfx": [m.to_dict() for m in self.vfx]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaIndexSubset":
        """Create from dictionary."""
        return cls(
            music=[MediaAssetMetadata.from_dict(m) for m in data.get("music", [])],
            sfx=[MediaAssetMetadata.from_dict(m) for m in data.get("sfx", [])],
            vfx=[MediaAssetMetadata.from_dict(m) for m in data.get("vfx", [])]
        )
    
    def get_all_assets(self) -> List[MediaAssetMetadata]:
        """Get all assets across all categories."""
        return self.music + self.sfx + self.vfx
    
    def estimate_tokens(self) -> int:
        """Estimate token count for AI context window planning.
        
        Rough estimate: 1 token ≈ 4 characters for English text.
        
        Returns:
            Estimated token count
        """
        total_chars = 0
        for asset in self.get_all_assets():
            total_chars += len(asset.path) + len(asset.filename)
            for tag in asset.tags:
                total_chars += len(tag)
        
        # Rough token estimate using CHARS_PER_TOKEN constant
        return total_chars // CHARS_PER_TOKEN


@dataclass
class DataBundle:
    """Complete data bundle sent to AI service - METADATA ONLY per NFR7.
    
    Contains:
    - Transcript text and segments from Resolve
    - Format template rules for structure and timing
    - Filtered media index (paths, tags, categories only)
    
    EXCLUDES: Actual media file contents, binary data, file streams
    """
    session_id: str
    transcript: TranscriptData
    format_template: FormatRules
    media_index: MediaIndexSubset
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "transcript": self.transcript.to_dict(),
            "format_template": self.format_template.to_dict(),
            "media_index": self.media_index.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataBundle":
        """Create from dictionary."""
        return cls(
            session_id=data.get("session_id", ""),
            transcript=TranscriptData.from_dict(data.get("transcript", {})),
            format_template=FormatRules.from_dict(data.get("format_template", {})),
            media_index=MediaIndexSubset.from_dict(data.get("media_index", {}))
        )
    
    def validate_metadata_only(self, allowed_base_paths: Optional[Set[str]] = None) -> bool:
        """Validate that bundle contains only metadata, no binary data.
        
        This is a critical security check per NFR7.
        
        Args:
            allowed_base_paths: Optional set of allowed base directories for validation
            
        Returns:
            True if validation passes
            
        Raises:
            ValueError: If binary data, file contents, or path traversal is detected
        """
        # Check transcript (should be text only)
        if not isinstance(self.transcript.text, str):
            raise ValueError("Transcript must be text only, not binary data")
        
        # Check media index (should be metadata only)
        for asset in self.media_index.get_all_assets():
            # Validate paths are strings, not binary
            if not isinstance(asset.path, str):
                raise ValueError(f"Asset path must be string, not binary data")
            
            # Validate tags are strings
            for tag in asset.tags:
                if not isinstance(tag, str):
                    raise ValueError(f"Tags must be strings, not binary data")
            
            # Validate no path traversal patterns
            for pattern in PATH_TRAVERSAL_PATTERNS:
                if pattern in asset.path:
                    raise ValueError(
                        f"Path traversal detected in asset path: {asset.path}. "
                        f"Pattern '{pattern}' is not allowed."
                    )
            
            # Validate path is within allowed directories if specified
            if allowed_base_paths:
                path_obj = Path(asset.path).resolve()
                is_allowed = any(
                    str(path_obj).startswith(str(Path(base).resolve()))
                    for base in allowed_base_paths
                )
                if not is_allowed:
                    raise ValueError(
                        f"Asset path outside allowed directories: {asset.path}"
                    )
        
        return True
    
    def estimate_total_tokens(self) -> int:
        """Estimate total token count for the entire bundle.
        
        Returns:
            Estimated token count
        """
        # Transcript tokens
        transcript_tokens = len(self.transcript.text) // CHARS_PER_TOKEN
        
        # Format template tokens (rough estimate)
        format_json = str(self.format_template.to_dict())
        format_tokens = len(format_json) // CHARS_PER_TOKEN
        
        # Media index tokens
        media_tokens = self.media_index.estimate_tokens()
        
        return transcript_tokens + format_tokens + media_tokens


class DataBundleBuilder:
    """Builder for constructing AI data bundles.
    
    Constructs DataBundle instances from rough cut session data,
    filtering media index to relevant categories only.
    
    Example:
        builder = DataBundleBuilder()
        bundle = builder.build(
            session_id="session_123",
            transcript_data={"text": "...", "segments": [...]},
            format_template={"slug": "...", "rules": {...}},
            media_index=[...],
            format_asset_groups=["intro_music", "narrative_bed"]
        )
    """
    
    DEFAULT_MAX_MEDIA_ASSETS = 500  # Max assets per category to respect token limits
    
    def __init__(self, max_media_assets: int = DEFAULT_MAX_MEDIA_ASSETS):
        """Initialize the builder.
        
        Args:
            max_media_assets: Maximum assets per category (token limit awareness)
        """
        self.max_media_assets = max_media_assets
    
    def build(
        self,
        session_id: str,
        transcript_data: Dict[str, Any],
        format_template: Dict[str, Any],
        media_index: List[Dict[str, Any]],
        format_asset_groups: Optional[List[str]] = None
    ) -> DataBundle:
        """Build data bundle from session data.
        
        Args:
            session_id: Session identifier
            transcript_data: Transcription with text and segments
            format_template: Format template with rules and asset groups
            media_index: Full media index from SpacetimeDB
            format_asset_groups: Optional list of asset group names to filter by
            
        Returns:
            Constructed DataBundle
        """
        logger.info(f"Building data bundle for session {session_id}")
        
        # Build transcript data
        transcript = TranscriptData.from_dict(transcript_data)
        
        # Build format rules
        format_rules = FormatRules.from_dict(format_template)
        
        # Build filtered media index
        media_subset = self._build_media_subset(
            media_index,
            format_rules,
            format_asset_groups
        )
        
        # Create bundle
        bundle = DataBundle(
            session_id=session_id,
            transcript=transcript,
            format_template=format_rules,
            media_index=media_subset
        )
        
        # Validate metadata-only compliance
        bundle.validate_metadata_only()
        
        # Log bundle stats
        total_assets = len(media_subset.get_all_assets())
        estimated_tokens = bundle.estimate_total_tokens()
        logger.info(
            f"Data bundle built: {total_assets} assets, "
            f"~{estimated_tokens} estimated tokens"
        )
        
        # Warn if bundle exceeds token limits
        if estimated_tokens > MAX_BUNDLE_TOKENS:
            logger.warning(
                f"Data bundle may exceed AI token limits: "
                f"~{estimated_tokens} tokens (limit: {MAX_BUNDLE_TOKENS}). "
                f"Consider reducing media assets or transcript length."
            )
        
        return bundle
    
    def _build_media_subset(
        self,
        media_index: List[Dict[str, Any]],
        format_rules: FormatRules,
        format_asset_groups: Optional[List[str]] = None
    ) -> MediaIndexSubset:
        """Build filtered media index subset.
        
        Filters media index to relevant categories based on format template
        requirements. Respects token limits by limiting assets per category.
        
        Args:
            media_index: Full media index
            format_rules: Format rules for context
            format_asset_groups: Optional asset group names to prioritize
            
        Returns:
            Filtered MediaIndexSubset
        """
        # Get categories needed by format template
        required_categories = self._extract_required_categories(format_rules)
        
        # Categorize assets
        music_assets = []
        sfx_assets = []
        vfx_assets = []
        
        for asset_data in media_index:
            asset = MediaAssetMetadata.from_dict(asset_data)
            
            # Filter by required categories
            if asset.category == "music" and "music" in required_categories:
                music_assets.append(asset)
            elif asset.category == "sfx" and "sfx" in required_categories:
                sfx_assets.append(asset)
            elif asset.category == "vfx" and "vfx" in required_categories:
                vfx_assets.append(asset)
        
        # Sort by relevance if asset groups specified
        if format_asset_groups:
            music_assets = self._sort_by_relevance(music_assets, format_asset_groups)
            sfx_assets = self._sort_by_relevance(sfx_assets, format_asset_groups)
            vfx_assets = self._sort_by_relevance(vfx_assets, format_asset_groups)
        
        # Limit to respect token constraints
        music_assets = music_assets[:self.max_media_assets]
        sfx_assets = sfx_assets[:self.max_media_assets]
        vfx_assets = vfx_assets[:self.max_media_assets]
        
        logger.info(
            f"Media subset: {len(music_assets)} music, "
            f"{len(sfx_assets)} sfx, {len(vfx_assets)} vfx"
        )
        
        return MediaIndexSubset(
            music=music_assets,
            sfx=sfx_assets,
            vfx=vfx_assets
        )
    
    def _extract_required_categories(self, format_rules: FormatRules) -> set:
        """Extract required media categories from format rules.
        
        Args:
            format_rules: Format rules with asset groups
            
        Returns:
            Set of required category names ("music", "sfx", "vfx")
        """
        categories = set()
        
        for asset_group in format_rules.asset_groups:
            category = asset_group.get("category", "").lower()
            if category in ["music", "sfx", "vfx"]:
                categories.add(category)
        
        # If no specific categories found, include all
        if not categories:
            categories = {"music", "sfx", "vfx"}
        
        return categories
    
    def _sort_by_relevance(
        self,
        assets: List[MediaAssetMetadata],
        format_asset_groups: List[str]
    ) -> List[MediaAssetMetadata]:
        """Sort assets by relevance to format asset groups.
        
        Args:
            assets: List of media assets
            format_asset_groups: Asset group names from format template
            
        Returns:
            Sorted list of assets (most relevant first)
        """
        def relevance_score(asset: MediaAssetMetadata) -> int:
            """Calculate relevance score for an asset.
            
            Higher score = more relevant to format requirements.
            """
            score = 0
            asset_tags = set(t.lower() for t in asset.tags)
            
            for group_name in format_asset_groups:
                group_keywords = set(group_name.lower().split("_"))
                
                # Check for keyword matches in tags
                for keyword in group_keywords:
                    if any(keyword in tag for tag in asset_tags):
                        score += 1
            
            return score
        
        # Sort by relevance (descending), then by path for stability
        return sorted(assets, key=lambda a: (-relevance_score(a), a.path))
