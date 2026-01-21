"""
Session + Model Service integration example.

Demonstrates end-to-end workflow with conversation memory (Chapters 2-4).
Automatically starts services and runs a conversation with context.
"""

import sys
import time
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from genai_platform import GenAIPlatform, workflow
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


def handle_patient_question_with_session(question: str, session_id: str):
    """
    Handle a question using an existing session.
    
    Demonstrates Session + Model Service integration (Chapters 2-4).
    """
    platform = GenAIPlatform()
    
    # Get conversation history
    messages, _ = platform.sessions.get_messages(session_id, limit=10)
    
    # Build conversation for model - just simple dicts!
    conversation = [
        {"role": "system", "content": "You are a helpful patient intake assistant."}
    ]
    
    # Add history (already in dict format from session service)
    conversation.extend(messages)
    
    # Add new question
    conversation.append({"role": "user", "content": question})
    
    # Generate response with streaming - clean API, no pb2!
    try:
        # Stream the response token by token
        answer_parts = []
        for token in platform.models.chat_stream(
            model="gpt-4o-mini",
            messages=conversation
        ):
            print(token, end="", flush=True)
            answer_parts.append(token)
        
        answer = "".join(answer_parts)
        print()  # New line after streaming
        
    except Exception as e:
        answer = f"[Model Service error: {e}]"
        print(answer)
    
    # Save conversation turn
    platform.sessions.add_messages(session_id, [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer}
    ])
    
    return {
        "response": answer,
        "session_id": session_id
    }


if __name__ == "__main__":
    print("="*60)
    print("  Session + Model Service Integration Demo")
    print("  Chapters 2-4: Workflow with Conversation Memory")
    print("="*60)
    print("\nStarting services...")
    
    # Start session service
    print("  Starting Session Service...")
    session_thread = start_service_in_thread(start_session_service, "SessionService")
    time.sleep(2)
    
    # Start model service
    print("  Starting Model Service...")
    model_thread = start_service_in_thread(start_model_service, "ModelService")
    time.sleep(2)
    
    # Start gateway
    print("  Starting API Gateway...")
    gateway_thread = start_service_in_thread(start_gateway, "Gateway")
    time.sleep(2)
    
    print("\n✓ Services started!\n")
    
    # Create platform and session ONCE for the conversation
    platform = GenAIPlatform()
    session = platform.sessions.get_or_create("patient-123")
    print(f"Using session: {session.session_id}\n")
    print("Running conversation with context...\n")
    
    # First interaction with unique detail
    print("Question 1: I'm traveling from Canada for my appointment. What documents do I need to bring?")
    print("Assistant: ", end="", flush=True)
    result1 = handle_patient_question_with_session(
        "I'm traveling from Canada for my appointment. What documents do I need to bring?",
        session.session_id
    )
    print()  # Extra line after response
    
    # Follow-up that tests if model remembers the context
    print("Question 2: Where am I coming from?")
    print("Assistant: ", end="", flush=True)
    result2 = handle_patient_question_with_session(
        "Where am I coming from?",
        session.session_id
    )
    print()  # Extra line after response
    
    # Verify context - should answer "Canada"
    if "canada" in result2['response'].lower():
        print("✓ Context awareness verified: Model remembered 'Canada' from Question 1!")
    else:
        print("⚠ Context not used: Model should have answered 'Canada'")
    
    print("\n" + "="*60)
    print(f"✓ Conversation complete!")
    print(f"Session ID: {session.session_id}")
    
    # Show what was actually stored in the session
    print("\n" + "-"*60)
    print("Messages stored in session:")
    print("-"*60)
    
    stored_messages, total = platform.sessions.get_messages(session.session_id)
    
    for i, msg in enumerate(stored_messages, 1):
        role = msg['role'].upper()
        content = msg.get('content', '')[:100]  # First 100 chars
        if len(msg.get('content', '')) > 100:
            content += "..."
        print(f"{i}. [{role}] {content}")
    
    print(f"\nTotal: {total} messages stored")
    print("="*60)
    print("\nDemo shows:")
    print("  • Session creation and retrieval")
    print("  • Conversation history management")
    print("  • Context-aware follow-up questions")
    print("  • Model Service integration")
    print("\nServices are running. Press Ctrl+C to stop.")
    
    try:
        # Keep main thread alive so services keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping services...")
        sys.exit(0)

