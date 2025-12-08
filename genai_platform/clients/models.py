"""
Model Service client.

Provides unified interface to AI model providers (OpenAI, Anthropic, etc.).
"""

from typing import Optional

from .base import BaseClient


class ModelClient(BaseClient):
    """
    Client for Model Service.
    
    Abstracts provider-specific APIs behind a unified interface.
    """
    
    def __init__(self, platform):
        super().__init__(platform, "models")
    
    def chat(
        self,
        model: str,
        query: str,
        system_prompt_name: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[str] = None,
        stream: bool = False
    ):
        """
        Generate chat response from model.
        
        Args:
            model: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet")
            query: User's query
            system_prompt_name: Optional registered system prompt
            session_id: Optional session ID for conversation context
            context: Optional additional context to include
            stream: Whether to stream response tokens
        
        Returns:
            Response from Model Service (implementation in Chapter 3)
        """
        # TODO: Implement in Chapter 3
        pass

