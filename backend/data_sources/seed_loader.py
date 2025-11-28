"""
SeedLoader - Loads travel data from JSON seed files
Part of 3-tier fallback: APIs → Seed Data → LLM
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SeedLoader:
    """Loads and queries seed data from JSON files"""
    
    def __init__(self, seed_data_dir: str = None):
        """
        Initialize SeedLoader
        
        Args:
            seed_data_dir: Path to seed_data directory. If None, auto-detects.
        """
        if seed_data_dir is None:
            # Auto-detect: backend/data_sources/ -> ../../seed_data/
            current_file = Path(__file__)
            self.seed_dir = current_file.parent.parent.parent / "seed_data"
        else:
            self.seed_dir = Path(seed_data_dir)
        
        # Cache loaded data
        self._destinations_cache: Optional[List[Dict]] = None
        self._hotels_cache: Optional[List[Dict]] = None
        self._restaurants_cache: Optional[List[Dict]] = None
        self._flights_cache: Optional[List[Dict]] = None
        
        logger.info(f"SeedLoader initialized with seed_dir: {self.seed_dir}")
    
    def _load_json(self, filename: str) -> List[Dict]:
        """Load JSON file and return data"""
        filepath = self.seed_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Seed file not found: {filepath}")
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract array from wrapper object
            # JSON structure: {"destinations": [...]} or {"hotels": [...]}
            if isinstance(data, dict):
                # Get the first key's value (the actual array)
                key = list(data.keys())[0]
                data = data[key]
            
            logger.info(f"Loaded {len(data)} entries from {filename}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {filename}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return []
    
    def load_destinations(self) -> List[Dict]:
        """Load all destinations from seed data"""
        if self._destinations_cache is None:
            self._destinations_cache = self._load_json("destinations.json")
        return self._destinations_cache
    
    def load_hotels(self) -> List[Dict]:
        """Load all hotels from seed data"""
        if self._hotels_cache is None:
            self._hotels_cache = self._load_json("hotels.json")
        return self._hotels_cache
    
    def load_restaurants(self) -> List[Dict]:
        """Load all restaurants from seed data"""
        if self._restaurants_cache is None:
            self._restaurants_cache = self._load_json("restaurants.json")
        return self._restaurants_cache
    
    def load_flights(self) -> List[Dict]:
        """Load all flight routes from seed data"""
        if self._flights_cache is None:
            self._flights_cache = self._load_json("flights.json")
        return self._flights_cache

    # ========== QUERY METHODS ==========
    
    def get_destination(self, city: str) -> Optional[Dict]:
        """
        Get destination info by city name
        
        Args:
            city: City name (case-insensitive)
            
        Returns:
            Destination dict or None if not found
        """
        destinations = self.load_destinations()
        city_lower = city.lower()
        
        for dest in destinations:
            # Check both 'name' and 'city' fields for compatibility
            dest_name = dest.get("name", dest.get("city", "")).lower()
            if dest_name == city_lower:
                logger.info(f"Found destination: {dest.get('name', dest.get('city'))}, {dest['country']}")
                return dest
        
        logger.warning(f"Destination not found: {city}")
        return None
    
    def get_hotels_by_city(
        self, 
        city: str, 
        category: Optional[str] = None,
        max_price: Optional[float] = None
    ) -> List[Dict]:
        """
        Get hotels in a city with optional filters
        
        Args:
            city: City name
            category: Filter by category (budget/mid-range/luxury)
            max_price: Maximum price per night
            
        Returns:
            List of matching hotels
        """
        hotels = self.load_hotels()
        city_lower = city.lower()
        
        results = []
        for hotel in hotels:
            hotel_city = hotel.get("city") or hotel.get("destination")
            if not hotel_city or hotel_city.lower() != city_lower:
                continue
            
            # Apply filters
            if category and hotel.get("category") != category:
                continue
            
            if max_price and hotel.get("price_per_night", 0) > max_price:
                continue
            
            results.append(hotel)
        
        logger.info(f"Found {len(results)} hotels in {city}")
        return results
    
    def get_restaurants_by_city(
        self,
        city: str,
        cuisine: Optional[str] = None,
        price_range: Optional[str] = None,
        meal_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get restaurants in a city with optional filters
        
        Args:
            city: City name
            cuisine: Filter by cuisine type
            price_range: Filter by price range ($, $$, $$$, $$$$)
            meal_type: Filter by meal type (breakfast/lunch/dinner/cafe)
            
        Returns:
            List of matching restaurants
        """
        restaurants = self.load_restaurants()
        city_lower = city.lower()
        
        results = []
        for restaurant in restaurants:
            rest_city = restaurant.get("city") or restaurant.get("destination")
            if not rest_city or rest_city.lower() != city_lower:
                continue
            
            # Apply filters
            if cuisine and cuisine.lower() not in restaurant.get("cuisine", "").lower():
                continue
            
            if price_range and restaurant.get("price_range") != price_range:
                continue
            
            if meal_type:
                meal_types = restaurant.get("meal_type", [])
                if meal_type not in meal_types:
                    continue
            
            results.append(restaurant)
        
        logger.info(f"Found {len(results)} restaurants in {city}")
        return results
    
    def get_flight_routes(
        self,
        origin: Optional[str] = None,
        destination: Optional[str] = None
    ) -> List[Dict]:
        """
        Get flight routes with optional origin/destination filters
        
        Args:
            origin: Origin city (partial match)
            destination: Destination city (partial match)
            
        Returns:
            List of matching flight routes
        """
        flights = self.load_flights()
        
        results = []
        for flight in flights:
            route = flight.get("route", "")
            
            # Apply filters (case-insensitive partial match)
            if origin and origin.lower() not in route.lower():
                continue
            
            if destination and destination.lower() not in route.lower().split("-")[-1]:
                continue
            
            results.append(flight)
        
        logger.info(f"Found {len(results)} flight routes")
        return results
    
    def get_available_cities(self) -> List[str]:
        """Get list of all available destination cities"""
        destinations = self.load_destinations()
        cities = [d.get("city") for d in destinations if d.get("city")]
        return sorted(cities)
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about loaded seed data"""
        return {
            "destinations": len(self.load_destinations()),
            "hotels": len(self.load_hotels()),
            "restaurants": len(self.load_restaurants()),
            "flight_routes": len(self.load_flights())
        }
    
    def get_flights(self, origin: str, destination: str) -> Optional[Dict]:
        """
        Get flights between two cities (transforms seed data to expected format)
        """
        flights = self.load_flights()
        origin_lower = origin.lower()
        dest_lower = destination.lower()
        
        # Find matching route
        for flight_route in flights:
            route = flight_route.get("route", "").lower()
            parts = route.split("-")
            
            if len(parts) != 2:
                continue
            
            route_origin = parts[0].strip()
            route_dest = parts[1].strip()
            
            # Check if route matches
            if origin_lower in route_origin and dest_lower in route_dest:
                logger.info(f"Found seed route: {flight_route.get('route')}")
                
                # Get airline code
                airline_name = flight_route.get("airline", "Unknown")
                airline_map = {
                    "garuda indonesia": "GA",
                    "lion air": "JT",
                    "airasia": "AK",
                    "singapore airlines": "SQ"
                }
                airline_code = airline_map.get(airline_name.lower(), "XX")
                
                # Get duration and prices
                duration_min = int(flight_route.get("duration_hours", 2) * 60)
                price_min = flight_route.get("price_range_min", 1000000)
                price_max = flight_route.get("price_range_max", 2000000)
                price_mid = (price_min + price_max) / 2
                
                # Calculate arrival times
                from datetime import datetime, timedelta
                
                def calc_arrival(dept_time, duration):
                    dept = datetime.strptime(dept_time, "%H:%M")
                    arr = dept + timedelta(minutes=duration)
                    return arr.strftime("%H:%M")
                
                # Generate outbound flights
                outbound = [
                    {
                        "airline": airline_code,
                        "flight_number": f"{airline_code}401",
                        "departure_time": "08:00",
                        "arrival_time": calc_arrival("08:00", duration_min),
                        "duration_minutes": duration_min,
                        "price": price_max,
                        "class": "economy"
                    },
                    {
                        "airline": airline_code,
                        "flight_number": f"{airline_code}403",
                        "departure_time": "14:00",
                        "arrival_time": calc_arrival("14:00", duration_min),
                        "duration_minutes": duration_min,
                        "price": price_mid,
                        "class": "economy"
                    },
                    {
                        "airline": airline_code,
                        "flight_number": f"{airline_code}405",
                        "departure_time": "19:00",
                        "arrival_time": calc_arrival("19:00", duration_min),
                        "duration_minutes": duration_min,
                        "price": price_min,
                        "class": "economy"
                    }
                ]
                
                # Generate return flights
                return_flights = [
                    {
                        "airline": airline_code,
                        "flight_number": f"{airline_code}402",
                        "departure_time": "09:00",
                        "arrival_time": calc_arrival("09:00", duration_min),
                        "duration_minutes": duration_min,
                        "price": price_max,
                        "class": "economy"
                    },
                    {
                        "airline": airline_code,
                        "flight_number": f"{airline_code}404",
                        "departure_time": "15:00",
                        "arrival_time": calc_arrival("15:00", duration_min),
                        "duration_minutes": duration_min,
                        "price": price_mid,
                        "class": "economy"
                    },
                    {
                        "airline": airline_code,
                        "flight_number": f"{airline_code}406",
                        "departure_time": "20:00",
                        "arrival_time": calc_arrival("20:00", duration_min),
                        "duration_minutes": duration_min,
                        "price": price_min,
                        "class": "economy"
                    }
                ]
                
                return {
                    "outbound": outbound,
                    "return": return_flights
                }
        
        logger.warning(f"No flights found for {origin} → {destination}")
        return None


# Singleton instance
_seed_loader_instance = None

def get_seed_loader() -> SeedLoader:
    """Get singleton SeedLoader instance"""
    global _seed_loader_instance
    if _seed_loader_instance is None:
        _seed_loader_instance = SeedLoader()
    return _seed_loader_instance