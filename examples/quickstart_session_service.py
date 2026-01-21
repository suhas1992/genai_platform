"""
Simple workflow example.

This demonstrates the basic SDK usage pattern from Chapter 2.
Automatically starts gateway and session service, then runs the workflow.
"""

import sys
import time
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from genai_platform import GenAIPlatform, workflow
from services.sessions.main import main as start_session_service
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


@workflow(
    name="patient_intake_assistant",
    api_path="/patient-assistant"
)
def handle_patient_question(question: str, patient_id: str):
    """
    Simple patient intake assistant workflow.
    
    This matches the example from Chapter 2, Listing 2.10.
    """
    platform = GenAIPlatform()
    
    # Get or create session for conversation memory
    session = platform.sessions.get_or_create(patient_id)
    
    return {
        "response": "[Model Service not yet implemented]",
        "session_id": session.session_id
    }


if __name__ == "__main__":
    print("Starting services...")
    
    # Start session service
    print("  Starting Session Service...")
    session_thread = start_service_in_thread(start_session_service, "SessionService")
    time.sleep(2)  # Wait for session service to start
    
    # Start gateway
    print("  Starting API Gateway...")
    gateway_thread = start_service_in_thread(start_gateway, "Gateway")
    time.sleep(2)  # Wait for gateway to start
    
    print("\nServices started. Running workflow...\n")
    
    # Run the workflow
    result = handle_patient_question(
        "What documents do I need for my appointment?",
        "patient-123"
    )
    
    print(f"Response: {result['response']}")
    print(f"Session ID: {result['session_id']}")
    print("\n✓ Workflow completed successfully!")
    print("Services are running in background. Press Ctrl+C to stop.")
    
    try:
        # Keep main thread alive so services keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping services...")
        sys.exit(0)

