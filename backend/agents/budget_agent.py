"""
BudgetAgent - Calculates budget breakdown and validates against total budget
"""

from typing import Dict, Optional, List
from .base_agent import BaseAgent
from models.schemas import (
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
        food_cost = self._calculate_food_cost(dining_output, request)
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
            self._add_warning(
                warnings,
                f"Total cost (${total_cost:.0f}) exceeds budget by ${over_budget:.0f}",
                "error"
            )
        elif remaining < request.budget * 0.1:
            self._add_warning(
                warnings,
                f"Budget is tight - only ${remaining:.0f} remaining",
                "warning"
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
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            data_source="seed",  # Budget is calculated from other agents
            data_quality_score=100 if hotel_output and flight_output else 70
        )
        
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
        return hotel_output.recommended_hotel.total_price
    
    def _calculate_flights_cost(self, flight_output: Optional[FlightOutput]) -> float:
        """Calculate total flights cost"""
        if not flight_output:
            return 0.0
        return flight_output.total_flight_cost
    
    def _calculate_food_cost(
        self, 
        dining_output: Optional[DiningOutput],
        request: TripRequest
    ) -> float:
        """Calculate total food cost"""
        if not dining_output:
            return 0.0
        
        # Calculate days
        from datetime import datetime
        try:
            start = datetime.strptime(request.start_date, "%Y-%m-%d")
            end = datetime.strptime(request.end_date, "%Y-%m-%d")
            days = (end - start).days + 1
        except:
            days = 1
        
        daily_cost = dining_output.estimated_daily_food_cost
        total_cost = daily_cost * days * request.travelers
        
        return total_cost
    
    def _calculate_activities_cost(
        self,
        destination_output: Optional[DestinationOutput],
        request: TripRequest
    ) -> float:
        """Estimate activities/attractions cost"""
        if not destination_output or not destination_output.attractions:
            # Default estimate: $50 per person per day
            from datetime import datetime
            try:
                start = datetime.strptime(request.start_date, "%Y-%m-%d")
                end = datetime.strptime(request.end_date, "%Y-%m-%d")
                days = (end - start).days + 1
            except:
                days = 1
            
            return 50 * days * request.travelers
        
        # Sum attraction costs
        total_cost = 0.0
        for attraction in destination_output.attractions:
            # Parse cost (handle different formats)
            cost_str = attraction.estimated_cost.lower()
            
            if "free" in cost_str:
                cost = 0
            else:
                # Extract number from string
                import re
                numbers = re.findall(r'\d+', cost_str)
                if numbers:
                    cost = float(numbers[0])
                else:
                    cost = 20  # Default estimate
            
            total_cost += cost
        
        # Multiply by travelers
        return total_cost * request.travelers
    
    def _estimate_local_transport(self, request: TripRequest) -> float:
        """Estimate local transportation cost"""
        # Calculate days
        from datetime import datetime
        try:
            start = datetime.strptime(request.start_date, "%Y-%m-%d")
            end = datetime.strptime(request.end_date, "%Y-%m-%d")
            days = (end - start).days + 1
        except:
            days = 1
        
        # Estimate $20 per person per day for local transport
        return 20 * days * request.travelers
    
    def _estimate_miscellaneous(self, request: TripRequest) -> float:
        """Estimate miscellaneous expenses (shopping, tips, etc.)"""
        # Calculate days
        from datetime import datetime
        try:
            start = datetime.strptime(request.start_date, "%Y-%m-%d")
            end = datetime.strptime(request.end_date, "%Y-%m-%d")
            days = (end - start).days + 1
        except:
            days = 1
        
        # Estimate $30 per person per day for misc
        return 30 * days * request.travelers
    
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
            suggestions.append(f"Your budget is well-planned with ${request.budget - total_cost:.0f} remaining for flexibility")
            return suggestions
        
        # Suggest cost reduction strategies
        suggestions.append(f"To fit within budget, consider reducing costs by ${over_budget:.0f}")
        
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
            if percentage > 30:
                if category == "accommodation":
                    suggestions.append("Consider a more budget-friendly hotel or shorter stay")
                elif category == "flights":
                    suggestions.append("Look for cheaper flights or alternative dates")
                elif category == "food":
                    suggestions.append("Try more budget-friendly restaurants or cook some meals")
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
            confidence=0
        )
        
        metadata = {
            "data_source": "error",
            "confidence": 0,
            "warnings": warnings
        }
        
        return output, metadata
