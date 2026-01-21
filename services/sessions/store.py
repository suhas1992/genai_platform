"""
Session Store - Data layer for session management.

Provides storage abstraction and PostgreSQL implementation for sessions,
messages, and model-managed memory.
"""

import json
import uuid
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

# Try to import psycopg (PostgreSQL driver) - optional dependency
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    # Fallback for backwards compatibility
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        PSYCOPG_AVAILABLE = True
        USING_PSYCOPG2 = True
    except ImportError:
        PSYCOPG_AVAILABLE = False
        USING_PSYCOPG2 = False
else:
    USING_PSYCOPG2 = False

from proto import sessions_pb2


class SessionStorage(ABC):
    """Abstract storage interface for session persistence."""
    
    @abstractmethod
    def get_or_create_session(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> sessions_pb2.GetOrCreateSessionResponse:
        """Retrieve existing session or create new one."""
        pass
    
    @abstractmethod
    def add_messages(
        self,
        session_id: str,
        messages: List[sessions_pb2.Message]
    ) -> int:
        """Append messages to session. Returns count added."""
        pass
    
    @abstractmethod
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[List[sessions_pb2.Message], int]:
        """Retrieve messages with pagination. Returns messages and total count."""
        pass
    
    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Remove session and all its messages. Returns success."""
        pass
    
    @abstractmethod
    def save_memory(
        self,
        user_id: str,
        key: str,
        value: Any,
        session_id: Optional[str] = None
    ) -> bool:
        """Save a fact to memory."""
        pass
    
    @abstractmethod
    def get_memory(
        self,
        user_id: str,
        key: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve memories for a user."""
        pass
    
    @abstractmethod
    def delete_memory(
        self,
        user_id: str,
        key: str,
        session_id: Optional[str] = None
    ) -> bool:
        """Remove a fact from memory. Returns True if key existed."""
        pass
    
    @abstractmethod
    def clear_user_memory(self, user_id: str) -> int:
        """Remove all memories for a user. Returns count deleted."""
        pass


class PostgresSessionStorage(SessionStorage):
    """PostgreSQL implementation of SessionStorage."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize PostgreSQL storage.
        
        Args:
            connection_string: PostgreSQL connection string.
                If not provided, uses environment variable DB_CONNECTION_STRING
                or defaults to localhost.
        
        Raises:
            ImportError: If psycopg is not installed
        """
        if not PSYCOPG_AVAILABLE:
            raise ImportError(
                "PostgreSQL support requires psycopg. Install with: "
                "pip install 'psycopg[binary]'"
            )
        
        if not connection_string:
            connection_string = os.getenv(
                "DB_CONNECTION_STRING",
                "postgresql://localhost/genai_platform"
            )
        
        self.connection_string = connection_string
        
        # Connect using psycopg3 or psycopg2
        if USING_PSYCOPG2:
            self.conn = psycopg2.connect(
                connection_string,
                cursor_factory=RealDictCursor
            )
        else:
            self.conn = psycopg.connect(
                connection_string,
                row_factory=dict_row
            )
        
        self._create_tables()
    
    def _create_tables(self):
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
            ON sessions(user_id)
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                content TEXT,
                tool_calls JSONB,
                tool_call_id VARCHAR(255),
                name VARCHAR(255),
                timestamp BIGINT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_id 
            ON messages(session_id)
        """)
        
        # Memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                user_id VARCHAR(255) NOT NULL,
                key VARCHAR(255) NOT NULL,
                value JSONB NOT NULL,
                session_id VARCHAR(255),
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL,
                PRIMARY KEY (user_id, key, COALESCE(session_id, ''))
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_user_id 
            ON memories(user_id)
        """)
        
        self.conn.commit()
    
    def get_or_create_session(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> sessions_pb2.GetOrCreateSessionResponse:
        """Get existing session or create new one."""
        cursor = self.conn.cursor()
        
        # If session_id provided, try to find it
        if session_id:
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = %s",
                (session_id,)
            )
            row = cursor.fetchone()
            if row:
                return sessions_pb2.GetOrCreateSessionResponse(
                    session_id=row['session_id'],
                    user_id=row['user_id'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
        
        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        now = int(datetime.utcnow().timestamp() * 1000)
        
        cursor.execute(
            """INSERT INTO sessions (session_id, user_id, created_at, updated_at)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (session_id) DO UPDATE 
               SET updated_at = EXCLUDED.updated_at
               RETURNING *""",
            (new_session_id, user_id, now, now)
        )
        
        self.conn.commit()
        row = cursor.fetchone()
        
        return sessions_pb2.GetOrCreateSessionResponse(
            session_id=row['session_id'],
            user_id=row['user_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def add_messages(
        self,
        session_id: str,
        messages: List[sessions_pb2.Message]
    ) -> int:
        """Add messages to a session."""
        cursor = self.conn.cursor()
        
        for message in messages:
            # Serialize tool_calls to JSON
            tool_calls_json = None
            if message.tool_calls:
                tool_calls_json = json.dumps([
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ])
            
            cursor.execute(
                """INSERT INTO messages
                   (session_id, role, content, tool_calls, tool_call_id, name, timestamp)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    session_id,
                    message.role,
                    message.content if message.HasField('content') else None,
                    tool_calls_json,
                    message.tool_call_id if message.HasField('tool_call_id') else None,
                    message.name if message.HasField('name') else None,
                    message.timestamp
                )
            )
        
        # Update session timestamp
        cursor.execute(
            "UPDATE sessions SET updated_at = %s WHERE session_id = %s",
            (int(datetime.utcnow().timestamp() * 1000), session_id)
        )
        
        self.conn.commit()
        return len(messages)
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[List[sessions_pb2.Message], int]:
        """Retrieve messages from a session."""
        cursor = self.conn.cursor()
        
        # Get total count
        cursor.execute(
            "SELECT COUNT(*) as count FROM messages WHERE session_id = %s",
            (session_id,)
        )
        total_count = cursor.fetchone()['count']
        
        # Build query with pagination
        query = "SELECT * FROM messages WHERE session_id = %s ORDER BY id"
        params = [session_id]
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        if offset:
            query += " OFFSET %s"
            params.append(offset)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to proto messages
        messages = []
        for row in rows:
            message = sessions_pb2.Message(
                role=row['role'],
                timestamp=row['timestamp']
            )
            
            if row['content']:
                message.content = row['content']
            
            if row['tool_call_id']:
                message.tool_call_id = row['tool_call_id']
            
            if row['name']:
                message.name = row['name']
            
            if row['tool_calls']:
                tool_calls_data = json.loads(row['tool_calls'])
                for tc_data in tool_calls_data:
                    tool_call = sessions_pb2.MessageToolCall(
                        id=tc_data['id'],
                        type=tc_data['type'],
                        function=sessions_pb2.MessageFunction(
                            name=tc_data['function']['name'],
                            arguments=tc_data['function']['arguments']
                        )
                    )
                    message.tool_calls.append(tool_call)
            
            messages.append(message)
        
        return messages, total_count
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        cursor = self.conn.cursor()
        
        cursor.execute(
            "DELETE FROM sessions WHERE session_id = %s",
            (session_id,)
        )
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def save_memory(
        self,
        user_id: str,
        key: str,
        value: Any,
        session_id: Optional[str] = None
    ) -> bool:
        """Save a memory entry."""
        cursor = self.conn.cursor()
        
        now = int(datetime.utcnow().timestamp() * 1000)
        value_json = json.dumps(value)
        
        cursor.execute(
            """INSERT INTO memories (user_id, key, value, session_id, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (user_id, key, COALESCE(session_id, ''))
               DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at""",
            (user_id, key, value_json, session_id, now, now)
        )
        
        self.conn.commit()
        return True
    
    def get_memory(
        self,
        user_id: str,
        key: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve memories for a user."""
        cursor = self.conn.cursor()
        
        query = "SELECT key, value FROM memories WHERE user_id = %s"
        params = [user_id]
        
        if key:
            query += " AND key = %s"
            params.append(key)
        
        if session_id:
            query += " AND session_id = %s"
            params.append(session_id)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return {row['key']: json.loads(row['value']) for row in rows}
    
    def delete_memory(
        self,
        user_id: str,
        key: str,
        session_id: Optional[str] = None
    ) -> bool:
        """Delete a memory entry."""
        cursor = self.conn.cursor()
        
        query = "DELETE FROM memories WHERE user_id = %s AND key = %s"
        params = [user_id, key]
        
        if session_id:
            query += " AND session_id = %s"
            params.append(session_id)
        else:
            query += " AND session_id IS NULL"
        
        cursor.execute(query, params)
        self.conn.commit()
        
        return cursor.rowcount > 0
    
    def clear_user_memory(self, user_id: str) -> int:
        """Clear all memories for a user."""
        cursor = self.conn.cursor()
        
        cursor.execute(
            "DELETE FROM memories WHERE user_id = %s",
            (user_id,)
        )
        
        self.conn.commit()
        return cursor.rowcount


# In-memory implementation for testing
class InMemorySessionStorage(SessionStorage):
    """In-memory implementation of SessionStorage for testing."""
    
    def __init__(self):
        self._sessions = {}
        self._messages = {}  # session_id -> list of messages
        self._memories = {}  # (user_id, key, session_id) -> value
    
    def get_or_create_session(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> sessions_pb2.GetOrCreateSessionResponse:
        """Get existing session or create new one."""
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            # Update timestamp
            now = int(datetime.utcnow().timestamp() * 1000)
            session['updated_at'] = now
            return sessions_pb2.GetOrCreateSessionResponse(**session)
        
        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        now = int(datetime.utcnow().timestamp() * 1000)
        
        session = {
            'session_id': new_session_id,
            'user_id': user_id,
            'created_at': now,
            'updated_at': now
        }
        
        self._sessions[new_session_id] = session
        self._messages[new_session_id] = []
        
        return sessions_pb2.GetOrCreateSessionResponse(**session)
    
    def add_messages(
        self,
        session_id: str,
        messages: List[sessions_pb2.Message]
    ) -> int:
        """Add messages to a session."""
        if session_id not in self._messages:
            self._messages[session_id] = []
        
        self._messages[session_id].extend(messages)
        
        # Update session timestamp
        if session_id in self._sessions:
            now = int(datetime.utcnow().timestamp() * 1000)
            self._sessions[session_id]['updated_at'] = now
        
        return len(messages)
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[List[sessions_pb2.Message], int]:
        """Retrieve messages from a session."""
        if session_id not in self._messages:
            return [], 0
        
        messages = self._messages[session_id]
        total_count = len(messages)
        
        # Apply pagination
        start = offset or 0
        end = start + limit if limit else None
        
        return messages[start:end], total_count
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if session_id in self._messages:
                del self._messages[session_id]
            return True
        return False
    
    def save_memory(
        self,
        user_id: str,
        key: str,
        value: Any,
        session_id: Optional[str] = None
    ) -> bool:
        """Save a memory entry."""
        memory_key = (user_id, key, session_id or '')
        self._memories[memory_key] = value
        return True
    
    def get_memory(
        self,
        user_id: str,
        key: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve memories for a user."""
        results = {}
        
        for (mem_user_id, mem_key, mem_session_id), value in self._memories.items():
            # Filter by user_id
            if mem_user_id != user_id:
                continue
            
            # Filter by key if provided
            if key and mem_key != key:
                continue
            
            # Filter by session_id if provided
            if session_id and mem_session_id != session_id:
                continue
            
            results[mem_key] = value
        
        return results
    
    def delete_memory(
        self,
        user_id: str,
        key: str,
        session_id: Optional[str] = None
    ) -> bool:
        """Delete a memory entry."""
        memory_key = (user_id, key, session_id or '')
        if memory_key in self._memories:
            del self._memories[memory_key]
            return True
        return False
    
    def clear_user_memory(self, user_id: str) -> int:
        """Clear all memories for a user."""
        to_delete = [
            k for k in self._memories.keys()
            if k[0] == user_id
        ]
        
        for key in to_delete:
            del self._memories[key]
        
        return len(to_delete)


# Factory function to create storage based on environment
def create_storage() -> SessionStorage:
    """
    Create storage instance based on environment configuration.
    
    Environment variables:
        SESSION_STORAGE: "memory" (default) or "postgres"
        DB_CONNECTION_STRING: PostgreSQL connection string (if using postgres)
    
    Returns:
        SessionStorage instance
    
    Examples:
        # Use in-memory storage (default, no dependencies)
        storage = create_storage()
        
        # Use PostgreSQL (requires psycopg)
        os.environ["SESSION_STORAGE"] = "postgres"
        os.environ["DB_CONNECTION_STRING"] = "postgresql://localhost/mydb"
        storage = create_storage()
    """
    storage_type = os.getenv("SESSION_STORAGE", "memory")
    
    if storage_type == "postgres":
        if not PSYCOPG_AVAILABLE:
            print("WARNING: PostgreSQL requested but psycopg not installed.")
            print("         Falling back to in-memory storage.")
            print("         Install with: pip install 'psycopg[binary]'")
            return InMemorySessionStorage()
        return PostgresSessionStorage()
    else:
        # Default to in-memory for development/testing
        return InMemorySessionStorage()
