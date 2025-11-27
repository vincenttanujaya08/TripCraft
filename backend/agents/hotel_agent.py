"""
Hotel Agent - Handles hotel search and recommendations
"""
import os
import json
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
import google.generativeai as genai
from backend.models.schemas import (
    TripRequest, 
    HotelOutput, 
    Hotel
)
from backend.agents.base_agent import BaseAgent
from backend.data_sources.seed_loader import SeedLoader

load_dotenv()

class HotelAgent(BaseAgent):
    """Agent responsible for finding and recommending hotels"""
    
    def __init__(self):
        super().__init__("Hotel")
        self.seed_loader = SeedLoader()
        
        # Initialize Gemini
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel("gemini-2.0-flash")
                self.llm_available = True
            else:
                self.llm_available = False
        except Exception as e:
            print(f"⚠️  Gemini not available: {e}")
            self.llm_available = False
    
    async def _get_from_llm(self, destination: str, request: TripRequest) -> List[Dict]:
        """Get hotel recommendations from LLM"""
        nights = (request.end_date - request.start_date).days
        budget_per_night = request.budget / nights / request.travelers if nights > 0 else 0
        
        prompt = f"""You are a hotel booking expert. Recommend 5 hotels in {destination}.

REQUIREMENTS:
- Nights: {nights}
- Travelers: {request.travelers}
- Budget: Rp {budget_per_night:,.0f} per person per night
- Mix budget levels: 2 budget-friendly, 2 mid-range, 1 premium

Return ONLY valid JSON array (no markdown):
[
  {{
    "name": "Hotel Name",
    "type": "hotel|resort|villa|hostel|guesthouse",
    "description": "Brief description highlighting unique features (1-2 sentences)",
    "address": "Specific address or area",
    "price_per_night": 500000.0,
    "rating": 4.5,
    "amenities": ["wifi", "pool", "breakfast", "parking"],
    "distance_to_center_km": 2.5,
    "room_type": "Deluxe Room"
  }}
]

Provide realistic prices in IDR. Rating 0.0-5.0. Return ONLY the JSON array."""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            hotels = json.loads(text)
            print(f"✅ LLM generated {len(hotels)} hotels for {destination}")
            return hotels
            
        except Exception as e:
            print(f"❌ LLM hotel search failed: {e}")
            return []
    
    async def execute(self, request: TripRequest) -> tuple[HotelOutput, Dict]:
        """Find suitable hotels"""
        start_time = datetime.now()
        data_source = "seed"
        
        try:
            # Calculate nights
            nights = (request.end_date - request.start_date).days
            if nights <= 0:
                nights = 1
            
            print(f"🛏️  Nights: {nights}, Travelers: {request.travelers}, Budget: Rp {request.budget:,.0f}")
            
            # Try seed data first
            hotels_data = self.seed_loader.get_hotels_by_city(request.destination)
            
            # Fallback to LLM if no seed data
            if not hotels_data:
                print(f"⚠️  No hotels in seed data for {request.destination}")
                if self.llm_available:
                    print(f"🤖 Trying LLM fallback...")
                    hotels_data = await self._get_from_llm(request.destination, request)
                    data_source = "llm_fallback"
                else:
                    raise ValueError(f"No hotels found for {request.destination}")
            
            # Parse hotels
            valid_hotels = []
            for hotel_data in hotels_data:
                try:
                    hotel = Hotel(
                        name=hotel_data.get("name", "Unknown Hotel"),
                        type=hotel_data.get("type", "hotel"),
                        description=hotel_data.get("description", ""),
                        address=hotel_data.get("address"),
                        price_per_night=float(hotel_data.get("price_per_night", 0)),
                        rating=hotel_data.get("rating"),
                        amenities=hotel_data.get("amenities", []),
                        distance_to_center_km=hotel_data.get("distance_to_center_km"),
                        room_type=hotel_data.get("room_type")
                    )
                    valid_hotels.append(hotel)
                except Exception as e:
                    print(f"⚠️  Skipped invalid hotel: {e}")
                    continue
            
            if not valid_hotels:
                raise ValueError(f"No valid hotels found for {request.destination}")
            
            # Filter by budget
            budget_per_night = request.budget / nights / request.travelers
            affordable = [h for h in valid_hotels if h.price_per_night <= budget_per_night * 1.5]
            
            if affordable:
                valid_hotels = affordable
            
            # Sort by rating and price
            valid_hotels.sort(key=lambda h: (h.rating or 0, -h.price_per_night), reverse=True)
            
            # Select top 5
            selected = valid_hotels[:5]
            recommended = selected[0] if selected else None
            
            # DEBUG: Print calculation
            if recommended:
                print(f"💰 CALCULATION:")
                print(f"   nights = {nights}")
                print(f"   price_per_night = {recommended.price_per_night:,.0f}")
                print(f"   formula: {nights} × {recommended.price_per_night:,.0f}")
            
            # Calculate total cost
            total_cost = nights * recommended.price_per_night if recommended else 0.0
            
            print(f"   RESULT: Rp {total_cost:,.0f}")
            
            # Confidence
            if data_source == "seed":
                confidence = 0.9 if len(selected) >= 3 else 0.7
            else:
                confidence = 0.7 if len(selected) >= 3 else 0.6
            
            output = HotelOutput(
                hotels=selected,
                recommended_hotel=recommended,
                total_accommodation_cost=total_cost,
                warnings=[] if data_source == "seed" else ["Hotels generated by AI - verify availability"],
                data_source=data_source,
                confidence=confidence
            )
            
            # Metadata
            processing_time = (datetime.now() - start_time).total_seconds()
            metadata = {
                "agent": self.name,
                "processing_time_ms": int(processing_time * 1000),
                "hotels_found": len(selected),
                "data_source": data_source,
                "nights": nights,
                "recommended_price": recommended.price_per_night if recommended else 0
            }
            
            return output, metadata
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            print(f"✗ {self.name} failed after {int(processing_time * 1000)}ms: {e}")
            raise
