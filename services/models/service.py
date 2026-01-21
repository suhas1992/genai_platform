"""
Model Service - Business logic layer.

Architecture:
- Provider adapters auto-discover their models (OpenAI, Anthropic)
- ModelRegistry stores explicit registrations (custom + overrides)
- Resolution: Check registry first (overrides), then adapters (defaults)
"""

from __future__ import annotations

import os
from typing import Dict, Iterable, Optional

import grpc

from proto import models_pb2
from proto import models_pb2_grpc
from services.shared.servicer_base import BaseServicer
from services.models.store import ModelRegistry, PromptRegistry
from services.models.providers import ModelProvider, OpenAIProvider, AnthropicProvider


class ModelService(models_pb2_grpc.ModelServiceServicer, BaseServicer):
    """
    Model Service implementation.
    
    Resolution order:
    1. Check ModelRegistry for explicit registrations (custom models + overrides)
    2. Check provider adapters for auto-discovered models (built-in defaults)
    3. Return None if not found
    """

    def __init__(self):
        # Provider adapters (auto-discover models)
        self._providers: Dict[str, ModelProvider] = {}
        self._initialize_providers()
        
        # Explicit model registrations (custom + overrides)
        self._model_registry = ModelRegistry()
        
        # System prompts
        self._prompts = PromptRegistry()

    def add_to_server(self, server: grpc.Server):
        """Add this servicer to a gRPC server."""
        models_pb2_grpc.add_ModelServiceServicer_to_server(self, server)

    # ==================== Core Inference ====================

    def Chat(self, request: models_pb2.ChatRequest, context) -> models_pb2.ChatResponse:
        """Generate a response synchronously."""
        model_name = request.model or self._get_default_model()
        if not model_name:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("No model specified and no providers configured.")
            return models_pb2.ChatResponse()

        provider = self._resolve_provider(model_name)
        if provider is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"No provider found for model '{model_name}'.")
            return models_pb2.ChatResponse()

        system_prompt = self._resolve_system_prompt(request, context)
        if request.system_prompt_name and system_prompt is None:
            # Error already set by _resolve_system_prompt
            return models_pb2.ChatResponse()

        config = request.config if request.HasField("config") else self._default_config()
        tools = list(request.tools) if request.tools else None
        response_format = (
            request.response_format if request.HasField("response_format") else None
        )

        return provider.chat(
            model=model_name,
            messages=list(request.messages),
            config=config,
            tools=tools,
            response_format=response_format,
            system_prompt=system_prompt,
        )

    def ChatStream(
        self,
        request: models_pb2.ChatRequest,
        context,
    ) -> Iterable[models_pb2.ChatChunk]:
        """Generate a streaming response."""
        model_name = request.model or self._get_default_model()
        if not model_name:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("No model specified and no providers configured.")
            return

        provider = self._resolve_provider(model_name)
        if provider is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"No provider found for model '{model_name}'.")
            return

        system_prompt = self._resolve_system_prompt(request, context)
        if request.system_prompt_name and system_prompt is None:
            # Error already set by _resolve_system_prompt
            return

        config = request.config if request.HasField("config") else self._default_config()
        tools = list(request.tools) if request.tools else None
        response_format = (
            request.response_format if request.HasField("response_format") else None
        )

        yield from provider.chat_stream(
            model=model_name,
            messages=list(request.messages),
            config=config,
            tools=tools,
            response_format=response_format,
            system_prompt=system_prompt,
        )

    # ==================== Discovery ====================

    def ListModels(self, request, context) -> models_pb2.ListModelsResponse:
        """
        List available models.
        
        Returns:
        - Auto-discovered models from provider adapters
        - Explicitly registered models (custom + overrides)
        
        Note: Explicit registrations override auto-discovered models with same name
        """
        models_by_name = {}
        
        # First, get auto-discovered models from providers
        for provider in self._providers.values():
            for model_info in provider.get_supported_models():
                models_by_name[model_info.name] = model_info
        
        # Then add/override with explicit registrations
        for registered in self._model_registry.list_all():
            models_by_name[registered.name] = models_pb2.ModelInfo(
                name=registered.name,
                provider=registered.provider,
                capabilities=registered.capabilities,
            )
        
        return models_pb2.ListModelsResponse(models=list(models_by_name.values()))

    def GetModelCapabilities(
        self,
        request,
        context,
    ) -> models_pb2.ModelCapabilities:
        """Get capabilities for a specific model."""
        # Check explicit registrations first
        registered = self._model_registry.get(request.model)
        if registered:
            return registered.capabilities
        
        # Check auto-discovered models from providers
        for provider in self._providers.values():
            for model_info in provider.get_supported_models():
                if model_info.name == request.model:
                    return model_info.capabilities
        
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(f"Model '{request.model}' not found")
        return models_pb2.ModelCapabilities()

    # ==================== Prompt Management ====================

    def RegisterPrompt(
        self,
        request,
        context,
    ) -> models_pb2.RegisterPromptResponse:
        """Register a system prompt with versioning."""
        prompt = self._prompts.register(
            name=request.name,
            content=request.content,
            metadata=request.metadata if request.HasField("metadata") else None,
        )
        return models_pb2.RegisterPromptResponse(
            name=prompt.name,
            version=prompt.version,
            created_at=prompt.created_at,
        )

    def GetPrompt(self, request, context) -> models_pb2.Prompt:
        """Retrieve a prompt by name and optional version."""
        prompt = self._prompts.get(request.name, request.version)
        if prompt is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Prompt '{request.name}' not found")
            return models_pb2.Prompt()
        return prompt

    def ListPrompts(self, request, context) -> models_pb2.ListPromptsResponse:
        """List latest version of all prompts."""
        return models_pb2.ListPromptsResponse(prompts=self._prompts.list_latest())

    # ==================== Model Registry ====================

    def RegisterModel(
        self,
        request,
        context,
    ) -> models_pb2.RegisterModelResponse:
        """
        Register a model explicitly.
        
        Use cases:
        - Custom self-hosted models
        - Override built-in model endpoints (e.g., Azure OpenAI)
        """
        model = self._model_registry.register(
            name=request.name,
            endpoint=request.endpoint,
            capabilities=request.capabilities,
            health_check=request.health_check,
            adapter_type=request.adapter_type or "openai",
            provider=request.provider if request.provider else None,
        )
        return models_pb2.RegisterModelResponse(
            name=model.name,
            status=model.status,
            registered_at=model.registered_at,
        )

    def ListRegisteredModels(
        self,
        request,
        context,
    ) -> models_pb2.ListRegisteredModelsResponse:
        """List explicitly registered models."""
        return models_pb2.ListRegisteredModelsResponse(
            models=self._model_registry.list_all()
        )

    def GetModelStatus(self, request, context) -> models_pb2.ModelStatus:
        """Get status for a registered model."""
        model = self._model_registry.get(request.name)
        if model is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Model '{request.name}' not registered")
            return models_pb2.ModelStatus()
        
        return models_pb2.ModelStatus(
            name=model.name,
            status=model.status,
            last_checked=model.registered_at,  # TODO: Implement health checking
            endpoint=model.endpoint,
        )

    # ==================== Private Helpers ====================

    def _initialize_providers(self) -> None:
        """
        Initialize provider adapters from environment.
        
        Providers auto-discover their supported models.
        """
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self._providers["openai"] = OpenAIProvider(
                api_key=openai_key,
                base_url=os.getenv("OPENAI_BASE_URL"),
            )

        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            self._providers["anthropic"] = AnthropicProvider(api_key=anthropic_key)

    def _resolve_provider(self, model_name: str) -> Optional[ModelProvider]:
        """
        Find the provider adapter for a model.
        
        Resolution order:
        1. Check explicit registrations (custom + overrides)
        2. Check provider auto-discovered models (built-in defaults)
        
        Returns:
            Provider adapter or None if not found
        """
        # Check explicit registrations first (overrides + custom models)
        registered = self._model_registry.get(model_name)
        if registered:
            # For now, we only support inference through default providers
            # TODO: Support custom adapters for registered models
            adapter_type = registered.adapter_type
            if adapter_type in self._providers:
                return self._providers[adapter_type]
            return None
        
        # Check auto-discovered models from providers
        for provider in self._providers.values():
            for model_info in provider.get_supported_models():
                if model_info.name == model_name:
                    return provider
        
        return None

    def _resolve_system_prompt(
        self,
        request: models_pb2.ChatRequest,
        context,
    ) -> Optional[str]:
        """Resolve system prompt from registry if specified."""
        if not request.system_prompt_name:
            return None
        
        prompt = self._prompts.get(request.system_prompt_name)
        if prompt is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Prompt '{request.system_prompt_name}' not found")
            return None
        
        return prompt.content

    def _get_default_model(self) -> Optional[str]:
        """Get a default model if none specified."""
        if "openai" in self._providers:
            return "gpt-4o"
        if "anthropic" in self._providers:
            return "claude-sonnet-4-5"
        return None

    def _default_config(self) -> models_pb2.ChatConfig:
        """Default chat configuration."""
        return models_pb2.ChatConfig(
            temperature=0.7,
            max_tokens=512,
            top_p=1.0,
        )
