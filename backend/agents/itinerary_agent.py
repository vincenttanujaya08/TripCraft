"""
ItineraryAgent - UPDATED to respect Flight Arrival Time
Generates day-by-day trip itinerary with specific restaurant assignments
and awareness of travel times.
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from backend.agents.base_agent import BaseAgent
from backend.models.schemas import (
    TripRequest, ItineraryOutput, DayItinerary, Activity,
    DestinationOutput, DiningOutput, HotelOutput, FlightOutput
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
        flight_output: Optional[FlightOutput] = context.get("flight_output")  # <--- NEW: Get flight data
        
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
            flight_output,  # <--- NEW: Pass flight data
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
        
        # Calculate confidence (0-1 range, not 0-100)
        confidence_score = self._calculate_confidence(
            data_source="seed",
            data_quality_score=100 if destination_output else 50
        )
        # Convert from 0-100 to 0-1
        confidence = confidence_score / 100.0
        
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
        flight_output: Optional[FlightOutput],  # <--- NEW Argument
        warnings: list
    ) -> List[DayItinerary]:
        """
        Generate itinerary for each day of the trip
        Respects flight arrival times to avoid scheduling activities during travel.
        """
        
        days = []
        
        # Get resources
        attractions = destination_output.attractions if destination_output else []
        hotel = hotel_output.recommended_hotel if hotel_output else None
        meal_plan = dining_output.meal_plan if dining_output else []
        
        # NEW: Determine arrival time logic
        arrival_dt = None
        start_tracking_activities = True 
        
        if flight_output and flight_output.recommended_outbound:
            # Get arrival time from flight agent (remove timezone info for simple comparison)
            raw_arrival = flight_output.recommended_outbound.arrival_time
            if raw_arrival:
                arrival_dt = raw_arrival.replace(tzinfo=None)
                self.logger.info(f"🛬 Flight arrives at: {arrival_dt}")
                start_tracking_activities = False # Don't start activities until we land
        else:
            # If no flight info, assume we arrive at 10 AM on start date
            arrival_dt = datetime.combine(request.start_date, datetime.min.time().replace(hour=10))
        
        self.logger.info(
            f"📅 Generating itinerary with {len(meal_plan)} days of meal plans"
        )
        
        # Generate itinerary loop
        current_date = request.start_date
        day_num = 1
        attraction_index = 0
        has_checked_in = False
        
        while current_date <= request.end_date:
            # Get meal plan for this day
            day_meals = next((m for m in meal_plan if m.day == day_num), None)
            
            activities = []
            daily_cost = 0.0
            
            # --- DEFINE SLOT TIMES ---
            morning_slot = datetime.combine(current_date, datetime.min.time().replace(hour=9, minute=0))
            lunch_slot = datetime.combine(current_date, datetime.min.time().replace(hour=12, minute=30))
            afternoon_slot = datetime.combine(current_date, datetime.min.time().replace(hour=14, minute=30))
            dinner_slot = datetime.combine(current_date, datetime.min.time().replace(hour=19, minute=0))
            
            # --- 1. MORNING ACTIVITY (09:00) ---
            if morning_slot >= arrival_dt:
                if attraction_index < len(attractions):
                    morning_activity = self._create_activity(
                        time="09:00",
                        activity_type="attraction",
                        attraction=attractions[attraction_index],
                        request=request
                    )
                    activities.append(morning_activity)
                    daily_cost += morning_activity.estimated_cost
                    attraction_index += 1
            
            # --- 2. LUNCH (12:30) ---
            if lunch_slot >= arrival_dt:
                if day_meals and day_meals.lunch:
                    lunch_activity = self._create_meal_activity(
                        time="12:30",
                        meal_type="lunch",
                        restaurant=day_meals.lunch,
                        request=request
                    )
                    activities.append(lunch_activity)
                    daily_cost += lunch_activity.estimated_cost
                elif day_meals and day_meals.breakfast_notes and not activities:
                    # Late breakfast/brunch if it's the first activity
                    breakfast_activity = Activity(
                        time="10:00",
                        name="Breakfast/Brunch",
                        type="dining",
                        location=hotel.name if hotel else "Hotel",
                        description="Start the day with a meal",
                        duration_hours=1.0,
                        estimated_cost=0
                    )
                    activities.append(breakfast_activity)

            # --- 3. CHECK-IN (Flexible Time) ---
            # Logic: Check-in usually 15:00. 
            # If we arrive BEFORE 15:00, check in at 15:00.
            # If we arrive AFTER 15:00, check in 1 hour after landing.
            if not has_checked_in and hotel:
                standard_checkin = datetime.combine(current_date, datetime.min.time().replace(hour=15, minute=0))
                
                # Check if we can check in today (arrival must be before or somewhat after checkin time on this day)
                # Ensure we strictly check in AFTER arrival
                
                checkin_time = None
                
                if arrival_dt.date() == current_date:
                    # Arriving today
                    if arrival_dt <= standard_checkin:
                        checkin_time = "15:00" # Standard checkin
                    else:
                        # Late arrival, check in 1 hour after landing
                        checkin_dt = arrival_dt + timedelta(hours=1)
                        checkin_time = checkin_dt.strftime("%H:%M")
                    
                    has_checked_in = True
                    
                elif arrival_dt.date() < current_date and not has_checked_in:
                    # Arrived previous day but somehow didn't check in? (Shouldn't happen with this logic, but safe fallback)
                    checkin_time = "15:00"
                    has_checked_in = True
                
                if has_checked_in and checkin_time:
                    checkin_activity = Activity(
                        time=checkin_time,
                        name=f"Check-in: {hotel.name}",
                        type="hotel",
                        location=hotel.address or "Hotel",
                        description=f"Check-in to {hotel.type} accommodation",
                        duration_hours=0.5,
                        estimated_cost=0
                    )
                    # Insert in correct order based on time string
                    activities.append(checkin_activity)
                    activities.sort(key=lambda x: x.time)

            # --- 4. AFTERNOON ACTIVITY (14:30) ---
            if afternoon_slot >= arrival_dt:
                # Only schedule afternoon if not conflicting with a late checkin
                # Simple logic: just add it
                if attraction_index < len(attractions):
                    afternoon_activity = self._create_activity(
                        time="14:30",
                        activity_type="attraction",
                        attraction=attractions[attraction_index],
                        request=request
                    )
                    # Avoid duplicate time slots if checkin is also 14:30/15:00, but keeping it simple
                    activities.append(afternoon_activity)
                    daily_cost += afternoon_activity.estimated_cost
                    attraction_index += 1
            
            # --- 5. DINNER (19:00) ---
            if dinner_slot >= arrival_dt:
                if day_meals and day_meals.dinner:
                    dinner_activity = self._create_meal_activity(
                        time="19:00",
                        meal_type="dinner",
                        restaurant=day_meals.dinner,
                        request=request
                    )
                    activities.append(dinner_activity)
                    daily_cost += dinner_activity.estimated_cost
            
            # Handle "In Transit" day
            if not activities and arrival_dt.date() == current_date:
                # We arrive today but too late for activities
                activities.append(Activity(
                    time=arrival_dt.strftime("%H:%M"),
                    name="Arrival & Transit",
                    type="travel",
                    location="Airport",
                    description="Arrive at destination and transfer to accommodation",
                    duration_hours=2.0,
                    estimated_cost=0
                ))
            elif not activities and arrival_dt.date() > current_date:
                 # Still flying (e.g. Day 1 of a long haul)
                 activities.append(Activity(
                    time="All Day",
                    name="En Route to Destination",
                    type="travel",
                    location="In Flight",
                    description="Travel day",
                    duration_hours=24.0,
                    estimated_cost=0
                ))

            # Re-sort activities by time just in case
            activities.sort(key=lambda x: x.time if x.time != "All Day" else "00:00")

            # Create day object
            title = f"Day {day_num}: Explore {request.destination}"
            if day_num == 1 or (arrival_dt.date() == current_date):
                title = f"Day {day_num}: Arrival & Settle In"
            elif current_date == request.end_date:
                title = f"Day {day_num}: Departure"
            elif arrival_dt.date() > current_date:
                title = f"Day {day_num}: Traveling"

            notes = self._generate_day_notes(day_num, current_date, request, len(activities))
            
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
    
    def _create_meal_activity(
        self,
        time: str,
        meal_type: str,
        restaurant: any,
        request: TripRequest
    ) -> Activity:
        """Create restaurant activity from meal_plan"""
        
        cost = restaurant.average_cost_per_person * request.travelers
        
        description = f"{restaurant.cuisine}"
        if restaurant.specialties:
            description += f" - Try: {', '.join(restaurant.specialties[:2])}"
        
        return Activity(
            time=time,
            type="dining",
            name=f"{meal_type.title()}: {restaurant.name}",
            location=restaurant.address or restaurant.name,
            duration_hours=1.5 if meal_type == "dinner" else 1.0,
            estimated_cost=cost,
            description=description
        )
    
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
        
        if activity_count == 0:
            return "Travel day or free time."

        if pace == "relaxed" and activity_count > 4:
            notes.append("Consider removing an activity for a more relaxed pace")
        elif pace == "packed" and activity_count < 4:
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
            "confidence": 0.0,  # 0-1 range
            "warnings": warnings
        }
        
        return output, metadata