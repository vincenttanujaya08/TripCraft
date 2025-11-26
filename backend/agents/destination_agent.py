"""
DestinationAgent - Researches destination info and attractions
"""

from typing import Dict, Optional
from .base_agent import BaseAgent
from models.schemas import TripRequest, DestinationOutput, DestinationInfo, Attraction
from data_sources import get_smart_retriever


class DestinationAgent(BaseAgent):
    """Agent that researches destination information and attractions"""
    
    def __init__(self):
        super().__init__("Destination")
        self.retriever = get_smart_retriever()
    
    async def execute(
        self, 
        request: TripRequest, 
        context: Optional[Dict] = None
    ) -> tuple[DestinationOutput, Dict]:
        """
        Research destination and attractions
        
        Args:
            request: Trip request
            context: Shared context (unused for this agent)
            
        Returns:
            (DestinationOutput, metadata)
        """
        
        warnings = []
        
        # Get destination info
        dest_data, dest_source = await self.retriever.get_destination(request.destination)
        
        if not dest_data:
            self._add_warning(
                warnings,
                f"Could not find information for {request.destination}",
                "error"
            )
            # Return minimal output
            return self._create_fallback_output(request.destination, warnings)
        
        # Parse destination info - FIX: use 'name' field from JSON
        dest_info = DestinationInfo(
            name=dest_data.get("name") or dest_data.get("city", request.destination),
            country=dest_data.get("country", "Unknown"),
            description=dest_data.get("description", ""),
            best_time_to_visit=dest_data.get("best_time_to_visit", "Year-round"),
            local_currency=dest_data.get("local_currency", "USD"),
            timezone=dest_data.get("timezone", "UTC"),
            language=dest_data.get("language", "English"),
            safety_tips=dest_data.get("safety_tips", [])
        )
        
        # Get attractions
        attractions_data = dest_data.get("attractions", [])
        
        if not attractions_data:
            self._add_warning(
                warnings,
                "No attractions found in destination data",
                "warning"
            )
        
        # Parse attractions
        attractions = []
        for attr_data in attractions_data[:10]:  # Limit to 10
            try:
                attraction = Attraction(
                    name=attr_data.get("name", "Unknown"),
                    type=attr_data.get("type", "attraction"),
                    description=attr_data.get("description", ""),
                    estimated_duration_hours=attr_data.get("estimated_duration_hours", 2.0),
                    entrance_fee=attr_data.get("entrance_fee", 0.0),
                    address=attr_data.get("address") or attr_data.get("location"),
                    opening_hours=attr_data.get("opening_hours")
                )
                attractions.append(attraction)
            except Exception as e:
                self.logger.warning(f"Failed to parse attraction: {e}")
        
        # Get local tips
        local_tips = dest_data.get("local_tips", [])
        
        if not local_tips:
            local_tips = [
                f"Research {dest_info.name} before your trip",
                "Check visa requirements",
                "Learn basic local phrases"
            ]
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            data_source=dest_source,
            data_quality_score=100 if attractions else 70
        )
        
        # Create output
        output = DestinationOutput(
            destination=dest_info,
            attractions=attractions,
            local_tips=local_tips,
            warnings=warnings,
            data_source=dest_source,
            confidence=confidence
        )
        
        # Metadata
        metadata = {
            "data_source": dest_source,
            "confidence": confidence,
            "warnings": warnings,
            "attractions_count": len(attractions)
        }
        
        return output, metadata
    
    def _create_fallback_output(
        self, 
        destination: str, 
        warnings: list
    ) -> tuple[DestinationOutput, Dict]:
        """Create minimal fallback output when destination not found"""
        
        dest_info = DestinationInfo(
            name=destination,
            country="Unknown",
            description=f"Information for {destination} is not available",
            local_currency="USD"
        )
        
        output = DestinationOutput(
            destination=dest_info,
            attractions=[],
            local_tips=[],
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