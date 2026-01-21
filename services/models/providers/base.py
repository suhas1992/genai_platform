"""
Provider adapter base class.

Defines a unified interface for all model providers.
"""

from abc import ABC, abstractmethod
from typing import Iterator, List, Optional

from proto import models_pb2


class ModelProvider(ABC):
    """Abstract base class that all provider adapters implement."""

    @abstractmethod
    def chat(
        self,
        model: str,
        messages: List[models_pb2.ChatMessage],
        config: models_pb2.ChatConfig,
        tools: Optional[List[models_pb2.ToolDefinition]] = None,
        response_format: Optional[models_pb2.ResponseFormat] = None,
        system_prompt: Optional[str] = None,
    ) -> models_pb2.ChatResponse:
        """Generate a response synchronously."""
        raise NotImplementedError

    @abstractmethod
    def chat_stream(
        self,
        model: str,
        messages: List[models_pb2.ChatMessage],
        config: models_pb2.ChatConfig,
        tools: Optional[List[models_pb2.ToolDefinition]] = None,
        response_format: Optional[models_pb2.ResponseFormat] = None,
        system_prompt: Optional[str] = None,
    ) -> Iterator[models_pb2.ChatChunk]:
        """Generate a response with streaming tokens."""
        raise NotImplementedError

    @abstractmethod
    def get_supported_models(self) -> List[models_pb2.ModelInfo]:
        """
        Report which models this provider supports.
        
        Returns:
            List of ModelInfo, each containing model name, provider, and capabilities
        """
        raise NotImplementedError
