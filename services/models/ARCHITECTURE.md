# Model Service Architecture

## Overview

The Model Service provides a unified interface to AI models with a simple principle: **provider adapters auto-discover built-in models, users register custom models**.

This aligns with Chapter 3's architecture while keeping configuration minimal.

## Core Principle

**Zero Config for Common Case:**
```bash
# Just set API keys - models work automatically
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Flexible When Needed:**
```python
# Register custom models or override defaults
platform.models.register_model(...)
```

## Architecture

### 1. Provider Adapters (`providers/`)

**Purpose**: Know HOW to talk to model APIs.

Each adapter:
- Implements the `ModelProvider` interface
- Auto-discovers its supported models via `get_supported_models()`
- Translates between platform format and provider API

**Available Adapters:**
- `OpenAIProvider` - OpenAI API format (gpt-4o, gpt-4o-mini, etc.)
- `AnthropicProvider` - Anthropic API format (claude-3-5-sonnet, etc.)
- Future: `VLLMProvider` - vLLM/OpenAI-compatible format

**Key Methods:**
```python
class ModelProvider(ABC):
    def chat(...) -> ChatResponse
    def chat_stream(...) -> Iterator[ChatChunk]
    def get_supported_models() -> List[ModelInfo]  # Report supported models
```

### 2. Model Registry (`store.py`)

**Purpose**: Stores explicit model registrations (custom + overrides).

**Use Cases:**
- Register custom self-hosted models
- Override built-in model endpoints (e.g., Azure OpenAI proxy)

**NOT for:** Built-in commercial models (those are auto-discovered).

```python
class ModelRegistry:
    def register(name, endpoint, capabilities, adapter_type)
    def get(name) -> RegisteredModel
    def list_all() -> List[RegisteredModel]
```

### 3. Prompt Registry (`store.py`)

**Purpose**: Version and manage system prompts.

Standard registry pattern - unchanged.

### 4. Model Service (`service.py`)

**Main orchestrator** with clean resolution logic.

## Resolution Flow

When a request comes in for model "X":

```
1. Check ModelRegistry (explicit registrations)
   - Custom models
   - Overrides of built-in models
   
2. Check provider adapters (auto-discovered)
   - OpenAI models (if OPENAI_API_KEY set)
   - Anthropic models (if ANTHROPIC_API_KEY set)
   
3. Return None if not found
```

### Examples

**Request "gpt-4o"** (not registered):
```
1. Registry check: Not found
2. Provider check: OpenAIProvider reports it supports "gpt-4o"
3. → Use OpenAIProvider with default endpoint
```

**Request "gpt-4o"** (explicitly registered):
```
1. Registry check: Found with custom endpoint
2. → Use OpenAIProvider with custom endpoint (override)
```

**Request "my-llama"** (custom model):
```
1. Registry check: Found with endpoint + adapter_type="vllm"
2. → Use VLLMProvider with that endpoint
```

## Visual Architecture

```
┌─────────────────────────────────────────────────────┐
│              Model Service                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Resolution Order:                                  │
│  1. ModelRegistry (explicit)                        │
│  2. Provider Adapters (auto-discovered)             │
│                                                     │
│  ┌─────────────────┐   ┌──────────────────────┐   │
│  │  ModelRegistry  │   │ Provider Adapters    │   │
│  │  (Explicit)     │   │ (Auto-discover)      │   │
│  │                 │   │                      │   │
│  │ • Custom models │   │ • OpenAIProvider     │   │
│  │ • Overrides     │   │ • AnthropicProvider  │   │
│  └─────────────────┘   │ • (Future: VLLM...)  │   │
│                        └──────────────────────┘   │
│                                                     │
│  ┌─────────────────┐                               │
│  │ PromptRegistry  │                               │
│  │ (Versioning)    │                               │
│  └─────────────────┘                               │
└─────────────────────────────────────────────────────┘
                      │
                      ├─→ api.openai.com
                      ├─→ api.anthropic.com  
                      └─→ localhost:8000 (custom)
