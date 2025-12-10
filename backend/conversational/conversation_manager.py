"""
ConversationManager - Main Conversation Orchestrator

Coordinates all conversational components:
- Intent parsing
- Modification processing
- Response generation
- Session management
- Image fetching

Author: TripCraft Team
Date: 2024
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from backend.models.conversation_schemas import (
    ConversationResponse,
    ConversationState,
    IntentType,
    ModificationAction,
    ActionResult
)
from backend.models.schemas import TripRequest
from backend.orchestrator.trip_orchestrator import TripOrchestrator
from .intent_parser import get_intent_parser
from .modification_engine import get_modification_engine
from .response_generator import get_response_generator
from .image_fetcher import get_image_fetcher
from .session_store import get_session_store

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Main conversation orchestrator
    
    Handles all user interactions and coordinates components
    """
    
    def __init__(self):
        self.intent_parser = get_intent_parser()
        self.modification_engine = get_modification_engine()
        self.response_generator = get_response_generator()
        self.image_fetcher = get_image_fetcher()
        self.session_store = get_session_store()
        self.trip_orchestrator = TripOrchestrator()
        
        logger.info("✅ ConversationManager initialized")
    
    async def handle_message(
        self,
        session_id: str,
        message: str
    ) -> ConversationResponse:
        """
        Main entry point for all user messages
        
        Args:
            session_id: Conversation session ID
            message: User's message
            
        Returns:
            ConversationResponse with bot reply and data
        """
        
        start_time = datetime.now()
        
        logger.info(f"📩 [{session_id[:8]}] Received: '{message[:50]}...'")
        
        try:
            # Load session
            session = await self.session_store.get(session_id)
            
            if not session:
                # Create new session
                session = self.session_store.create_session()
                session_id = session.session_id
                logger.info(f"✨ Created new session: {session_id[:8]}")
            
            # Increment message count
            session.message_count += 1
            
            # Parse intent
            intent = await self.intent_parser.parse(message, session)
            
            logger.info(f"🎯 Intent: {intent.type.value} (confidence: {intent.confidence:.2f})")
            
            # Handle based on intent type
            if intent.type == IntentType.INITIAL_PLAN:
                response = await self._handle_initial_plan(intent, session)
            
            elif intent.type == IntentType.MODIFY:
                response = await self._handle_modification(intent, session)
            
            elif intent.type == IntentType.APPLY:
                response = await self._handle_apply(intent, session)
            
            elif intent.type == IntentType.QUERY:
                response = await self._handle_query(intent, session)
            
            elif intent.type == IntentType.FINALIZE:
                response = await self._handle_finalize(intent, session)
            
            elif intent.type == IntentType.UNDO:
                response = await self._handle_undo(intent, session)
            
            elif intent.type == IntentType.REDO:
                response = await self._handle_redo(intent, session)
            
            elif intent.type == IntentType.SHOW_HISTORY:
                response = await self._handle_show_history(intent, session)
            
            elif intent.type == IntentType.UNCLEAR:
                response = await self._handle_unclear(intent, session)
            
            else:
                response = await self._handle_unclear(intent, session)
            
            # Save session
            await self.session_store.save(session)
            
            # Add processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            response.processing_time_ms = int(processing_time)
            
            logger.info(
                f"✅ [{session_id[:8]}] Response generated in {processing_time:.0f}ms"
            )
            
            return response
        
        except Exception as e:
            logger.error(f"❌ [{session_id[:8]}] Error: {e}")
            import traceback
            traceback.print_exc()
            
            # Return error response
            return ConversationResponse(
                session_id=session_id,
                message=self.response_generator.format_error_response(str(e)),
                state=session.state if session else ConversationState.IDLE,
                suggested_actions=["Try again", "Type 'help' for assistance"]
            )
    
    async def _handle_initial_plan(self, intent, session) -> ConversationResponse:
        """Handle initial trip planning request"""
        
        logger.info("🗺️  Starting initial trip planning...")
        
        # Update state
        session.state = ConversationState.PLANNING
        
        # Extract parameters
        params = intent.params
        
        # Check if we have required params
        if "destination" not in params:
            return ConversationResponse(
                session_id=session.session_id,
                message="Untuk merencanakan trip, saya perlu tahu:\n• Destinasi\n• Tanggal mulai & akhir\n• Budget\n• Jumlah travelers\n\nContoh: 'Plan trip to Bali from 2025-07-15 to 2025-07-20, budget 15 million, 2 travelers'",
                state=session.state,
                suggested_actions=["Provide trip details"]
            )
        
        # Build TripRequest
        try:
            # Set defaults
            if "start_date" not in params:
                from datetime import timedelta
                params["start_date"] = (datetime.now() + timedelta(days=14)).date()
            
            if "end_date" not in params:
                from datetime import timedelta
                params["end_date"] = (datetime.now() + timedelta(days=18)).date()
            
            if "budget" not in params:
                params["budget"] = 15000000.0  # Default 15M
            
            if "travelers" not in params:
                params["travelers"] = 2
            
            # Create TripRequest
            from backend.models.schemas import TripPreferences
            
            trip_request = TripRequest(
                destination=params["destination"],
                origin=params.get("origin"),
                start_date=params["start_date"],
                end_date=params["end_date"],
                budget=params["budget"],
                travelers=params["travelers"],
                preferences=TripPreferences()
            )
            
            session.initial_request = trip_request
            
        except Exception as e:
            logger.error(f"Failed to build TripRequest: {e}")
            return ConversationResponse(
                session_id=session.session_id,
                message=f"Maaf, ada error dalam memproses request: {str(e)}\n\nTolong coba lagi dengan format yang jelas.",
                state=session.state,
                suggested_actions=["Try again"]
            )
        
        # Generate trip plan
        try:
            trip_plan, metadata = await self.trip_orchestrator.plan_trip(trip_request)
            
            session.trip_plan = trip_plan
            session.state = ConversationState.REVIEWING
            
            # Start fetching images in background
            image_states = await self.image_fetcher.fetch_all_images(trip_plan)
            session.image_states = image_states
            
            # Generate response
            message = self.response_generator.format_initial_plan_response(
                trip_plan,
                image_loading=True
            )
            
            return ConversationResponse(
                session_id=session.session_id,
                message=message,
                state=session.state,
                trip_plan=trip_plan,
                image_states=image_states,
                suggested_actions=[
                    "Show hotel options",
                    "Change something",
                    "Finalize plan"
                ]
            )
        
        except Exception as e:
            logger.error(f"Trip planning failed: {e}")
            session.state = ConversationState.IDLE
            
            return ConversationResponse(
                session_id=session.session_id,
                message=f"Maaf, gagal membuat trip plan: {str(e)}\n\nTolong coba lagi atau ubah parameter.",
                state=session.state,
                suggested_actions=["Try different destination", "Adjust budget"]
            )
    
    async def _handle_modification(self, intent, session) -> ConversationResponse:
        """Handle modification request"""
        
        if not session.has_plan():
            return ConversationResponse(
                session_id=session.session_id,
                message="Belum ada trip plan aktif. Silakan buat plan terlebih dahulu.\n\nContoh: 'Plan trip to Bali'",
                state=session.state,
                suggested_actions=["Create trip plan first"]
            )
        
        session.state = ConversationState.MODIFYING
        
        # Build modification description
        action = intent.action
        params = intent.params
        
        description = self._build_modification_description(action, params)
        
        # Queue modification
        result = self.modification_engine.queue_modification(
            action=action,
            params=params,
            description=description,
            current_plan=session.trip_plan
        )
        
        # Get queue summary
        queue_summary = self.modification_engine.get_pending_summary()
        
        # Generate response
        message = self.response_generator.format_modification_queued_response(
            result,
            queue_summary
        )
        
        return ConversationResponse(
            session_id=session.session_id,
            message=message,
            state=session.state,
            pending_modifications=queue_summary,
            suggested_actions=["Add more changes", "Apply changes", "Clear queue"]
        )
    
    async def _handle_apply(self, intent, session) -> ConversationResponse:
        """Handle apply modifications request"""
        
        if not session.has_pending_modifications():
            return ConversationResponse(
                session_id=session.session_id,
                message="Tidak ada perubahan pending untuk diterapkan.",
                state=session.state,
                suggested_actions=["Make changes first"]
            )
        
        session.state = ConversationState.APPLYING
        
        # Store old plan
        old_plan = session.trip_plan
        
        # Apply modifications
        updated_plan, results = await self.modification_engine.apply_all(
            current_plan=session.trip_plan,
            request=session.initial_request
        )
        
        session.trip_plan = updated_plan
        session.state = ConversationState.REVIEWING
        
        # Update images
        image_states = await self.image_fetcher.fetch_all_images(updated_plan)
        session.image_states = image_states
        
        # Generate response
        message = self.response_generator.format_modifications_applied_response(
            old_plan,
            updated_plan,
            results
        )
        
        return ConversationResponse(
            session_id=session.session_id,
            message=message,
            state=session.state,
            trip_plan=updated_plan,
            image_states=image_states,
            suggested_actions=["Make more changes", "Finalize", "Undo"]
        )
    
    async def _handle_query(self, intent, session) -> ConversationResponse:
        """Handle query/information request"""
        
        if not session.has_plan():
            return ConversationResponse(
                session_id=session.session_id,
                message="Belum ada trip plan untuk ditampilkan.",
                state=session.state,
                suggested_actions=["Create trip plan first"]
            )
        
        # Determine query type from params
        params = intent.params
        query_type = params.get("query_type", "budget")
        
        # Get relevant data
        if query_type == "budget":
            data = session.trip_plan.budget
        elif query_type == "itinerary":
            data = session.trip_plan.itinerary
        elif query_type == "hotel":
            data = session.trip_plan.hotels
        elif query_type == "restaurants":
            data = session.trip_plan.dining
        else:
            data = session.trip_plan
        
        # Generate response
        message = self.response_generator.format_query_response(query_type, data)
        
        return ConversationResponse(
            session_id=session.session_id,
            message=message,
            state=session.state,
            suggested_actions=["Show other details", "Make changes"]
        )
    
    async def _handle_finalize(self, intent, session) -> ConversationResponse:
        """Handle finalize request"""
        
        if not session.has_plan():
            return ConversationResponse(
                session_id=session.session_id,
                message="Tidak ada plan untuk difinalize.",
                state=session.state
            )
        
        session.state = ConversationState.FINALIZED
        
        message = f"""✅ **Trip plan finalized!**

Plan Anda sudah siap untuk digunakan.

**Next steps:**
• Download PDF itinerary
• Export to calendar
• Share dengan travel companions

Terima kasih telah menggunakan TripCraft! 🎉

Ingin plan trip lain? Ketik 'new trip'"""
        
        return ConversationResponse(
            session_id=session.session_id,
            message=message,
            state=session.state,
            trip_plan=session.trip_plan,
            suggested_actions=["Download PDF", "New trip"]
        )
    
    async def _handle_undo(self, intent, session) -> ConversationResponse:
        """Handle undo request"""
        
        previous_plan = self.modification_engine.undo(session.trip_plan)
        
        if previous_plan:
            session.trip_plan = previous_plan
            
            message = "⏪ **Undo successful!**\n\nPerubahan terakhir dibatalkan."
            suggested_actions = ["Make changes", "Redo", "Finalize"]
        else:
            message = "⚠️  Tidak ada yang bisa di-undo."
            suggested_actions = ["Make changes"]
        
        return ConversationResponse(
            session_id=session.session_id,
            message=message,
            state=session.state,
            trip_plan=session.trip_plan if previous_plan else None,
            suggested_actions=suggested_actions
        )
    
    async def _handle_redo(self, intent, session) -> ConversationResponse:
        """Handle redo request"""
        
        next_plan = self.modification_engine.redo(session.trip_plan)
        
        if next_plan:
            session.trip_plan = next_plan
            
            message = "⏩ **Redo successful!**\n\nPerubahan dikembalikan."
            suggested_actions = ["Make changes", "Undo", "Finalize"]
        else:
            message = "⚠️  Tidak ada yang bisa di-redo."
            suggested_actions = ["Make changes"]
        
        return ConversationResponse(
            session_id=session.session_id,
            message=message,
            state=session.state,
            trip_plan=session.trip_plan if next_plan else None,
            suggested_actions=suggested_actions
        )
    
    async def _handle_show_history(self, intent, session) -> ConversationResponse:
        """Handle show history request"""
        
        history = self.modification_engine.get_history_summary()
        
        if history:
            message = "📜 **Modification History:**\n\n"
            message += "\n".join(history)
        else:
            message = "Belum ada modification history."
        
        return ConversationResponse(
            session_id=session.session_id,
            message=message,
            state=session.state,
            suggested_actions=["Make changes", "Undo"]
        )
    
    async def _handle_unclear(self, intent, session) -> ConversationResponse:
        """Handle unclear intent"""
        
        if intent.raw_message.lower() in ["help", "bantuan", "?", "commands"]:
            message = self.response_generator.format_help_response()
        else:
            message = self.response_generator.format_unclear_intent_response(
                intent.raw_message
            )
        
        return ConversationResponse(
            session_id=session.session_id,
            message=message,
            state=session.state,
            suggested_actions=["Try again", "Type 'help'"]
        )
    
    def _build_modification_description(
        self,
        action: ModificationAction,
        params: Dict[str, Any]
    ) -> str:
        """Build human-readable modification description"""
        
        if action == ModificationAction.CHANGE_HOTEL:
            if "constraint" in params:
                return f"Change hotel (constraint: {params['constraint']})"
            elif "max_price" in params:
                return f"Change hotel (max price: Rp {params['max_price']:,.0f})"
            else:
                return "Change hotel"
        
        elif action == ModificationAction.CHANGE_MEAL:
            day = params.get("day", "?")
            meal = params.get("meal", "?")
            dietary = params.get("dietary", "")
            return f"Change Day {day} {meal} to {dietary}"
        
        elif action == ModificationAction.ADD_ACTIVITY:
            activity = params.get("activity_type", "activity")
            day = params.get("day", "")
            return f"Add {activity} activity" + (f" on Day {day}" if day else "")
        
        elif action == ModificationAction.REMOVE_ACTIVITY:
            activity = params.get("activity_name", "activity")
            return f"Remove {activity}"
        
        else:
            return f"{action.value}"


# Singleton instance
_conversation_manager = None

def get_conversation_manager() -> ConversationManager:
    """Get singleton ConversationManager instance"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager