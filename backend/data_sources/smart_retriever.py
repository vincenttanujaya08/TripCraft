"""
SmartRetriever - Orchestrates 3-tier data fallback strategy
Priority: APIs → Seed Data → LLM Fallback
"""

import logging
from typing import Optional, List, Dict, Any, Literal
from .seed_loader import get_seed_loader
from .opentripmap_client import get_opentripmap_client
from .gemini_fallback import get_gemini_fallback

logger = logging.getLogger(__name__)

DataSource = Literal["api", "seed", "llm_fallback"]


class SmartRetriever:
    """Smart data retriever with 3-tier fallback strategy"""
    
    def __init__(
        self,
        opentripmap_key: Optional[str] = None,
        gemini_key: Optional[str] = None
    ):
        """
        Initialize SmartRetriever
        
        Args:
            opentripmap_key: OpenTripMap API key (optional)
            gemini_key: Gemini API key (required)
        """
        self.seed_loader = get_seed_loader()
        self.opentripmap = get_opentripmap_client(api_key=opentripmap_key)
        self.gemini = get_gemini_fallback(api_key=gemini_key)
        
        logger.info("SmartRetriever initialized with 3-tier fallback")
    
    # ========== DESTINATION ==========
    
    async def get_destination(self, city: str) -> tuple[Optional[Dict], DataSource]:
        """
        Get destination info with fallback
        
        Returns:
            (destination_data, data_source)
        """
        
        # Tier 1: Try seed data first (fastest)
        logger.info(f"[Tier 1] Checking seed data for {city}")
        seed_data = self.seed_loader.get_destination(city)
        
        if seed_data:
            logger.info(f"✓ Found {city} in seed data")
            return seed_data, "seed"
        
        # Tier 2: Try OpenTripMap API (if enabled)
        if self.opentripmap.enabled:
            logger.info(f"[Tier 2] Trying OpenTripMap API for {city}")
            # Note: OpenTripMap doesn't provide full destination info,
            # so we skip to Tier 3 for destinations
            pass
        
        # Tier 3: LLM fallback
        logger.info(f"[Tier 3] Using Gemini LLM for {city}")
        llm_data = await self.gemini.generate_destination_info(city)
        
        if llm_data:
            logger.info(f"✓ Generated {city} info via LLM")
            return llm_data, "llm_fallback"
        
        logger.error(f"✗ All tiers failed for destination: {city}")
        return None, "llm_fallback"
    
    # ========== HOTELS ==========
    
    async def get_hotels(
        self,
        city: str,
        budget: str = "mid-range",
        max_price: Optional[float] = None,
        count: int = 5
    ) -> tuple[List[Dict], DataSource]:
        """
        Get hotel recommendations with fallback
        
        Args:
            city: City name
            budget: Budget category
            max_price: Maximum price filter
            count: Number of hotels to return
            
        Returns:
            (hotels_list, data_source)
        """
        
        # Tier 1: Seed data
        logger.info(f"[Tier 1] Checking seed hotels in {city}")
        seed_hotels = self.seed_loader.get_hotels_by_city(
            city=city,
            category=budget,
            max_price=max_price
        )
        
        if seed_hotels:
            logger.info(f"✓ Found {len(seed_hotels)} hotels in seed data")
            return seed_hotels[:count], "seed"
        
        # Tier 2: API (skipped - would need hotel API like Booking.com)
        
        # Tier 3: LLM fallback
        logger.info(f"[Tier 3] Generating hotels via LLM for {city}")
        llm_hotels = await self.gemini.generate_hotels(
            city=city,
            budget=budget,
            count=count
        )
        
        if llm_hotels:
            logger.info(f"✓ Generated {len(llm_hotels)} hotels via LLM")
            return llm_hotels, "llm_fallback"
        
        logger.error(f"✗ All tiers failed for hotels in {city}")
        return [], "llm_fallback"
    
    # ========== RESTAURANTS ==========
    
    async def get_restaurants(
        self,
        city: str,
        cuisine: Optional[str] = None,
        price_range: Optional[str] = None,
        count: int = 6
    ) -> tuple[List[Dict], DataSource]:
        """
        Get restaurant recommendations with fallback
        
        Args:
            city: City name
            cuisine: Cuisine filter
            price_range: Price range filter
            count: Number of restaurants
            
        Returns:
            (restaurants_list, data_source)
        """
        
        # Tier 1: Seed data
        logger.info(f"[Tier 1] Checking seed restaurants in {city}")
        seed_restaurants = self.seed_loader.get_restaurants_by_city(
            city=city,
            cuisine=cuisine,
            price_range=price_range
        )
        
        if seed_restaurants:
            logger.info(f"✓ Found {len(seed_restaurants)} restaurants in seed data")
            return seed_restaurants[:count], "seed"
        
        # Tier 2: API (skipped - would need restaurant API)
        
        # Tier 3: LLM fallback
        logger.info(f"[Tier 3] Generating restaurants via LLM for {city}")
        llm_restaurants = await self.gemini.generate_restaurants(
            city=city,
            cuisine=cuisine,
            count=count
        )
        
        if llm_restaurants:
            logger.info(f"✓ Generated {len(llm_restaurants)} restaurants via LLM")
            return llm_restaurants, "llm_fallback"
        
        logger.error(f"✗ All tiers failed for restaurants in {city}")
        return [], "llm_fallback"
    
    # ========== FLIGHTS ==========
    
    async def get_flights(
        self,
        origin: str,
        destination: str
    ) -> tuple[Optional[Dict], DataSource]:
        """
        Get flight information with fallback
        
        Args:
            origin: Origin city
            destination: Destination city
            
        Returns:
            (flight_data, data_source)
        """
        
        # Tier 1: Seed data
        logger.info(f"[Tier 1] Checking seed flights: {origin} → {destination}")
        seed_flights = self.seed_loader.get_flight_routes(
            origin=origin,
            destination=destination
        )
        
        if seed_flights:
            logger.info(f"✓ Found {len(seed_flights)} flight routes in seed data")
            # Return first match
            return seed_flights[0], "seed"
        
        # Tier 2: API (skipped - would need flight API like Skyscanner)
        
        # Tier 3: LLM fallback
        logger.info(f"[Tier 3] Generating flight estimate via LLM")
        llm_flight = await self.gemini.generate_flight_estimate(
            origin=origin,
            destination=destination
        )
        
        if llm_flight:
            logger.info(f"✓ Generated flight estimate via LLM")
            return llm_flight, "llm_fallback"
        
        logger.error(f"✗ All tiers failed for flights {origin} → {destination}")
        return None, "llm_fallback"
    
    # ========== ATTRACTIONS (API-focused) ==========
    
    async def get_attractions(
        self,
        city: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        count: int = 10
    ) -> tuple[List[Dict], DataSource]:
        """
        Get attractions/POI with API-first approach
        
        Args:
            city: City name
            lat, lon: Coordinates (optional, for API)
            count: Number of attractions
            
        Returns:
            (attractions_list, data_source)
        """
        
        # Tier 1: Try API first (if coordinates available)
        if self.opentripmap.enabled and lat and lon:
            logger.info(f"[Tier 1] Trying OpenTripMap API for {city}")
            api_attractions = await self.opentripmap.search_attractions_by_city(
                city_name=city,
                lat=lat,
                lon=lon,
                limit=count
            )
            
            if api_attractions:
                logger.info(f"✓ Found {len(api_attractions)} attractions via API")
                return api_attractions, "api"
        
        # Tier 2: Seed data (from destination info)
        logger.info(f"[Tier 2] Checking seed destination for {city}")
        dest_data = self.seed_loader.get_destination(city)
        
        if dest_data and "attractions" in dest_data:
            attractions = dest_data["attractions"]
            logger.info(f"✓ Found {len(attractions)} attractions in seed data")
            return attractions[:count], "seed"
        
        # Tier 3: LLM fallback
        logger.info(f"[Tier 3] Generating attractions via LLM for {city}")
        dest_info = await self.gemini.generate_destination_info(city)
        
        if dest_info and "attractions" in dest_info:
            logger.info(f"✓ Generated attractions via LLM")
            return dest_info["attractions"], "llm_fallback"
        
        logger.error(f"✗ All tiers failed for attractions in {city}")
        return [], "llm_fallback"
    
    # ========== UTILITY ==========
    
    def get_available_cities(self) -> List[str]:
        """Get list of cities with seed data"""
        return self.seed_loader.get_available_cities()
    
    def get_data_stats(self) -> Dict[str, Any]:
        """Get statistics about available data"""
        return {
            "seed_data": self.seed_loader.get_stats(),
            "api_enabled": {
                "opentripmap": self.opentripmap.enabled
            }
        }


# Singleton instance
_smart_retriever = None

def get_smart_retriever(
    opentripmap_key: Optional[str] = None,
    gemini_key: Optional[str] = None
) -> SmartRetriever:
    """Get singleton SmartRetriever instance"""
    global _smart_retriever
    if _smart_retriever is None:
        _smart_retriever = SmartRetriever(
            opentripmap_key=opentripmap_key,
            gemini_key=gemini_key
        )
    return _smart_retriever
