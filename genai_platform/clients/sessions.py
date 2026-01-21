"""
Session Service client.

Handles conversation state, session management, and context tracking.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from .base import BaseClient
from proto import sessions_pb2
from proto import sessions_pb2_grpc


class SessionClient(BaseClient):
    """
    Client for Session Service.
    
    Manages conversation state, message storage, and model-managed memory.
    """
    
    def __init__(self, platform):
        super().__init__(platform, "sessions")
        self._stub = sessions_pb2_grpc.SessionServiceStub(self._channel)
    
    # Session management
    
    def get_or_create(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> sessions_pb2.GetOrCreateSessionResponse:
        """
        Get existing session or create a new one.
        
        Args:
            user_id: User identifier
            session_id: Optional existing session ID
        
        Returns:
            Session object with session_id, user_id, created_at, updated_at
        
        Example:
            session = platform.sessions.get_or_create("patient-123")
            print(f"Session ID: {session.session_id}")
        """
        request = sessions_pb2.GetOrCreateSessionRequest(
            user_id=user_id,
            session_id=session_id if session_id else ""
        )
        response = self._stub.GetOrCreateSession(
            request,
            metadata=self.metadata
        )
        return response
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its messages.
        
        Args:
            session_id: Session to delete
        
        Returns:
            True if deletion was successful
        
        Example:
            success = platform.sessions.delete_session("session-123")
        """
        request = sessions_pb2.DeleteSessionRequest(session_id=session_id)
        response = self._stub.DeleteSession(request, metadata=self.metadata)
        return response.success
    
    # Message operations
    
    def add_messages(
        self,
        session_id: str,
        messages: List[Dict[str, Any]]
    ) -> int:
        """
        Add messages to a session.
        
        Args:
            session_id: Session to add messages to
            messages: List of message dicts with role, content, etc.
        
        Returns:
            Number of messages added
        
        Example:
            messages = [
                {"role": "user", "content": "What documents do I need?"},
                {"role": "assistant", "content": "You'll need your ID and insurance card."}
            ]
            count = platform.sessions.add_messages("session-123", messages)
        """
        # Convert dicts to proto messages
        proto_messages = []
        for msg in messages:
            proto_msg = self._dict_to_message(msg)
            proto_messages.append(proto_msg)
        
        request = sessions_pb2.AddMessagesRequest(
            session_id=session_id,
            messages=proto_messages
        )
        response = self._stub.AddMessages(request, metadata=self.metadata)
        return response.message_count
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        strategy: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get messages from a session.
        
        Args:
            session_id: Session to retrieve messages from
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            strategy: Context window strategy ("truncate", "hierarchical", etc.)
        
        Returns:
            Tuple of (messages list, total count)
        
        Example:
            messages, total = platform.sessions.get_messages(
                "session-123", 
                limit=20
            )
            print(f"Retrieved {len(messages)} of {total} messages")
        """
        request = sessions_pb2.GetMessagesRequest(session_id=session_id)
        
        if limit is not None:
            request.limit = limit
        
        if offset is not None:
            request.offset = offset
        
        if strategy:
            request.strategy = strategy
        
        response = self._stub.GetMessages(request, metadata=self.metadata)
        
        # Convert proto messages to dicts
        messages = [self._message_to_dict(msg) for msg in response.messages]
        
        return messages, response.total_count
    
    # Memory operations
    
    def save_memory(
        self,
        user_id: str,
        key: str,
        value: Any,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Save a fact to memory.
        
        Args:
            user_id: User identifier
            key: Memory key (e.g., "allergies", "preferences")
            value: Memory value (any JSON-serializable data)
            session_id: Optional session ID for session-scoped memory
        
        Returns:
            True if save was successful
        
        Example:
            platform.sessions.save_memory(
                "patient-123",
                "allergies",
                ["penicillin", "latex"]
            )
        """
        request = sessions_pb2.SaveMemoryRequest(
            user_id=user_id,
            key=key,
            value=json.dumps(value),
            session_id=session_id if session_id else ""
        )
        response = self._stub.SaveMemory(request, metadata=self.metadata)
        return response.success
    
    def get_memory(
        self,
        user_id: str,
        key: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve memories for a user.
        
        Args:
            user_id: User identifier
            key: Optional specific key to retrieve
            session_id: Optional filter by session
        
        Returns:
            Dictionary mapping keys to values
        
        Example:
            # Get all memories for a user
            memories = platform.sessions.get_memory("patient-123")
            allergies = memories.get("allergies", [])
            
            # Get specific memory
            preferences = platform.sessions.get_memory("patient-123", key="preferences")
        """
        request = sessions_pb2.GetMemoryRequest(user_id=user_id)
        
        if key:
            request.key = key
        
        if session_id:
            request.session_id = session_id
        
        response = self._stub.GetMemory(request, metadata=self.metadata)
        
        # Deserialize JSON values
        return {k: json.loads(v) for k, v in response.memories.items()}
    
    def delete_memory(
        self,
        user_id: str,
        key: str,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Delete a memory entry.
        
        Args:
            user_id: User identifier
            key: Memory key to delete
            session_id: Optional session filter
        
        Returns:
            True if memory was deleted
        
        Example:
            platform.sessions.delete_memory("patient-123", "temporary_note")
        """
        request = sessions_pb2.DeleteMemoryRequest(
            user_id=user_id,
            key=key,
            session_id=session_id if session_id else ""
        )
        response = self._stub.DeleteMemory(request, metadata=self.metadata)
        return response.success
    
    def clear_user_memory(self, user_id: str) -> int:
        """
        Clear all memories for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            Number of memories deleted
        
        Example:
            count = platform.sessions.clear_user_memory("patient-123")
            print(f"Deleted {count} memories")
        """
        request = sessions_pb2.ClearUserMemoryRequest(user_id=user_id)
        response = self._stub.ClearUserMemory(request, metadata=self.metadata)
        return response.count
    
    # Helper methods for message conversion
    
    def _dict_to_message(self, msg_dict: Dict[str, Any]) -> sessions_pb2.Message:
        """Convert a message dict to proto Message."""
        message = sessions_pb2.Message(
            role=msg_dict.get("role", "user"),
            timestamp=msg_dict.get("timestamp", int(datetime.utcnow().timestamp() * 1000))
        )
        
        if "content" in msg_dict and msg_dict["content"] is not None:
            message.content = msg_dict["content"]
        
        if "tool_call_id" in msg_dict and msg_dict["tool_call_id"] is not None:
            message.tool_call_id = msg_dict["tool_call_id"]
        
        if "name" in msg_dict and msg_dict["name"] is not None:
            message.name = msg_dict["name"]
        
        if "tool_calls" in msg_dict and msg_dict["tool_calls"]:
            for tc in msg_dict["tool_calls"]:
                tool_call = sessions_pb2.MessageToolCall(
                    id=tc["id"],
                    type=tc.get("type", "function"),
                    function=sessions_pb2.MessageFunction(
                        name=tc["function"]["name"],
                        arguments=tc["function"]["arguments"]
                    )
                )
                message.tool_calls.append(tool_call)
        
        return message
    
    def _message_to_dict(self, message: sessions_pb2.Message) -> Dict[str, Any]:
        """Convert a proto Message to dict."""
        result = {
            "role": message.role,
            "timestamp": message.timestamp
        }
        
        if message.HasField("content"):
            result["content"] = message.content
        
        if message.HasField("tool_call_id"):
            result["tool_call_id"] = message.tool_call_id
        
        if message.HasField("name"):
            result["name"] = message.name
        
        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        
        return result
