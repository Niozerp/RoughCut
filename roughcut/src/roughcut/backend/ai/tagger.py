# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

#!/usr/bin/env python3
"""Media tagger for AI-powered tag generation.

Provides MediaTagger class that coordinates AI tag generation
and tag normalization for media assets.
"""

from pathlib import Path
from typing import List

from .openai_client import OpenAIClient, TagResult
from ...utils.exceptions import AIError


class MediaTagger:
    """Generates AI-powered tags for media assets.
    
    Coordinates with OpenAIClient to generate tags from file metadata
    and normalizes the results for storage.
    
    Example:
        >>> client = OpenAIClient(api_key="sk-...")
        >>> tagger = MediaTagger(client)
        >>> result = await tagger.tag_media(
        ...     Path("/Music/Corporate/Upbeat/bright_corporate_theme.wav"),
        ...     "music"
        ... )
        >>> print(result.tags)
        ['corporate', 'upbeat', 'bright', 'theme', 'electronic']
    """
    
    def __init__(self, ai_client: OpenAIClient):
        """Initialize the media tagger.
        
        Args:
            ai_client: Configured OpenAI client instance
        """
        self.ai_client = ai_client
    
    async def tag_media(
        self,
        file_path: Path,
        category: str
    ) -> TagResult:
        """Generate tags for a media file.
        
        Analyzes the file path and name to generate relevant tags
        using the AI service.
        
        Args:
            file_path: Path to the media file
            category: Media category ("music", "sfx", "vfx")
            
        Returns:
            TagResult with cleaned and normalized tags
            
        Raises:
            AIError: If tag generation fails
            
        Example:
            Input: "/Music/Corporate/Upbeat/bright_corporate_theme.wav", "music"
            Output: TagResult(tags=["corporate", "upbeat", "bright", "theme", ...])
        """
        file_name = file_path.name
        folder_path = str(file_path.parent)
        
        # Call AI to generate tags
        result = await self.ai_client.generate_tags(
            file_name=file_name,
            folder_path=folder_path,
            category=category
        )
        
        # Clean and normalize tags
        cleaned_tags = self._clean_tags(result.tags)
        
        return TagResult(
            tags=cleaned_tags,
            confidence=result.confidence,
            raw_response=result.raw_response
        )
    
    def _clean_tags(self, tags: List[str]) -> List[str]:
        """Clean and normalize generated tags.
        
        Performs the following operations:
        - Strips whitespace
        - Converts to lowercase
        - Removes punctuation
        - Filters empty tags
        - Removes duplicates while preserving order
        
        Args:
            tags: Raw tags from AI
            
        Returns:
            Cleaned and normalized tags
        """
        cleaned = []
        seen = set()
        
        for tag in tags:
            # Split by common delimiters first (in case AI returns joined tags)
            subtags = tag.replace('?', ',').replace('!', ',').split(',')
            
            for subtag in subtags:
                # Remove extra whitespace and convert to lowercase
                subtag = subtag.strip().lower()
                
                # Remove common punctuation
                for char in '.,!?;:"()[]{}':
                    subtag = subtag.replace(char, '')
                
                # Skip empty tags (but keep single character tags if they're not empty)
                if not subtag:
                    continue
                
                # Skip duplicates (case-insensitive check)
                if subtag not in seen:
                    cleaned.append(subtag)
                    seen.add(subtag)
        
        return cleaned
    
    async def tag_batch(
        self,
        files: List[tuple[Path, str]],
        progress_callback = None
    ) -> dict[Path, TagResult]:
        """Tag multiple files with progress tracking.
        
        Args:
            files: List of (file_path, category) tuples
            progress_callback: Optional callback(current, total, file_name)
            
        Returns:
            Dictionary mapping file paths to tag results
        """
        import asyncio
        
        results = {}
        total = len(files)
        
        async def tag_single(index: int, file_path: Path, category: str):
            try:
                result = await self.tag_media(file_path, category)
                results[file_path] = result
                
                if progress_callback:
                    progress_callback(index + 1, total, file_path.name)
                    
            except AIError as e:
                # Log but continue with other files
                results[file_path] = TagResult(
                    tags=[],
                    confidence=0.0,
                    raw_response=f"Error: {e.message}"
                )
                if progress_callback:
                    progress_callback(index + 1, total, file_path.name)
        
        # Process all files
        await asyncio.gather(*[
            tag_single(i, path, cat)
            for i, (path, cat) in enumerate(files)
        ])
        
        return results
