"""
Hotel Agent - Handles hotel search and recommendations
"""
import logging
from datetime import datetime
from typing import List, Optional
from models.schemas import (
    TripRequest, 
    HotelOutput, 
    Hotel
)
from agents.base_agent import BaseAgent

logger = logging.getLogger(f"agent.Hotel")


class HotelAgent(BaseAgent):
    """Agent responsible for finding and recommending hotels"""
    
    def __init__(self):
        """Initialize without retriever - uses seed data directly"""
        super().__init__("Hotel")
        
    async def execute(self, request: TripRequest) -> HotelOutput:
        """
        Find suitable hotels based on trip requirements
        
        Args:
            request: Trip planning request
            
        Returns:
            HotelOutput with hotel recommendations
        """
        self.logger.info("🚀 Hotel agent starting...")
        start_time = datetime.now()
        
        try:
            # Calculate number of nights
            try:
                nights = (request.end_date - request.start_date).days
                self.logger.debug(f"Trip duration: {nights} nights")
            except Exception as e:
                self.logger.error(f"Failed to calculate nights: {e}")
                nights = 1
            
            # Load hotels from seed data directly
            from data_sources.seed_loader import SeedLoader
            from pathlib import Path
            
            seed_dir = Path(__file__).parent.parent.parent / "seed_data"
            seed_loader = SeedLoader(seed_dir)
            
            # Get hotels for destination
            hotels_data = seed_loader.get_hotels(request.destination)
            
            if not hotels_data:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                self.logger.warning(f"No hotels found in seed data for {request.destination}")
                
                # Return empty result
                return HotelOutput(
                    hotels=[],
                    recommended_hotel=None,
                    total_accommodation_cost=0.0,
                    warnings=[f"No hotels found in {request.destination}"],
                    metadata=self._create_metadata("seed", duration),
                    data_source="seed",
                    confidence=0.0
                )
            
            # Parse hotels
            valid_hotels = []
            for hotel_data in hotels_data:
                try:
                    hotel = Hotel.model_validate(hotel_data)
                    valid_hotels.append(hotel)
                except Exception as e:
                    self.logger.warning(f"Failed to parse hotel: {e}")
                    continue
            
            if not valid_hotels:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                return HotelOutput(
                    hotels=[],
                    recommended_hotel=None,
                    total_accommodation_cost=0.0,
                    warnings=[f"No valid hotels found in {request.destination}"],
                    metadata=self._create_metadata("seed", duration),
                    data_source="seed",
                    confidence=0.0
                )
            
            # Filter by budget per night
            budget_per_night = request.budget / nights / request.travelers if nights > 0 else request.budget
            affordable_hotels = [h for h in valid_hotels if h.price_per_night <= budget_per_night * 1.5]
            
            # Use affordable hotels if available, otherwise use all
            if affordable_hotels:
                valid_hotels = affordable_hotels
            
            # Sort by rating and price
            valid_hotels.sort(key=lambda h: (h.rating, -h.price_per_night), reverse=True)
            
            # Select top hotels (max 5)
            selected_hotels = valid_hotels[:5]
            
            # Recommend the best one
            recommended = selected_hotels[0] if selected_hotels else None
            
            # Calculate total accommodation cost
            total_cost = nights * recommended.price_per_night if recommended else 0.0
            
            # Calculate confidence
            confidence = self._calculate_confidence(
                source="seed",
                data_quality_score=len(selected_hotels) * 20
            )
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.info(
                f"✓ Hotel completed in {duration:.0f}ms "
                f"(found {len(selected_hotels)} hotels, confidence: {confidence*100:.0f}%)"
            )
            
            return HotelOutput(
                hotels=selected_hotels,
                recommended_hotel=recommended,
                total_accommodation_cost=total_cost,
                warnings=[],
                metadata=self._create_metadata("seed", duration),
                data_source="seed",
                confidence=confidence
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"✗ Hotel failed after {duration:.0f}ms: {e}")
            raise