"""
SessionStore - Conversation State Management

Manages conversation sessions with in-memory storage
(Can be extended to Redis/DB later)

Author: TripCraft Team
Date: 2024
"""

import logging
import uuid
from typing import Dict, Optional
from datetime import datetime
from backend.models.conversation_schemas import (
    ConversationSession,
    ConversationState
)

logger = logging.getLogger(__name__)


class SessionStore:
    """In-memory session storage"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        logger.info("SessionStore initialized")
    
    def create_session(self) -> ConversationSession:
        """Create new conversation session"""
        
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        
        session = ConversationSession(
            session_id=session_id,
            state=ConversationState.IDLE,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.sessions[session_id] = session
        
        logger.info(f"✅ Created session: {session_id}")
        
        return session
    
    async def get(self, session_id: str) -> Optional[ConversationSession]:
        """Get session by ID"""
        
        session = self.sessions.get(session_id)
        
        if session:
            logger.debug(f"Retrieved session: {session_id}")
        else:
            logger.warning(f"Session not found: {session_id}")
        
        return session
    
    async def save(self, session: ConversationSession):
        """Save/update session"""
        
        session.updated_at = datetime.now()
        self.sessions[session.session_id] = session
        
        logger.debug(f"Saved session: {session.session_id}")
    
    async def delete(self, session_id: str):
        """Delete session"""
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"🗑️  Deleted session: {session_id}")
        else:
            logger.warning(f"Cannot delete - session not found: {session_id}")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        return len(self.sessions)
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours"""
        
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        old_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.updated_at < cutoff_time:
                old_sessions.append(session_id)
        
        for session_id in old_sessions:
            del self.sessions[session_id]
        
        if old_sessions:
            logger.info(f"🗑️  Cleaned up {len(old_sessions)} old sessions")


# Singleton instance
_session_store = None

def get_session_store() -> SessionStore:
    """Get singleton SessionStore instance"""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store