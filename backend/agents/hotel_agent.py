"""
Hotel Agent - UPDATED with budget allocation awareness
Handles hotel search and recommendations with budget constraints
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
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
    """Agent responsible for finding and recommending hotels with budget awareness"""
    
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
    
    async def execute(
        self, 
        request: TripRequest,
        max_budget: Optional[float] = None,  # NEW: Budget allocation parameter
        context: Optional[Dict] = None
    ) -> tuple[HotelOutput, Dict]:
        """
        Find suitable hotels with budget awareness
        
        NEW: Added max_budget parameter for budget allocation
        
        Args:
            request: Trip request
            max_budget: Maximum budget allocated for accommodation (optional)
            
        Returns:
            (HotelOutput, metadata)
        """
        start_time = datetime.now()
        data_source = "seed"
        warnings = []
        
        try:
            # Calculate nights
            nights = (request.end_date - request.start_date).days
            if nights <= 0:
                nights = 1
            
            # Calculate budget constraints
            if max_budget:
                budget_per_night_total = max_budget / nights
                self.logger.info(
                    f"💰 Hotel budget: Rp {max_budget:,.0f} total "
                    f"(Rp {budget_per_night_total:,.0f}/night for all rooms)"
                )
            else:
                budget_per_night_total = None
            
            self.logger.info(
                f"🛏️  Nights: {nights}, Travelers: {request.travelers}, "
                f"Total budget: Rp {request.budget:,.0f}"
            )
            
            # Try seed data first
            hotels_data = self.seed_loader.get_hotels_by_city(request.destination)
            
            # Fallback to LLM if no seed data
            if not hotels_data:
                self.logger.warning(f"⚠️  No hotels in seed data for {request.destination}")
                if self.llm_available:
                    self.logger.info(f"🤖 Trying LLM fallback...")
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
                    self.logger.warning(f"⚠️  Skipped invalid hotel: {e}")
                    continue
            
            if not valid_hotels:
                raise ValueError(f"No valid hotels found for {request.destination}")
            
            # BUDGET FILTERING (if max_budget provided)
            if max_budget and budget_per_night_total:
                affordable = [
                    h for h in valid_hotels 
                    if h.price_per_night <= budget_per_night_total
                ]
                
                if affordable:
                    self.logger.info(
                        f"✓ Found {len(affordable)}/{len(valid_hotels)} hotels within budget"
                    )
                    valid_hotels = affordable
                else:
                    # No hotels within strict budget
                    self.logger.warning(
                        f"⚠️  No hotels within budget Rp {budget_per_night_total:,.0f}/night"
                    )
                    
                    # Find cheapest option
                    cheapest = min(valid_hotels, key=lambda h: h.price_per_night)
                    cheapest_total = cheapest.price_per_night * nights
                    over_amount = cheapest_total - max_budget
                    
                    warnings.append(
                        f"⚠️ No hotels found within budget (Rp {budget_per_night_total:,.0f}/night). "
                        f"Cheapest option: {cheapest.name} at Rp {cheapest.price_per_night:,.0f}/night "
                        f"(Rp {cheapest_total:,.0f} total, over budget by Rp {over_amount:,.0f})"
                    )
                    
                    # Keep cheapest 3 as options
                    valid_hotels = sorted(valid_hotels, key=lambda h: h.price_per_night)[:3]
            
            # Sort by rating and price
            valid_hotels.sort(key=lambda h: (h.rating or 0, -h.price_per_night), reverse=True)
            
            # Select top 5
            selected = valid_hotels[:5]
            recommended = selected[0] if selected else None
            
            # Calculate total cost
            total_cost = nights * recommended.price_per_night if recommended else 0.0
            
            self.logger.info(f"💰 CALCULATION:")
            self.logger.info(f"   nights = {nights}")
            if recommended:
                self.logger.info(f"   price_per_night = Rp {recommended.price_per_night:,.0f}")
                self.logger.info(f"   formula: {nights} × Rp {recommended.price_per_night:,.0f}")
                self.logger.info(f"   RESULT: Rp {total_cost:,.0f}")
            
            # CHECK BUDGET (if max_budget provided)
            if max_budget and recommended:
                if total_cost > max_budget:
                    over_amount = total_cost - max_budget
                    over_pct = (over_amount / max_budget) * 100
                    
                    self.logger.warning(
                        f"⚠️ Recommended hotel over budget: "
                        f"Rp {total_cost:,.0f} > Rp {max_budget:,.0f} (+{over_pct:.1f}%)"
                    )
                    
                    warnings.append(
                        f"⚠️ Recommended hotel ({recommended.name}) exceeds budget by "
                        f"Rp {over_amount:,.0f} ({over_pct:.1f}%). "
                        f"Consider: 1) Increase budget, 2) Choose cheaper hotel, 3) Reduce nights"
                    )
                else:
                    self.logger.info(f"✅ Hotel within budget!")
            
            # Calculate confidence
            if data_source == "seed":
                confidence = 0.9 if len(selected) >= 3 else 0.7
            else:
                confidence = 0.7 if len(selected) >= 3 else 0.6
            
            # Add data source warning
            if data_source == "llm_fallback":
                warnings.append("Hotels generated by AI - verify availability")
            
            # Create output
            output = HotelOutput(
                hotels=selected,
                recommended_hotel=recommended,
                total_accommodation_cost=total_cost,
                warnings=warnings,
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
                "recommended_price": recommended.price_per_night if recommended else 0,
                "budget_allocated": max_budget,
                "within_budget": total_cost <= max_budget if max_budget else True
            }
            
            return output, metadata
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"✗ {self.name} failed after {int(processing_time * 1000)}ms: {e}")
            raise