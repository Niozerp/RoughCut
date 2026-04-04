"""Format template management module.

Provides discovery, loading, and management of video format templates
stored as markdown files in templates/formats/.
"""

from .models import (
    FormatTemplate, FormatTemplateCollection, TemplateSegment, AssetGroup,
    FormatRule, RuleType, TimingConstraint, SegmentStructure, TransitionRule,
    MediaMatchingCriteria, MatchingCriteriaType, MatchingRule
)
from .scanner import TemplateScanner, TemplateScannerError, MAX_FILE_SIZE, MAX_TEMPLATES
from .parser import TemplateParser, TemplateParserError, FormatRuleParseError
from .discovery import TemplateDiscovery, DiscoveredTemplate, DiscoveryError
from .cache import TemplateCache, CachedTemplate, get_template_cache, reset_template_cache
from .validator import TemplateValidator, ValidationError, FormatRuleValidator
from .prompt_formatter import FormatRulePromptFormatter

__all__ = [
    # Core models
    "FormatTemplate",
    "FormatTemplateCollection",
    "TemplateSegment",
    "AssetGroup",
    # Story 3.4 additions
    "TemplateDiscovery",
    "DiscoveredTemplate",
    "DiscoveryError",
    "TemplateCache",
    "CachedTemplate",
    "get_template_cache",
    "reset_template_cache",
    "TemplateValidator",
    "ValidationError",
    # Story 3.6 additions - Format Rules
    "FormatRule",
    "RuleType",
    "TimingConstraint",
    "SegmentStructure",
    "TransitionRule",
    "FormatRuleParseError",
    "FormatRuleValidator",
    # Story 3.6 additions - Media Matching
    "MediaMatchingCriteria",
    "MatchingCriteriaType",
    "MatchingRule",
    # Story 3.6 additions - Prompt Formatter
    "FormatRulePromptFormatter",
    # Core utilities
    "TemplateScanner",
    "TemplateScannerError",
    "TemplateParser",
    "TemplateParserError",
    "MAX_FILE_SIZE",
    "MAX_TEMPLATES",
]
