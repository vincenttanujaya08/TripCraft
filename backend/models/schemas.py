"""
Pydantic schemas for TripCraft Lite
Defines all data structures with strict validation
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal, Dict, Any
from datetime import date, datetime
from enum import Enum


# ============================================================================
# REQUEST MODELS
# ============================================================================

class TripPreferences(BaseModel):
    """User preferences for trip planning"""
    accommodation: Literal["budget", "mid-range", "luxury"] = "mid-range"
    interests: List[str] = Field(default_factory=list, description="e.g., ['culture', 'food', 'nature']")
    dietary_restrictions: List[str] = Field(default_factory=list, description="e.g., ['vegetarian', 'halal']")
    pace: Literal["relaxed", "moderate", "packed"] = "moderate"


class TripRequest(BaseModel):
    """Main trip request from user"""
    destination: str = Field(..., description="City, Country (e.g., 'Bali, Indonesia')")
    origin: Optional[str] = Field(None, description="Departure city for flights")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    budget: float = Field(..., gt=0, description="Total budget in IDR")
    travelers: int = Field(default=1, ge=1, le=20)
    preferences: TripPreferences = Field(default_factory=TripPreferences)
    
    @validator('end_date')
    def end_after_start(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
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
    coordinates: Optional[Dict[str, float]] = None  # {"lat": -8.65, "lon": 115.22}
    opening_hours: Optional[str] = None
    entrance_fee: Optional[float] = Field(None, description="Fee in IDR, 0 if free")
    estimated_duration_hours: float = Field(default=2.0)
    image: Optional[Dict[str, Any]] = None  # Will be populated by image service


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
    data_source: Literal["api", "seed", "llm_fallback"]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ============================================================================
# DINING MODELS
# ============================================================================

class Restaurant(BaseModel):
    """Restaurant recommendation"""
    name: str
    cuisine: str = Field(..., description="e.g., 'Indonesian', 'Italian', 'Seafood'")
    description: str
    address: Optional[str] = None
    price_range: Literal["$", "$$", "$$$", "$$$$"] = "$$"
    average_cost_per_person: float = Field(..., description="Average meal cost in IDR")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    specialties: List[str] = Field(default_factory=list)
    dietary_options: List[str] = Field(default_factory=list, description="e.g., ['vegetarian', 'halal']")
    opening_hours: Optional[str] = None
    image: Optional[Dict[str, Any]] = None


class DiningOutput(BaseModel):
    """Output from Dining Agent"""
    restaurants: List[Restaurant]
    estimated_total_cost: float = Field(..., description="Total dining cost for trip in IDR")
    warnings: List[str] = Field(default_factory=list)
    data_source: Literal["api", "seed", "llm_fallback"]


# ============================================================================
# HOTEL MODELS
# ============================================================================

class Hotel(BaseModel):
    """Hotel accommodation option"""
    name: str
    type: Literal["hotel", "hostel", "resort", "villa", "guesthouse"] = "hotel"
    description: str
    address: Optional[str] = None
    price_per_night: float = Field(..., description="Price in IDR")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    amenities: List[str] = Field(default_factory=list, description="e.g., ['wifi', 'pool', 'breakfast']")
    distance_to_center_km: Optional[float] = None
    room_type: Optional[str] = Field(None, description="e.g., 'Standard Room', 'Deluxe Suite'")
    image: Optional[Dict[str, Any]] = None


class HotelOutput(BaseModel):
    """Output from Hotel Agent"""
    hotels: List[Hotel]
    recommended_hotel: Optional[Hotel] = None  # Top pick
    total_accommodation_cost: float = Field(..., description="Total cost for all nights in IDR")
    warnings: List[str] = Field(default_factory=list)
    data_source: Literal["api", "seed", "llm_fallback"]


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
    price: float = Field(..., description="Price in IDR")
    stops: int = Field(default=0, ge=0)
    cabin_class: Literal["economy", "business", "first"] = "economy"


class FlightOutput(BaseModel):
    """Output from Flight Agent"""
    outbound_flights: List[Flight]
    return_flights: List[Flight]
    recommended_outbound: Optional[Flight] = None
    recommended_return: Optional[Flight] = None
    total_flight_cost: float = Field(..., description="Round-trip cost in IDR")
    warnings: List[str] = Field(default_factory=list)
    data_source: Literal["api", "seed", "llm_fallback"]


# ============================================================================
# BUDGET MODELS
# ============================================================================

class BudgetBreakdown(BaseModel):
    """Detailed budget breakdown"""
    flights: float = 0.0
    accommodation: float = 0.0
    dining: float = 0.0
    attractions: float = 0.0
    transportation_local: float = 0.0
    miscellaneous: float = 0.0
    emergency_buffer: float = 0.0
    
    @property
    def total(self) -> float:
        return (
            self.flights + 
            self.accommodation + 
            self.dining + 
            self.attractions + 
            self.transportation_local + 
            self.miscellaneous + 
            self.emergency_buffer
        )


class BudgetOutput(BaseModel):
    """Output from Budget Agent"""
    total_budget: float
    breakdown: BudgetBreakdown
    remaining_budget: float
    is_over_budget: bool
    budget_utilization_percent: float
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# ============================================================================
# ITINERARY MODELS
# ============================================================================

class Activity(BaseModel):
    """Single activity in itinerary"""
    time: str = Field(..., description="Time in HH:MM format")
    name: str
    type: Literal["attraction", "dining", "hotel", "transport", "free_time"]
    location: str
    description: str
    duration_hours: float
    estimated_cost: float = Field(default=0.0, description="Cost in IDR")
    notes: Optional[str] = None
    image: Optional[Dict[str, Any]] = None


class DayItinerary(BaseModel):
    """Itinerary for a single day"""
    day_number: int = Field(..., ge=1)
    date: date
    title: str = Field(..., description="e.g., 'Explore Cultural Sites'")
    activities: List[Activity]
    total_estimated_cost: float = Field(default=0.0)
    notes: Optional[str] = None


class ItineraryOutput(BaseModel):
    """Output from Itinerary Agent"""
    days: List[DayItinerary]
    total_activities: int
    overview: str = Field(..., description="Brief summary of the trip")
    tips: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# VERIFIER MODELS
# ============================================================================

class ValidationIssue(BaseModel):
    """Single validation issue found"""
    severity: Literal["error", "warning", "info"]
    category: str = Field(..., description="e.g., 'budget', 'schedule', 'feasibility'")
    message: str
    affected_items: List[str] = Field(default_factory=list)


class VerificationOutput(BaseModel):
    """Output from Verifier Agent"""
    is_valid: bool
    issues: List[ValidationIssue]
    score: float = Field(..., ge=0.0, le=100.0, description="Quality score 0-100")
    summary: str


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
    progress: Optional[Dict[str, str]] = None  # {"destination": "completed", "dining": "processing"}
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
    source: Literal["unsplash", "pexels", "placeholder"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: Optional[str] = None
    photographer: Optional[str] = None
    is_generic: bool = False
    validated: bool = False
