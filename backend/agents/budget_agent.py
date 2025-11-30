"""
BudgetAgent - UPDATED to use meal_plan from DiningAgent
Calculates budget breakdown and validates against total budget
"""

from typing import Dict, Optional, List
from backend.agents.base_agent import BaseAgent
from backend.models.schemas import (
    TripRequest, BudgetOutput, BudgetBreakdown,
    HotelOutput, DiningOutput, FlightOutput, DestinationOutput
)


class BudgetAgent(BaseAgent):
    """Agent that calculates budget breakdown and provides recommendations"""
    
    def __init__(self):
        super().__init__("Budget")
    
    async def execute(
        self, 
        request: TripRequest, 
        context: Optional[Dict] = None
    ) -> tuple[BudgetOutput, Dict]:
        """
        Calculate budget breakdown from previous agent outputs
        
        UPDATED: Now uses meal_plan from DiningAgent for accurate food costs
        
        Args:
            request: Trip request
            context: Shared context with previous agent outputs (REQUIRED)
            
        Returns:
            (BudgetOutput, metadata)
        """
        
        warnings = []
        
        if not context:
            self._add_warning(
                warnings,
                "No context provided - cannot calculate budget",
                "error"
            )
            return self._create_fallback_output(request, warnings)
        
        # Extract agent outputs from context
        hotel_output: Optional[HotelOutput] = context.get("hotel_output")
        dining_output: Optional[DiningOutput] = context.get("dining_output")
        flight_output: Optional[FlightOutput] = context.get("flight_output")
        destination_output: Optional[DestinationOutput] = context.get("destination_output")
        
        # Calculate costs
        accommodation_cost = self._calculate_accommodation_cost(hotel_output)
        flights_cost = self._calculate_flights_cost(flight_output)
        
        # NEW: Use meal_plan from DiningAgent (more accurate!)
        food_cost = self._calculate_food_cost_from_meal_plan(dining_output, request)
        
        activities_cost = self._calculate_activities_cost(destination_output, request)
        local_transport_cost = self._estimate_local_transport(request)
        miscellaneous_cost = self._estimate_miscellaneous(request)
        
        # Total
        total_cost = (
            accommodation_cost + 
            flights_cost + 
            food_cost + 
            activities_cost + 
            local_transport_cost + 
            miscellaneous_cost
        )
        
        # Remaining budget
        remaining = request.budget - total_cost
        
        # Check if within budget
        is_within_budget = total_cost <= request.budget
        
        # Generate suggestions
        suggestions = self._generate_suggestions(
            request,
            total_cost,
            accommodation_cost,
            flights_cost,
            food_cost,
            activities_cost
        )
        
        # Add warnings
        if not is_within_budget:
            over_budget = total_cost - request.budget
            warnings.append(
                f"Total cost (Rp {total_cost:,.0f}) exceeds budget by Rp {over_budget:,.0f}"
            )
        elif remaining < request.budget * 0.1:
            warnings.append(
                f"Budget is tight - only Rp {remaining:,.0f} remaining"
            )
        
        # Create breakdown
        breakdown = BudgetBreakdown(
            accommodation=accommodation_cost,
            flights=flights_cost,
            food=food_cost,
            activities=activities_cost,
            transportation_local=local_transport_cost,
            miscellaneous=miscellaneous_cost,
            total=total_cost,
            remaining=remaining
        )
        
        # Calculate confidence (0-1 range, not 0-100)
        confidence_score = self._calculate_confidence(
            data_source="seed",  # Budget is calculated from other agents
            data_quality_score=100 if hotel_output and flight_output else 70
        )
        # Convert from 0-100 to 0-1
        confidence = confidence_score / 100.0
        
        # Create output
        output = BudgetOutput(
            breakdown=breakdown,
            is_within_budget=is_within_budget,
            suggestions=suggestions,
            warnings=warnings,
            data_source="seed",
            confidence=confidence
        )
        
        # Metadata
        metadata = {
            "data_source": "seed",
            "confidence": confidence,
            "warnings": warnings,
            "total_cost": total_cost,
            "budget_utilization": (total_cost / request.budget) * 100
        }
        
        return output, metadata
    
    def _calculate_accommodation_cost(self, hotel_output: Optional[HotelOutput]) -> float:
        """Calculate total accommodation cost"""
        if not hotel_output or not hotel_output.recommended_hotel:
            return 0.0
        return hotel_output.total_accommodation_cost
    
    def _calculate_flights_cost(self, flight_output: Optional[FlightOutput]) -> float:
        """Calculate total flights cost"""
        if not flight_output:
            return 0.0
        return flight_output.total_flight_cost
    
    def _calculate_food_cost_from_meal_plan(
        self, 
        dining_output: Optional[DiningOutput],
        request: TripRequest
    ) -> float:
        """
        Calculate total food cost from DiningAgent's meal_plan
        
        NEW: Uses actual meal_plan instead of estimates
        """
        if not dining_output:
            # Fallback to old method if no dining output
            return self._calculate_food_cost_fallback(request)
        
        # Use estimated_total_cost from DiningAgent (most accurate!)
        if hasattr(dining_output, 'estimated_total_cost') and dining_output.estimated_total_cost:
            self.logger.info(
                f"✓ Using meal_plan total cost: Rp {dining_output.estimated_total_cost:,.0f}"
            )
            return dining_output.estimated_total_cost
        
        # Fallback: sum daily costs from meal_plan
        if hasattr(dining_output, 'meal_plan') and dining_output.meal_plan:
            total = sum(day.daily_cost for day in dining_output.meal_plan)
            self.logger.info(
                f"✓ Calculated from meal_plan: Rp {total:,.0f}"
            )
            return total
        
        # Last resort: use estimated_daily_cost
        if hasattr(dining_output, 'estimated_daily_cost') and dining_output.estimated_daily_cost:
            from datetime import datetime
            try:
                start = datetime.strptime(str(request.start_date), "%Y-%m-%d")
                end = datetime.strptime(str(request.end_date), "%Y-%m-%d")
                days = (end - start).days + 1
            except:
                days = (request.end_date - request.start_date).days + 1
            
            total = dining_output.estimated_daily_cost * days
            self.logger.info(
                f"✓ Calculated from daily estimate: Rp {total:,.0f}"
            )
            return total
        
        # Ultimate fallback
        return self._calculate_food_cost_fallback(request)
    
    def _calculate_food_cost_fallback(self, request: TripRequest) -> float:
        """Fallback food cost calculation (when no DiningOutput)"""
        try:
            days = (request.end_date - request.start_date).days + 1
        except:
            days = 1
        
        # Estimate: Rp 200K per person per day
        daily_per_person = 200000
        total_cost = daily_per_person * days * request.travelers
        
        self.logger.warning(
            f"⚠️  Using fallback food estimate: Rp {total_cost:,.0f}"
        )
        
        return total_cost
    
    def _calculate_activities_cost(
        self,
        destination_output: Optional[DestinationOutput],
        request: TripRequest
    ) -> float:
        """Estimate activities/attractions cost"""
        if not destination_output or not destination_output.attractions:
            # Default estimate: Rp 50K per person per day
            try:
                days = (request.end_date - request.start_date).days + 1
            except:
                days = 1
            
            return 50000 * days * request.travelers
        
        # Sum attraction costs
        total_cost = 0.0
        for attraction in destination_output.attractions:
            # Parse cost (handle different formats)
            cost = attraction.entrance_fee
            
            if cost is None:
                cost = 0
            elif isinstance(cost, str):
                cost_str = cost.lower()
                if "free" in cost_str:
                    cost = 0
                else:
                    # Extract number from string
                    import re
                    numbers = re.findall(r'\d+', cost_str)
                    if numbers:
                        cost = float(numbers[0])
                    else:
                        cost = 20000  # Default estimate
            
            total_cost += float(cost)
        
        # Multiply by travelers
        return total_cost * request.travelers
    
    def _estimate_local_transport(self, request: TripRequest) -> float:
        """Estimate local transportation cost"""
        # Calculate days
        try:
            days = (request.end_date - request.start_date).days + 1
        except:
            days = 1
        
        # Estimate Rp 50K per person per day for local transport
        return 50000 * days * request.travelers
    
    def _estimate_miscellaneous(self, request: TripRequest) -> float:
        """Estimate miscellaneous expenses (shopping, tips, etc.)"""
        # Calculate days
        try:
            days = (request.end_date - request.start_date).days + 1
        except:
            days = 1
        
        # Estimate Rp 100K per person per day for misc
        return 100000 * days * request.travelers
    
    def _generate_suggestions(
        self,
        request: TripRequest,
        total_cost: float,
        accommodation_cost: float,
        flights_cost: float,
        food_cost: float,
        activities_cost: float
    ) -> List[str]:
        """Generate budget optimization suggestions"""
        
        suggestions = []
        over_budget = total_cost - request.budget
        
        if over_budget <= 0:
            suggestions.append(
                f"Your budget is well-planned with Rp {request.budget - total_cost:,.0f} remaining for flexibility"
            )
            return suggestions
        
        # Suggest cost reduction strategies
        suggestions.append(f"To fit within budget, consider reducing costs by Rp {over_budget:,.0f}")
        
        # Check which category is most expensive
        costs = {
            "accommodation": accommodation_cost,
            "flights": flights_cost,
            "food": food_cost,
            "activities": activities_cost
        }
        
        # Sort by cost
        sorted_costs = sorted(costs.items(), key=lambda x: x[1], reverse=True)
        
        # Suggest reducing top 2 categories
        for category, cost in sorted_costs[:2]:
            percentage = (cost / total_cost) * 100
            if percentage > 25:
                if category == "accommodation":
                    suggestions.append("Consider a more budget-friendly hotel or shorter stay")
                elif category == "flights":
                    suggestions.append("Look for cheaper flights or alternative dates")
                elif category == "food":
                    suggestions.append("Try more budget-friendly restaurants or reduce meals")
                elif category == "activities":
                    suggestions.append("Prioritize free/low-cost attractions")
        
        return suggestions
    
    def _create_fallback_output(
        self, 
        request: TripRequest, 
        warnings: list
    ) -> tuple[BudgetOutput, Dict]:
        """Create minimal fallback output"""
        
        breakdown = BudgetBreakdown(
            accommodation=0,
            flights=0,
            food=0,
            activities=0,
            transportation_local=0,
            miscellaneous=0,
            total=0,
            remaining=request.budget
        )
        
        output = BudgetOutput(
            breakdown=breakdown,
            is_within_budget=True,
            suggestions=["Unable to calculate budget - missing data from other agents"],
            warnings=warnings,
            data_source="error",
            confidence=0.0  # 0-1 range
        )
        
        metadata = {
            "data_source": "error",
            "confidence": 0.0,  # 0-1 range
            "warnings": warnings
        }
        
        return output, metadata