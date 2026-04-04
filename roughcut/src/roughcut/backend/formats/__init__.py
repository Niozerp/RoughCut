"""Format template management module.

Provides discovery, loading, and management of video format templates
stored as markdown files in templates/formats/.
"""

from .models import FormatTemplate, FormatTemplateCollection, TemplateSegment, AssetGroup
from .scanner import TemplateScanner, TemplateScannerError, MAX_FILE_SIZE, MAX_TEMPLATES
from .parser import TemplateParser, TemplateParserError
from .discovery import TemplateDiscovery, DiscoveredTemplate, DiscoveryError
from .cache import TemplateCache, CachedTemplate, get_template_cache, reset_template_cache
from .validator import TemplateValidator, ValidationError

__all__ = [
    "FormatTemplate",
    "FormatTemplateCollection",
    "TemplateSegment",
    "AssetGroup",
    "TemplateScanner",
    "TemplateScannerError",
    "TemplateParser",
    "TemplateParserError",
    "MAX_FILE_SIZE",
    "MAX_TEMPLATES",
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
]
