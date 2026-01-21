"""
Quick start example for Model Service.

Demonstrates basic chat with OpenAI and Anthropic.
Requires OPENAI_API_KEY and/or ANTHROPIC_API_KEY in .env file.
"""

import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from genai_platform import GenAIPlatform
from services.sessions.main import main as start_session_service
from services.models.main import main as start_model_service
from services.gateway.main import main as start_gateway


def start_service_in_thread(service_func, service_name):
    def run_service():
        try:
            service_func()
        except KeyboardInterrupt:
            pass
    thread = threading.Thread(target=run_service, daemon=True, name=service_name)
    thread.start()
    return thread


def main():
    print("Starting services...")
    start_service_in_thread(start_session_service, "SessionService")
    time.sleep(1)
    start_service_in_thread(start_model_service, "ModelService")
    time.sleep(1)
    start_service_in_thread(start_gateway, "Gateway")
    time.sleep(1)
    print("Services ready!\n")
    
    platform = GenAIPlatform()
    
    # Example 1: Simple chat with OpenAI
    print("=" * 50)
    print("OpenAI (gpt-4o)")
    print("=" * 50)
    question = "Explain quantum computing in one sentence."
    print(f"Q: {question}")
    
    response = platform.models.chat(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
        temperature=0.7,
        max_tokens=100
    )
    
    print(f"A: {response['text']}")
    print(f"Tokens: {response['usage']['total_tokens']}\n")
    
    # Example 2: Simple chat with Anthropic
    print("=" * 50)
    print("Anthropic (claude-sonnet-4-5)")
    print("=" * 50)
    question = "What's the speed of light?"
    print(f"Q: {question}")
    
    response = platform.models.chat(
        model="claude-sonnet-4-5",
        messages=[{"role": "user", "content": question}],
        temperature=0.7,
        max_tokens=100
    )
    
    print(f"A: {response['text']}")
    print(f"Tokens: {response['usage']['total_tokens']}\n")
    
    # Example 3: Streaming with OpenAI
    print("=" * 50)
    print("Streaming - OpenAI (gpt-4o)")
    print("=" * 50)
    question = "Count from 1 to 3."
    print(f"Q: {question}")
    print("A: ", end="", flush=True)
    
    for token in platform.models.chat_stream(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
        max_tokens=50
    ):
        print(token, end="", flush=True)
    
    print("\n")
    
    # Example 4: Streaming with Anthropic (longer response)
    print("=" * 50)
    print("Streaming - Anthropic (claude-sonnet-4-5)")
    print("=" * 50)
    question = "Explain the process of photosynthesis in plants."
    print(f"Q: {question}")
    print("A: ", end="", flush=True)
    
    for token in platform.models.chat_stream(
        model="claude-sonnet-4-5",
        messages=[{"role": "user", "content": question}],
        temperature=0.7,
        max_tokens=200
    ):
        print(token, end="", flush=True)
    
    print("\n")
    
    print("\n✓ Done! Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        sys.exit(0)


if __name__ == "__main__":
    main()
