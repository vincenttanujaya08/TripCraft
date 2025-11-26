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
from data_sources.smart_retriever import SmartRetriever

logger = logging.getLogger(f"agent.Hotel")


class HotelAgent(BaseAgent):
    """Agent responsible for finding and recommending hotels"""
    
    def __init__(self, retriever: SmartRetriever):
        super().__init__("Hotel", retriever)
        
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
            # Calculate number of nights - FIX: Use date objects directly
            try:
                nights = (request.end_date - request.start_date).days
                self.logger.debug(f"Trip duration: {nights} nights")
            except Exception as e:
                self.logger.error(f"Failed to calculate nights: {e}")
                nights = 1
            
            # Retrieve hotels from data sources
            hotels_data = await self.retriever.get_hotels(
                city=request.destination,
                budget_per_night=request.budget / nights / request.travelers if nights > 0 else request.budget,
                accommodation_type=request.accommodation_type
            )
            
            if not hotels_data:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                self.logger.error(f"✗ Hotel failed after {duration:.0f}ms: No hotels found")
                
                # FIX: Return proper format with all required fields
                return HotelOutput(
                    hotels=[],
                    recommended_hotel=None,
                    total_accommodation_cost=0.0,
                    warnings=[f"No hotels found in {request.destination}"],
                    metadata=self._create_metadata("llm_fallback", 0),
                    data_source="llm_fallback",
                    confidence=0
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
                self.logger.error(f"✗ Hotel failed after {duration:.0f}ms: No valid hotels")
                
                return HotelOutput(
                    hotels=[],
                    recommended_hotel=None,
                    total_accommodation_cost=0.0,
                    warnings=[f"No valid hotels found in {request.destination}"],
                    metadata=self._create_metadata("llm_fallback", 0),
                    data_source="llm_fallback",
                    confidence=0
                )
            
            # Filter by accommodation type if specified
            if request.accommodation_type:
                filtered = [h for h in valid_hotels if h.type.lower() == request.accommodation_type.lower()]
                if filtered:
                    valid_hotels = filtered
            
            # Sort by rating and price
            valid_hotels.sort(key=lambda h: (h.rating, -h.price_per_night), reverse=True)
            
            # Select top hotels (max 5)
            selected_hotels = valid_hotels[:5]
            
            # Recommend the best one
            recommended = selected_hotels[0] if selected_hotels else None
            
            # FIX: Calculate total accommodation cost
            total_cost = nights * recommended.price_per_night if recommended else 0.0
            
            # Calculate confidence based on data quality
            data_source = hotels_data[0].get("_source", "seed") if hotels_data else "seed"
            confidence = self._calculate_confidence(
                source=data_source,
                data_quality_score=len(selected_hotels) * 20  # More hotels = higher confidence
            )
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.info(
                f"✓ Hotel completed in {duration:.0f}ms "
                f"(source: {data_source}, confidence: {confidence*100:.0f}%)"
            )
            
            return HotelOutput(
                hotels=[Hotel.model_validate(h.model_dump()) for h in selected_hotels],
                recommended_hotel=Hotel.model_validate(recommended.model_dump()) if recommended else None,
                total_accommodation_cost=total_cost,
                warnings=[],
                metadata=self._create_metadata(data_source, duration),
                data_source=data_source,
                confidence=confidence
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"✗ Hotel failed after {duration:.0f}ms: {e}")
            raise