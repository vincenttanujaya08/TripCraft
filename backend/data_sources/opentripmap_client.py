"""
OpenTripMapClient - Fetches Points of Interest from OpenTripMap API
Optional data source (free API, no key required for basic usage)
"""

import httpx
import logging
from typing import Optional, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class OpenTripMapClient:
    """Client for OpenTripMap API"""
    
    BASE_URL = "https://api.opentripmap.com/0.1/en/places"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenTripMap client
        
        Args:
            api_key: OpenTripMap API key (optional for basic usage)
        """
        self.api_key = api_key
        self.enabled = api_key is not None
        
        if not self.enabled:
            logger.warning("OpenTripMap API key not provided - API features disabled")
        else:
            logger.info("OpenTripMap client initialized")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any]
    ) -> Optional[Dict]:
        """Make HTTP request to OpenTripMap API with retry logic"""
        
        if not self.enabled:
            return None
        
        # Add API key to params
        params["apikey"] = self.api_key
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenTripMap API error {e.response.status_code}: {e}")
            return None
        
        except httpx.TimeoutException:
            logger.error("OpenTripMap API timeout")
            return None
        
        except Exception as e:
            logger.error(f"OpenTripMap API request failed: {e}")
            return None
    
    async def get_places_by_bbox(
        self,
        lon_min: float,
        lat_min: float,
        lon_max: float,
        lat_max: float,
        kinds: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get places within bounding box
        
        Args:
            lon_min, lat_min, lon_max, lat_max: Bounding box coordinates
            kinds: Place categories (e.g., "interesting_places,tourist_facilities")
            limit: Maximum number of results
            
        Returns:
            List of place dictionaries
        """
        
        params = {
            "lon_min": lon_min,
            "lat_min": lat_min,
            "lon_max": lon_max,
            "lat_max": lat_max,
            "limit": limit,
            "format": "json"
        }
        
        if kinds:
            params["kinds"] = kinds
        
        result = await self._make_request("bbox", params)
        
        if result and isinstance(result, list):
            logger.info(f"Found {len(result)} places via OpenTripMap")
            return result
        
        return []
    
    async def get_places_by_radius(
        self,
        lat: float,
        lon: float,
        radius: int = 1000,
        kinds: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get places within radius from point
        
        Args:
            lat, lon: Center coordinates
            radius: Search radius in meters
            kinds: Place categories
            limit: Maximum number of results
            
        Returns:
            List of place dictionaries
        """
        
        params = {
            "lat": lat,
            "lon": lon,
            "radius": radius,
            "limit": limit,
            "format": "json"
        }
        
        if kinds:
            params["kinds"] = kinds
        
        result = await self._make_request("radius", params)
        
        if result and isinstance(result, list):
            logger.info(f"Found {len(result)} places via OpenTripMap")
            return result
        
        return []
    
    async def get_place_details(self, xid: str) -> Optional[Dict]:
        """
        Get detailed information about a place
        
        Args:
            xid: Place ID from OpenTripMap
            
        Returns:
            Place details dictionary
        """
        
        result = await self._make_request(f"xid/{xid}", {})
        
        if result:
            logger.info(f"Got details for place {xid}")
        
        return result
    
    async def search_attractions_by_city(
        self,
        city_name: str,
        lat: float,
        lon: float,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search for tourist attractions in a city
        
        Args:
            city_name: City name (for logging)
            lat, lon: City coordinates
            limit: Maximum results
            
        Returns:
            List of attractions
        """
        
        # Search within 10km radius
        places = await self.get_places_by_radius(
            lat=lat,
            lon=lon,
            radius=10000,
            kinds="interesting_places,tourist_facilities,cultural,historic",
            limit=limit
        )
        
        # Enrich with details (optional, can be slow)
        # enriched = []
        # for place in places[:5]:  # Only enrich top 5
        #     details = await self.get_place_details(place.get("xid"))
        #     if details:
        #         enriched.append(details)
        
        return places


# Singleton instance
_opentripmap_client = None

def get_opentripmap_client(api_key: Optional[str] = None) -> OpenTripMapClient:
    """Get singleton OpenTripMapClient instance"""
    global _opentripmap_client
    if _opentripmap_client is None:
        _opentripmap_client = OpenTripMapClient(api_key=api_key)
    return _opentripmap_client
