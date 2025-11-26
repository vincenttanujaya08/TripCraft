"""
Budget Agent - Handles budget planning and cost calculations
"""
import logging
from datetime import datetime
from typing import Dict, List
from models.schemas import (
    TripRequest, 
    BudgetOutput, 
    BudgetBreakdown,
    DestinationOutput,
    HotelOutput,
    DiningOutput,
    FlightOutput,
    
)
from agents.base_agent import BaseAgent
from data_sources.smart_retriever import SmartRetriever

logger = logging.getLogger(f"agent.Budget")


class BudgetAgent(BaseAgent):
    """Agent responsible for budget planning and cost calculations"""
    
    def __init__(self, retriever: SmartRetriever):
        super().__init__("Budget", retriever)
        
    async def execute(
        self,
        request: TripRequest,
        destination_output: DestinationOutput = None,
        hotel_output: HotelOutput = None,
        dining_output: DiningOutput = None,
        flight_output: FlightOutput = None
    ) -> BudgetOutput:
        """
        Calculate budget breakdown based on trip components
        
        Args:
            request: Trip planning request
            destination_output: Output from destination agent
            hotel_output: Output from hotel agent
            dining_output: Output from dining agent
            flight_output: Output from flight agent
            
        Returns:
            BudgetOutput with budget breakdown and analysis
        """
        self.logger.info("🚀 Budget agent starting...")
        start_time = datetime.now()
        
        try:
            # Initialize costs
            accommodation_cost = 0.0
            dining_cost = 0.0
            flight_cost = 0.0
            attraction_cost = 0.0
            
            # Extract accommodation costs
            if hotel_output and hotel_output.total_accommodation_cost:
                accommodation_cost = hotel_output.total_accommodation_cost
            
            # Extract dining costs
            if dining_output and dining_output.estimated_total_cost:
                dining_cost = dining_output.estimated_total_cost
            
            # Extract flight costs
            if flight_output and flight_output.total_flight_cost:
                flight_cost = flight_output.total_flight_cost
            
            # Calculate attraction costs - FIX: Use entrance_fee instead of estimated_cost
            if destination_output and destination_output.destination.attractions:
                for attraction in destination_output.destination.attractions:
                    if hasattr(attraction, 'entrance_fee') and attraction.entrance_fee:
                        attraction_cost += attraction.entrance_fee * request.travelers
            
            # Calculate transportation and miscellaneous (estimate 15% of total)
            subtotal = accommodation_cost + dining_cost + flight_cost + attraction_cost
            transportation_cost = subtotal * 0.10  # 10% for local transport
            miscellaneous_cost = subtotal * 0.05   # 5% for misc expenses
            
            # Total spending
            total_spent = (
                accommodation_cost + 
                dining_cost + 
                flight_cost + 
                attraction_cost + 
                transportation_cost + 
                miscellaneous_cost
            )
            
            # FIX: Calculate all required fields
            remaining = request.budget - total_spent
            is_over = total_spent > request.budget
            utilization = (total_spent / request.budget * 100) if request.budget > 0 else 0
            
            # Create breakdown
            breakdown = BudgetBreakdown(
                accommodation=accommodation_cost,
                dining=dining_cost,
                flights=flight_cost,
                attractions=attraction_cost,
                transportation=transportation_cost,
                miscellaneous=miscellaneous_cost
            )
            
            # Generate warnings if needed
            warnings = []
            if is_over:
                over_amount = total_spent - request.budget
                warnings.append(
                    f"Budget exceeded by Rp {over_amount:,.0f} "
                    f"({(over_amount/request.budget*100):.1f}%)"
                )
            elif utilization > 90:
                warnings.append(
                    f"Budget utilization is high ({utilization:.1f}%). "
                    f"Consider reducing costs or increasing budget."
                )
            
            # Calculate confidence based on data availability
            data_quality = 0
            if hotel_output and hotel_output.recommended_hotel:
                data_quality += 25
            if dining_output and dining_output.restaurants:
                data_quality += 25
            if flight_output and flight_output.recommended_outbound:
                data_quality += 25
            if destination_output and destination_output.destination.attractions:
                data_quality += 25
            
            confidence = self._calculate_confidence(
                source="seed",
                data_quality_score=data_quality
            )
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.info(
                f"✓ Budget completed in {duration:.0f}ms "
                f"(confidence: {confidence*100:.0f}%)"
            )
            
            # FIX: Return all required fields
            return BudgetOutput(
                breakdown=breakdown,
                total_budget=request.budget,
                remaining_budget=remaining,
                is_over_budget=is_over,
                budget_utilization_percent=utilization,
                warnings=warnings,
                metadata=self._create_metadata("seed", duration),
                data_source="seed",
                confidence=confidence
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"✗ Budget failed after {duration:.0f}ms: {e}")
            raise