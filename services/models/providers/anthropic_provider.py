"""
Anthropic (Claude) provider adapter.
"""

from __future__ import annotations

import json
from typing import Iterator, List, Optional

from anthropic import Anthropic

from proto import models_pb2
from services.models.providers.base import ModelProvider


class AnthropicProvider(ModelProvider):
    """Adapter for Anthropic Messages API."""

    def __init__(self, api_key: str):
        self._client = Anthropic(api_key=api_key)

    def chat(
        self,
        model: str,
        messages: List[models_pb2.ChatMessage],
        config: models_pb2.ChatConfig,
        tools: Optional[List[models_pb2.ToolDefinition]] = None,
        response_format: Optional[models_pb2.ResponseFormat] = None,
        system_prompt: Optional[str] = None,
    ) -> models_pb2.ChatResponse:
        system_text, conversation = self._split_system_messages(messages, system_prompt)
        payload = {
            "model": model,
            "messages": [self._convert_message(message) for message in conversation],
            "max_tokens": config.max_tokens,
            "stop_sequences": list(config.stop_sequences),
        }
        
        # Anthropic doesn't allow both temperature and top_p
        # Prefer temperature if set, otherwise use top_p
        if config.temperature > 0:
            payload["temperature"] = config.temperature
        elif config.top_p > 0 and config.top_p < 1:
            payload["top_p"] = config.top_p
        if system_text:
            payload["system"] = system_text
        if tools:
            payload["tools"] = [self._convert_tool(tool) for tool in tools]
        if response_format:
            payload["response_format"] = self._convert_response_format(response_format)

        response = self._client.messages.create(**payload)
        text = self._extract_text(response.content)
        usage = response.usage

        return models_pb2.ChatResponse(
            text=text,
            model=response.model,
            provider="anthropic",
            usage=models_pb2.TokenUsage(
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens,
                total_tokens=usage.input_tokens + usage.output_tokens,
            ),
            finish_reason=response.stop_reason or "",
        )

    def chat_stream(
        self,
        model: str,
        messages: List[models_pb2.ChatMessage],
        config: models_pb2.ChatConfig,
        tools: Optional[List[models_pb2.ToolDefinition]] = None,
        response_format: Optional[models_pb2.ResponseFormat] = None,
        system_prompt: Optional[str] = None,
    ) -> Iterator[models_pb2.ChatChunk]:
        system_text, conversation = self._split_system_messages(messages, system_prompt)
        payload = {
            "model": model,
            "messages": [self._convert_message(message) for message in conversation],
            "max_tokens": config.max_tokens,
            "stop_sequences": list(config.stop_sequences),
        }
        
        # Anthropic doesn't allow both temperature and top_p
        # Prefer temperature if set, otherwise use top_p
        if config.temperature > 0:
            payload["temperature"] = config.temperature
        elif config.top_p > 0 and config.top_p < 1:
            payload["top_p"] = config.top_p
        if system_text:
            payload["system"] = system_text
        if tools:
            payload["tools"] = [self._convert_tool(tool) for tool in tools]
        if response_format:
            payload["response_format"] = self._convert_response_format(response_format)

        index = 0
        with self._client.messages.stream(**payload) as stream:
            for text in stream.text_stream:
                yield models_pb2.ChatChunk(token=text, index=index)
                index += 1
            final = stream.get_final_message()

        usage = final.usage
        yield models_pb2.ChatChunk(
            token="",
            index=index,
            finish_reason=final.stop_reason or "stop",
            usage=models_pb2.TokenUsage(
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens,
                total_tokens=usage.input_tokens + usage.output_tokens,
            ),
        )

    def get_supported_models(self) -> List[models_pb2.ModelInfo]:
        return [
            # Claude 4.5 Sonnet (2026 - current flagship)
            models_pb2.ModelInfo(
                name="claude-sonnet-4-5",
                provider="anthropic",
                capabilities=models_pb2.ModelCapabilities(
                    context_window=200000,
                    supports_vision=True,
                    supports_tools=True,
                ),
            ),
            # Claude 4.5 Haiku (2026 - fast model)
            models_pb2.ModelInfo(
                name="claude-haiku-4-5",
                provider="anthropic",
                capabilities=models_pb2.ModelCapabilities(
                    context_window=200000,
                    supports_vision=True,
                    supports_tools=True,
                ),
            ),
            # Claude Opus 4.5 - Maximum intelligence with practical performance
            models_pb2.ModelInfo(
                name="claude-opus-4-5",
                provider="anthropic",
                capabilities=models_pb2.ModelCapabilities(
                    context_window=200000,
                    supports_vision=True,
                    supports_tools=True,
                ),
            ),
            # Claude Opus 4.1 - Exceptional intelligence for specialized tasks
            models_pb2.ModelInfo(
                name="claude-opus-4-1",
                provider="anthropic",
                capabilities=models_pb2.ModelCapabilities(
                    context_window=200000,
                    supports_vision=True,
                    supports_tools=True,
                ),
            ),
        ]

    def _split_system_messages(
        self,
        messages: List[models_pb2.ChatMessage],
        system_prompt: Optional[str],
    ) -> tuple[Optional[str], List[models_pb2.ChatMessage]]:
        system_messages = []
        conversation = []
        for message in messages:
            if message.role == "system":
                system_messages.append(message.content)
            else:
                conversation.append(message)
        if system_prompt:
            system_messages.insert(0, system_prompt)
        combined = "\n".join([text for text in system_messages if text])
        return combined if combined else None, conversation

    def _convert_message(self, message: models_pb2.ChatMessage) -> dict:
        return {
            "role": message.role,
            "content": message.content,
        }

    def _convert_tool(self, tool: models_pb2.ToolDefinition) -> dict:
        input_schema = {}
        if tool.parameters_json:
            input_schema = json.loads(tool.parameters_json)
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": input_schema,
        }

    def _convert_response_format(self, response_format: models_pb2.ResponseFormat) -> dict:
        return {"type": response_format.type}

    def _extract_text(self, blocks) -> str:
        parts = []
        for block in blocks:
            if block.type == "text":
                parts.append(block.text)
        return "".join(parts)
