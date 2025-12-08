# GenAI Platform

A platform for building production-ready GenAI applications. This codebase accompanies the book on building GenAI platforms.

## Architecture

The platform provides a service-oriented architecture with:
- **SDK**: Python SDK for building AI workflows
- **Services**: Session, Model, Data, Guardrails, Tool, Evaluation, and Workflow services
- **API Gateway**: Unified entry point for external and internal communication
- **Protocol**: gRPC for internal service communication, HTTP for external clients

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -e ".[dev]"
```

### 2. Generate Protocol Buffer Code

The SDK uses Protocol Buffers for service communication. Generate the Python code:

```bash
python -m proto.generate
```

This creates `*_pb2.py` and `*_pb2_grpc.py` files from the `.proto` definitions.

### 3. Try the Example Workflow

```bash
python examples/simple_workflow.py
```

## Project Structure

```
genai_platform/
├── genai_platform/          # SDK package
│   ├── __init__.py
│   ├── platform.py          # GenAIPlatform class
│   ├── workflow.py          # @workflow decorator
│   └── clients/             # Service clients
│       ├── base.py
│       ├── sessions.py
│       ├── models.py
│       ├── data.py
│       ├── guardrails.py
│       ├── tools.py
│       └── evaluation.py
├── proto/                   # Protocol Buffer definitions (shared)
│   ├── sessions.proto
│   └── generate.py
├── services/                # Backend services
│   ├── gateway/             # API Gateway
│   └── sessions/            # Session Service
└── examples/                # Example workflows
```

## Development

This is a work in progress. The SDK foundation is implemented, with service implementations coming in subsequent chapters.
