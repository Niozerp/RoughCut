"""Notion API integration module.

Provides Notion API client for media database synchronization.
"""

from .client import NotionClient, is_notion_available

__all__ = ['NotionClient', 'is_notion_available']
