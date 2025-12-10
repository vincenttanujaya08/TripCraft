"""
Conversation System Schemas
Pydantic models for conversational trip planning

Author: TripCraft Team
Date: 2024
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


# ============================================================================
# INTENT MODELS
# ============================================================================

class IntentType(str, Enum):
    """Types of user intents"""
    INITIAL_PLAN = "initial_plan"          # "Plan trip to Bali"
    MODIFY = "modify"                      # "Change hotel"
    APPLY = "apply"                        # "Apply changes"
    QUERY = "query"                        # "Show budget"
    FINALIZE = "finalize"                  # "Finalize plan"
    UNDO = "undo"                          # "Undo last change"
    REDO = "redo"                          # "Redo"
    SHOW_HISTORY = "show_history"          # "Show my changes"
    UNCLEAR = "unclear"                    # Couldn't parse


class ModificationAction(str, Enum):
    """Specific modification actions"""
    CHANGE_HOTEL = "change_hotel"
    CHANGE_FLIGHT = "change_flight"
    CHANGE_MEAL = "change_meal"
    ADD_ACTIVITY = "add_activity"
    REMOVE_ACTIVITY = "remove_activity"
    SWAP_DAYS = "swap_days"
    ADD_CUSTOM_ITEM = "add_custom_item"
    REGENERATE_COMPONENT = "regenerate_component"


class Intent(BaseModel):
    """Parsed user intent"""
    type: IntentType
    action: Optional[ModificationAction] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    raw_message: str


# ============================================================================
# MODIFICATION MODELS
# ============================================================================

class Modification(BaseModel):
    """Single modification to trip plan"""
    id: str
    action: ModificationAction
    params: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    description: str  # Human-readable description
    
    # Which agents need to re-run
    affected_agents: List[str] = Field(default_factory=list)


class ModificationResult(BaseModel):
    """Result of applying a modification"""
    success: bool
    modification: Modification
    message: str
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class QueueResult(BaseModel):
    """Result of queueing a modification"""
    success: bool
    message: str
    pending_count: int
    conflicts: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# ============================================================================
# IMAGE LOADING MODELS
# ============================================================================

class ImageStatus(str, Enum):
    """Image loading status"""
    PENDING = "pending"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"


class ImageLoadingState(BaseModel):
    """Track image loading for a single item"""
    item_id: str
    item_type: Literal["hotel", "restaurant", "attraction", "general"]
    status: ImageStatus
    url: Optional[str] = None
    error: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.now)


class ImageBatch(BaseModel):
    """Batch of images being loaded"""
    images: Dict[str, ImageLoadingState]
    total_count: int
    loaded_count: int
    failed_count: int


# ============================================================================
# CONVERSATION SESSION MODELS
# ============================================================================

class ConversationState(str, Enum):
    """Conversation state machine"""
    IDLE = "idle"                    # No active trip
    PLANNING = "planning"            # Generating initial plan
    REVIEWING = "reviewing"          # User reviewing plan
    MODIFYING = "modifying"          # User making changes
    APPLYING = "applying"            # Applying modifications
    FINALIZED = "finalized"          # Plan is final


class ConversationSession(BaseModel):
    """Single conversation session"""
    session_id: str
    state: ConversationState = ConversationState.IDLE
    
    # Trip data
    trip_plan: Optional[Any] = None  # TripPlan (avoid circular import)
    initial_request: Optional[Any] = None  # TripRequest
    
    # Modification tracking
    modification_queue: List[Modification] = Field(default_factory=list)
    modification_history: List[Modification] = Field(default_factory=list)
    history_index: int = -1  # For undo/redo
    
    # Image loading
    image_states: Dict[str, ImageLoadingState] = Field(default_factory=dict)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    message_count: int = 0
    
    def has_plan(self) -> bool:
        """Check if session has active trip plan"""
        return self.trip_plan is not None
    
    def has_pending_modifications(self) -> bool:
        """Check if there are queued modifications"""
        return len(self.modification_queue) > 0
    
    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return self.history_index > 0
    
    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return self.history_index < len(self.modification_history) - 1


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class ConversationResponse(BaseModel):
    """Response sent to user"""
    session_id: str
    message: str  # Natural language response
    state: ConversationState
    
    # Optional data
    trip_plan: Optional[Any] = None
    image_states: Optional[Dict[str, ImageLoadingState]] = None
    pending_modifications: Optional[List[str]] = None
    
    # UI hints
    suggested_actions: List[str] = Field(default_factory=list)
    requires_user_choice: bool = False
    choices: Optional[List[Dict[str, Any]]] = None
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    processing_time_ms: Optional[int] = None


class ActionResult(BaseModel):
    """Result of executing an action"""
    type: str  # Action type identifier
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    message: str
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


# ============================================================================
# CONFLICT DETECTION MODELS
# ============================================================================

class ConflictType(str, Enum):
    """Types of conflicts"""
    BUDGET_EXCEEDED = "budget_exceeded"
    IMPOSSIBLE_REQUEST = "impossible_request"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    DATA_UNAVAILABLE = "data_unavailable"


class Conflict(BaseModel):
    """Detected conflict in modification"""
    type: ConflictType
    severity: Literal["warning", "error", "critical"]
    message: str
    affected_modifications: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# ============================================================================
# PROACTIVE SUGGESTION MODELS
# ============================================================================

class SuggestionType(str, Enum):
    """Types of proactive suggestions"""
    BUDGET_OPTIMIZATION = "budget_optimization"
    LOW_CONFIDENCE_WARNING = "low_confidence_warning"
    PREFERENCE_MISMATCH = "preference_mismatch"
    BETTER_ALTERNATIVE = "better_alternative"


class ProactiveSuggestion(BaseModel):
    """System-generated suggestion"""
    type: SuggestionType
    priority: Literal["low", "medium", "high"]
    message: str
    actions: List[str] = Field(default_factory=list)
    estimated_impact: Optional[str] = None  # e.g., "Save Rp 1.5M"


# ============================================================================
# CUSTOM ITEM SEARCH MODELS
# ============================================================================

class CustomItemType(str, Enum):
    """Types of custom items user can add"""
    RESTAURANT = "restaurant"
    HOTEL = "hotel"
    ATTRACTION = "attraction"
    ACTIVITY = "activity"


class CustomItemSearchResult(BaseModel):
    """Result from searching custom item"""
    found: bool
    item_type: CustomItemType
    item_data: Optional[Dict[str, Any]] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    source: Literal["seed", "llm", "not_found"] = "not_found"
    message: str


# ============================================================================
# MODIFICATION QUEUE
# ============================================================================

class ModificationQueue(BaseModel):
    """Queue of pending modifications"""
    modifications: List[Modification] = Field(default_factory=list)
    
    def add(self, modification: Modification):
        """Add modification to queue"""
        self.modifications.append(modification)
    
    def clear(self):
        """Clear all modifications"""
        self.modifications.clear()
    
    def __len__(self) -> int:
        return len(self.modifications)
    
    def is_empty(self) -> bool:
        return len(self.modifications) == 0


# ============================================================================
# HISTORY TRACKING
# ============================================================================

class HistoryEntry(BaseModel):
    """Single entry in modification history"""
    modification: Modification
    plan_snapshot: Optional[Any] = None  # TripPlan snapshot
    timestamp: datetime = Field(default_factory=datetime.now)


class ModificationHistory(BaseModel):
    """Linear undo/redo history"""
    entries: List[HistoryEntry] = Field(default_factory=list)
    current_index: int = -1
    
    def push(self, modification: Modification, plan_snapshot: Any):
        """Add entry to history"""
        # Clear any "redo" history if user made new change
        self.entries = self.entries[:self.current_index + 1]
        
        entry = HistoryEntry(
            modification=modification,
            plan_snapshot=plan_snapshot
        )
        self.entries.append(entry)
        self.current_index += 1
    
    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return self.current_index > 0
    
    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return self.current_index < len(self.entries) - 1
    
    def undo(self) -> Optional[HistoryEntry]:
        """Go back one step"""
        if self.can_undo():
            self.current_index -= 1
            return self.entries[self.current_index]
        return None
    
    def redo(self) -> Optional[HistoryEntry]:
        """Go forward one step"""
        if self.can_redo():
            self.current_index += 1
            return self.entries[self.current_index]
        return None
    
    def get_history_summary(self) -> List[str]:
        """Get human-readable history"""
        return [
            f"{'→ ' if i == self.current_index else '  '}{entry.modification.description}"
            for i, entry in enumerate(self.entries)
        ]