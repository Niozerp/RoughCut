"""Format template management module.

Provides discovery, loading, and management of video format templates
stored as markdown files in templates/formats/.
"""

from .models import FormatTemplate, FormatTemplateCollection, TemplateSegment, AssetGroup
from .scanner import TemplateScanner, TemplateScannerError, MAX_FILE_SIZE, MAX_TEMPLATES
from .parser import TemplateParser, TemplateParserError

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
]
