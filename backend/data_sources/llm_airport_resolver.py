"""
LLM Airport Code Resolver - Uses Gemini to find airport codes
Handles ANY city name without hardcoded mappings
"""

import os
import json
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Try to import Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI not available")


class LLMAirportResolver:
    """Use LLM to resolve city names to airport codes"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM resolver
        
        Args:
            api_key: Gemini API key (or get from env GEMINI_API_KEY)
        """
        if not GEMINI_AVAILABLE:
            logger.warning("Gemini not available - LLM resolver disabled")
            self.enabled = False
            return
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found - LLM resolver disabled")
            self.enabled = False
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
            self.enabled = True
            logger.info("✅ LLM Airport Resolver initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.enabled = False
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    def get_airport_code(self, city_name: str) -> Optional[str]:
        """
        Get IATA airport code using LLM
        
        Args:
            city_name: City name (any language, any format)
            
        Returns:
            3-letter IATA code or None
        """
        
        if not self.enabled:
            return None
        
        try:
            prompt = f"""You are an aviation expert. Find the main international airport IATA code for this city.

City: {city_name}

Rules:
1. Return ONLY the 3-letter IATA code
2. Choose the MAIN international airport (not regional)
3. If multiple airports, choose the largest/busiest
4. If city not found or no airport, return "NONE"
5. DO NOT explain, just return the code

Examples:
- Jakarta → CGK
- Bali → DPS
- New York → JFK
- Yogyakarta → JOG

Your answer (ONLY the code):"""

            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,  # Low temperature for consistency
                    "top_p": 0.8,
                    "max_output_tokens": 10,  # Only need 3-4 characters
                }
            )
            
            # Parse response
            code = response.text.strip().upper()
            
            # Validate format
            if code == "NONE" or len(code) != 3 or not code.isalpha():
                logger.warning(f"LLM returned invalid code for {city_name}: {code}")
                return None
            
            logger.info(f"✅ LLM resolved: {city_name} → {code}")
            return code
            
        except Exception as e:
            logger.error(f"LLM resolution failed for {city_name}: {e}")
            return None
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    def get_airport_code_with_validation(self, city_name: str) -> Optional[dict]:
        """
        Get airport code with additional validation info
        
        Returns:
            {
                "code": "CGK",
                "airport_name": "Soekarno-Hatta International Airport",
                "city": "Jakarta",
                "country": "Indonesia",
                "confidence": "high"
            }
        """
        
        if not self.enabled:
            return None
        
        try:
            prompt = f"""You are an aviation expert. Find airport information for this city.

City: {city_name}

Return ONLY valid JSON in this exact format (no markdown, no explanations):
{{
  "code": "XXX",
  "airport_name": "Full Airport Name",
  "city": "City Name",
  "country": "Country",
  "confidence": "high|medium|low"
}}

If no major airport exists, return:
{{
  "code": null,
  "airport_name": null,
  "city": "{city_name}",
  "country": "Unknown",
  "confidence": "low"
}}

Examples:
Jakarta → {{"code": "CGK", "airport_name": "Soekarno-Hatta International Airport", "city": "Jakarta", "country": "Indonesia", "confidence": "high"}}
Bali → {{"code": "DPS", "airport_name": "Ngurah Rai International Airport", "city": "Denpasar", "country": "Indonesia", "confidence": "high"}}
Malang → {{"code": null, "airport_name": null, "city": "Malang", "country": "Indonesia", "confidence": "low"}}

Your JSON response:"""

            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "max_output_tokens": 150,
                }
            )
            
            # Parse JSON response
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            data = json.loads(text)
            
            if data.get("code"):
                logger.info(
                    f"✅ LLM resolved with validation: {city_name} → "
                    f"{data['code']} ({data['airport_name']})"
                )
            else:
                logger.warning(f"⚠️  No airport found for: {city_name}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return None
            
        except Exception as e:
            logger.error(f"LLM validation failed for {city_name}: {e}")
            return None


# Singleton instance
_llm_resolver = None

def get_llm_resolver(api_key: Optional[str] = None) -> LLMAirportResolver:
    """Get singleton LLM resolver instance"""
    global _llm_resolver
    if _llm_resolver is None:
        _llm_resolver = LLMAirportResolver(api_key=api_key)
    return _llm_resolver