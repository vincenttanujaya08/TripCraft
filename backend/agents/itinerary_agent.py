"""
ItineraryAgent - Generates day-by-day trip itinerary
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from models.schemas import (
    TripRequest, ItineraryOutput, DayItinerary, Activity,
    DestinationOutput, DiningOutput, HotelOutput
)


class ItineraryAgent(BaseAgent):
    """Agent that generates detailed day-by-day itinerary"""
    
    def __init__(self):
        super().__init__("Itinerary")
    
    async def execute(
        self, 
        request: TripRequest, 
        context: Optional[Dict] = None
    ) -> tuple[ItineraryOutput, Dict]:
        """
        Generate day-by-day itinerary from trip data
        
        Args:
            request: Trip request
            context: Shared context with previous agent outputs
            
        Returns:
            (ItineraryOutput, metadata)
        """
        
        warnings = []
        
        if not context:
            self._add_warning(
                warnings,
                "No context provided - cannot generate itinerary",
                "error"
            )
            return self._create_fallback_output(request, warnings)
        
        # Extract agent outputs
        destination_output: Optional[DestinationOutput] = context.get("destination_output")
        dining_output: Optional[DiningOutput] = context.get("dining_output")
        hotel_output: Optional[HotelOutput] = context.get("hotel_output")
        
        if not destination_output:
            self._add_warning(
                warnings,
                "Missing destination data",
                "error"
            )
        
        # Generate day-by-day itinerary
        days = self._generate_daily_itineraries(
            request,
            destination_output,
            dining_output,
            hotel_output,
            warnings
        )
        
        # Calculate total activities
        total_activities = sum(len(day.activities) for day in days)
        
        # Generate overview
        overview = f"A {request.duration_days}-day trip to {request.destination} with {total_activities} planned activities."
        
        # Create output
        output = ItineraryOutput(
            days=days,
            total_activities=total_activities,
            overview=overview,
            tips=["Wear comfortable shoes", "Stay hydrated", "Keep valuables secure"],
            warnings=warnings
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            data_source="seed",
            data_quality_score=100 if destination_output else 50
        )
        
        # Metadata
        metadata = {
            "data_source": "seed",
            "confidence": confidence,
            "warnings": warnings,
            "total_days": len(days),
            "total_activities": total_activities
        }
        
        return output, metadata
    
    def _generate_daily_itineraries(
        self,
        request: TripRequest,
        destination_output: Optional[DestinationOutput],
        dining_output: Optional[DiningOutput],
        hotel_output: Optional[HotelOutput],
        warnings: list
    ) -> List[DayItinerary]:
        """Generate itinerary for each day of the trip"""
        
        days = []
        
        # Get attractions and restaurants
        attractions = destination_output.attractions if destination_output else []
        restaurants = dining_output.restaurants if dining_output else []
        hotel = hotel_output.recommended_hotel if hotel_output else None
        
        # Generate itinerary for each day
        current_date = request.start_date
        day_num = 1
        attraction_index = 0
        
        while current_date <= request.end_date:
            # Generate activities for the day
            activities = []
            daily_cost = 0.0
            
            # Check-in (first day)
            if day_num == 1 and hotel:
                checkin_activity = Activity(
                    time="15:00",
                    name=f"Check-in: {hotel.name}",
                    type="hotel",
                    location=hotel.address or "Hotel",
                    description=f"Check-in to {hotel.type} accommodation",
                    duration_hours=0.5,
                    estimated_cost=0
                )
                activities.append(checkin_activity)
            
            # Morning activity (if available)
            if attraction_index < len(attractions):
                morning_activity = self._create_activity(
                    time="09:00",
                    activity_type="attraction",
                    attraction=attractions[attraction_index],
                    request=request
                )
                activities.append(morning_activity)
                daily_cost += self._parse_cost(attractions[attraction_index].entrance_fee) * request.travelers
                attraction_index += 1
            
            # Lunch
            if restaurants:
                lunch_spot = self._select_restaurant(restaurants, "lunch")
                if lunch_spot:
                    lunch_activity = self._create_restaurant_activity(
                        time="12:30",
                        meal_type="lunch",
                        restaurant=lunch_spot,
                        request=request
                    )
                    activities.append(lunch_activity)
                    daily_cost += lunch_spot.average_cost_per_person * request.travelers
            
            # Afternoon activity (if available)
            if attraction_index < len(attractions):
                afternoon_activity = self._create_activity(
                    time="14:30",
                    activity_type="attraction",
                    attraction=attractions[attraction_index],
                    request=request
                )
                activities.append(afternoon_activity)
                daily_cost += self._parse_cost(attractions[attraction_index].entrance_fee) * request.travelers
                attraction_index += 1
            
            # Dinner
            if restaurants:
                dinner_spot = self._select_restaurant(restaurants, "dinner")
                if dinner_spot:
                    dinner_activity = self._create_restaurant_activity(
                        time="19:00",
                        meal_type="dinner",
                        restaurant=dinner_spot,
                        request=request
                    )
                    activities.append(dinner_activity)
                    daily_cost += dinner_spot.average_cost_per_person * request.travelers
            
            # Create day title
            title = f"Day {day_num}: Explore {request.destination}"
            if day_num == 1:
                title = f"Day {day_num}: Arrival & Check-in"
            elif current_date == request.end_date:
                title = f"Day {day_num}: Final Day & Departure"
            
            # Create day notes
            notes = self._generate_day_notes(day_num, current_date, request, len(activities))
            
            # Create day itinerary
            day = DayItinerary(
                day_number=day_num,
                date=current_date,
                title=title,
                activities=activities,
                total_estimated_cost=daily_cost,
                notes=notes
            )
            
            days.append(day)
            
            # Move to next day
            current_date += timedelta(days=1)
            day_num += 1
        
        return days
    
    def _create_activity(
        self,
        time: str,
        activity_type: str,
        attraction: any,
        request: TripRequest
    ) -> Activity:
        """Create activity from attraction"""
        
        cost = self._parse_cost(attraction.entrance_fee) * request.travelers
        
        return Activity(
            time=time,
            type=activity_type,
            name=attraction.name,
            location=attraction.address or attraction.name,
            description=attraction.description,
            duration_hours=attraction.estimated_duration_hours,
            estimated_cost=cost
        )
    
    def _create_restaurant_activity(
        self,
        time: str,
        meal_type: str,
        restaurant: any,
        request: TripRequest
    ) -> Activity:
        """Create restaurant activity"""
        
        cost = restaurant.average_cost_per_person * request.travelers
        
        return Activity(
            time=time,
            type="dining",
            name=f"{meal_type.title()}: {restaurant.name}",
            location=restaurant.address or restaurant.name,
            duration_hours=1.5,
            estimated_cost=cost,
            description=f"{restaurant.cuisine} - {restaurant.description[:100]}"
        )
    
    def _select_restaurant(
        self,
        restaurants: List,
        meal_type: str
    ) -> Optional[any]:
        """Select restaurant suitable for meal type"""
        
        # Simple rotation through restaurants
        if restaurants:
            import random
            return random.choice(restaurants)
        
        return None
    
    def _parse_cost(self, cost: any) -> float:
        """Parse cost to float"""
        if cost is None:
            return 0.0
        
        if isinstance(cost, (int, float)):
            return float(cost)
        
        if isinstance(cost, str):
            cost_lower = cost.lower()
            
            if "free" in cost_lower:
                return 0.0
            
            # Extract number
            import re
            numbers = re.findall(r'\d+', cost)
            if numbers:
                return float(numbers[0])
        
        return 0.0
    
    def _generate_day_notes(
        self,
        day_num: int,
        date: datetime,
        request: TripRequest,
        activity_count: int
    ) -> str:
        """Generate notes for the day"""
        
        day_name = date.strftime("%A")
        pace = request.preferences.pace
        
        notes = []
        
        if day_num == 1:
            notes.append("First day - allow extra time for check-in and orientation")
        
        if pace == "relaxed" and activity_count > 3:
            notes.append("Consider removing an activity for a more relaxed pace")
        elif pace == "packed" and activity_count < 3:
            notes.append("You might have time for additional activities")
        
        notes.append(f"Enjoy your {day_name}")
        
        return ". ".join(notes)
    
    def _create_fallback_output(
        self, 
        request: TripRequest, 
        warnings: list
    ) -> tuple[ItineraryOutput, Dict]:
        """Create minimal fallback output"""
        
        output = ItineraryOutput(
            days=[],
            total_activities=0,
            overview="Unable to generate itinerary due to missing data",
            tips=[],
            warnings=warnings
        )
        
        metadata = {
            "data_source": "error",
            "confidence": 0,
            "warnings": warnings
        }
        
        return output, metadata