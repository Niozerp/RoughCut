"""Format template management module.

Provides discovery, loading, and management of video format templates
stored as markdown files in templates/formats/.
"""

from .models import FormatTemplate, FormatTemplateCollection
from .scanner import TemplateScanner, TemplateScannerError

__all__ = [
    "FormatTemplate",
    "FormatTemplateCollection",
    "TemplateScanner",
    "TemplateScannerError",
]
