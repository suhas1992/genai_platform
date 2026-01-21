"""
OpenAI provider adapter.
"""

from __future__ import annotations

import json
from typing import Iterator, List, Optional

from openai import OpenAI

from proto import models_pb2
from services.models.providers.base import ModelProvider


class OpenAIProvider(ModelProvider):
    """Adapter for OpenAI Chat Completions API."""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if base_url:
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self._client = OpenAI(api_key=api_key)

    def chat(
        self,
        model: str,
        messages: List[models_pb2.ChatMessage],
        config: models_pb2.ChatConfig,
        tools: Optional[List[models_pb2.ToolDefinition]] = None,
        response_format: Optional[models_pb2.ResponseFormat] = None,
        system_prompt: Optional[str] = None,
    ) -> models_pb2.ChatResponse:
        openai_messages = [self._convert_message(message) for message in messages]
        if system_prompt:
            openai_messages.insert(
                0,
                {"role": "system", "content": system_prompt},
            )
        payload = {
            "model": model,
            "messages": openai_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stop": list(config.stop_sequences),
        }
        if tools:
            payload["tools"] = [self._convert_tool(tool) for tool in tools]
        if response_format:
            payload["response_format"] = self._convert_response_format(response_format)

        response = self._client.chat.completions.create(**payload)
        message = response.choices[0].message
        tool_calls = self._extract_tool_calls(message.tool_calls or [])
        usage = response.usage

        return models_pb2.ChatResponse(
            text=message.content or "",
            model=response.model,
            provider="openai",
            usage=models_pb2.TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            ),
            tool_calls=tool_calls,
            finish_reason=response.choices[0].finish_reason or "",
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
        openai_messages = [self._convert_message(message) for message in messages]
        if system_prompt:
            openai_messages.insert(
                0,
                {"role": "system", "content": system_prompt},
            )
        payload = {
            "model": model,
            "messages": openai_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stop": list(config.stop_sequences),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = [self._convert_tool(tool) for tool in tools]
        if response_format:
            payload["response_format"] = self._convert_response_format(response_format)

        index = 0
        final_finish = None
        final_usage = None
        stream = self._client.chat.completions.create(**payload)
        for event in stream:
            # Check if choices array is not empty (OpenAI may send empty choices)
            if not event.choices:
                if event.usage:
                    final_usage = event.usage
                continue
            
            choice = event.choices[0]
            delta = choice.delta
            if delta and delta.content:
                yield models_pb2.ChatChunk(
                    token=delta.content,
                    index=index,
                )
                index += 1
            if choice.finish_reason:
                final_finish = choice.finish_reason
            if event.usage:
                final_usage = event.usage

        if final_usage:
            usage = models_pb2.TokenUsage(
                prompt_tokens=final_usage.prompt_tokens,
                completion_tokens=final_usage.completion_tokens,
                total_tokens=final_usage.total_tokens,
            )
        else:
            usage = None

        yield models_pb2.ChatChunk(
            token="",
            index=index,
            finish_reason=final_finish or "stop",
            usage=usage if usage else None,
        )

    def get_supported_models(self) -> List[models_pb2.ModelInfo]:
        return [
            models_pb2.ModelInfo(
                name="gpt-4o",
                provider="openai",
                capabilities=models_pb2.ModelCapabilities(
                    context_window=128000,
                    supports_vision=True,
                    supports_tools=True,
                ),
            ),
            models_pb2.ModelInfo(
                name="gpt-4o-mini",
                provider="openai",
                capabilities=models_pb2.ModelCapabilities(
                    context_window=128000,
                    supports_vision=True,
                    supports_tools=True,
                ),
            ),
        ]

    def _convert_message(self, message: models_pb2.ChatMessage) -> dict:
        data = {
            "role": message.role,
            "content": message.content,
        }
        if message.tool_calls:
            data["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": call.arguments_json,
                    },
                }
                for call in message.tool_calls
            ]
        if message.tool_call_id:
            data["tool_call_id"] = message.tool_call_id
        return data

    def _convert_tool(self, tool: models_pb2.ToolDefinition) -> dict:
        parameters = {}
        if tool.parameters_json:
            parameters = json.loads(tool.parameters_json)
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": parameters,
            },
        }

    def _convert_response_format(self, response_format: models_pb2.ResponseFormat) -> dict:
        payload = {"type": response_format.type}
        if response_format.schema_json:
            payload["json_schema"] = json.loads(response_format.schema_json)
        return payload

    def _extract_tool_calls(
        self,
        tool_calls,
    ) -> List[models_pb2.ToolCall]:
        converted = []
        for call in tool_calls:
            function = call.function
            converted.append(
                models_pb2.ToolCall(
                    id=call.id,
                    name=function.name,
                    arguments_json=function.arguments,
                )
            )
        return converted
