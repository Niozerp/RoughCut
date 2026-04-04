"""Format template management module.

Provides discovery, loading, and management of video format templates
stored as markdown files in templates/formats/.
"""

from .models import FormatTemplate, FormatTemplateCollection
from .scanner import TemplateScanner, TemplateScannerError, MAX_FILE_SIZE, MAX_TEMPLATES

__all__ = [
    "FormatTemplate",
    "FormatTemplateCollection",
    "TemplateScanner",
    "TemplateScannerError",
    "MAX_FILE_SIZE",
    "MAX_TEMPLATES",
]
