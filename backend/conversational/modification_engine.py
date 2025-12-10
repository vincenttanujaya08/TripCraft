"""
ModificationEngine - Batch Modification Processor

Handles queueing and applying modifications to trip plans
with smart agent re-execution

Author: TripCraft Team
Date: 2024
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from backend.models.conversation_schemas import (
    Modification,
    ModificationAction,
    ModificationResult,
    QueueResult,
    Conflict,
    ConflictType,
    ModificationQueue,
    ModificationHistory
)
from backend.agents.hotel_agent import HotelAgent
from backend.agents.dining_agent import DiningAgent
from backend.agents.itinerary_agent import ItineraryAgent
from backend.agents.budget_agent import BudgetAgent
from backend.agents.destination_agent import DestinationAgent

logger = logging.getLogger(__name__)


class ModificationEngine:
    """
    Processes modifications to trip plans
    
    Features:
    - Queues modifications
    - Detects conflicts
    - Re-runs only affected agents
    - Maintains modification history
    """
    
    # Agent dependency graph
    AGENT_DEPENDENCIES = {
        "hotel": ["BudgetAgent", "ItineraryAgent"],
        "flight": ["BudgetAgent", "ItineraryAgent"],
        "meal": ["BudgetAgent", "ItineraryAgent"],
        "activity": ["ItineraryAgent", "BudgetAgent"],
        "destination": ["BudgetAgent", "ItineraryAgent"]
    }
    
    # Execution order (respects dependencies)
    AGENT_EXECUTION_ORDER = [
        "DestinationAgent",
        "FlightAgent",
        "HotelAgent",
        "DiningAgent",
        "BudgetAgent",
        "ItineraryAgent"
    ]
    
    def __init__(self):
        self.queue = ModificationQueue()
        self.history = ModificationHistory()
        
        # Initialize agents (will be reused)
        self.hotel_agent = HotelAgent()
        self.dining_agent = DiningAgent()
        self.itinerary_agent = ItineraryAgent()
        self.budget_agent = BudgetAgent()
        self.destination_agent = DestinationAgent()
        
        logger.info("✅ ModificationEngine initialized")
    
    def queue_modification(
        self,
        action: ModificationAction,
        params: Dict[str, Any],
        description: str,
        current_plan: Any
    ) -> QueueResult:
        """
        Add modification to queue
        
        Args:
            action: Modification action type
            params: Action parameters
            description: Human-readable description
            current_plan: Current TripPlan
            
        Returns:
            QueueResult with success status and conflicts
        """
        
        # Create modification
        modification = Modification(
            id=f"mod_{uuid.uuid4().hex[:8]}",
            action=action,
            params=params,
            description=description,
            affected_agents=self._determine_affected_agents(action)
        )
        
        # Detect conflicts
        conflicts = self._detect_conflicts(modification, current_plan)
        
        if conflicts:
            logger.warning(f"⚠️  Conflicts detected for modification: {description}")
            
            return QueueResult(
                success=False,
                message=f"Cannot apply: {conflicts[0].message}",
                pending_count=len(self.queue),
                conflicts=[c.message for c in conflicts],
                suggestions=[s for c in conflicts for s in c.suggestions]
            )
        
        # Add to queue
        self.queue.add(modification)
        
        logger.info(f"✅ Queued modification: {description} ({len(self.queue)} pending)")
        
        return QueueResult(
            success=True,
            message=f"✓ Queued: {description}",
            pending_count=len(self.queue),
            conflicts=[],
            suggestions=[]
        )
    
    async def apply_all(
        self,
        current_plan: Any,
        request: Any
    ) -> Tuple[Any, List[ModificationResult]]:
        """
        Apply all queued modifications
        
        Args:
            current_plan: Current TripPlan
            request: Original TripRequest
            
        Returns:
            (updated_plan, results)
        """
        
        if self.queue.is_empty():
            logger.warning("No modifications to apply")
            return current_plan, []
        
        logger.info(f"🔄 Applying {len(self.queue)} modifications...")
        
        # Group modifications by affected agents
        agent_groups = self._group_by_agents(self.queue.modifications)
        
        logger.info(f"📊 Affected agents: {list(agent_groups.keys())}")
        
        # Execute in optimal order
        updated_plan = current_plan
        results = []
        
        for agent_name in self.AGENT_EXECUTION_ORDER:
            if agent_name not in agent_groups:
                continue
            
            modifications = agent_groups[agent_name]
            
            logger.info(f"🔧 Re-running {agent_name} with {len(modifications)} modifications...")
            
            try:
                updated_plan = await self._run_agent(
                    agent_name,
                    modifications,
                    updated_plan,
                    request
                )
                
                # Record successful results
                for mod in modifications:
                    results.append(ModificationResult(
                        success=True,
                        modification=mod,
                        message=f"✅ Applied: {mod.description}",
                        errors=[],
                        warnings=[]
                    ))
                
            except Exception as e:
                logger.error(f"❌ Agent {agent_name} failed: {e}")
                
                # Record failures
                for mod in modifications:
                    results.append(ModificationResult(
                        success=False,
                        modification=mod,
                        message=f"❌ Failed: {mod.description}",
                        errors=[str(e)],
                        warnings=[]
                    ))
        
        # Save to history
        for mod in self.queue.modifications:
            self.history.push(mod, updated_plan)
        
        # Clear queue
        self.queue.clear()
        
        logger.info(f"✅ Applied {len(results)} modifications successfully")
        
        return updated_plan, results
    
    def _determine_affected_agents(self, action: ModificationAction) -> List[str]:
        """Determine which agents need to re-run"""
        
        action_to_category = {
            ModificationAction.CHANGE_HOTEL: "hotel",
            ModificationAction.CHANGE_FLIGHT: "flight",
            ModificationAction.CHANGE_MEAL: "meal",
            ModificationAction.ADD_ACTIVITY: "activity",
            ModificationAction.REMOVE_ACTIVITY: "activity",
            ModificationAction.ADD_CUSTOM_ITEM: "activity",
        }
        
        category = action_to_category.get(action)
        
        if not category:
            return ["BudgetAgent", "ItineraryAgent"]
        
        return self.AGENT_DEPENDENCIES.get(category, [])
    
    def _group_by_agents(
        self,
        modifications: List[Modification]
    ) -> Dict[str, List[Modification]]:
        """Group modifications by affected agents"""
        
        groups = {}
        
        for mod in modifications:
            for agent_name in mod.affected_agents:
                if agent_name not in groups:
                    groups[agent_name] = []
                groups[agent_name].append(mod)
        
        return groups
    
    async def _run_agent(
        self,
        agent_name: str,
        modifications: List[Modification],
        current_plan: Any,
        request: Any
    ) -> Any:
        """Re-run specific agent with modifications"""
        
        # Build context from current plan
        context = self._build_context(current_plan)
        
        if agent_name == "HotelAgent":
            # Extract constraints from modifications
            constraints = self._extract_hotel_constraints(modifications)
            
            # Re-run hotel agent
            new_output, metadata = await self.hotel_agent.execute(
                request=request,
                max_budget=constraints.get("max_budget"),
                context=context
            )
            
            # Update plan
            current_plan.hotels = new_output
        
        elif agent_name == "DiningAgent":
            # Extract meal modifications
            meal_changes = self._extract_meal_changes(modifications)
            
            # Re-run dining agent
            new_output, metadata = await self.dining_agent.execute(
                request=request,
                context=context
            )
            
            # Apply specific meal changes
            if meal_changes:
                new_output = self._apply_meal_changes(new_output, meal_changes)
            
            current_plan.dining = new_output
        
        elif agent_name == "ItineraryAgent":
            # Re-run itinerary agent
            new_output, metadata = await self.itinerary_agent.execute(
                request=request,
                context=context
            )
            
            current_plan.itinerary = new_output
        
        elif agent_name == "BudgetAgent":
            # Always re-run budget agent (depends on all others)
            new_output, metadata = await self.budget_agent.execute(
                request=request,
                context=context
            )
            
            current_plan.budget = new_output
        
        return current_plan
    
    def _build_context(self, trip_plan: Any) -> Dict[str, Any]:
        """Build context dict from trip plan"""
        
        return {
            "destination_output": trip_plan.destination,
            "hotel_output": trip_plan.hotels,
            "dining_output": trip_plan.dining,
            "flight_output": trip_plan.flights,
            "budget_output": trip_plan.budget,
            "itinerary_output": trip_plan.itinerary
        }
    
    def _extract_hotel_constraints(
        self,
        modifications: List[Modification]
    ) -> Dict[str, Any]:
        """Extract hotel constraints from modifications"""
        
        constraints = {}
        
        for mod in modifications:
            params = mod.params
            
            if "max_price" in params:
                constraints["max_budget"] = params["max_price"]
            
            if "constraint" in params and params["constraint"] == "cheaper":
                # Set max_budget to 80% of current
                if "current_price" in params:
                    constraints["max_budget"] = params["current_price"] * 0.8
        
        return constraints
    
    def _extract_meal_changes(
        self,
        modifications: List[Modification]
    ) -> List[Dict[str, Any]]:
        """Extract meal-specific changes"""
        
        meal_changes = []
        
        for mod in modifications:
            if mod.action == ModificationAction.CHANGE_MEAL:
                meal_changes.append(mod.params)
        
        return meal_changes
    
    def _apply_meal_changes(
        self,
        dining_output: Any,
        meal_changes: List[Dict[str, Any]]
    ) -> Any:
        """Apply specific meal changes to dining output"""
        
        # This is a simplified version
        # In real implementation, would search and replace specific meals
        
        for change in meal_changes:
            day = change.get("day")
            meal_type = change.get("meal")
            dietary = change.get("dietary")
            
            if day and meal_type and dining_output.meal_plan:
                # Find suitable restaurant with dietary constraint
                suitable = [
                    r for r in dining_output.restaurants
                    if dietary.lower() in r.cuisine.lower() or
                       dietary.lower() in str(r.dietary_options).lower()
                ]
                
                if suitable and day <= len(dining_output.meal_plan):
                    day_plan = dining_output.meal_plan[day - 1]
                    
                    if meal_type == "lunch":
                        day_plan.lunch = suitable[0]
                    elif meal_type == "dinner":
                        day_plan.dinner = suitable[0]
                    elif meal_type == "breakfast":
                        day_plan.breakfast = suitable[0]
        
        return dining_output
    
    def _detect_conflicts(
        self,
        modification: Modification,
        current_plan: Any
    ) -> List[Conflict]:
        """Detect conflicts in modification"""
        
        conflicts = []
        
        # Check budget conflicts
        if modification.action == ModificationAction.CHANGE_HOTEL:
            max_price = modification.params.get("max_price")
            
            if max_price and max_price < 100000:
                conflicts.append(Conflict(
                    type=ConflictType.IMPOSSIBLE_REQUEST,
                    severity="error",
                    message=f"No hotels available below Rp {max_price:,.0f}/night",
                    suggestions=[
                        "Increase max price to at least Rp 200,000",
                        "Consider different destination",
                        "Look for hostels/guesthouses"
                    ]
                ))
        
        # Check data availability
        if modification.action == ModificationAction.ADD_CUSTOM_ITEM:
            item_name = modification.params.get("item_name")
            if not item_name:
                conflicts.append(Conflict(
                    type=ConflictType.DATA_UNAVAILABLE,
                    severity="error",
                    message="Item name is required",
                    suggestions=["Specify the item name (e.g., 'Warung Bu Yanti')"]
                ))
        
        return conflicts
    
    def undo(self, current_plan: Any) -> Optional[Any]:
        """Undo last modification"""
        
        entry = self.history.undo()
        
        if entry:
            logger.info(f"⏪ Undo: {entry.modification.description}")
            return entry.plan_snapshot
        
        logger.warning("Cannot undo - no history")
        return None
    
    def redo(self, current_plan: Any) -> Optional[Any]:
        """Redo modification"""
        
        entry = self.history.redo()
        
        if entry:
            logger.info(f"⏩ Redo: {entry.modification.description}")
            return entry.plan_snapshot
        
        logger.warning("Cannot redo")
        return None
    
    def get_pending_summary(self) -> List[str]:
        """Get summary of pending modifications"""
        
        return [mod.description for mod in self.queue.modifications]
    
    def get_history_summary(self) -> List[str]:
        """Get summary of modification history"""
        
        return self.history.get_history_summary()


# Singleton instance
_modification_engine = None

def get_modification_engine() -> ModificationEngine:
    """Get singleton ModificationEngine instance"""
    global _modification_engine
    if _modification_engine is None:
        _modification_engine = ModificationEngine()
    return _modification_engine