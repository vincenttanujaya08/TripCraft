"""
Amadeus API Client with LLM-Powered Airport Resolution
FIXED: Stable Gemini model + robust error handling
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Try to import Amadeus
try:
    from amadeus import Client, ResponseError
    AMADEUS_AVAILABLE = True
except ImportError:
    AMADEUS_AVAILABLE = False
    logger.warning("Amadeus SDK not installed")

# Try to import Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI not installed")


class DateValidationError(Exception):
    """Custom exception for date validation errors"""
    pass


class AmadeusFlightClient:
    """Client for Amadeus Flight Offers with LLM airport resolution"""
    
    # Date validation constants
    MIN_DAYS_ADVANCE = 0
    MAX_DAYS_ADVANCE = 330
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize Amadeus client with LLM support"""
        
        # Initialize Amadeus
        if not AMADEUS_AVAILABLE:
            logger.warning("Amadeus SDK not available")
            self.enabled = False
            self.client = None
        else:
            self.api_key = api_key or os.getenv("AMADEUS_API_KEY")
            self.api_secret = api_secret or os.getenv("AMADEUS_API_SECRET")
            
            if not self.api_key or not self.api_secret:
                logger.warning("Amadeus API credentials not found")
                self.enabled = False
                self.client = None
            else:
                try:
                    self.client = Client(
                        client_id=self.api_key,
                        client_secret=self.api_secret,
                        hostname='test'
                    )
                    self.enabled = True
                    logger.info("✅ Amadeus client initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize Amadeus: {e}")
                    self.enabled = False
                    self.client = None
        
        # Initialize Gemini for LLM resolution
        self.llm_enabled = False
        gemini_key = os.getenv("GEMINI_API_KEY")
        
        if GEMINI_AVAILABLE and gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                # Use STABLE model (not -exp)
                self.llm_model = genai.GenerativeModel("gemini-2.0-flash")
                self.llm_enabled = True
                logger.info("✅ LLM airport resolver enabled (gemini-2.0-flash)")
            except Exception as e:
                logger.error(f"Failed to initialize LLM: {e}")
                self.llm_enabled = False
        else:
            if not GEMINI_AVAILABLE:
                logger.warning("LLM resolver not available - Gemini SDK not installed")
            elif not gemini_key:
                logger.warning("LLM resolver not available - GEMINI_API_KEY not found")
    
    def validate_date(self, flight_date: date, date_type: str = "departure") -> Dict[str, Any]:
        """Validate flight date is within acceptable range"""
        
        today = date.today()
        days_from_now = (flight_date - today).days
        
        min_date = today + timedelta(days=self.MIN_DAYS_ADVANCE)
        max_date = today + timedelta(days=self.MAX_DAYS_ADVANCE)
        
        result = {
            "valid": True,
            "error": None,
            "days_from_now": days_from_now,
            "min_date": min_date,
            "max_date": max_date,
            "today": today
        }
        
        # Check if date is in the past
        if days_from_now < self.MIN_DAYS_ADVANCE:
            result["valid"] = False
            result["error"] = (
                f"Invalid {date_type} date: {flight_date} is in the past. "
                f"Please select a date starting from {min_date}."
            )
            return result
        
        # Check if date is too far in future
        if days_from_now > self.MAX_DAYS_ADVANCE:
            result["valid"] = False
            result["error"] = (
                f"Invalid {date_type} date: {flight_date} is too far in the future. "
                f"Maximum booking window is {self.MAX_DAYS_ADVANCE} days. "
                f"Latest valid date: {max_date}."
            )
            return result
        
        return result
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None,
        adults: int = 1,
        travel_class: str = "ECONOMY",
        currency: str = "IDR",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for flights using Amadeus API with date validation"""
        
        if not self.enabled:
            logger.warning("Amadeus API not enabled")
            return []
        
        try:
            # Validate departure date
            departure_validation = self.validate_date(departure_date, "departure")
            if not departure_validation["valid"]:
                logger.error(f"❌ Date validation failed: {departure_validation['error']}")
                raise DateValidationError(departure_validation["error"])
            
            # Validate return date if provided
            if return_date:
                return_validation = self.validate_date(return_date, "return")
                if not return_validation["valid"]:
                    logger.error(f"❌ Date validation failed: {return_validation['error']}")
                    raise DateValidationError(return_validation["error"])
                
                # Check return is after departure
                if return_date <= departure_date:
                    error = f"Return date ({return_date}) must be after departure date ({departure_date})"
                    logger.error(f"❌ {error}")
                    raise DateValidationError(error)
            
            # Dates are valid, proceed with search
            departure_str = departure_date.strftime("%Y-%m-%d")
            return_str = return_date.strftime("%Y-%m-%d") if return_date else None
            
            logger.info(
                f"🔍 Searching flights: {origin} → {destination} "
                f"on {departure_str}" + (f" (return {return_str})" if return_str else "")
            )
            logger.info(f"   📅 Departure: +{departure_validation['days_from_now']} days from today")
            
            search_params = {
                'originLocationCode': origin,
                'destinationLocationCode': destination,
                'departureDate': departure_str,
                'adults': adults,
                'travelClass': travel_class,
                'currencyCode': currency,
                'max': max_results
            }
            
            if return_str:
                search_params['returnDate'] = return_str
            
            response = self.client.shopping.flight_offers_search.get(**search_params)
            flight_offers = response.data if hasattr(response, 'data') else []
            
            logger.info(f"✅ Found {len(flight_offers)} flight offers from Amadeus API")
            
            parsed_offers = []
            for offer in flight_offers:
                parsed = self._parse_flight_offer(offer, departure_date, return_date)
                if parsed:
                    parsed_offers.append(parsed)
            
            return parsed_offers
        
        except DateValidationError as e:
            logger.error(f"Date validation error: {e}")
            raise
        
        except ResponseError as error:
            logger.error(f"❌ Amadeus API error [{error.response.status_code}]: {error.description}")
            
            if hasattr(error, 'response') and hasattr(error.response, 'result'):
                errors = error.response.result.get('errors', [])
                for err in errors:
                    detail = err.get('detail', 'No details')
                    logger.error(f"   ⚠️  {detail}")
            
            return []
        
        except Exception as e:
            logger.error(f"❌ Flight search failed: {e}")
            return []
    
    def _parse_flight_offer(self, offer: Dict, departure_date: date, return_date: Optional[date]) -> Optional[Dict]:
        """Parse Amadeus flight offer to our format"""
        
        try:
            itineraries = offer.get('itineraries', [])
            if not itineraries:
                return None
            
            price_info = offer.get('price', {})
            total_price = float(price_info.get('total', 0))
            currency = price_info.get('currency', 'IDR')
            
            outbound = itineraries[0]
            outbound_segments = outbound.get('segments', [])
            
            if not outbound_segments:
                return None
            
            first_segment = outbound_segments[0]
            last_segment = outbound_segments[-1]
            
            carrier_code = first_segment.get('carrierCode', '')
            flight_number = f"{carrier_code}{first_segment.get('number', '')}"
            
            duration_str = outbound.get('duration', 'PT0M')
            duration_minutes = self._parse_duration(duration_str)
            
            departure = first_segment.get('departure', {})
            arrival = last_segment.get('arrival', {})
            
            flight_data = {
                'offer_id': offer.get('id'),
                'airline': self._get_airline_name(carrier_code),
                'airline_code': carrier_code,
                'flight_number': flight_number,
                'departure_airport': departure.get('iataCode', ''),
                'arrival_airport': arrival.get('iataCode', ''),
                'departure_time': departure.get('at', ''),
                'arrival_time': arrival.get('at', ''),
                'duration_minutes': duration_minutes,
                'duration_hours': round(duration_minutes / 60, 1),
                'price': total_price,
                'currency': currency,
                'stops': len(outbound_segments) - 1,
                'cabin_class': first_segment.get('cabin', 'ECONOMY').lower(),
                'aircraft': first_segment.get('aircraft', {}).get('code', 'Unknown'),
                'segments': len(outbound_segments),
                'source': 'amadeus_api',
                '_raw_offer': offer
            }
            
            if len(itineraries) > 1:
                return_itinerary = itineraries[1]
                return_segments = return_itinerary.get('segments', [])
                
                if return_segments:
                    return_first = return_segments[0]
                    return_last = return_segments[-1]
                    
                    flight_data['return_flight'] = {
                        'flight_number': f"{return_first.get('carrierCode', '')}{return_first.get('number', '')}",
                        'departure_airport': return_first.get('departure', {}).get('iataCode', ''),
                        'arrival_airport': return_last.get('arrival', {}).get('iataCode', ''),
                        'departure_time': return_first.get('departure', {}).get('at', ''),
                        'arrival_time': return_last.get('arrival', {}).get('at', ''),
                        'duration_minutes': self._parse_duration(return_itinerary.get('duration', 'PT0M')),
                        'stops': len(return_segments) - 1
                    }
            
            return flight_data
        
        except Exception as e:
            logger.error(f"Failed to parse flight offer: {e}")
            return None
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration to minutes"""
        try:
            import re
            duration_str = duration_str.replace('PT', '')
            hours = 0
            minutes = 0
            
            hour_match = re.search(r'(\d+)H', duration_str)
            if hour_match:
                hours = int(hour_match.group(1))
            
            minute_match = re.search(r'(\d+)M', duration_str)
            if minute_match:
                minutes = int(minute_match.group(1))
            
            return (hours * 60) + minutes
        except Exception:
            return 0
    
    def _get_airline_name(self, carrier_code: str) -> str:
        """Map airline codes to full names"""
        airline_map = {
            'GA': 'Garuda Indonesia', 'SQ': 'Singapore Airlines',
            'QZ': 'AirAsia Indonesia', 'ID': 'Batik Air',
            'JT': 'Lion Air', 'QG': 'Citilink',
            'MH': 'Malaysia Airlines', 'TG': 'Thai Airways',
            'CX': 'Cathay Pacific', 'NH': 'ANA',
            'JL': 'Japan Airlines', 'KE': 'Korean Air',
            'EK': 'Emirates', 'QR': 'Qatar Airways',
            'AF': 'Air France', 'BA': 'British Airways',
            'LH': 'Lufthansa', 'UA': 'United Airlines',
            'AA': 'American Airlines', 'DL': 'Delta Air Lines'
        }
        return airline_map.get(carrier_code, carrier_code)
    
    def get_airport_code(self, city_name: str) -> Optional[str]:
        """
        Get IATA airport code using 3-tier strategy:
        1. Static fallback map (fastest)
        2. LLM (Gemini) - handles ANY city name
        3. Amadeus API (last resort)
        """
        
        # TIER 1: Static fallback map
        fallback_code = self._get_airport_code_fallback(city_name)
        if fallback_code:
            logger.info(f"✅ [Tier 1] Static map: {city_name} → {fallback_code}")
            return fallback_code
        
        # TIER 2: LLM resolution
        if self.llm_enabled:
            llm_code = self._get_airport_code_llm(city_name)
            if llm_code:
                logger.info(f"✅ [Tier 2] LLM resolved: {city_name} → {llm_code}")
                return llm_code
        
        # TIER 3: Amadeus API
        if self.enabled:
            try:
                logger.info(f"🔍 [Tier 3] Trying Amadeus API for: {city_name}")
                response = self.client.reference_data.locations.get(
                    keyword=city_name,
                    subType='AIRPORT'
                )
                
                locations = response.data if hasattr(response, 'data') else []
                
                if locations:
                    code = locations[0].get('iataCode')
                    logger.info(f"✅ [Tier 3] Amadeus API: {city_name} → {code}")
                    return code
            except Exception as e:
                logger.error(f"❌ Amadeus API error: {e}")
        
        logger.warning(f"⚠️  No airport code found for: {city_name}")
        return None
    
    def _get_airport_code_llm(self, city_name: str) -> Optional[str]:
        """Use LLM to resolve airport code with robust error handling"""
        
        if not self.llm_enabled:
            return None
        
        try:
            prompt = f"""You are an aviation expert. Find the main international airport IATA code for this city.

City: {city_name}

CRITICAL RULES:
1. Return ONLY the 3-letter IATA airport code
2. If the city has NO major airport, return exactly: NONE
3. Choose the MAIN international airport (not regional)
4. DO NOT add any explanation, punctuation, or extra text
5. Just the code or NONE, nothing else

Examples:
Jakarta → CGK
Bali → DPS
New York → JFK
Yogyakarta → JOG
Malang → MLG
Small Village → NONE

Your answer (ONLY the code or NONE):"""

            response = self.llm_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "top_k": 1,
                    "max_output_tokens": 10,
                }
            )
            
            # Robust response parsing
            if not response or not hasattr(response, 'text'):
                logger.warning(f"LLM returned empty response for {city_name}")
                return None
            
            # Get text and clean it
            code = response.text.strip().upper()
            
            # Remove any markdown, quotes, or extra characters
            code = code.replace('```', '').replace('`', '').replace('"', '').replace("'", '')
            code = code.strip()
            
            # Take only first word if multiple words returned
            if ' ' in code:
                code = code.split()[0]
            
            # Validate format
            if code == "NONE":
                logger.info(f"LLM confirmed no major airport for: {city_name}")
                return None
            
            if len(code) != 3 or not code.isalpha():
                logger.warning(f"LLM returned invalid format for {city_name}: '{code}'")
                return None
            
            logger.info(f"✅ LLM resolved: {city_name} → {code}")
            return code
            
        except AttributeError as e:
            logger.error(f"LLM response parsing error for {city_name}: {e}")
            return None
            
        except IndexError as e:
            logger.error(f"LLM response index error for {city_name}: {e}")
            return None
            
        except Exception as e:
            logger.error(f"LLM resolution failed for {city_name}: {type(e).__name__}: {e}")
            return None
    
    def _get_airport_code_fallback(self, city_name: str) -> Optional[str]:
        """Static fallback map for common airports"""
        
        city_lower = city_name.lower().strip()
        
        # Expanded airport map with more Indonesian cities
        airport_map = {
            # Indonesia - Major
            'jakarta': 'CGK', 'bali': 'DPS', 'denpasar': 'DPS',
            'surabaya': 'SUB', 'yogyakarta': 'JOG', 'medan': 'KNO',
            'makassar': 'UPG', 'lombok': 'LOP', 'bandung': 'BDO',
            'semarang': 'SRG',
            
            # Indonesia - Secondary
            'malang': 'MLG', 'solo': 'SOC', 'surakarta': 'SOC',
            'balikpapan': 'BPN', 'banjarmasin': 'BDJ',
            'manado': 'MDC', 'palembang': 'PLM',
            'pekanbaru': 'PKU', 'pontianak': 'PNK',
            'batam': 'BTH', 'padang': 'PDG',
            'kupang': 'KOE', 'ambon': 'AMQ',
            'jayapura': 'DJJ', 'kendari': 'KDI',
            'mataram': 'AMI', 'tarakan': 'TRK',
            
            # Southeast Asia
            'singapore': 'SIN', 'kuala lumpur': 'KUL',
            'bangkok': 'BKK', 'manila': 'MNL',
            'ho chi minh': 'SGN', 'hanoi': 'HAN',
            'phnom penh': 'PNH', 'vientiane': 'VTE',
            'yangon': 'RGN',
            
            # East Asia
            'tokyo': 'NRT', 'seoul': 'ICN',
            'hong kong': 'HKG', 'taipei': 'TPE',
            'beijing': 'PEK', 'shanghai': 'PVG',
            
            # Oceania
            'sydney': 'SYD', 'melbourne': 'MEL',
            'brisbane': 'BNE', 'auckland': 'AKL',
            
            # Europe
            'paris': 'CDG', 'london': 'LHR',
            'amsterdam': 'AMS', 'frankfurt': 'FRA',
            
            # Americas
            'new york': 'JFK', 'los angeles': 'LAX',
            'san francisco': 'SFO', 'chicago': 'ORD',
            
            # Middle East
            'dubai': 'DXB', 'doha': 'DOH',
            'abu dhabi': 'AUH', 'riyadh': 'RUH'
        }
        
        # Direct match
        code = airport_map.get(city_lower)
        if code:
            return code
        
        # Partial match
        for city, code in airport_map.items():
            if city in city_lower or city_lower in city:
                logger.info(f"Partial match: {city_name} → {code} (matched '{city}')")
                return code
        
        return None
    
    def get_valid_date_range(self) -> Dict[str, date]:
        """Get valid date range for flight bookings"""
        today = date.today()
        return {
            "today": today,
            "min_date": today + timedelta(days=self.MIN_DAYS_ADVANCE),
            "max_date": today + timedelta(days=self.MAX_DAYS_ADVANCE),
            "min_days": self.MIN_DAYS_ADVANCE,
            "max_days": self.MAX_DAYS_ADVANCE
        }


# Singleton
_amadeus_client = None

def get_amadeus_client(api_key: Optional[str] = None, api_secret: Optional[str] = None) -> AmadeusFlightClient:
    """Get singleton AmadeusFlightClient instance"""
    global _amadeus_client
    if _amadeus_client is None:
        _amadeus_client = AmadeusFlightClient(api_key=api_key, api_secret=api_secret)
    return _amadeus_client