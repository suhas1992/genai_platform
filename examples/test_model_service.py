"""
Complete Model Service test - demonstrates all operations.

Tests:
- ListModels (discovery)
- GetModelCapabilities
- Chat with OpenAI
- Chat with Anthropic  
- ChatStream (streaming)
- Prompt management (register, get, list)
- Custom model registration

Automatically starts all required services.
"""

import sys
import time
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from genai_platform import GenAIPlatform
from proto import models_pb2
from services.sessions.main import main as start_session_service
from services.models.main import main as start_model_service
from services.gateway.main import main as start_gateway


def start_service_in_thread(service_func, service_name):
    """Start a service in a background thread."""
    def run_service():
        try:
            service_func()
        except KeyboardInterrupt:
            pass
    
    thread = threading.Thread(target=run_service, daemon=True, name=service_name)
    thread.start()
    return thread


def test_discovery(platform: GenAIPlatform):
    """Test model discovery operations."""
    print("\n" + "="*60)
    print("TEST: Model Discovery")
    print("="*60)
    
    # List all available models
    response = platform.models.list_models()
    print(f"\nAvailable models: {len(response.models)}")
    for model in response.models:
        print(f"  - {model.name} ({model.provider})")
        print(f"    Context: {model.capabilities.context_window}")
        print(f"    Vision: {model.capabilities.supports_vision}")
        print(f"    Tools: {model.capabilities.supports_tools}")
    
    # Get capabilities for specific model
    if response.models:
        model_name = response.models[0].name
        caps_response = platform.models.get_model_capabilities(
            models_pb2.GetCapabilitiesRequest(model=model_name)
        )
        print(f"\nCapabilities for {model_name}:")
        print(f"  Context window: {caps_response.context_window}")
        print(f"  Vision: {caps_response.supports_vision}")
        print(f"  Tools: {caps_response.supports_tools}")


def test_chat(platform: GenAIPlatform, model: str, prompt: str):
    """Test basic chat completion."""
    print(f"\n[Chat] Model: {model}")
    print(f"Prompt: {prompt}")
    
    request = models_pb2.ChatRequest(
        model=model,
        messages=[
            models_pb2.ChatMessage(role="user", content=prompt),
        ],
        config=models_pb2.ChatConfig(
            temperature=0.7,
            max_tokens=150,
            top_p=1.0,
        ),
    )
    
    response = platform.models.chat(request)
    print(f"Response: {response.text}")
    print(f"Tokens: {response.usage.total_tokens} "
          f"(prompt: {response.usage.prompt_tokens}, "
          f"completion: {response.usage.completion_tokens})")
    print(f"Finish reason: {response.finish_reason}")


def test_streaming(platform: GenAIPlatform, model: str):
    """Test streaming chat completion."""
    print(f"\n[Streaming] Model: {model}")
    print("Streaming response: ", end="", flush=True)
    
    request = models_pb2.ChatRequest(
        model=model,
        messages=[
            models_pb2.ChatMessage(
                role="user",
                content="Count from 1 to 5, one number per line.",
            ),
        ],
        config=models_pb2.ChatConfig(
            temperature=0.7,
            max_tokens=50,
        ),
    )
    
    for chunk in platform.models.chat_stream(request):
        if chunk.token:
            print(chunk.token, end="", flush=True)
        if chunk.finish_reason:
            print(f"\n[Finish: {chunk.finish_reason}]")
            if chunk.usage:
                print(f"Tokens: {chunk.usage.total_tokens}")


def test_prompts(platform: GenAIPlatform):
    """Test prompt management."""
    print("\n" + "="*60)
    print("TEST: Prompt Management")
    print("="*60)
    
    # Register a prompt
    register_response = platform.models.register_prompt(
        models_pb2.RegisterPromptRequest(
            name="patient-intake",
            content="You are a helpful patient intake assistant for a medical clinic.",
            metadata=models_pb2.PromptMetadata(
                author="test@example.com",
                reviewed_by="admin@example.com",
                tags=["production", "medical"],
            ),
        )
    )
    print(f"\nRegistered prompt: {register_response.name} v{register_response.version}")
    
    # Get the prompt
    get_response = platform.models.get_prompt(
        models_pb2.GetPromptRequest(name="patient-intake", version=0)
    )
    print(f"Retrieved: {get_response.name} v{get_response.version}")
    print(f"Content: {get_response.content[:50]}...")
    
    # List all prompts
    list_response = platform.models.list_prompts()
    print(f"\nAll prompts: {len(list_response.prompts)}")
    for prompt in list_response.prompts:
        print(f"  - {prompt.name} v{prompt.version}")
    
    # Use prompt in chat
    print("\nUsing registered prompt in chat:")
    request = models_pb2.ChatRequest(
        model="gpt-4o",
        system_prompt_name="patient-intake",
        messages=[
            models_pb2.ChatMessage(
                role="user",
                content="What information do I need to bring?",
            ),
        ],
        config=models_pb2.ChatConfig(max_tokens=100),
    )
    response = platform.models.chat(request)
    print(f"Response: {response.text[:100]}...")


def test_custom_models(platform: GenAIPlatform):
    """Test custom model registration."""
    print("\n" + "="*60)
    print("TEST: Custom Model Registration")
    print("="*60)
    
    # Register a custom model
    register_response = platform.models.register_model(
        models_pb2.RegisterModelRequest(
            name="my-llama-70b",
            endpoint="http://localhost:8000/v1",
            capabilities=models_pb2.ModelCapabilities(
                context_window=8192,
                supports_vision=False,
                supports_tools=True,
            ),
            health_check="/health",
            adapter_type="openai-compatible",
        )
    )
    print(f"\nRegistered: {register_response.name}")
    print(f"Status: {register_response.status}")
    
    # List registered models
    list_response = platform.models.list_registered_models()
    print(f"\nCustom models: {len(list_response.models)}")
    for model in list_response.models:
        print(f"  - {model.name} ({model.adapter_type})")
        print(f"    Endpoint: {model.endpoint}")
    
    # Get model status
    status_response = platform.models.get_model_status(
        models_pb2.GetModelStatusRequest(name="my-llama-70b")
    )
    print(f"\nStatus for {status_response.name}:")
    print(f"  Status: {status_response.status}")
    print(f"  Endpoint: {status_response.endpoint}")


def main():
    print("="*60)
    print("Model Service Comprehensive Test")
    print("="*60)
    print("\nStarting services...")
    
    # Start services
    start_service_in_thread(start_session_service, "SessionService")
    time.sleep(2)
    start_service_in_thread(start_model_service, "ModelService")
    time.sleep(2)
    start_service_in_thread(start_gateway, "Gateway")
    time.sleep(2)
    
    print("Services started!\n")
    
    # Initialize platform
    platform = GenAIPlatform()
    
    try:
        # Discovery tests
        test_discovery(platform)
        
        # Chat tests
        print("\n" + "="*60)
        print("TEST: Chat Completions")
        print("="*60)
        test_chat(platform, "gpt-4o", "What is the capital of France?")
        test_chat(platform, "claude-sonnet-4-5", "What is 2+2?")
        
        # Streaming test
        print("\n" + "="*60)
        print("TEST: Streaming")
        print("="*60)
        test_streaming(platform, "gpt-4o")
        
        # Prompt management tests
        test_prompts(platform)
        
        # Custom model tests
        test_custom_models(platform)
        
        print("\n" + "="*60)
        print("✓ All tests completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nPress Ctrl+C to stop services...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        sys.exit(0)


if __name__ == "__main__":
    main()
