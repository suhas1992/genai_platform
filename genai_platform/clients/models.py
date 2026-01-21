"""
Model Service client.

Provides clean Python API - pb2 objects are internal implementation only.
"""

from typing import Iterator, Optional, List, Dict, Any

from proto import models_pb2
from proto import models_pb2_grpc

from .base import BaseClient


class ModelClient(BaseClient):
    """
    Client for Model Service.
    
    All methods accept clean Python types (dicts, strings, etc.)
    Protocol Buffers are internal implementation details.
    """

    def __init__(self, platform):
        super().__init__(platform, "models")
        self._stub = models_pb2_grpc.ModelServiceStub(self._channel)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a chat response.
        
        Args:
            model: Model name (e.g., "gpt-4o", "claude-sonnet-4-5")
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict with 'text', 'model', 'usage', etc.
            
        Example:
            response = platform.models.chat(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello!"}]
            )
            print(response['text'])
        """
        # Build pb2 request internally
        pb_messages = [
            models_pb2.ChatMessage(role=msg["role"], content=msg["content"])
            for msg in messages
        ]
        
        config = models_pb2.ChatConfig(temperature=temperature)
        if max_tokens:
            config.max_tokens = max_tokens
        
        request = models_pb2.ChatRequest(
            model=model,
            messages=pb_messages,
            config=config
        )
        
        # Call service
        response = self._stub.Chat(request, metadata=self.metadata)
        
        # Return clean dict
        return {
            'text': response.text,
            'model': response.model,
            'provider': response.provider,
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            } if response.HasField('usage') else None,
            'finish_reason': response.finish_reason
        }

    def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        Stream a chat response token by token.
        
        Args:
            model: Model name
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            
        Yields:
            String tokens as they're generated
            
        Example:
            for token in platform.models.chat_stream(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}]
            ):
                print(token, end="", flush=True)
        """
        # Build pb2 request internally
        pb_messages = [
            models_pb2.ChatMessage(role=msg["role"], content=msg["content"])
            for msg in messages
        ]
        
        config = models_pb2.ChatConfig(temperature=temperature)
        if max_tokens:
            config.max_tokens = max_tokens
        
        request = models_pb2.ChatRequest(
            model=model,
            messages=pb_messages,
            config=config
        )
        
        # Stream tokens
        for chunk in self._stub.ChatStream(request, metadata=self.metadata):
            if chunk.token:
                yield chunk.token

    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models and capabilities.
        
        Returns:
            List of model dicts with name, provider, capabilities
            
        Example:
            models = platform.models.list_models()
            for model in models:
                print(f"{model['name']} ({model['provider']})")
        """
        response = self._stub.ListModels(
            models_pb2.ListModelsRequest(),
            metadata=self.metadata
        )
        
        return [
            {
                'name': model.name,
                'provider': model.provider,
                'capabilities': {
                    'context_window': model.capabilities.context_window,
                    'supports_vision': model.capabilities.supports_vision,
                    'supports_tools': model.capabilities.supports_tools
                }
            }
            for model in response.models
        ]
    
    def get_model_capabilities(self, model: str) -> Dict[str, Any]:
        """
        Get capabilities for a specific model.
        
        Args:
            model: Model name
            
        Returns:
            Dict with context_window, supports_vision, supports_tools
        """
        request = models_pb2.GetCapabilitiesRequest(model=model)
        caps = self._stub.GetModelCapabilities(request, metadata=self.metadata)
        
        return {
            'context_window': caps.context_window,
            'supports_vision': caps.supports_vision,
            'supports_tools': caps.supports_tools
        }
    
    def register_prompt(
        self,
        name: str,
        content: str,
        author: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Register a system prompt with versioning.
        
        Args:
            name: Prompt name
            content: Prompt text
            author: Optional author name
            tags: Optional tags
            
        Returns:
            Dict with name, version, created_at
        """
        metadata_pb = models_pb2.PromptMetadata(
            author=author or "",
            tags=tags or []
        )
        
        request = models_pb2.RegisterPromptRequest(
            name=name,
            content=content,
            metadata=metadata_pb
        )
        
        response = self._stub.RegisterPrompt(request, metadata=self.metadata)
        
        return {
            'name': response.name,
            'version': response.version,
            'created_at': response.created_at
        }
    
    def get_prompt(self, name: str, version: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve a prompt by name and version.
        
        Args:
            name: Prompt name
            version: Optional version (latest if not provided)
            
        Returns:
            Dict with name, version, content, metadata
        """
        request = models_pb2.GetPromptRequest(
            name=name,
            version=version or 0
        )
        
        prompt = self._stub.GetPrompt(request, metadata=self.metadata)
        
        return {
            'name': prompt.name,
            'version': prompt.version,
            'content': prompt.content,
            'metadata': {
                'author': prompt.metadata.author,
                'tags': list(prompt.metadata.tags)
            },
            'created_at': prompt.created_at
        }
    
    def list_prompts(self) -> List[Dict[str, Any]]:
        """
        List all prompts (latest version per prompt).
        
        Returns:
            List of prompt dicts
        """
        response = self._stub.ListPrompts(
            models_pb2.ListPromptsRequest(),
            metadata=self.metadata
        )
        
        return [
            {
                'name': prompt.name,
                'version': prompt.version,
                'content': prompt.content,
                'created_at': prompt.created_at
            }
            for prompt in response.prompts
        ]
    
    def register_model(
        self,
        name: str,
        endpoint: str,
        adapter_type: str,
        context_window: int = 8192,
        supports_vision: bool = False,
        supports_tools: bool = True,
        provider: Optional[str] = None,
        health_check: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a custom model endpoint.
        
        Args:
            name: Model name
            endpoint: API endpoint URL
            adapter_type: "openai", "anthropic", or "vllm"
            context_window: Token limit
            supports_vision: Whether model supports images
            supports_tools: Whether model supports function calling
            provider: Optional provider display name
            health_check: Optional health check endpoint
            
        Returns:
            Dict with name, status, registered_at
        """
        capabilities = models_pb2.ModelCapabilities(
            context_window=context_window,
            supports_vision=supports_vision,
            supports_tools=supports_tools
        )
        
        request = models_pb2.RegisterModelRequest(
            name=name,
            endpoint=endpoint,
            capabilities=capabilities,
            health_check=health_check or "",
            adapter_type=adapter_type,
            provider=provider or ""
        )
        
        response = self._stub.RegisterModel(request, metadata=self.metadata)
        
        return {
            'name': response.name,
            'status': response.status,
            'registered_at': response.registered_at
        }
    
    def list_registered_models(self) -> List[Dict[str, Any]]:
        """
        List all registered custom models.
        
        Returns:
            List of registered model dicts
        """
        response = self._stub.ListRegisteredModels(
            models_pb2.ListRegisteredModelsRequest(),
            metadata=self.metadata
        )
        
        return [
            {
                'name': model.name,
                'endpoint': model.endpoint,
                'provider': model.provider,
                'adapter_type': model.adapter_type,
                'status': model.status
            }
            for model in response.models
        ]
    
    def get_model_status(self, name: str) -> Dict[str, Any]:
        """
        Get status for a registered model.
        
        Args:
            name: Model name
            
        Returns:
            Dict with name, status, last_checked, endpoint
        """
        request = models_pb2.GetModelStatusRequest(name=name)
        status = self._stub.GetModelStatus(request, metadata=self.metadata)
        
        return {
            'name': status.name,
            'status': status.status,
            'last_checked': status.last_checked,
            'endpoint': status.endpoint
        }

