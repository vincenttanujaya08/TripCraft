"""
TripOrchestrator - Master Coordinator for Budget-Aware Trip Planning

FIXED: Only FlightAgent needs retriever parameter
All other agents create their own dependencies internally

Responsibilities:
1. Sequential agent execution with context sharing
2. Budget allocation strategy (Phase 1: Auto-decide)
3. Error handling and recovery
4. Progress tracking for user feedback

Author: TripCraft Team
Date: 2024
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from backend.models.schemas import (
    TripRequest,
    DestinationOutput,
    FlightOutput,
    HotelOutput,
    DiningOutput,
    BudgetOutput,
    ItineraryOutput,
    VerificationOutput,
    TripPlan
)
from backend.agents.destination_agent import DestinationAgent
from backend.agents.flight_agent import FlightAgent
from backend.agents.hotel_agent import HotelAgent
from backend.agents.dining_agent import DiningAgent
from backend.agents.budget_agent import BudgetAgent
from backend.agents.itinerary_agent import ItineraryAgent
from backend.agents.verifier_agent import VerifierAgent

logger = logging.getLogger(__name__)


class BudgetAllocationStrategy:
    """
    Phase 1: Auto-decide budget allocation
    
    Standard allocation:
    - Flights: 35%
    - Hotels: 30%
    - Food: 20%
    - Activities: 10%
    - Miscellaneous: 5%
    """
    
    FLIGHT_PERCENTAGE = 0.35
    HOTEL_PERCENTAGE = 0.30
    FOOD_PERCENTAGE = 0.20
    ACTIVITIES_PERCENTAGE = 0.10
    MISC_PERCENTAGE = 0.05
    
    @classmethod
    def allocate(cls, total_budget: float) -> Dict[str, float]:
        """Allocate budget across categories"""
        return {
            'flight': total_budget * cls.FLIGHT_PERCENTAGE,
            'hotel': total_budget * cls.HOTEL_PERCENTAGE,
            'food': total_budget * cls.FOOD_PERCENTAGE,
            'activities': total_budget * cls.ACTIVITIES_PERCENTAGE,
            'misc': total_budget * cls.MISC_PERCENTAGE,
        }
    
    @classmethod
    def get_allocation_summary(cls, total_budget: float) -> str:
        """Get human-readable allocation summary"""
        allocation = cls.allocate(total_budget)
        return (
            f"Budget Allocation (Total: Rp {total_budget:,.0f}):\n"
            f"  • Flights: Rp {allocation['flight']:,.0f} ({cls.FLIGHT_PERCENTAGE*100:.0f}%)\n"
            f"  • Hotels: Rp {allocation['hotel']:,.0f} ({cls.HOTEL_PERCENTAGE*100:.0f}%)\n"
            f"  • Food: Rp {allocation['food']:,.0f} ({cls.FOOD_PERCENTAGE*100:.0f}%)\n"
            f"  • Activities: Rp {allocation['activities']:,.0f} ({cls.ACTIVITIES_PERCENTAGE*100:.0f}%)\n"
            f"  • Miscellaneous: Rp {allocation['misc']:,.0f} ({cls.MISC_PERCENTAGE*100:.0f}%)"
        )


class ExecutionProgress:
    """Track execution progress for user feedback"""
    
    def __init__(self):
        self.current_step: int = 0
        self.total_steps: int = 7
        self.current_agent: str = ""
        self.messages: List[str] = []
        
    def start_step(self, agent_name: str, step_num: int):
        """Mark start of agent execution"""
        self.current_step = step_num
        self.current_agent = agent_name
        msg = f"[{step_num}/{self.total_steps}] Starting {agent_name}..."
        self.messages.append(msg)
        logger.info(msg)
        
    def complete_step(self, agent_name: str, success: bool = True):
        """Mark completion of agent execution"""
        status = "✅" if success else "❌"
        msg = f"{status} {agent_name} completed"
        self.messages.append(msg)
        logger.info(msg)
        
    def add_message(self, message: str):
        """Add custom progress message"""
        self.messages.append(message)
        logger.info(message)
        
    def get_progress_percentage(self) -> float:
        """Get completion percentage"""
        return (self.current_step / self.total_steps) * 100


class TripOrchestrator:
    """
    Master coordinator for trip planning
    
    Orchestrates all agents in sequence with:
    - Budget allocation
    - Context sharing
    - Error handling
    - Progress tracking
    """
    
    def __init__(self):
        """
        Initialize orchestrator and all agents
        
        FIXED: Only FlightAgent needs retriever parameter
        """
        # Import here to avoid circular imports
        from backend.data_sources.smart_retriever import SmartRetriever
        
        # Create retriever for FlightAgent
        retriever = SmartRetriever()
        logger.info("Created SmartRetriever instance for FlightAgent")
        
        # Initialize all agents
        self.destination_agent = DestinationAgent()
        self.flight_agent = FlightAgent()  # ✅ Only one that needs it
        self.hotel_agent = HotelAgent()
        self.dining_agent = DiningAgent()
        self.budget_agent = BudgetAgent()
        self.itinerary_agent = ItineraryAgent()
        self.verifier_agent = VerifierAgent()  # ✅ No retriever needed
        
        self.progress = ExecutionProgress()
        
        logger.info("TripOrchestrator initialized with 7 agents")
    
    async def plan_trip(
        self,
        request: TripRequest,
        progress_callback: Optional[callable] = None
    ) -> Tuple[TripPlan, Dict[str, Any]]:
        """
        Main orchestration method - plans complete trip
        
        Args:
            request: Trip planning request
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (TripPlan, metadata)
            
        Raises:
            Exception: If critical agent fails
        """
        logger.info(f"Starting trip planning for {request.destination}")
        logger.info(f"Budget: Rp {request.budget:,.0f}, Days: {request.duration_days}")
        
        # Reset progress
        self.progress = ExecutionProgress()
        
        # Phase 1: Budget Allocation
        allocation = BudgetAllocationStrategy.allocate(request.budget)
        self.progress.add_message("💰 Budget allocated across categories")
        logger.info(BudgetAllocationStrategy.get_allocation_summary(request.budget))
        
        # Shared context for all agents
        context: Dict[str, Any] = {
            'request': request,
            'budget_allocation': allocation
        }
        
        # Metadata for debugging/monitoring
        metadata: Dict[str, Any] = {
            'orchestrator_version': '1.0',
            'execution_start': datetime.now().isoformat(),
            'budget_allocation': allocation,
            'agent_metadata': {}
        }
        
        try:
            # Step 1: Destination Agent
            destination_output = await self._execute_destination_agent(request, context)
            context['destination_output'] = destination_output
            
            # Step 2: Flight Agent (with budget constraint)
            flight_output = await self._execute_flight_agent(request, context, allocation['flight'])
            context['flight_output'] = flight_output
            
            # Step 3: Hotel Agent (with budget constraint)
            hotel_output = await self._execute_hotel_agent(request, context, allocation['hotel'])
            context['hotel_output'] = hotel_output
            
            # Step 4: Dining Agent
            dining_output = await self._execute_dining_agent(request, context)
            context['dining_output'] = dining_output
            
            # Step 5: Budget Agent (consolidates all costs)
            budget_output = await self._execute_budget_agent(request, context)
            context['budget_output'] = budget_output
            
            # Step 6: Itinerary Agent (uses meal_plan from dining)
            itinerary_output = await self._execute_itinerary_agent(request, context)
            context['itinerary_output'] = itinerary_output
            
            # Step 7: Verifier Agent (final validation)
            verification_output = await self._execute_verifier_agent(request, context)
            context['verification_output'] = verification_output
            
            # Build final TripPlan
            trip_plan = self._build_trip_plan(
                request,
                destination_output,
                flight_output,
                hotel_output,
                dining_output,
                budget_output,
                itinerary_output,
                verification_output
            )
            
            # Update metadata
            metadata['execution_end'] = datetime.now().isoformat()
            metadata['success'] = True
            metadata['progress_messages'] = self.progress.messages
            
            logger.info("✅ Trip planning completed successfully!")
            self.progress.add_message("🎉 Trip plan ready!")
            
            if progress_callback:
                progress_callback(self.progress)
            
            return trip_plan, metadata
            
        except Exception as e:
            logger.error(f"❌ Trip planning failed: {str(e)}")
            metadata['execution_end'] = datetime.now().isoformat()
            metadata['success'] = False
            metadata['error'] = str(e)
            metadata['progress_messages'] = self.progress.messages
            raise
    
    async def _execute_destination_agent(
        self,
        request: TripRequest,
        context: Dict[str, Any]
    ) -> DestinationOutput:
        """Execute DestinationAgent"""
        self.progress.start_step("DestinationAgent", 1)
        
        try:
            output, agent_metadata = await self.destination_agent.execute(request, context)
            
            self.progress.complete_step("DestinationAgent", success=True)
            self.progress.add_message(f"  → Found {len(output.attractions)} attractions")
            
            # Store metadata
            context['agent_metadata'] = context.get('agent_metadata', {})
            context['agent_metadata']['destination'] = agent_metadata
            
            return output
            
        except Exception as e:
            self.progress.complete_step("DestinationAgent", success=False)
            logger.error(f"DestinationAgent failed: {str(e)}")
            raise
    
    async def _execute_flight_agent(
        self,
        request: TripRequest,
        context: Dict[str, Any],
        max_budget: float
    ) -> FlightOutput:
        """Execute FlightAgent with budget constraint"""
        self.progress.start_step("FlightAgent", 2)
        
        try:
            # FlightAgent accepts max_budget parameter
            output = await self.flight_agent.execute(
                request,
                max_budget=max_budget
            )
            
            self.progress.complete_step("FlightAgent", success=True)
            self.progress.add_message(
                f"  → Budget: Rp {max_budget:,.0f}, Cost: Rp {output.total_flight_cost:,.0f}"
            )
            
            # Warnings if over budget
            if output.total_flight_cost > max_budget:
                over_pct = ((output.total_flight_cost - max_budget) / max_budget) * 100
                self.progress.add_message(
                    f"  ⚠️  Flights exceed budget by {over_pct:.1f}%"
                )
            
            context['agent_metadata']['flight'] = output.metadata
            return output
            
        except Exception as e:
            self.progress.complete_step("FlightAgent", success=False)
            logger.error(f"FlightAgent failed: {str(e)}")
            raise
    
    async def _execute_hotel_agent(
        self,
        request: TripRequest,
        context: Dict[str, Any],
        max_budget: float
    ) -> HotelOutput:
        """Execute HotelAgent with budget constraint"""
        self.progress.start_step("HotelAgent", 3)
        
        try:
            # HotelAgent accepts max_budget parameter
            output, agent_metadata = await self.hotel_agent.execute(
                request,
                max_budget=max_budget
            )
            
            self.progress.complete_step("HotelAgent", success=True)
            self.progress.add_message(
                f"  → Budget: Rp {max_budget:,.0f}, Cost: Rp {output.total_accommodation_cost:,.0f}"
            )
            
            # Warnings if over budget
            if output.total_accommodation_cost > max_budget:
                over_pct = ((output.total_accommodation_cost - max_budget) / max_budget) * 100
                self.progress.add_message(
                    f"  ⚠️  Hotel exceeds budget by {over_pct:.1f}%"
                )
            
            context['agent_metadata']['hotel'] = agent_metadata
            return output
            
        except Exception as e:
            self.progress.complete_step("HotelAgent", success=False)
            logger.error(f"HotelAgent failed: {str(e)}")
            raise
    
    async def _execute_dining_agent(
        self,
        request: TripRequest,
        context: Dict[str, Any]
    ) -> DiningOutput:
        """Execute DiningAgent"""
        self.progress.start_step("DiningAgent", 4)
        
        try:
            output, agent_metadata = await self.dining_agent.execute(request, context)
            
            self.progress.complete_step("DiningAgent", success=True)
            self.progress.add_message(
                f"  → {len(output.meal_plan)} day meal plan, Cost: Rp {output.estimated_total_cost:,.0f}"
            )
            
            context['agent_metadata']['dining'] = agent_metadata
            return output
            
        except Exception as e:
            self.progress.complete_step("DiningAgent", success=False)
            logger.error(f"DiningAgent failed: {str(e)}")
            raise
    
    async def _execute_budget_agent(
        self,
        request: TripRequest,
        context: Dict[str, Any]
    ) -> BudgetOutput:
        """Execute BudgetAgent"""
        self.progress.start_step("BudgetAgent", 5)
        
        try:
            output, agent_metadata = await self.budget_agent.execute(request, context)
            
            self.progress.complete_step("BudgetAgent", success=True)
            
            within_budget = "✅ Within" if output.is_within_budget else "⚠️  Over"
            self.progress.add_message(
                f"  → Total: Rp {output.breakdown.total:,.0f}, {within_budget} budget"
            )
            
            context['agent_metadata']['budget'] = agent_metadata
            return output
            
        except Exception as e:
            self.progress.complete_step("BudgetAgent", success=False)
            logger.error(f"BudgetAgent failed: {str(e)}")
            raise
    
    async def _execute_itinerary_agent(
        self,
        request: TripRequest,
        context: Dict[str, Any]
    ) -> ItineraryOutput:
        """Execute ItineraryAgent"""
        self.progress.start_step("ItineraryAgent", 6)
        
        try:
            output, agent_metadata = await self.itinerary_agent.execute(request, context)
            
            self.progress.complete_step("ItineraryAgent", success=True)
            
            total_activities = sum(len(day.activities) for day in output.days)
            self.progress.add_message(
                f"  → {len(output.days)} days, {total_activities} activities"
            )
            
            context['agent_metadata']['itinerary'] = agent_metadata
            return output
            
        except Exception as e:
            self.progress.complete_step("ItineraryAgent", success=False)
            logger.error(f"ItineraryAgent failed: {str(e)}")
            raise
    
    async def _execute_verifier_agent(
        self,
        request: TripRequest,
        context: Dict[str, Any]
    ) -> VerificationOutput:
        """Execute VerifierAgent"""
        self.progress.start_step("VerifierAgent", 7)
        
        try:
            output, agent_metadata = await self.verifier_agent.execute(request, context)
            
            self.progress.complete_step("VerifierAgent", success=True)
            
            status = "✅ Valid" if output.is_valid else "⚠️  Issues found"
            self.progress.add_message(f"  → {status}, Score: {output.quality_score:.1f}/100")
            
            context['agent_metadata']['verifier'] = agent_metadata
            return output
            
        except Exception as e:
            self.progress.complete_step("VerifierAgent", success=False)
            logger.error(f"VerifierAgent failed: {str(e)}")
            raise
    
    def _build_trip_plan(
        self,
        request: TripRequest,
        destination_output: DestinationOutput,
        flight_output: FlightOutput,
        hotel_output: HotelOutput,
        dining_output: DiningOutput,
        budget_output: BudgetOutput,
        itinerary_output: ItineraryOutput,
        verification_output: VerificationOutput
    ) -> TripPlan:
        """Build final TripPlan from all agent outputs"""
        
        # Collect all warnings
        all_warnings = []
        all_warnings.extend(destination_output.warnings)
        all_warnings.extend(flight_output.warnings)
        all_warnings.extend(hotel_output.warnings)
        all_warnings.extend(dining_output.warnings)
        all_warnings.extend(budget_output.warnings)
        all_warnings.extend(itinerary_output.warnings)
        
        # Calculate overall confidence (weighted average)
        weights = {
            'destination': 0.15,
            'flight': 0.20,
            'hotel': 0.20,
            'dining': 0.15,
            'budget': 0.10,
            'itinerary': 0.15,
            'verification': 0.05
        }
        
        overall_confidence = (
            destination_output.confidence * weights['destination'] +
            flight_output.confidence * weights['flight'] +
            hotel_output.confidence * weights['hotel'] +
            dining_output.confidence * weights['dining'] +
            budget_output.confidence * weights['budget'] +
            (verification_output.quality_score / 100) * weights['verification']
        )
        
        trip_plan = TripPlan(
            request=request,
            destination=destination_output,
            flights=flight_output,
            hotels=hotel_output,
            dining=dining_output,
            budget=budget_output,
            itinerary=itinerary_output,
            verification=verification_output,
            overall_confidence=overall_confidence,
            warnings=all_warnings
        )
        
        return trip_plan