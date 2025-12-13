"""
SmartRetriever - Updated with restaurant retrieval and Amadeus API for flights
Priority: Amadeus API → Seed Data → LLM Fallback
UPDATED: Added get_restaurants() method
"""

import logging
from typing import Optional, List, Dict, Any, Literal, Tuple
from datetime import date
from .seed_loader import get_seed_loader
from .opentripmap_client import get_opentripmap_client
# from .gemini_fallback import get_gemini_fallback <-- REMOVED
from .llm_fallback import get_llm_fallback  # <-- ADDED
from .amadeus_client import get_amadeus_client

logger = logging.getLogger(__name__)

DataSource = Literal["api", "seed", "llm_fallback"]


class SmartRetriever:
    """Smart data retriever with 3-tier fallback strategy"""
    
    def __init__(
        self,
        opentripmap_key: Optional[str] = None,
        gemini_key: Optional[str] = None, # kept for signature compat but unused
        amadeus_key: Optional[str] = None,
        amadeus_secret: Optional[str] = None
    ):
        """
        Initialize SmartRetriever
        
        Args:
            opentripmap_key: OpenTripMap API key (optional)
            gemini_key: Gemini API key (DEPRECATED/UNUSED)
            amadeus_key: Amadeus API key (optional, for real flight data)
            amadeus_secret: Amadeus API secret (optional)
        """
        self.seed_loader = get_seed_loader()
        self.opentripmap = get_opentripmap_client(api_key=opentripmap_key)
        
        # Use LLM Fallback (Gemini)
        self.llm = get_llm_fallback()
        
        self.amadeus = get_amadeus_client(api_key=amadeus_key, api_secret=amadeus_secret)
        
        logger.info(
            f"SmartRetriever initialized - "
            f"Amadeus: {'enabled' if self.amadeus.enabled else 'disabled'}, "
            f"OpenTripMap: {'enabled' if self.opentripmap.enabled else 'disabled'}, "
            f"LLM: {'enabled' if self.llm.enabled else 'disabled'}"
        )
    
    # ========================================
    # RESTAURANTS (NEW!)
    # ========================================
    
    async def get_restaurants(
        self,
        city: str,
        cuisine: Optional[str] = None,
        price_range: Optional[str] = None,
        meal_type: Optional[str] = None,
        count: int = 20
    ) -> Tuple[List[Dict], DataSource]:
        """
        Get restaurant options with 3-tier fallback
        
        PRIORITY:
        Tier 1: External API (if available - not implemented yet)
        Tier 2: Seed Data
        Tier 3: LLM Fallback
        
        Args:
            city: City name (e.g., "Bali", "Tokyo")
            cuisine: Optional cuisine filter (e.g., "Indonesian", "Japanese")
            price_range: Optional price filter ("$", "$$", "$$$", "$$$$")
            meal_type: Optional meal type filter ("breakfast", "lunch", "dinner")
            count: Number of restaurants to return
            
        Returns:
            (restaurants_list, data_source)
        """
        
        # ========================================
        # TIER 1: External API (Future)
        # ========================================
        # TODO: Add Yelp/Google Places API integration
        
        # ========================================
        # TIER 2: Seed Data
        # ========================================
        logger.info(f"[Tier 2] Checking seed data for restaurants in {city}")
        
        seed_restaurants = self.seed_loader.get_restaurants_by_city(
            city=city,
            cuisine=cuisine,
            price_range=price_range,
            meal_type=meal_type
        )
        
        if seed_restaurants:
            logger.info(f"✓ Found {len(seed_restaurants)} restaurants in seed data")
            
            # Return up to 'count' restaurants
            return seed_restaurants[:count], "seed"
        
        # ========================================
        # TIER 3: LLM Fallback
        # ========================================
        logger.info(f"[Tier 3] Generating restaurants via LLM for {city}")
        
        llm_restaurants = await self.llm.generate_restaurants(
            city=city,
            cuisine=cuisine,
            count=count
        )
        
        if llm_restaurants:
            logger.info(f"✓ Generated {len(llm_restaurants)} restaurants via LLM")
            return llm_restaurants, "llm_fallback"
        
        logger.error(f"✗ All tiers failed for restaurants in {city}")
        return [], "llm_fallback"
    
    # ========================================
    # FLIGHTS (Existing - keep as is)
    # ========================================
    
    async def get_flights(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None,
        travelers: int = 1,
        travel_class: str = "economy"
    ) -> Tuple[List[Dict], DataSource]:
        """
        Get flight options with Amadeus API first, then fallback
        
        NEW PRIORITY:
        Tier 1: Amadeus API (real-time flight data) ✈️
        Tier 2: Seed Data (fallback)
        Tier 3: LLM (generate estimate)
        
        Args:
            origin: Origin city name (e.g., "Jakarta")
            destination: Destination city name (e.g., "Bali")
            departure_date: Departure date
            return_date: Return date (optional)
            travelers: Number of passengers
            travel_class: economy/business/first
            
        Returns:
            (flights_list, data_source)
        """
        
        # ========================================
        # TIER 1: Try Amadeus API (if enabled)
        # ========================================
        if self.amadeus and self.amadeus.enabled:
            logger.info(f"[Tier 1] Trying Amadeus API for {origin} → {destination}")
            
            try:
                # Convert city names to airport codes
                origin_code = self.amadeus.get_airport_code(origin)
                dest_code = self.amadeus.get_airport_code(destination)
                
                if origin_code and dest_code:
                    logger.info(f"Airport codes: {origin} ({origin_code}) → {destination} ({dest_code})")
                    
                    # Map travel class
                    class_map = {
                        'economy': 'ECONOMY',
                        'business': 'BUSINESS',
                        'first': 'FIRST',
                        'premium_economy': 'PREMIUM_ECONOMY'
                    }
                    amadeus_class = class_map.get(travel_class.lower(), 'ECONOMY')
                    
                    # Search flights
                    flights = await self.amadeus.search_flights(
                        origin=origin_code,
                        destination=dest_code,
                        departure_date=departure_date,
                        return_date=return_date,
                        adults=travelers,
                        travel_class=amadeus_class,
                        currency='IDR',
                        max_results=5
                    )
                    
                    if flights:
                        logger.info(f"✓ Found {len(flights)} flights via Amadeus API")
                        return flights, "api"
                    else:
                        logger.warning("Amadeus returned no flights")
                else:
                    logger.warning(f"Could not resolve airport codes for {origin}/{destination}")
            
            except Exception as e:
                logger.error(f"Amadeus API failed: {e}")
        
        # ========================================
        # TIER 2: Seed Data Fallback
        # ========================================
        logger.info(f"[Tier 2] Checking seed data for {origin} → {destination}")
        
        seed_flights = self.seed_loader.get_flight_routes(
            origin=origin,
            destination=destination
        )
        
        if seed_flights:
            logger.info(f"✓ Found {len(seed_flights)} flight routes in seed data")
            
            # Convert seed format to standard format
            converted_flights = []
            for flight in seed_flights:
                # Build departure and arrival datetime
                dep_time = flight.get('departure_time', '10:00')
                arr_time = flight.get('arrival_time', '12:00')
                
                # Create full datetime strings
                departure_datetime = f"{departure_date}T{dep_time}:00"
                
                # Calculate arrival datetime (might be next day)
                # Calculate arrival datetime (might be next day)
                from datetime import datetime, timedelta
                dep_dt = datetime.fromisoformat(departure_datetime)
                try:
                    duration_hours = float(flight.get('duration_hours', 2))
                except (TypeError, ValueError):
                    duration_hours = 2.0  # Default fallback
                arr_dt = dep_dt + timedelta(hours=float(duration_hours or 2))
                arrival_datetime = arr_dt.isoformat()
                
                # Calculate average price
                min_price = flight.get('price_range_min', 1000000)
                max_price = flight.get('price_range_max', 2000000)
                avg_price = (min_price + max_price) / 2
                
                converted = {
                    'airline': flight.get('airline', 'Unknown'),
                    'airline_code': self._get_airline_code(flight.get('airline', '')),
                    'flight_number': flight.get('flight_number', 'XX000'),
                    'departure_airport': flight.get('departure_airport', origin[:3].upper()),
                    'arrival_airport': flight.get('arrival_airport', destination[:3].upper()),
                    'departure_time': departure_datetime,
                    'arrival_time': arrival_datetime,
                    'duration_minutes': int(duration_hours * 60),
                    'duration_hours': duration_hours,
                    'price': avg_price,
                    'currency': 'IDR',
                    'stops': 0,
                    'cabin_class': travel_class if travel_class in ['economy', 'business', 'first'] else 'economy',
                    'source': 'seed'
                }
                converted_flights.append(converted)
            
            # If return_date provided, generate return flights
            if return_date and converted_flights:
                return_flights = []
                for flight in converted_flights[:3]:  # Generate return for top 3
                    ret_time = flight.get('departure_time', '10:00').split('T')[1].split(':00')[0] + ':00'
                    arr_ret_time = flight.get('arrival_time', '12:00').split('T')[1].split(':00')[0] + ':00'
                    
                    return_datetime = f"{return_date}T{ret_time}:00"
                    
                    from datetime import datetime, timedelta
                    ret_dt = datetime.fromisoformat(return_datetime)
                    duration_hours = flight['duration_hours']
                    arr_ret_dt = ret_dt + timedelta(hours=float(duration_hours or 2))
                    arrival_ret_datetime = arr_ret_dt.isoformat()
                    
                    return_flight = {
                        'airline': flight['airline'],
                        'airline_code': flight['airline_code'],
                        'flight_number': flight['flight_number'].replace('OUT', 'RET'),
                        'departure_airport': flight['arrival_airport'],  # Swap
                        'arrival_airport': flight['departure_airport'],  # Swap
                        'departure_time': return_datetime,
                        'arrival_time': arrival_ret_datetime,
                        'duration_minutes': flight['duration_minutes'],
                        'duration_hours': flight['duration_hours'],
                        'price': flight['price'],
                        'currency': flight['currency'],
                        'stops': 0,
                        'cabin_class': travel_class,
                        'source': 'seed'
                    }
                    return_flights.append(return_flight)
                
                # Combine outbound and return
                converted_flights.extend(return_flights)
            
            return converted_flights, "seed"
        
        # ========================================
        # TIER 3: LLM Fallback
        # ========================================
        logger.info(f"[Tier 3] Generating flight estimate via LLM")
        
        llm_flight = await self.llm.generate_flight_estimate(
            origin=origin,
            destination=destination
        )
        
        if llm_flight:
            # Convert LLM format
            dep_time = "10:00"
            arr_time = "12:00"
            departure_datetime = f"{departure_date}T{dep_time}:00"
            
            from datetime import datetime, timedelta
            dep_dt = datetime.fromisoformat(departure_datetime)
            duration_hours = llm_flight.get('duration_hours', 2)
            arr_dt = dep_dt + timedelta(hours=float(duration_hours or 2))
            arrival_datetime = arr_dt.isoformat()
            
            min_price = llm_flight.get('price_range_min', 1000000)
            max_price = llm_flight.get('price_range_max', 3000000)
            avg_price = (min_price + max_price) / 2
            
            converted = {
                'airline': llm_flight.get('airline', 'Unknown Airline'),
                'airline_code': 'XX',
                'flight_number': 'XX000',
                'departure_airport': llm_flight.get('departure_airport', origin[:3].upper()),
                'arrival_airport': llm_flight.get('arrival_airport', destination[:3].upper()),
                'departure_time': departure_datetime,
                'arrival_time': arrival_datetime,
                'duration_minutes': int(duration_hours * 60),
                'duration_hours': duration_hours,
                'price': avg_price,
                'currency': 'IDR',
                'stops': 0,
                'cabin_class': travel_class,
                'source': 'llm_fallback'
            }
            
            logger.info(f"✓ Generated flight estimate via LLM")
            return [converted], "llm_fallback"
        
        logger.error(f"✗ All tiers failed for flights {origin} → {destination}")
        return [], "llm_fallback"
    
    def get_ground_transport(
        self,
        origin: str,
        destination: str
    ) -> Tuple[Optional[Dict], DataSource]:
        """
        Get ground transport options (train/bus/ferry)
        
        Uses hardcoded database for Indonesian routes
        
        Args:
            origin: Origin city
            destination: Destination city
            
        Returns:
            (transport_data, data_source)
        """
        
        from backend.constants.ground_transport import get_ground_transport
        
        logger.info(f"🚂 Checking ground transport: {origin} → {destination}")
        
        transport_data = get_ground_transport(origin, destination)
        
        if transport_data:
            logger.info(f"✓ Found ground transport options: {list(transport_data.keys())}")
            return transport_data, "seed"
        
        logger.info(f"✗ No ground transport available for this route")
        return None, "seed"
    
    def _get_airline_code(self, airline_name: str) -> str:
        """Map airline name to 2-letter code"""
        code_map = {
            'Garuda Indonesia': 'GA',
            'Singapore Airlines': 'SQ',
            'AirAsia': 'QZ',
            'Lion Air': 'JT',
            'Batik Air': 'ID',
            'Citilink': 'QG',
            'Malaysia Airlines': 'MH',
            'Thai Airways': 'TG',
            'Japan Airlines': 'JL',
            'ANA': 'NH',
            'Korean Air': 'KE',
            'Emirates': 'EK',
            'Qatar Airways': 'QR'
        }
        
        for name, code in code_map.items():
            if name.lower() in airline_name.lower():
                return code
        
        return 'XX'


# Singleton instance
_smart_retriever = None

def get_smart_retriever(
    opentripmap_key: Optional[str] = None,
    gemini_key: Optional[str] = None,
    amadeus_key: Optional[str] = None,
    amadeus_secret: Optional[str] = None
) -> SmartRetriever:
    """Get singleton SmartRetriever instance"""
    global _smart_retriever
    if _smart_retriever is None:
        _smart_retriever = SmartRetriever(
            opentripmap_key=opentripmap_key,
            gemini_key=gemini_key,
            amadeus_key=amadeus_key,
            amadeus_secret=amadeus_secret
        )
    return _smart_retriever