# /// script
# requires-python = ">=3.10"
# dependencies = ["openai"]
# ///

#!/usr/bin/env python3
"""OpenAI client wrapper with error handling and retries.

Provides OpenAIClient class for generating AI-powered tags
with timeout handling, rate limiting, and error recovery.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path

import openai

from ...utils.exceptions import AIError, AIRateLimitError

logger = logging.getLogger(__name__)


@dataclass
class TagResult:
    """Result of AI tag generation."""
    tags: List[str]
    confidence: float
    raw_response: str


class OpenAIClient:
    """Wrapper for OpenAI API with error handling and retries.
    
    Features:
    - 30-second timeout on API calls (per NFR3)
    - Exponential backoff for rate limiting
    - Structured error handling
    - Configurable model selection
    """
    
    DEFAULT_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_MODEL = "gpt-3.5-turbo"
    
    def __init__(
        self,
        api_key: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        model: str = DEFAULT_MODEL
    ):
        """Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key
            timeout: API call timeout in seconds
            max_retries: Maximum retry attempts for rate limits
            model: Model to use for tag generation
        """
        if not api_key or not api_key.strip():
            raise AIError(
                code="AI_CONFIG_ERROR",
                category="config",
                message="API key is required",
                recoverable=True,
                suggestion="Configure OpenAI API key in settings"
            )
        
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.timeout = timeout
        self.max_retries = max_retries
        self.model = model
    
    async def generate_tags(
        self,
        file_name: str,
        folder_path: str,
        category: str
    ) -> TagResult:
        """Generate AI tags for a media file.
        
        Args:
            file_name: Name of the file (e.g., "bright_corporate_theme.wav")
            folder_path: Full path to the file
            category: Media category ("music", "sfx", "vfx")
        
        Returns:
            TagResult with extracted tags
            
        Raises:
            AIError: If API call fails or times out
        """
        prompt = self._build_prompt(file_name, folder_path, category)
        
        try:
            response = await asyncio.wait_for(
                self._call_api_with_retry(prompt),
                timeout=self.timeout
            )
            
            tags = self._parse_tags(response)
            
            # Calculate confidence based on parsing success
            confidence = self._calculate_confidence(tags, response)
            
            return TagResult(
                tags=tags,
                confidence=confidence,
                raw_response=response
            )
            
        except asyncio.TimeoutError:
            raise AIError(
                code="AI_TIMEOUT",
                category="external_api",
                message=f"AI service timeout after {self.timeout}s",
                recoverable=True,
                suggestion="Check API credits or retry"
            )
        except AIError:
            raise
        except Exception as e:
            raise AIError(
                code="AI_ERROR",
                category="external_api",
                message=f"AI service error: {str(e)}",
                recoverable=True,
                suggestion="Check API key and network connection"
            )
    
    async def _call_api_with_retry(self, prompt: str) -> str:
        """Call OpenAI API with exponential backoff retry.
        
        Args:
            prompt: Prompt to send to the API
            
        Returns:
            API response text
            
        Raises:
            AIRateLimitError: If rate limit persists after retries
            AIError: For other API errors
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a media asset tagger."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=100
                )
                
                # Validate response has content
                if not response.choices or len(response.choices) == 0:
                    raise AIError(
                        code="AI_EMPTY_RESPONSE",
                        category="external_api",
                        message="API returned empty choices list",
                        recoverable=True,
                        suggestion="Retry the request"
                    )
                
                content = response.choices[0].message.content
                if content is None:
                    raise AIError(
                        code="AI_NO_CONTENT",
                        category="external_api",
                        message="API returned no content",
                        recoverable=True,
                        suggestion="Retry the request"
                    )
                
                return content
                
            except openai.RateLimitError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    raise AIRateLimitError(
                        message=f"Rate limit exceeded after {self.max_retries} retries",
                        retry_after=getattr(e, 'retry_after', None)
                    )
            except openai.AuthenticationError as e:
                raise AIError(
                    code="AI_AUTH_ERROR",
                    category="config",
                    message="Invalid API key",
                    recoverable=True,
                    suggestion="Verify your OpenAI API key in settings"
                )
            except openai.APIConnectionError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise AIError(
                        code="AI_CONNECTION_ERROR",
                        category="external_api",
                        message=f"Connection error: {str(e)}",
                        recoverable=True,
                        suggestion="Check network connection and retry"
                    )
            except openai.BadRequestError as e:
                raise AIError(
                    code="AI_BAD_REQUEST",
                    category="external_api",
                    message=f"Invalid request: {str(e)}",
                    recoverable=False,
                    suggestion="Check file metadata format"
                )
            except openai.InternalServerError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise AIError(
                        code="AI_SERVER_ERROR",
                        category="external_api",
                        message=f"OpenAI server error: {str(e)}",
                        recoverable=True,
                        suggestion="Retry after a short delay"
                    )
            except openai.APIError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise AIError(
                        code="AI_API_ERROR",
                        category="external_api",
                        message=f"API error: {str(e)}",
                        recoverable=True,
                        suggestion="Retry or check OpenAI status page"
                    )
        
        # Should never reach here if max_retries >= 1, but for type safety
        raise AIError(
            code="AI_RETRY_EXHAUSTED",
            category="external_api",
            message="All retry attempts exhausted",
            recoverable=True,
            suggestion="Retry after a short delay"
        )
    
    async def send_rough_cut_request(
        self,
        prompt_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send rough cut generation request to AI service.
        
        Sends transcript, format rules, and media index to AI for
        processing. Implements 30-second timeout per NFR3 with
        exponential backoff retry logic.
        
        Args:
            prompt_data: Complete prompt data from PromptBuilder
            
        Returns:
            Parsed JSON response from AI
            
        Raises:
            AIError: If API call fails, times out, or returns invalid JSON
        """
        import json
        
        logger.info("Sending rough cut generation request to AI")
        
        try:
            response = await asyncio.wait_for(
                self._call_rough_cut_api_with_retry(prompt_data),
                timeout=self.timeout
            )
            
            # Parse JSON response
            try:
                parsed_response = json.loads(response)
                return parsed_response
            except json.JSONDecodeError as e:
                raise AIError(
                    code="AI_INVALID_RESPONSE",
                    category="external_api",
                    message=f"AI returned invalid JSON: {str(e)}",
                    recoverable=True,
                    suggestion="Retry the request"
                )
            
        except asyncio.TimeoutError:
            raise AIError(
                code="AI_TIMEOUT",
                category="external_api",
                message=f"AI service timeout after {self.timeout}s",
                recoverable=True,
                suggestion="Check API credits or retry with shorter transcript"
            )
        except AIError:
            raise
        except Exception as e:
            raise AIError(
                code="AI_ERROR",
                category="external_api",
                message=f"AI service error: {str(e)}",
                recoverable=True,
                suggestion="Check API key and network connection"
            )
    
    async def _call_rough_cut_api_with_retry(self, prompt_data: Dict[str, Any]) -> str:
        """Call OpenAI API for rough cut with exponential backoff retry.
        
        Args:
            prompt_data: Complete prompt from PromptBuilder
            
        Returns:
            API response text (should be JSON)
            
        Raises:
            AIRateLimitError: If rate limit persists after retries
            AIError: For other API errors
        """
        # Guard against invalid retry configuration
        if self.max_retries < 1:
            raise AIError(
                code="AI_CONFIG_ERROR",
                category="config",
                message="max_retries must be >= 1",
                recoverable=True,
                suggestion="Configure valid retry count"
            )
        
        # Extract and validate prompt data with fallbacks
        model = prompt_data.get("model", self.DEFAULT_MODEL)
        messages = prompt_data.get("messages", [])
        temperature = prompt_data.get("temperature") if prompt_data.get("temperature") is not None else 0.3
        max_tokens = prompt_data.get("max_tokens") if prompt_data.get("max_tokens") is not None else 4000
        
        # Validate messages is not empty
        if not messages or not isinstance(messages, list):
            raise AIError(
                code="AI_INVALID_PROMPT",
                category="validation",
                message="Messages must be a non-empty list",
                recoverable=True,
                suggestion="Check prompt builder output"
            )
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Validate response has content
                if not response.choices or len(response.choices) == 0:
                    raise AIError(
                        code="AI_EMPTY_RESPONSE",
                        category="external_api",
                        message="API returned empty choices list",
                        recoverable=True,
                        suggestion="Retry the request"
                    )
                
                content = response.choices[0].message.content
                if content is None:
                    raise AIError(
                        code="AI_NO_CONTENT",
                        category="external_api",
                        message="API returned no content",
                        recoverable=True,
                        suggestion="Retry the request"
                    )
                
                return content
                
            except openai.RateLimitError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s for attempts 0, 1, 2
                    await asyncio.sleep(wait_time)
                else:
                    raise AIRateLimitError(
                        message=f"Rate limit exceeded after {self.max_retries} retries",
                        retry_after=getattr(e, 'retry_after', None)
                    )
            except openai.AuthenticationError as e:
                raise AIError(
                    code="AI_AUTH_ERROR",
                    category="config",
                    message="Invalid API key",
                    recoverable=True,
                    suggestion="Verify your OpenAI API key in settings"
                )
            except openai.APIConnectionError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise AIError(
                        code="AI_CONNECTION_ERROR",
                        category="external_api",
                        message=f"Connection error: {str(e)}",
                        recoverable=True,
                        suggestion="Check network connection and retry"
                    )
            except openai.BadRequestError as e:
                raise AIError(
                    code="AI_BAD_REQUEST",
                    category="external_api",
                    message=f"Invalid request: {str(e)}",
                    recoverable=False,
                    suggestion="Check prompt format and length"
                )
            except openai.InternalServerError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise AIError(
                        code="AI_SERVER_ERROR",
                        category="external_api",
                        message=f"OpenAI server error: {str(e)}",
                        recoverable=True,
                        suggestion="Retry after a short delay"
                    )
            except openai.APIError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise AIError(
                        code="AI_API_ERROR",
                        category="external_api",
                        message=f"API error: {str(e)}",
                        recoverable=True,
                        suggestion="Retry or check OpenAI status page"
                    )
        
        # Should never reach here if max_retries >= 1
        raise AIError(
            code="AI_RETRY_EXHAUSTED",
            category="external_api",
            message="All retry attempts exhausted",
            recoverable=True,
            suggestion="Retry after a short delay"
        )

    def _build_prompt(self, file_name: str, folder_path: str, category: str) -> str:
        """Build prompt for tag generation.
        
        Args:
            file_name: Name of the media file
            folder_path: Full path to the file
            category: Media category
            
        Returns:
            Formatted prompt string
        """
        return f"""Analyze this media file and generate relevant descriptive tags.

File Information:
- Filename: {file_name}
- Full Path: {folder_path}
- Category: {category}

Instructions:
1. Extract meaningful keywords from the filename
2. Consider the folder path structure as context
3. Generate 5-10 relevant tags
4. Tags should help categorize and search for this asset
5. Use lowercase, single words or short phrases
6. Avoid generic tags like "audio" or "file"

For music files, consider: genre, mood, tempo, instrumentation, style
For SFX files, consider: sound type, context, intensity, duration hint
For VFX files, consider: effect type, style, use case, visual style

Output format: Return ONLY a comma-separated list of tags.
Example: corporate, upbeat, bright, theme, electronic, background"""
    
    def _calculate_confidence(self, tags: List[str], raw_response: str) -> float:
        """Calculate confidence score based on parsing quality.
        
        Args:
            tags: Parsed tags
            raw_response: Raw API response
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not raw_response or not raw_response.strip():
            return 0.0
        
        if not tags:
            # Response received but no tags could be parsed
            return 0.3
        
        # Check if response was properly comma-separated
        expected_format = ',' in raw_response
        
        if expected_format and len(tags) >= 3:
            # Good parsing with multiple tags
            return 0.95
        elif expected_format and len(tags) >= 1:
            # Decent parsing but fewer tags
            return 0.8
        else:
            # Response received but format was unexpected
            return 0.6
    
    def _parse_tags(self, response: str) -> List[str]:
        """Parse comma-separated tags from AI response.
        
        Args:
            response: Raw API response text
            
        Returns:
            List of tag strings
        """
        if not response:
            return []
        
        # Split by comma and clean
        tags = []
        for tag in response.split(','):
            tag = tag.strip().lower()
            # Remove punctuation
            tag = tag.replace('.', '').replace('!', '').replace('?', '')
            if tag and len(tag) > 1:
                tags.append(tag)
        
        return tags
