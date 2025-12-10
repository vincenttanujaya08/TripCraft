"""
ImageFetcher - Async image fetching with Unsplash API

Features:
- Unsplash API integration
- In-memory caching
- Async batch loading
- Loading state tracking

Author: TripCraft Team
Date: 2024
"""

import os
import asyncio
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import httpx
from backend.models.conversation_schemas import (
    ImageLoadingState,
    ImageStatus,
    ImageBatch
)

logger = logging.getLogger(__name__)


class ImageCache:
    """Simple in-memory cache for images"""
    
    def __init__(self, ttl_hours: int = 24):
        self.cache: Dict[str, Tuple[str, datetime]] = {}
        self.ttl = timedelta(hours=ttl_hours)
    
    async def get(self, key: str) -> Optional[str]:
        """Get cached image URL"""
        if key in self.cache:
            url, cached_at = self.cache[key]
            
            # Check if still valid
            if datetime.now() - cached_at < self.ttl:
                logger.debug(f"Cache HIT: {key}")
                return url
            else:
                # Expired
                del self.cache[key]
                logger.debug(f"Cache EXPIRED: {key}")
        
        logger.debug(f"Cache MISS: {key}")
        return None
    
    async def set(self, key: str, url: str):
        """Cache image URL"""
        self.cache[key] = (url, datetime.now())
        logger.debug(f"Cache SET: {key}")
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        logger.info("Cache cleared")


