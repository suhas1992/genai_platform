# GenAI Platform

Production-ready platform for building GenAI applications with multi-provider support. Accompanies the book on building GenAI platforms.

## Features

- **Multi-provider inference**: OpenAI, Anthropic (with streaming)
- **Session management**: Conversation history and model-managed memory
- **Message storage**: Full tool call support with proper linkage
- **Model discovery**: Query capabilities, register custom models
- **Prompt registry**: Centralized system prompt management
- **Storage abstraction**: In-memory (dev) or PostgreSQL (production)
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

**Model Service (Chapter 3):**
```bash
# Quick demo - OpenAI & Anthropic chat/streaming
python examples/quickstart_models.py

# Full test - discovery, prompts, custom models
python examples/test_model_service.py
```

**Session Service (Chapter 4):**
```bash
# Full test - messages, pagination, memory
python examples/test_session_service.py

# Conversation demo - Session + Model integration
python examples/quickstart_conversation.py
```

**Run services separately** (optional):
```bash
python -m services.sessions.main  # Terminal 1
python -m services.models.main    # Terminal 2
python -m services.gateway.main   # Terminal 3
```

## Usage

### Model Service
```python
from genai_platform import GenAIPlatform

platform = GenAIPlatform()

# Chat
response = platform.models.chat(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.7,
    max_tokens=150
)
print(response['text'])

# Streaming
for token in platform.models.chat_stream(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
):
    print(token, end="", flush=True)
```

### Session Service
```python
# Create session
session = platform.sessions.get_or_create("user-123")

# Store conversation
platform.sessions.add_messages(session.session_id, [
    {"role": "user", "content": "What documents do I need?"},
    {"role": "assistant", "content": "You'll need ID and insurance."}
])

# Retrieve history
messages, total = platform.sessions.get_messages(session.session_id, limit=20)

# Model-managed memory
platform.sessions.save_memory("user-123", "allergies", ["penicillin"])
memories = platform.sessions.get_memory("user-123")
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

✅ **Model Service** (Chapter 3): OpenAI, Anthropic, streaming, prompt management  
✅ **Session Service** (Chapter 4): Messages, pagination, model-managed memory  
✅ **API Gateway**: gRPC proxy with service discovery  
🚧 **Data Service** (Chapter 5): Search, retrieval, embeddings  
🚧 **Tool Service** (Chapter 6): Function calling, tool registry  
🚧 **Guardrails Service** (Chapter 7): Content filtering, safety  
🚧 **Evaluation Service** (Chapter 8): Testing, metrics
