"""
Destination Agent - Finds and validates destination information
"""
from typing import Dict, List
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from backend.models.schemas import (
    TripRequest, 
    DestinationOutput, 
    DestinationInfo, 
    Attraction
)
from backend.agents.base_agent import BaseAgent
from backend.data_sources.seed_loader import SeedLoader

# Load environment variables
load_dotenv()

class DestinationAgent(BaseAgent):
    """Agent responsible for destination research and validation"""
    
    def __init__(self):
        super().__init__("Destination")
        self.seed_loader = SeedLoader()
        
        # Initialize Gemini from environment variable
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment")
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            self.llm_available = True
        except Exception as e:
            print(f"⚠️  Gemini not available: {e}")
            self.llm_available = False
    
    def _calculate_trip_days(self, request: TripRequest) -> int:
        """Calculate number of days in trip"""
        return (request.end_date - request.start_date).days
    
    def _get_recommended_attraction_count(self, days: int) -> int:
        """Get recommended number of attractions based on trip duration"""
        if days <= 2:
            return 5  # Quick visit - top highlights
        elif days <= 4:
            return 8  # Medium stay - balanced
        elif days <= 7:
            return 12  # Week-long - comprehensive
        else:
            return 15  # Extended stay - deep exploration
    
    async def _get_from_llm(self, destination: str, request: TripRequest) -> Dict:
        """Fallback: Get destination info from Gemini LLM"""
        
        # Calculate trip details
        days = self._calculate_trip_days(request)
        num_attractions = self._get_recommended_attraction_count(days)
        travelers = request.travelers
        
        # Budget per person per day
        budget_per_day = request.budget / travelers / days if days > 0 else 0
        
        # Determine travel style based on budget
        if budget_per_day > 1500000:  # >1.5M IDR/day
            style = "luxury and premium experiences"
        elif budget_per_day > 750000:  # >750K IDR/day
            style = "comfortable mid-range experiences"
        else:
            style = "budget-friendly but quality experiences"
        
        prompt = f"""You are a travel expert. Create a personalized {days}-day itinerary for {destination}.

TRIP DETAILS:
- Duration: {days} days ({request.start_date} to {request.end_date})
- Travelers: {travelers} person(s)
- Budget: Rp {request.budget:,.0f} total (Rp {budget_per_day:,.0f}/person/day)
- Style: {style}

REQUIREMENTS:
1. Provide {num_attractions} diverse attractions suitable for this {days}-day trip
2. Mix popular landmarks with hidden gems and local favorites
3. Include variety: cultural sites, nature, food spots, activities
4. Consider the budget level - suggest appropriate venues
5. Balance must-see places with relaxing/authentic experiences

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "name": "City Name",
  "country": "Country",
  "description": "Engaging 2-3 sentence description highlighting what makes this destination special",
  "best_time_to_visit": "e.g., April-October (dry season)",
  "timezone": "e.g., UTC+7",
  "currency": "e.g., IDR",
  "language": "e.g., Indonesian, Balinese",
  "attractions": [
    {{
      "name": "Attraction Name",
      "category": "temple|museum|park|beach|market|restaurant|viewpoint|waterfall|cultural|nightlife|shopping",
      "description": "Specific description (what to see/do, why it's special, 1-2 sentences)",
      "estimated_duration": 2.0,
      "opening_hours": "e.g., 08:00-17:00 or 24/7",
      "entrance_fee": 50000.0
    }}
  ]
}}

IMPORTANT:
- Provide EXACTLY {num_attractions} attractions
- Vary the categories - don't repeat similar types
- Include realistic entrance fees in IDR (0 if free)
- Opening hours should be realistic
- Estimated duration in hours (0.5 to 4.0 typical)
- Descriptions should be specific and useful for planning

Return ONLY the JSON, nothing else."""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            data = json.loads(text)
            
            # Validate we got enough attractions
            attractions = data.get("attractions", [])
            print(f"✅ LLM generated {len(attractions)} attractions for {days}-day trip to {data.get('name')}")
            
            return data
            
        except Exception as e:
            print(f"❌ LLM fallback failed: {e}")
            raise ValueError(f"Destination '{destination}' not found and LLM fallback failed")
    
    async def execute(self, request: TripRequest) -> tuple[DestinationOutput, Dict]:
        """
        Find destination information and attractions
        
        Returns:
            tuple: (DestinationOutput, metadata)
        """
        start_time = datetime.now()
        data_source = "seed"
        
        try:
            # Try seed database first
            dest_data = self.seed_loader.get_destination(request.destination)
            
            # Fallback to LLM if not in database
            if not dest_data:
                print(f"⚠️  Destination not found in seed data: {request.destination}")
                if self.llm_available:
                    print(f"🤖 Trying LLM fallback...")
                    dest_data = await self._get_from_llm(request.destination, request)
                    data_source = "llm_fallback"
                else:
                    raise ValueError(f"Destination '{request.destination}' not found in database and LLM unavailable")
            
            # Extract attractions
            attractions = []
            for attr in dest_data.get("attractions", []):
                attractions.append(Attraction(
                    name=attr.get("name", "Unknown"),
                    type=attr.get("category") or attr.get("type", "general"),
                    description=attr.get("description", ""),
                    opening_hours=attr.get("opening_hours"),
                    estimated_duration_hours=attr.get("estimated_duration", 2.0),
                    entrance_fee=attr.get("entrance_fee", 0.0)
                ))
            
            # Create DestinationInfo
            dest_info = DestinationInfo(
                name=dest_data.get("name") or dest_data.get("city", request.destination),
                country=dest_data.get("country", "Unknown"),
                description=dest_data.get("description", ""),
                best_time_to_visit=dest_data.get("best_time_to_visit", "Year-round"),
                timezone=dest_data.get("timezone", "UTC+0"),
                currency=dest_data.get("currency", "USD"),
                language=dest_data.get("language", "English")
            )
            
            # Calculate confidence (lower for LLM)
            if data_source == "seed":
                confidence = 0.9 if len(attractions) >= 5 else 0.7
            else:  # llm_fallback
                confidence = 0.7 if len(attractions) >= 8 else 0.6
            
            # Create output
            output = DestinationOutput(
                destination=dest_info,
                attractions=attractions,
                data_source=data_source,
                confidence=confidence,
                warnings=[] if data_source == "seed" else ["Information generated by AI - verify important details"]
            )
            
            # Metadata
            processing_time = (datetime.now() - start_time).total_seconds()
            metadata = {
                "agent": self.name,
                "processing_time_ms": int(processing_time * 1000),
                "attractions_found": len(attractions),
                "data_source": data_source,
                "trip_duration_days": self._calculate_trip_days(request)
            }
            
            return output, metadata
            
        except Exception as e:
            # Log error
            processing_time = (datetime.now() - start_time).total_seconds()
            print(f"✗ {self.name} failed after {int(processing_time * 1000)}ms: {str(e)}")
            raise