class UnsplashClient:
    """Unsplash API client"""
    
    BASE_URL = "https://api.unsplash.com"
    
    def __init__(self):
        self.access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        
        if not self.access_key:
            logger.warning("UNSPLASH_ACCESS_KEY not found in environment")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("✅ Unsplash client initialized")
    
    async def search_photo(
        self, 
        query: str, 
        orientation: str = "landscape"
    ) -> Optional[str]:
        """
        Search for a photo on Unsplash
        
        Args:
            query: Search query (e.g., "Bali beach resort")
            orientation: "landscape", "portrait", or "squarish"
            
        Returns:
            Image URL or None if not found
        """
        
        if not self.enabled:
            logger.warning("Unsplash not enabled")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search/photos",
                    params={
                        "query": query,
                        "per_page": 1,
                        "orientation": orientation
                    },
                    headers={
                        "Authorization": f"Client-ID {self.access_key}"
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                
                if results:
                    image_url = results[0]["urls"]["regular"]
                    logger.info(f"✅ Found image for '{query}': {image_url[:50]}...")
                    return image_url
                else:
                    logger.warning(f"⚠️  No image found for '{query}'")
                    return None
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Unsplash API error {e.response.status_code}: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Unsplash search failed: {e}")
            return None


class ImageFetcher:
    """
    Fetch images with caching and async loading
    
    Strategy:
    1. Check cache (instant)
    2. Fetch from Unsplash API (200-500ms)
    3. Return None if failed
    """
    
    def __init__(self):
        self.cache = ImageCache()
        self.unsplash = UnsplashClient()
        self.loading_states: Dict[str, ImageLoadingState] = {}
    
    async def fetch_all_images(
        self, 
        trip_plan: Any
    ) -> Dict[str, ImageLoadingState]:
        """
        Start fetching all images for trip plan
        Returns loading states immediately, fetches in background
        
        Args:
            trip_plan: TripPlan object
            
        Returns:
            Dict of item_id -> ImageLoadingState
        """
        
        # Collect items to fetch
        items_to_fetch = []
        
        # Hotel
        if trip_plan.hotels and trip_plan.hotels.recommended_hotel:
            hotel = trip_plan.hotels.recommended_hotel
            items_to_fetch.append(("hotel", hotel.name, hotel))
        
        # Restaurants (top 10)
        if trip_plan.dining and trip_plan.dining.restaurants:
            for restaurant in trip_plan.dining.restaurants[:10]:
                items_to_fetch.append(("restaurant", restaurant.name, restaurant))
        
        # Attractions (top 10)
        if trip_plan.destination and trip_plan.destination.attractions:
            for attraction in trip_plan.destination.attractions[:10]:
                items_to_fetch.append(("attraction", attraction.name, attraction))
        
        # Initialize loading states
        self.loading_states = {}
        
        for item_type, item_name, item_data in items_to_fetch:
            item_id = f"{item_type}_{item_name.replace(' ', '_')}"
            
            self.loading_states[item_id] = ImageLoadingState(
                item_id=item_id,
                item_type=item_type,
                status=ImageStatus.LOADING,
                url=None
            )
        
        # Start background fetching (don't await!)
        asyncio.create_task(
            self._fetch_images_background(items_to_fetch)
        )
        
        logger.info(f"🖼️  Started fetching {len(items_to_fetch)} images in background")
        
        return self.loading_states
    
    async def _fetch_images_background(
        self,
        items: List[Tuple[str, str, Any]]
    ):
        """
        Background task to fetch all images
        Updates loading_states as images are fetched
        """
        
        tasks = []
        
        for item_type, item_name, item_data in items:
            task = self._fetch_single_image(item_type, item_name, item_data)
            tasks.append(task)
        
        # Execute all fetches concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Summary
        loaded = sum(1 for state in self.loading_states.values() 
                    if state.status == ImageStatus.LOADED)
        failed = sum(1 for state in self.loading_states.values() 
                    if state.status == ImageStatus.FAILED)
        
        logger.info(
            f"🖼️  Image fetching complete: "
            f"{loaded} loaded, {failed} failed, {len(self.loading_states)} total"
        )
    
    async def _fetch_single_image(
        self,
        item_type: str,
        item_name: str,
        item_data: Any
    ):
        """Fetch image for a single item"""
        
        item_id = f"{item_type}_{item_name.replace(' ', '_')}"
        state = self.loading_states[item_id]
        
        try:
            # Check cache first
            cached_url = await self.cache.get(item_name)
            
            if cached_url:
                state.status = ImageStatus.LOADED
                state.url = cached_url
                state.updated_at = datetime.now()
                logger.debug(f"✅ [CACHE] {item_id}")
                return
            
            # Build search query
            query = self._build_search_query(item_type, item_data)
            
            # Fetch from Unsplash
            image_url = await self.unsplash.search_photo(query)
            
            if image_url:
                state.status = ImageStatus.LOADED
                state.url = image_url
                state.updated_at = datetime.now()
                
                # Cache it
                await self.cache.set(item_name, image_url)
                
                logger.debug(f"✅ [UNSPLASH] {item_id}")
            else:
                state.status = ImageStatus.FAILED
                state.error = "No image found"
                state.updated_at = datetime.now()
                
                logger.debug(f"❌ [NOT FOUND] {item_id}")
        
        except Exception as e:
            state.status = ImageStatus.FAILED
            state.error = str(e)
            state.updated_at = datetime.now()
            
            logger.error(f"❌ [ERROR] {item_id}: {e}")
    
    def _build_search_query(self, item_type: str, item_data: Any) -> str:
        """
        Build effective Unsplash search query
        
        Strategy:
        - Hotel: "{location} {type} hotel resort"
        - Restaurant: "{cuisine} food restaurant"
        - Attraction: "{name} {location}"
        """
        
        if item_type == "hotel":
            # Try to get location from address or use generic
            location = getattr(item_data, 'address', None) or getattr(item_data, 'name', '')
            hotel_type = getattr(item_data, 'type', 'hotel')
            
            # Extract city from address if possible
            if location:
                # Simple extraction: take first word
                location_parts = location.split(',')
                city = location_parts[0] if location_parts else location
            else:
                city = ""
            
            return f"{city} {hotel_type} resort luxury".strip()
        
        elif item_type == "restaurant":
            cuisine = getattr(item_data, 'cuisine', 'food')
            return f"{cuisine} restaurant food dining"
        
        elif item_type == "attraction":
            name = getattr(item_data, 'name', '')
            attr_type = getattr(item_data, 'type', '')
            
            return f"{name} {attr_type} travel destination".strip()
        
        return "travel destination"
    
    def get_image_batch_status(self) -> ImageBatch:
        """Get current status of all images"""
        
        loaded_count = sum(
            1 for state in self.loading_states.values() 
            if state.status == ImageStatus.LOADED
        )
        
        failed_count = sum(
            1 for state in self.loading_states.values() 
            if state.status == ImageStatus.FAILED
        )
        
        return ImageBatch(
            images=self.loading_states,
            total_count=len(self.loading_states),
            loaded_count=loaded_count,
            failed_count=failed_count
        )
    
    def get_loading_states(self) -> Dict[str, ImageLoadingState]:
        """Get current loading states"""
        return self.loading_states.copy()


# Singleton instance
_image_fetcher = None

def get_image_fetcher() -> ImageFetcher:
    """Get singleton ImageFetcher instance"""
    global _image_fetcher
    if _image_fetcher is None:
        _image_fetcher = ImageFetcher()
    return _image_fetcher