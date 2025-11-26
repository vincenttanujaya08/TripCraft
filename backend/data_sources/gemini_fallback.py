"""
GeminiFallback - Uses Gemini LLM when APIs and seed data are unavailable
Last resort in 3-tier fallback: APIs → Seed Data → LLM
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class GeminiFallback:
    """Uses Gemini LLM to generate travel data when other sources fail"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client
        
        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        logger.info("GeminiFallback initialized with gemini-2.5-flash")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _generate(self, prompt: str) -> Optional[str]:
        """Generate text using Gemini with retry logic"""
        
        try:
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                logger.info("Gemini generation successful")
                return response.text.strip()
            else:
                logger.warning("Gemini returned empty response")
                return None
        
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return None
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from text response (handles markdown code blocks)"""
        
        try:
            # Try direct JSON parse first
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                json_str = text[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        
        # Try to find JSON object
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            json_str = text[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        logger.error("Failed to extract JSON from Gemini response")
        return None
    
    async def generate_destination_info(
        self,
        city: str,
        country: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Generate destination information using LLM
        
        Args:
            city: City name
            country: Country name (optional)
            
        Returns:
            Destination info dictionary
        """
        
        location = f"{city}, {country}" if country else city
        
        prompt = f"""Generate comprehensive travel information about {location}.

Return ONLY a valid JSON object (no additional text) with this EXACT structure:

{{
  "city": "{city}",
  "country": "<country name>",
  "description": "<2-3 sentence description>",
  "best_time_to_visit": "<best months to visit>",
  "local_currency": "<currency name and code>",
  "timezone": "<timezone>",
  "language": "<primary language>",
  "attractions": [
    {{
      "name": "<attraction name>",
      "type": "<museum/landmark/park/etc>",
      "description": "<brief description>",
      "estimated_duration_hours": <number>,
      "estimated_cost": "<approximate cost in local currency>"
    }}
  ],
  "local_tips": [
    "<practical tip 1>",
    "<practical tip 2>",
    "<practical tip 3>"
  ]
}}

Include 5 top attractions. Be accurate and practical."""

        response = await self._generate(prompt)
        
        if response:
            return self._extract_json(response)
        
        return None
    
    async def generate_hotels(
        self,
        city: str,
        budget: str = "mid-range",
        count: int = 3
    ) -> Optional[List[Dict]]:
        """
        Generate hotel recommendations using LLM
        
        Args:
            city: City name
            budget: Budget level (budget/mid-range/luxury)
            count: Number of hotels to generate
            
        Returns:
            List of hotel dictionaries
        """
        
        prompt = f"""Generate {count} realistic {budget} hotel recommendations for {city}.

Return ONLY a valid JSON array (no additional text) with this structure:

[
  {{
    "name": "<hotel name>",
    "category": "{budget}",
    "price_per_night": <number in local currency>,
    "rating": <float between 0-5>,
    "amenities": ["<amenity1>", "<amenity2>"],
    "location": "<neighborhood or area>",
    "description": "<1-2 sentence description>"
  }}
]

Use realistic prices and actual hotel names when possible."""

        response = await self._generate(prompt)
        
        if response:
            data = self._extract_json(response)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "hotels" in data:
                return data["hotels"]
        
        return None
    
    async def generate_restaurants(
        self,
        city: str,
        cuisine: Optional[str] = None,
        count: int = 4
    ) -> Optional[List[Dict]]:
        """
        Generate restaurant recommendations using LLM
        
        Args:
            city: City name
            cuisine: Preferred cuisine (optional)
            count: Number of restaurants
            
        Returns:
            List of restaurant dictionaries
        """
        
        cuisine_filter = f" specializing in {cuisine}" if cuisine else ""
        
        prompt = f"""Generate {count} restaurant recommendations for {city}{cuisine_filter}.

Return ONLY a valid JSON array (no additional text):

[
  {{
    "name": "<restaurant name>",
    "cuisine": "<cuisine type>",
    "price_range": "<$/$$/$$$/$$$$>",
    "estimated_cost_per_person": <number in local currency>,
    "rating": <float between 0-5>,
    "specialties": ["<dish1>", "<dish2>"],
    "description": "<1-2 sentences>"
  }}
]

Use realistic restaurants and prices."""

        response = await self._generate(prompt)
        
        if response:
            data = self._extract_json(response)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "restaurants" in data:
                return data["restaurants"]
        
        return None
    
    async def generate_flight_estimate(
        self,
        origin: str,
        destination: str
    ) -> Optional[Dict]:
        """
        Generate flight route and price estimate
        
        Args:
            origin: Origin city
            destination: Destination city
            
        Returns:
            Flight estimate dictionary
        """
        
        prompt = f"""Estimate flight information from {origin} to {destination}.

Return ONLY a valid JSON object (no additional text):

{{
  "route": "{origin}-{destination}",
  "airline": "<typical airline for this route>",
  "duration_hours": <flight duration>,
  "price_range_min": <minimum price in USD>,
  "price_range_max": <maximum price in USD>,
  "departure_airport": "<airport code>",
  "arrival_airport": "<airport code>"
}}

Use realistic flight times and prices."""

        response = await self._generate(prompt)
        
        if response:
            return self._extract_json(response)
        
        return None
    
    async def generate_itinerary_suggestions(
        self,
        city: str,
        days: int,
        interests: List[str]
    ) -> Optional[str]:
        """
        Generate itinerary suggestions
        
        Args:
            city: City name
            days: Number of days
            interests: List of traveler interests
            
        Returns:
            Itinerary text
        """
        
        interests_str = ", ".join(interests) if interests else "general sightseeing"
        
        prompt = f"""Create a {days}-day itinerary for {city} focusing on: {interests_str}.

Provide day-by-day suggestions with:
- Morning, afternoon, evening activities
- Estimated times
- Transportation tips
- Meal recommendations

Keep it practical and realistic."""

        response = await self._generate(prompt)
        return response


# Singleton instance
_gemini_fallback = None

def get_gemini_fallback(api_key: Optional[str] = None) -> GeminiFallback:
    """Get singleton GeminiFallback instance"""
    global _gemini_fallback
    if _gemini_fallback is None:
        _gemini_fallback = GeminiFallback(api_key=api_key)
    return _gemini_fallback
