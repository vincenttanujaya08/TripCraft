"""
Conversation API Router

Provides conversational trip planning endpoints

Author: TripCraft Team
Date: 2024
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.conversational import get_conversation_manager

router = APIRouter()

conversation_manager = get_conversation_manager()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ChatMessage(BaseModel):
    """Chat message from user"""
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    """Chat response to user"""
    session_id: str
    message: str
    state: str
    trip_plan: Optional[Any] = None
    image_states: Optional[Dict[str, Any]] = None
    pending_modifications: Optional[list] = None
    suggested_actions: list = []
    processing_time_ms: Optional[int] = None


class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    state: str
    has_plan: bool
    pending_modifications: int
    message_count: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatMessage):
    """
    Main chat endpoint
    
    User sends message, bot responds with natural language + data
    """
    
    try:
        # Get or create session ID
        session_id = request.session_id or "new"
        
        # Handle message
        response = await conversation_manager.handle_message(
            session_id=session_id,
            message=request.message
        )
        
        # Convert to response model
        return ChatResponse(
            session_id=response.session_id,
            message=response.message,
            state=response.state.value,
            trip_plan=response.trip_plan,
            image_states=response.image_states,
            pending_modifications=response.pending_modifications,
            suggested_actions=response.suggested_actions,
            processing_time_ms=response.processing_time_ms
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """Get information about a session"""
    
    from backend.conversational import get_session_store
    
    session_store = get_session_store()
    session = await session_store.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionInfo(
        session_id=session.session_id,
        state=session.state.value,
        has_plan=session.has_plan(),
        pending_modifications=len(session.modification_queue),
        message_count=session.message_count
    )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    
    from backend.conversational import get_session_store
    
    session_store = get_session_store()
    await session_store.delete(session_id)
    
    return {"message": "Session deleted successfully"}


@router.get("/images/{session_id}")
async def get_image_states(session_id: str):
    """Get current image loading states for a session"""
    
    from backend.conversational import get_session_store
    
    session_store = get_session_store()
    session = await session_store.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "images": session.image_states
    }


@router.get("/health")
async def health_check():
    """Health check for conversation system"""
    
    return {
        "status": "healthy",
        "conversation_manager": "active",
        "components": {
            "intent_parser": "ready",
            "modification_engine": "ready",
            "response_generator": "ready",
            "image_fetcher": "ready",
            "session_store": "ready"
        }
    }