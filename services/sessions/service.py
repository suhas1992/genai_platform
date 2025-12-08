"""
Session Service - Business logic layer.

Implements the Session Service gRPC interface.
"""

import grpc
from proto import sessions_pb2_grpc
from services.shared.servicer_base import BaseServicer
from services.sessions.store import SessionStore


class SessionService(sessions_pb2_grpc.SessionServiceServicer, BaseServicer):
    """
    Implementation of Session Service.
    
    Handles gRPC requests for session management.
    """
    
    def __init__(self):
        self.store = SessionStore()
    
    def add_to_server(self, server: grpc.Server):
        """Add this servicer to a gRPC server."""
        sessions_pb2_grpc.add_SessionServiceServicer_to_server(self, server)
    
    def GetOrCreateSession(self, request, context):
        """
        Get existing session or create a new one.
        
        Args:
            request: GetOrCreateSessionRequest
            context: gRPC context
        
        Returns:
            Session object
        """
        session_id = request.session_id if request.session_id else None
        session = self.store.get_or_create(
            user_id=request.user_id,
            session_id=session_id
        )
        return session
