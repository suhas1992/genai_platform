"""
Session Service client.

Handles conversation state, session management, and context tracking.
"""

import grpc
from typing import Optional

from .base import BaseClient
from proto import sessions_pb2
from proto import sessions_pb2_grpc

# Use the proto-generated Session message directly
Session = sessions_pb2.Session


class SessionClient(BaseClient):
    """
    Client for Session Service.
    
    Manages conversation state and session persistence.
    """
    
    def __init__(self, platform):
        super().__init__(platform, "sessions")
        self._stub = sessions_pb2_grpc.SessionServiceStub(self._channel)
    
    def get_or_create(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> Session:
        """
        Get existing session or create a new one.
        
        Args:
            user_id: User identifier
            session_id: Optional existing session ID
        
        Returns:
            Session object
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

