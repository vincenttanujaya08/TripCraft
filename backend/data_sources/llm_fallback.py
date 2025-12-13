"""
LLMFallback - Uses Ollama when APIs and seed data are unavailable
Last resort in 3-tier fallback: APIs → Seed Data → LLM
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from backend.utils.llm_client import GeminiClient

logger = logging.getLogger(__name__)


class LLMFallback:
    """Uses LLM (Gemini) to generate travel data when other sources fail"""
    
    def __init__(self):
        """Initialize Gemini client"""
        try:
            self.model = GeminiClient()
            self.enabled = True
            logger.info(f"✅ LLMFallback initialized with Gemini")
        except Exception as e:
            logger.error(f"❌ Failed to init OllamaFallback: {e}")
            self.enabled = False
    
    async def _generate(self, prompt: str) -> Optional[str]:
        """Generate text using Gemini"""
        if not self.enabled:
            return None
            
        try:
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            return None
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return None
    
    def _extract_json(self, text: str) -> Optional[Any]:
        """Extract JSON from text response"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try markdown code block
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                if "json" in part:
                    part = part.replace("json", "", 1)
                part = part.strip()
                if part.startswith("{") or part.startswith("["):
                    try:
                        return json.loads(part)
                    except:
                        continue
        
        # Try raw substring
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            try:
                return json.loads(text[start:end])
            except:
                pass
                
        if "[" in text and "]" in text:
            start = text.find("[")
            end = text.rfind("]") + 1
            try:
                return json.loads(text[start:end])
            except:
                pass
                
        logger.error("Failed to extract JSON from response")
        return None
    
    async def generate_destination_info(self, city: str, country: Optional[str] = None) -> Optional[Dict]:
        location = f"{city}, {country}" if country else city
        prompt = f"""Generate travel info for {location}.
Return ONLY valid JSON:
{{
  "city": "{city}",
  "country": "Country",
  "description": "Short description",
  "best_time_to_visit": "Months",
  "local_currency": "Currency",
  "timezone": "Timezone",
  "language": "Language",
  "attractions": [
    {{
      "name": "Attraction Name",
      "type": "Type",
      "description": "Short description",
      "estimated_duration_hours": 2,
      "estimated_cost": "Cost description"
    }}
  ],
  "local_tips": ["Tip 1", "Tip 2"]
}}"""
        response = await self._generate(prompt)
        return self._extract_json(response) if response else None

    async def generate_hotels(self, city: str, budget: str = "mid-range", count: int = 3) -> Optional[List[Dict]]:
        prompt = f"""Generate {count} {budget} hotels in {city}.
Return ONLY valid JSON array:
[
  {{
    "name": "Hotel Name",
    "category": "{budget}",
    "price_per_night": 1000000,
    "rating": 4.5,
    "amenities": ["Wifi", "Pool"],
    "location": "Area",
    "description": "Short description"
  }}
]"""
        response = await self._generate(prompt)
        if response:
            data = self._extract_json(response)
            if isinstance(data, list): return data
            if isinstance(data, dict) and "hotels" in data: return data["hotels"]
        return None

    async def generate_restaurants(self, city: str, cuisine: Optional[str] = None, count: int = 4) -> Optional[List[Dict]]:
        cuisine_filter = f" specializing in {cuisine}" if cuisine else ""
        prompt = f"""Generate {count} restaurants in {city}{cuisine_filter}.
Return ONLY valid JSON array:
[
  {{
    "name": "Restaurant Name",
    "cuisine": "Cuisine",
    "price_range": "$/$$/$$$",
    "estimated_cost_per_person": 150000,
    "rating": 4.5,
    "specialties": ["Dish 1"],
    "description": "Short description"
  }}
]"""
        response = await self._generate(prompt)
        if response:
            data = self._extract_json(response)
            if isinstance(data, list): return data
            if isinstance(data, dict) and "restaurants" in data: return data["restaurants"]
        return None

    async def generate_flight_estimate(self, origin: str, destination: str) -> Optional[Dict]:
        prompt = f"""Estimate flight {origin} to {destination}.
Return ONLY valid JSON:
{{
  "route": "{origin}-{destination}",
  "airline": "Airline",
  "duration_hours": 2.0,
  "price_range_min": 1000000,
  "price_range_max": 2000000,
  "departure_airport": "CODE",
  "arrival_airport": "CODE"
}}"""
        response = await self._generate(prompt)
        return self._extract_json(response) if response else None

    async def generate_itinerary_suggestions(self, city: str, days: int, interests: List[str]) -> Optional[str]:
        prompt = f"""Create {days}-day itinerary for {city}, interests: {', '.join(interests)}. Practical, short."""
        return await self._generate(prompt)


# Singleton
_llm_fallback = None

def get_llm_fallback() -> LLMFallback:
    global _llm_fallback
    if _llm_fallback is None:
        _llm_fallback = LLMFallback()
    return _llm_fallback
