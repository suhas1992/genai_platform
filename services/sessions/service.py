"""
Session Service - Business logic layer.

Implements the Session Service gRPC interface.
"""

import grpc
from proto import sessions_pb2, sessions_pb2_grpc
from services.shared.servicer_base import BaseServicer
from services.sessions.store import create_storage, SessionStorage


class SessionService(sessions_pb2_grpc.SessionServiceServicer, BaseServicer):
    """
    Implementation of Session Service.
    
    Handles gRPC requests for session management, messages, and memories.
    """
    
    def __init__(self, storage: SessionStorage = None):
        """
        Initialize Session Service.
        
        Args:
            storage: Storage backend. If None, creates from environment config.
        """
        self.storage = storage or create_storage()
    
    def add_to_server(self, server: grpc.Server):
        """Add this servicer to a gRPC server."""
        sessions_pb2_grpc.add_SessionServiceServicer_to_server(self, server)
    
    # Session management operations
    
    def GetOrCreateSession(self, request, context):
        """
        Get existing session or create a new one.
        
        Args:
            request: GetOrCreateSessionRequest
            context: gRPC context
        
        Returns:
            GetOrCreateSessionResponse
        """
        try:
            session_id = request.session_id if request.HasField('session_id') else None
            
            response = self.storage.get_or_create_session(
                user_id=request.user_id,
                session_id=session_id
            )
            
            return response
        
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get or create session: {str(e)}")
            return sessions_pb2.GetOrCreateSessionResponse()
    
    # Message operations
    
    def AddMessages(self, request, context):
        """
        Add messages to a session.
        
        Args:
            request: AddMessagesRequest
            context: gRPC context
        
        Returns:
            AddMessagesResponse
        """
        try:
            count = self.storage.add_messages(
                session_id=request.session_id,
                messages=list(request.messages)
            )
            
            return sessions_pb2.AddMessagesResponse(
                success=True,
                message_count=count
            )
        
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to add messages: {str(e)}")
            return sessions_pb2.AddMessagesResponse(success=False, message_count=0)
    
    def GetMessages(self, request, context):
        """
        Get messages from a session.
        
        Args:
            request: GetMessagesRequest
            context: gRPC context
        
        Returns:
            GetMessagesResponse
        """
        try:
            limit = request.limit if request.HasField('limit') else None
            offset = request.offset if request.HasField('offset') else None
            
            messages, total_count = self.storage.get_messages(
                session_id=request.session_id,
                limit=limit,
                offset=offset
            )
            
            return sessions_pb2.GetMessagesResponse(
                messages=messages,
                total_count=total_count
            )
        
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get messages: {str(e)}")
            return sessions_pb2.GetMessagesResponse(messages=[], total_count=0)
    
    def DeleteSession(self, request, context):
        """
        Delete a session and all its messages.
        
        Args:
            request: DeleteSessionRequest
            context: gRPC context
        
        Returns:
            DeleteSessionResponse
        """
        try:
            success = self.storage.delete_session(request.session_id)
            
            return sessions_pb2.DeleteSessionResponse(success=success)
        
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to delete session: {str(e)}")
            return sessions_pb2.DeleteSessionResponse(success=False)
    
    # Memory operations
    
    def SaveMemory(self, request, context):
        """
        Save a memory entry.
        
        Args:
            request: SaveMemoryRequest
            context: gRPC context
        
        Returns:
            SaveMemoryResponse
        """
        try:
            session_id = request.session_id if request.HasField('session_id') else None
            
            success = self.storage.save_memory(
                user_id=request.user_id,
                key=request.key,
                value=request.value,
                session_id=session_id
            )
            
            return sessions_pb2.SaveMemoryResponse(success=success)
        
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to save memory: {str(e)}")
            return sessions_pb2.SaveMemoryResponse(success=False)
    
    def GetMemory(self, request, context):
        """
        Get memory entries.
        
        Args:
            request: GetMemoryRequest
            context: gRPC context
        
        Returns:
            GetMemoryResponse
        """
        try:
            key = request.key if request.HasField('key') else None
            session_id = request.session_id if request.HasField('session_id') else None
            
            memories = self.storage.get_memory(
                user_id=request.user_id,
                key=key,
                session_id=session_id
            )
            
            # Convert dict values back to JSON strings for transport
            import json
            memories_json = {k: json.dumps(v) for k, v in memories.items()}
            
            return sessions_pb2.GetMemoryResponse(memories=memories_json)
        
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get memory: {str(e)}")
            return sessions_pb2.GetMemoryResponse(memories={})
    
    def DeleteMemory(self, request, context):
        """
        Delete a memory entry.
        
        Args:
            request: DeleteMemoryRequest
            context: gRPC context
        
        Returns:
            DeleteMemoryResponse
        """
        try:
            session_id = request.session_id if request.HasField('session_id') else None
            
            success = self.storage.delete_memory(
                user_id=request.user_id,
                key=request.key,
                session_id=session_id
            )
            
            return sessions_pb2.DeleteMemoryResponse(success=success)
        
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to delete memory: {str(e)}")
            return sessions_pb2.DeleteMemoryResponse(success=False)
    
    def ClearUserMemory(self, request, context):
        """
        Clear all memories for a user.
        
        Args:
            request: ClearUserMemoryRequest
            context: gRPC context
        
        Returns:
            ClearUserMemoryResponse
        """
        try:
            count = self.storage.clear_user_memory(request.user_id)
            
            return sessions_pb2.ClearUserMemoryResponse(count=count)
        
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to clear user memory: {str(e)}")
            return sessions_pb2.ClearUserMemoryResponse(count=0)
