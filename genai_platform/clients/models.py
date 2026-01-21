"""
Model Service client.

Exposes gRPC methods using Protocol Buffer request/response types directly.
"""

from typing import Iterator, Optional

from proto import models_pb2
from proto import models_pb2_grpc

from .base import BaseClient


class ModelClient(BaseClient):
    """
    Client for Model Service.

    Uses proto messages directly for all requests and responses.
    """

    def __init__(self, platform):
        super().__init__(platform, "models")
        self._stub = models_pb2_grpc.ModelServiceStub(self._channel)

    def chat(self, request: models_pb2.ChatRequest) -> models_pb2.ChatResponse:
        """Generate a chat response from a model."""
        return self._stub.Chat(request, metadata=self.metadata)

    def chat_stream(
        self,
        request: models_pb2.ChatRequest,
    ) -> Iterator[models_pb2.ChatChunk]:
        """Stream a chat response from a model."""
        return self._stub.ChatStream(request, metadata=self.metadata)

    def list_models(
        self,
        request: Optional[models_pb2.ListModelsRequest] = None,
    ) -> models_pb2.ListModelsResponse:
        """List available models and capabilities."""
        return self._stub.ListModels(
            request or models_pb2.ListModelsRequest(),
            metadata=self.metadata,
        )

    def get_model_capabilities(
        self,
        request: models_pb2.GetCapabilitiesRequest,
    ) -> models_pb2.ModelCapabilities:
        """Get capabilities for a specific model."""
        return self._stub.GetModelCapabilities(request, metadata=self.metadata)

    def register_prompt(
        self,
        request: models_pb2.RegisterPromptRequest,
    ) -> models_pb2.RegisterPromptResponse:
        """Register a system prompt with versioning."""
        return self._stub.RegisterPrompt(request, metadata=self.metadata)

    def get_prompt(
        self,
        request: models_pb2.GetPromptRequest,
    ) -> models_pb2.Prompt:
        """Retrieve a prompt by name and version."""
        return self._stub.GetPrompt(request, metadata=self.metadata)

    def list_prompts(
        self,
        request: Optional[models_pb2.ListPromptsRequest] = None,
    ) -> models_pb2.ListPromptsResponse:
        """List prompts (latest version per prompt)."""
        return self._stub.ListPrompts(
            request or models_pb2.ListPromptsRequest(),
            metadata=self.metadata,
        )

    def register_model(
        self,
        request: models_pb2.RegisterModelRequest,
    ) -> models_pb2.RegisterModelResponse:
        """Register a custom model endpoint."""
        return self._stub.RegisterModel(request, metadata=self.metadata)

    def list_registered_models(
        self,
        request: Optional[models_pb2.ListRegisteredModelsRequest] = None,
    ) -> models_pb2.ListRegisteredModelsResponse:
        """List registered custom models."""
        return self._stub.ListRegisteredModels(
            request or models_pb2.ListRegisteredModelsRequest(),
            metadata=self.metadata,
        )

    def get_model_status(
        self,
        request: models_pb2.GetModelStatusRequest,
    ) -> models_pb2.ModelStatus:
        """Get status for a registered model."""
        return self._stub.GetModelStatus(request, metadata=self.metadata)

