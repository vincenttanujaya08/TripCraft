"""
Pydantic schemas for TripCraft Lite
FIXED: Removed circular references that caused RecursionError
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from enum import Enum


# ============================================================================
# REQUEST MODELS
# ============================================================================

class TripPreferences(BaseModel):
    """User preferences for trip planning"""
    accommodation: str = Field(default="mid-range", pattern="^(budget|mid-range|luxury)$")
    interests: List[str] = Field(default_factory=list, description="e.g., ['culture', 'food', 'nature']")
    dietary_restrictions: List[str] = Field(default_factory=list, description="e.g., ['vegetarian', 'halal']")
    pace: str = Field(default="moderate", pattern="^(relaxed|moderate|packed)$")


class TripRequest(BaseModel):
    """Main trip request from user"""
    destination: str = Field(..., description="City, Country (e.g., 'Bali, Indonesia')")
    origin: Optional[str] = Field(None, description="Departure city for flights")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    budget: float = Field(..., gt=0, description="Total budget in IDR")
    travelers: int = Field(default=1, ge=1, le=20)
    preferences: TripPreferences = Field(default_factory=TripPreferences)
    
    @field_validator('end_date')
    @classmethod
    def end_after_start(cls, v, info):
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days


# ============================================================================
# DESTINATION MODELS
# ============================================================================

class Attraction(BaseModel):
    """Tourist attraction or point of interest"""
    name: str
    type: str = Field(..., description="e.g., 'museum', 'temple', 'park', 'beach'")
    description: str
    address: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    opening_hours: Optional[str] = None
    entrance_fee: Optional[float] = Field(None, description="Fee in IDR, 0 if free")
    estimated_duration_hours: float = Field(default=2.0)
    image: Optional[Dict[str, Any]] = None


class DestinationInfo(BaseModel):
    """Information about the destination city"""
    name: str
    country: str
    description: str
    best_time_to_visit: Optional[str] = None
    local_currency: str = "IDR"
    timezone: Optional[str] = None
    language: Optional[str] = None
    safety_tips: List[str] = Field(default_factory=list)


class DestinationOutput(BaseModel):
    """Output from Destination Agent"""
    destination: DestinationInfo
    attractions: List[Attraction]
    local_tips: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    data_source: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ============================================================================
# DINING MODELS (FIXED - No circular refs!)
# ============================================================================

class Restaurant(BaseModel):
    """Restaurant recommendation"""
    name: str
    cuisine: str = Field(..., description="e.g., 'Indonesian', 'Italian', 'Seafood'")
    description: str
    address: Optional[str] = None
    price_range: str = Field(default="$$", pattern=r"^(\$|\$\$|\$\$\$|\$\$\$\$)$")
    average_cost_per_person: float = Field(..., description="Average meal cost in IDR")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    specialties: List[str] = Field(default_factory=list)
    dietary_options: List[str] = Field(default_factory=list)
    opening_hours: Optional[str] = None
    meal_types: List[str] = Field(default_factory=list)
    image: Optional[Dict[str, Any]] = None
    
    model_config = {"arbitrary_types_allowed": True}


class DailyMealPlan(BaseModel):
    """Meal plan for one day"""
    day: int = Field(..., ge=1)
    date: date
    breakfast: Optional[Restaurant] = None
    breakfast_notes: Optional[str] = None
    lunch: Optional[Restaurant] = None
    dinner: Optional[Restaurant] = None
    daily_cost: float = Field(default=0.0)
    notes: Optional[str] = None
    
    model_config = {"arbitrary_types_allowed": True}


class DiningOutput(BaseModel):
    """Output from Dining Agent"""
    restaurants: List[Restaurant]
    meal_plan: List[DailyMealPlan]
    estimated_total_cost: float
    estimated_daily_cost: float
    budget_breakdown: Dict[str, float] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    data_source: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    model_config = {"arbitrary_types_allowed": True}


# ============================================================================
# HOTEL MODELS
# ============================================================================

class Hotel(BaseModel):
    """Hotel accommodation option"""
    name: str
    type: str = Field(default="hotel", pattern="^(hotel|hostel|resort|villa|guesthouse)$")
    description: str
    address: Optional[str] = None
    price_per_night: float = Field(..., description="Price in IDR")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    amenities: List[str] = Field(default_factory=list)
    distance_to_center_km: Optional[float] = None
    room_type: Optional[str] = None
    image: Optional[Dict[str, Any]] = None


class HotelOutput(BaseModel):
    """Output from Hotel Agent"""
    hotels: List[Hotel]
    recommended_hotel: Optional[Hotel] = None
    total_accommodation_cost: float
    warnings: List[str] = Field(default_factory=list)
    data_source: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ============================================================================
# FLIGHT MODELS
# ============================================================================

class Flight(BaseModel):
    """Flight option"""
    airline: str
    flight_number: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime
    duration_hours: float
    price: float
    stops: int = Field(default=0, ge=0)
    cabin_class: str = Field(default="economy", pattern="^(economy|business|first)$")


class FlightOutput(BaseModel):
    """Output from Flight Agent"""
    outbound_flights: List[Flight]
    return_flights: List[Flight]
    recommended_outbound: Optional[Flight] = None
    recommended_return: Optional[Flight] = None
    total_flight_cost: float
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    data_source: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ============================================================================
# BUDGET MODELS
# ============================================================================

class BudgetBreakdown(BaseModel):
    """Detailed budget breakdown"""
    accommodation: float = 0.0
    flights: float = 0.0
    food: float = 0.0
    activities: float = 0.0
    transportation_local: float = 0.0
    miscellaneous: float = 0.0
    total: float = 0.0
    remaining: float = 0.0


class BudgetOutput(BaseModel):
    """Output from Budget Agent"""
    breakdown: BudgetBreakdown
    is_within_budget: bool
    suggestions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    data_source: str = "seed"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ============================================================================
# ITINERARY MODELS
# ============================================================================

class Activity(BaseModel):
    """Single activity in itinerary"""
    time: str
    name: str
    type: str
    location: str
    description: str
    duration_hours: float
    estimated_cost: float = Field(default=0.0)
    notes: Optional[str] = None
    image: Optional[Dict[str, Any]] = None


class DayItinerary(BaseModel):
    """Itinerary for a single day"""
    day_number: int = Field(..., ge=1)
    date: date
    title: str
    activities: List[Activity]
    total_estimated_cost: float = Field(default=0.0)
    notes: Optional[str] = None


class ItineraryOutput(BaseModel):
    """Output from Itinerary Agent"""
    days: List[DayItinerary]
    total_activities: int
    overview: str
    tips: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# VERIFIER MODELS
# ============================================================================

class ValidationIssue(BaseModel):
    """Single validation issue found"""
    severity: str
    component: str
    message: str
    suggestion: str


class VerificationOutput(BaseModel):
    """Output from Verifier Agent"""
    is_valid: bool
    issues: List[ValidationIssue]
    quality_score: float = Field(..., ge=0.0, le=100.0)
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    data_source: str = "seed"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ============================================================================
# GROUND TRANSPORT MODELS
# ============================================================================

class GroundTransportOption(BaseModel):
    """Ground transport option (train/bus/ferry)"""
    transport_type: str = Field(..., description="train/bus/ferry")
    name: str
    operator: Optional[str] = None
    cost_per_person: float
    duration_hours: float
    frequency: Optional[str] = None
    class_available: List[str] = Field(default_factory=list)


class GroundTransportRoute(BaseModel):
    """Ground transport route between two cities"""
    origin: str
    destination: str
    options: List[GroundTransportOption]
    cheapest_option: GroundTransportOption
    recommended: bool = Field(default=False, description="Recommended over flight?")


# ============================================================================
# COMPLETE TRIP MODELS
# ============================================================================

class CompleteTripPlan(BaseModel):
    """Complete aggregated trip plan"""
    trip_id: str
    trace_id: str
    request: TripRequest
    destination: DestinationOutput
    dining: DiningOutput
    hotel: HotelOutput
    flights: FlightOutput
    budget: BudgetOutput
    itinerary: ItineraryOutput
    verification: VerificationOutput
    created_at: datetime
    processing_time_seconds: float


class TripStatus(str, Enum):
    """Trip processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TripResponse(BaseModel):
    """Response for trip status endpoint"""
    trip_id: str
    trace_id: str
    status: TripStatus
    progress: Optional[Dict[str, str]] = None
    result: Optional[CompleteTripPlan] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# IMAGE MODELS
# ============================================================================

class ImageData(BaseModel):
    """Image metadata"""
    url: str
    source: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: Optional[str] = None
    photographer: Optional[str] = None
    is_generic: bool = False
    validated: bool = False