```

## Discovery (ListModels)

Returns unified list:
1. Auto-discovered from all provider adapters
2. Plus explicitly registered models
3. Explicit registrations override auto-discovered (same name)

Result: Single consistent model list regardless of source.

## Configuration

### Environment Variables

**OpenAI:**
```bash
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional
```

**Anthropic:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

**Auto-discovery:** If key is present, provider initializes and reports its models.

### Registering Custom Models

```python
platform.models.register_model(
    models_pb2.RegisterModelRequest(
        name="my-llama-70b",
        endpoint="http://localhost:8000/v1",
        capabilities=models_pb2.ModelCapabilities(
            context_window=8192,
            supports_vision=False,
            supports_tools=True,
        ),
        adapter_type="vllm",  # Which adapter: "openai", "anthropic", "vllm"
        provider="Internal Llama",  # Optional display name
        health_check="/health",
    )
)
```

### Overriding Built-in Models

```python
# Use Azure OpenAI instead of default
platform.models.register_model(
    models_pb2.RegisterModelRequest(
        name="gpt-4o",  # Same name = override
        endpoint="https://my-azure.openai.azure.com/v1",
        capabilities=...,  # Copy from default or customize
        adapter_type="openai",
    )
)
```

## Key Design Decisions

### 1. Auto-Discovery from Adapters

**Why:** Zero configuration for 99% of users.

Provider adapters know which models they support. No need to register "gpt-4o" manually - it's automatically available when `OPENAI_API_KEY` is set.

### 2. Explicit Registration for Custom Only

**Why:** Minimal boilerplate while supporting customization.

Only register when you need to:
- Add a custom model
- Override a default endpoint

### 3. Registry Overrides Auto-Discovered

**Why:** Power users can customize without breaking defaults.

Resolution checks registry first, so you can override any auto-discovered model by registering with the same name.

### 4. Single Resolution Path

**Why:** Simple to understand and debug.

Both built-in and custom models go through the same resolution logic. The only difference is where the model info comes from (adapter vs registry).

### 5. Adapter Type Field

**Why:** Future-proof for multiple self-hosted options.

Custom models specify which adapter to use:
- `"openai"` - OpenAI-compatible APIs (vLLM, Text Generation Inference, etc.)
- `"vllm"` - Dedicated vLLM adapter (future)
- `"anthropic"` - Anthropic-compatible APIs (future)

## Comparison: Before vs After

### Before (Confusing)
```
ProviderRegistry = commercial models
ModelRegistry = custom models
→ Two separate systems, unclear why
```

### After (Clean)
```
Provider Adapters = HOW to talk (OpenAI format, Anthropic format)
ModelRegistry = Explicit registrations (custom + overrides)

Resolution = Check registry first, then adapters
```

## Adding New Providers

### Commercial Provider (Auto-Discovered)

1. Create adapter in `providers/`:
```python
class GoogleProvider(ModelProvider):
    def get_supported_models(self):
        return [
            ModelInfo(name="gemini-pro", ...),
            ModelInfo(name="gemini-ultra", ...),
        ]
    # ... implement chat, chat_stream
```

2. Register in `ModelService._initialize_providers()`:
```python
google_key = os.getenv("GOOGLE_API_KEY")
if google_key:
    self._providers["google"] = GoogleProvider(api_key=google_key)
```

Done! Models auto-discovered when key is present.

### Custom Provider (User-Registered)

User registers via RPC - no code changes needed.

## Testing

```bash
# Quick test (auto-starts services)
python examples/quickstart_models.py

# Comprehensive test
python examples/test_model_service.py
```

## Future Enhancements

1. **Custom Model Inference**: Currently registered but not routable for inference. Need to support calling custom endpoints.

2. **Health Checking**: Implement actual health checks for registered models.

3. **Fallback Chains**: Chapter 3 fallback logic.

4. **Response Caching**: Chapter 3 caching strategies.

5. **vLLM Provider**: Dedicated adapter for vLLM-specific features.

## Summary

**Simple principle:**
- Provider adapters auto-discover built-in models (zero config)
- Users register custom models (explicit when needed)
- Single resolution path for both

**Result:**
- Zero config for common case
- Flexible when needed
- Easy to understand and debug
