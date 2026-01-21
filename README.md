# GenAI Platform

Production-ready platform for building GenAI applications with multi-provider support. Accompanies the book on building GenAI platforms.

## Features

- **Multi-provider inference**: OpenAI, Anthropic (with streaming)
- **Session management**: Conversation history
- **Model discovery**: Query capabilities, register custom models
- **Prompt registry**: Centralized system prompt management
- **Service architecture**: gRPC services with unified API Gateway

## Setup

```bash
# 1. Install
pip install -e .

# 2. Configure API keys (create .env file)
echo "OPENAI_API_KEY=your-key" > .env
echo "ANTHROPIC_API_KEY=your-key" >> .env

# 3. Generate Protocol Buffer code
python -m proto.generate
```

## Quick Start

**Model Service:**
```bash
# Quick demo - OpenAI & Anthropic chat/streaming
python examples/quickstart_models.py

# Full test - discovery, prompts, custom models
python examples/test_model_service.py
```

**Session Service:**
```bash
python examples/quickstart_session_service.py
```

**Run services separately** (optional):
```bash
python -m services.sessions.main  # Terminal 1
python -m services.models.main    # Terminal 2
python -m services.gateway.main   # Terminal 3
```

## Usage

```python
from genai_platform import GenAIPlatform
from proto import models_pb2

platform = GenAIPlatform()

# Basic chat
request = models_pb2.ChatRequest(
    model="gpt-4o",
    messages=[models_pb2.ChatMessage(role="user", content="Hello!")],
)
response = platform.models.chat(request)

# Streaming
for chunk in platform.models.chat_stream(request):
    print(chunk.token, end="", flush=True)

# Model discovery
models = platform.models.list_models()
```

## Supported Models

**OpenAI**: `gpt-4o`, `gpt-4o-mini`  
**Anthropic**: `claude-sonnet-4-5`, `claude-opus-4-5`, `claude-opus-4-1`, `claude-haiku-4-5`

## Architecture

```
genai_platform/
├── genai_platform/     # SDK
│   └── clients/        # Service clients (sessions, models)
├── proto/              # Protocol Buffer definitions
├── services/
│   ├── gateway/        # API Gateway
│   ├── sessions/       # Session Service
│   └── models/         # Model Service
│       └── providers/  # OpenAI, Anthropic adapters
└── examples/           # Demo scripts
```

## Status

✅ Session Service, Model Service (OpenAI, Anthropic), API Gateway  
🚧 Data, Guardrails, Tool, Evaluation services (coming soon)
