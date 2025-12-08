"""
Session Store - Data layer for session management.

Handles session persistence and retrieval.
Currently in-memory, will be extended with database support.
"""

import time
from typing import Dict, Optional

from proto import sessions_pb2


class SessionStore:
    """Simple in-memory session storage."""
    
    def __init__(self):
        self._sessions: Dict[str, sessions_pb2.Session] = {}
    
    def get_or_create(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> sessions_pb2.Session:
        """
        Get existing session or create a new one.
        
        Args:
            user_id: User identifier
            session_id: Optional existing session ID
        
        Returns:
            Session object
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = f"session_{user_id}_{int(time.time())}"
        
        # Check if session exists
        if session_id in self._sessions:
            session = self._sessions[session_id]
            # Update timestamp
            session.updated_at = int(time.time())
            return session
        
        # Create new session
        now = int(time.time())
        session = sessions_pb2.Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now
        )
        self._sessions[session_id] = session
        return session
