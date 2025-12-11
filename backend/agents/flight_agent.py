"""
FlightAgent - COMPLETE FIXED VERSION
- Tier 1: Amadeus API (real data)
- Tier 2: SmartRetriever seed data  
- Tier 3: LLM Fallback with REALISTIC pricing ✅ FIXED!
- Tier 4: Ground Transport
- Tier 5: Empty with warning

KEY FIXES:
✅ Added REALISTIC_PRICES constants (500k-8M IDR based on route type)
✅ Added _estimate_route_category() method 
✅ Fixed LLM fallback price generation (Bandung Rp 260 → Rp 850,000)
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict, Any
from backend.models.schemas import (
    TripRequest, 
    FlightOutput, 
    Flight,
    GroundTransportOption,
    GroundTransportRoute
)
from backend.agents.base_agent import BaseAgent
from backend.data_sources.amadeus_client import get_amadeus_client, DateValidationError

logger = logging.getLogger(f"agent.Flight")


class FlightAgent(BaseAgent):
    """Agent responsible for finding flight options with 5-tier fallback strategy"""
    
    # ========================================================================
    # REALISTIC PRICE RANGES - FIXED! ✅
    # ========================================================================
    REALISTIC_PRICES = {
        "short_domestic": {"min": 500000, "max": 1200000},      # Jakarta-Bandung
        "medium_domestic": {"min": 800000, "max": 2000000},     # Jakarta-Bali
        "long_domestic": {"min": 1500000, "max": 3500000},      # Jakarta-Papua
        "asean": {"min": 1000000, "max": 3000000},              # Singapore, Malaysia
        "asia_near": {"min": 3000000, "max": 8000000},          # Japan, Korea
    }
    
    def __init__(self):
        """Initialize with Amadeus client, SmartRetriever, and LLM fallback"""
        super().__init__("Flight")
        
        # Tier 1: Amadeus API
        self.amadeus_client = get_amadeus_client()
        
        # Tier 2: SmartRetriever
        from backend.data_sources.smart_retriever import SmartRetriever
        self.retriever = SmartRetriever()
        
        # Tier 3: LLM
        self.llm_enabled = self.amadeus_client.llm_enabled
        
        if self.amadeus_client.enabled:
            logger.info("✅ FlightAgent initialized with Amadeus API")
        else:
            logger.warning("⚠️  Amadeus API not available - using fallback only")
        
        if self.llm_enabled:
            logger.info("✅ LLM fallback enabled with REALISTIC pricing")
    
    def _map_accommodation_to_cabin(self, accommodation: str) -> str:
        """Map accommodation preference to flight cabin class"""
        mapping = {
            'budget': 'economy',
            'mid-range': 'economy',
            'luxury': 'business',
            'premium': 'first'
        }
        return mapping.get(accommodation.lower(), 'economy')
    
    def _estimate_route_category(self, origin: str, destination: str) -> str:
        """
        Estimate flight category for realistic pricing ✅ NEW METHOD!
        
        Returns category name for REALISTIC_PRICES lookup
        """
        indo_cities = ["jakarta", "bali", "surabaya", "yogyakarta", "bandung", 
                       "medan", "makassar", "lombok", "semarang", "malang"]
        asean = ["singapore", "malaysia", "thailand", "vietnam", "philippines"]
        
        origin_lower = origin.lower()
        dest_lower = destination.lower()
        
        # Both Indonesian = domestic
        if any(c in origin_lower for c in indo_cities) and \
           any(c in dest_lower for c in indo_cities):
            
            # Special cases for known short routes
            short_routes = [("jakarta", "bandung"), ("surabaya", "bali"), ("jakarta", "yogyakarta")]
            for o, d in short_routes:
                if (o in origin_lower and d in dest_lower) or \
                   (d in origin_lower and o in dest_lower):
                    return "short_domestic"
            
            # Default domestic
            return "medium_domestic"
        
        # ASEAN countries
        if any(c in origin_lower for c in asean) or \
           any(c in dest_lower for c in asean):
            return "asean"
        
        # Default: Asia near
        return "asia_near"
    
    async def execute(
        self, 
        request: TripRequest,
        max_budget: Optional[float] = None,
        context: Optional[Dict] = None
    ) -> FlightOutput:
        """Find suitable flights with 5-tier fallback strategy"""
        self.logger.info("🚀 Flight agent starting...")
        start_time = datetime.now()
        
        warnings = []
        
        if max_budget:
            per_person_budget = max_budget / request.travelers
            self.logger.info(f"💰 Flight budget: Rp {max_budget:,.0f} (Rp {per_person_budget:,.0f}/person)")
        else:
            per_person_budget = None
        
        try:
            cabin_class = self._map_accommodation_to_cabin(
                request.preferences.accommodation
            )
            
            # TIER 1: Try Amadeus API
            flights_data, data_source = await self._try_amadeus_api(
                request, cabin_class, warnings
            )
            
            # TIER 2: Fallback to SmartRetriever
            if not flights_data:
                self.logger.warning("⚠️  Amadeus API failed/empty - trying SmartRetriever")
                flights_data, data_source = await self._try_smart_retriever_fallback(
                    request, cabin_class
                )
            
            # TIER 3: LLM Fallback with REALISTIC PRICES ✅
            if not flights_data:
                self.logger.warning("⚠️  SmartRetriever empty - trying LLM fallback")
                flights_data, data_source = await self._try_llm_fallback(
                    request, cabin_class, warnings
                )
            
            # TIER 4: Check ground transport
            if not flights_data:
                self.logger.warning("⚠️  No flights - checking ground transport")
                duration = (datetime.now() - start_time).total_seconds() * 1000
                return await self._try_ground_transport_fallback(
                    request, warnings, "no_flights", duration
                )
            
            # Parse flights
            valid_flights = self._parse_flights(flights_data, request, data_source)
            
            if not valid_flights:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                return await self._try_ground_transport_fallback(
                    request, warnings, data_source, duration
                )
            
            # Separate outbound and return
            outbound_flights = []
            return_flights = []
            
            for flight in valid_flights:
                flight_date = flight.departure_time.date()
                
                if flight_date == request.start_date:
                    outbound_flights.append(flight)
                elif flight_date == request.end_date:
                    return_flights.append(flight)
                else:
                    outbound_flights.append(flight)
            
            # Generate return flights if missing
            if outbound_flights and not return_flights:
                for outbound in outbound_flights[:3]:
                    return_flight = self._generate_return_flight(outbound, request)
                    return_flights.append(return_flight)
            
            # Sort by price
            outbound_flights.sort(key=lambda f: (f.price, f.duration_hours))
            return_flights.sort(key=lambda f: (f.price, f.duration_hours))
            
            # Select top options
            selected_outbound = outbound_flights[:3]
            selected_return = return_flights[:3]
            
            # Recommend cheapest
            recommended_out = selected_outbound[0] if selected_outbound else None
            recommended_ret = selected_return[0] if selected_return else None
            
            # Calculate total cost
            total_cost = 0.0
            if recommended_out:
                total_cost += recommended_out.price * request.travelers
            if recommended_ret:
                total_cost += recommended_ret.price * request.travelers
            
            # CHECK BUDGET
            if max_budget and total_cost > max_budget:
                over_amount = total_cost - max_budget
                over_pct = (over_amount / max_budget) * 100
                
                self.logger.warning(
                    f"⚠️  Flight over budget: Rp {total_cost:,.0f} > Rp {max_budget:,.0f} "
                    f"(+{over_pct:.1f}%)"
                )
                
                # Check ground transport
                ground_data, _ = self.retriever.get_ground_transport(
                    origin=request.origin or "Jakarta",
                    destination=request.destination
                )
                
                if ground_data:
                    from backend.constants.ground_transport import get_cheapest_option
                    cheapest = get_cheapest_option(
                        request.origin or "Jakarta",
                        request.destination
                    )
                    
                    if cheapest:
                        warnings.append(
                            f"⚠️  Flight exceeds budget by Rp {over_amount:,.0f} ({over_pct:.1f}%). "
                            f"Consider {cheapest['transport_type']}: Rp {cheapest['cost_per_person']:,.0f}/person "
                            f"({cheapest['duration_hours']}h)"
                        )
                else:
                    warnings.append(
                        f"⚠️  Flight exceeds budget by Rp {over_amount:,.0f} ({over_pct:.1f}%). "
                        f"Options: 1) Increase budget, 2) Change dates, 3) Reduce hotel budget"
                    )
            
            # Calculate confidence
            confidence = self._calculate_confidence(
                source=data_source,
                data_quality_score=(len(selected_outbound) + len(selected_return)) * 10
            )
            
            # Data source warnings
            if data_source == "seed":
                warnings.append("Using fallback flight data - prices may not be current")
            elif data_source == "llm_fallback":
                warnings.append("⚠️  Flight prices are AI estimates - VERIFY before booking")
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.info(
                f"✓ Flight completed in {duration:.0f}ms "
                f"(source: {data_source}, confidence: {confidence*100:.0f}%)"
            )
            
            return FlightOutput(
                outbound_flights=selected_outbound,
                return_flights=selected_return,
                recommended_outbound=recommended_out,
                recommended_return=recommended_ret,
                total_flight_cost=total_cost,
                warnings=warnings,
                metadata=self._create_metadata(data_source, duration),
                data_source=data_source,
                confidence=confidence
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"✗ Flight failed after {duration:.0f}ms: {e}")
            raise
    
    async def _try_amadeus_api(
        self,
        request: TripRequest,
        cabin_class: str,
        warnings: List[str]
    ) -> Tuple[List[dict], str]:
        """TIER 1: Try Amadeus API"""
        
        if not self.amadeus_client.enabled:
            return [], "seed"
        
        try:
            origin = request.origin or "Jakarta"
            destination = request.destination
            
            self.logger.info(f"🔍 [Tier 1] Resolving: {origin} → {destination}")
            
            origin_code = self.amadeus_client.get_airport_code(origin)
            dest_code = self.amadeus_client.get_airport_code(destination)
            
            if not origin_code or not dest_code:
                return [], "seed"
            
            self.logger.info(f"✅ Codes: {origin_code} → {dest_code}")
            
            flights_data = await self.amadeus_client.search_flights(
                origin=origin_code,
                destination=dest_code,
                departure_date=request.start_date,
                return_date=request.end_date,
                adults=request.travelers,
                travel_class=cabin_class.upper(),
                currency="IDR",
                max_results=5
            )
            
            if flights_data:
                self.logger.info(f"✅ [Tier 1] Got {len(flights_data)} flights")
                return flights_data, "amadeus_api"
            else:
                return [], "seed"
        
        except DateValidationError as e:
            self.logger.error(f"❌ Date error: {e}")
            warnings.append(f"Date validation error: {str(e)}")
            return [], "seed"
        
        except Exception as e:
            self.logger.error(f"❌ [Tier 1] Error: {e}")
            return [], "seed"
    
    async def _try_smart_retriever_fallback(
        self,
        request: TripRequest,
        cabin_class: str
    ) -> Tuple[List[dict], str]:
        """TIER 2: SmartRetriever seed data"""
        
        try:
            self.logger.info("🔄 [Tier 2] Using SmartRetriever...")
            
            flights_data, data_source = await self.retriever.get_flights(
                origin=request.origin or "Jakarta",
                destination=request.destination,
                departure_date=request.start_date,
                return_date=request.end_date,
                travelers=request.travelers,
                travel_class=cabin_class
            )
            
            if flights_data:
                self.logger.info(f"✅ [Tier 2] Got {len(flights_data)} flights")
            
            return flights_data, data_source
        
        except Exception as e:
            self.logger.error(f"❌ [Tier 2] Error: {e}")
            return [], "seed"
    
    async def _try_llm_fallback(
        self,
        request: TripRequest,
        cabin_class: str,
        warnings: List[str]
    ) -> Tuple[List[dict], str]:
        """TIER 3: LLM with REALISTIC PRICES ✅ FIXED!"""
        
        if not self.llm_enabled:
            return [], "llm_unavailable"
        
        try:
            self.logger.info("🧠 [Tier 3] LLM fallback with realistic pricing...")
            
            import google.generativeai as genai
            
            origin = request.origin or "Jakarta"
            destination = request.destination
            
            prompt = f"""Aviation expert: Check if {origin} → {destination} has major airports.

RULES:
1. If NO airport, return: {{"has_airport": false}}
2. If has airport, return: {{"has_airport": true, "estimated_duration_hours": X}}
3. ONLY JSON, no markdown

Examples:
Jakarta → Bali: {{"has_airport": true, "estimated_duration_hours": 2.0}}
Jakarta → Village: {{"has_airport": false}}

Your JSON:"""

            response = self.amadeus_client.llm_model.generate_content(
                prompt,
                generation_config={"temperature": 0.2, "max_output_tokens": 100}
            )
            
            import json
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            data = json.loads(text)
            
            if not data.get("has_airport", False):
                self.logger.warning(f"⚠️  [Tier 3] No airport")
                return [], "no_airport"
            
            # ========================================================================
            # ✅ FIXED: Use REALISTIC prices instead of LLM estimates!
            # ========================================================================
            duration_hours = data.get("estimated_duration_hours", 2.0)
            
            # Determine route category
            category = self._estimate_route_category(origin, destination)
            price_range = self.REALISTIC_PRICES.get(category, self.REALISTIC_PRICES["medium_domestic"])
            
            # Calculate with ±15% variation
            import random
            avg_price = (price_range["min"] + price_range["max"]) // 2
            variation = random.uniform(0.85, 1.15)
            outbound_price = int(avg_price * variation)
            return_price = int(avg_price * variation)
            
            self.logger.info(f"   💰 Realistic ({category}): Rp {outbound_price:,.0f}/person")
            # ========================================================================
            
            # Create flight data
            flights_data = []
            
            # Outbound
            departure = datetime.combine(request.start_date, datetime.min.time().replace(hour=8))
            arrival = departure + timedelta(hours=duration_hours)
            
            flights_data.append({
                "airline": "Estimated Airline",
                "flight_number": "EST-OUT",
                "departure_airport": origin[:3].upper(),
                "arrival_airport": destination[:3].upper(),
                "departure_time": departure.isoformat(),
                "arrival_time": arrival.isoformat(),
                "duration_hours": duration_hours,
                "price": outbound_price,
                "stops": 0,
                "cabin_class": cabin_class
            })
            
            # Return
            return_dep = datetime.combine(request.end_date, datetime.min.time().replace(hour=16))
            return_arr = return_dep + timedelta(hours=duration_hours)
            
            flights_data.append({
                "airline": "Estimated Airline",
                "flight_number": "EST-RET",
                "departure_airport": destination[:3].upper(),
                "arrival_airport": origin[:3].upper(),
                "departure_time": return_dep.isoformat(),
                "arrival_time": return_arr.isoformat(),
                "duration_hours": duration_hours,
                "price": return_price,
                "stops": 0,
                "cabin_class": cabin_class
            })
            
            self.logger.info(f"✅ [Tier 3] Generated {len(flights_data)} realistic flights")
            warnings.append("🤖 Flight prices are AI estimates - VERIFY before booking")
            
            return flights_data, "llm_fallback"
        
        except Exception as e:
            self.logger.error(f"❌ [Tier 3] Error: {e}")
            
            # TIER 3.5: Hardcoded Heuristic Fallback (Safety Net)
            self.logger.info("🛡️ [Tier 3.5] Using hardcoded heuristic fallback")
            
            # Determine route category
            category = self._estimate_route_category(request.origin or "Jakarta", request.destination)
            price_range = self.REALISTIC_PRICES.get(category, self.REALISTIC_PRICES["medium_domestic"])
            
            # Use average price
            avg_price = (price_range["min"] + price_range["max"]) // 2
            
            # Create flight data
            flights_data = []
            
            # Outbound
            departure = datetime.combine(request.start_date, datetime.min.time().replace(hour=8))
            arrival = departure + timedelta(hours=2) # Assume 2h
            
            flights_data.append({
                "airline": "Estimated Airline",
                "flight_number": "SAFE-OUT",
                "departure_airport": (request.origin or "JKT")[:3].upper(),
                "arrival_airport": request.destination[:3].upper(),
                "departure_time": departure.isoformat(),
                "arrival_time": arrival.isoformat(),
                "duration_hours": 2.0,
                "price": avg_price,
                "stops": 0,
                "cabin_class": cabin_class
            })
            
            # Return
            return_dep = datetime.combine(request.end_date, datetime.min.time().replace(hour=16))
            return_arr = return_dep + timedelta(hours=2)
            
            flights_data.append({
                "airline": "Estimated Airline",
                "flight_number": "SAFE-RET",
                "departure_airport": request.destination[:3].upper(),
                "arrival_airport": (request.origin or "JKT")[:3].upper(),
                "departure_time": return_dep.isoformat(),
                "arrival_time": return_arr.isoformat(),
                "duration_hours": 2.0,
                "price": avg_price,
                "stops": 0,
                "cabin_class": cabin_class
            })
            
            warnings.append("⚠️ Could not search flights - using route estimate")
            return flights_data, "estimate"
    
    async def _try_ground_transport_fallback(
        self,
        request: TripRequest,
        warnings: List[str],
        data_source: str,
        duration: float
    ) -> FlightOutput:
        """TIER 4: Ground transport"""
        
        self.logger.info("🚂 [Tier 4] Checking ground transport...")
        
        ground_data, _ = self.retriever.get_ground_transport(
            origin=request.origin or "Jakarta",
            destination=request.destination
        )
        
        if ground_data:
            from backend.constants.ground_transport import get_cheapest_option
            cheapest = get_cheapest_option(
                request.origin or "Jakarta",
                request.destination
            )
            
            if cheapest:
                warnings.append(
                    f"✈️  No flights available. "
                    f"Alternative: {cheapest['transport_type'].title()} "
                    f"- Rp {cheapest['cost_per_person']:,.0f}/person ({cheapest['duration_hours']}h)"
                )
        else:
            warnings.append(
                f"❌ No flights or ground transport for this route"
            )
        
        return FlightOutput(
            outbound_flights=[],
            return_flights=[],
            recommended_outbound=None,
            recommended_return=None,
            total_flight_cost=0.0,
            warnings=warnings,
            metadata=self._create_metadata(data_source, duration),
            data_source=data_source,
            confidence=0.0
        )
    
    def _parse_flights(
        self, 
        flights_data: List[dict], 
        request: TripRequest,
        data_source: str
    ) -> List[Flight]:
        """Parse flight data to Flight objects"""
        
        flights = []
        
        for flight_data in flights_data:
            try:
                if data_source == "amadeus_api":
                    flight = self._parse_amadeus_flight(flight_data)
                else:
                    flight = self._parse_retriever_flight(flight_data)
                
                if flight:
                    flights.append(flight)
                
            except Exception as e:
                self.logger.warning(f"Parse failed: {e}")
                continue
        
        return flights
    
    def _parse_amadeus_flight(self, flight_data: dict) -> Optional[Flight]:
        """Parse Amadeus format"""
        try:
            return Flight(
                airline=flight_data.get('airline', 'Unknown'),
                flight_number=flight_data.get('flight_number', 'UNKNOWN'),
                departure_airport=flight_data.get('departure_airport', ''),
                arrival_airport=flight_data.get('arrival_airport', ''),
                departure_time=datetime.fromisoformat(
                    flight_data['departure_time'].replace('Z', '+00:00')
                ),
                arrival_time=datetime.fromisoformat(
                    flight_data['arrival_time'].replace('Z', '+00:00')
                ),
                duration_hours=flight_data.get('duration_hours', 0),
                price=flight_data.get('price', 0),
                stops=flight_data.get('stops', 0),
                cabin_class=flight_data.get('cabin_class', 'economy')
            )
        except Exception as e:
            self.logger.warning(f"Parse Amadeus failed: {e}")
            return None
    
    def _parse_retriever_flight(self, flight_data: dict) -> Optional[Flight]:
        """Parse SmartRetriever/LLM format"""
        try:
            return Flight(
                airline=flight_data.get('airline', 'Unknown'),
                flight_number=flight_data.get('flight_number', 'UNKNOWN'),
                departure_airport=flight_data.get('departure_airport', ''),
                arrival_airport=flight_data.get('arrival_airport', ''),
                departure_time=datetime.fromisoformat(
                    flight_data['departure_time'].replace('Z', '+00:00')
                ),
                arrival_time=datetime.fromisoformat(
                    flight_data['arrival_time'].replace('Z', '+00:00')
                ),
                duration_hours=flight_data.get('duration_hours', 0),
                price=flight_data.get('price', 0),
                stops=flight_data.get('stops', 0),
                cabin_class=flight_data.get('cabin_class', 'economy')
            )
        except Exception as e:
            self.logger.warning(f"Parse retriever failed: {e}")
            return None
    
    def _generate_return_flight(self, outbound: Flight, request: TripRequest) -> Flight:
        """Generate return flight"""
        return Flight(
            airline=outbound.airline,
            flight_number=outbound.flight_number.replace('OUT', 'RET'),
            departure_airport=outbound.arrival_airport,
            arrival_airport=outbound.departure_airport,
            departure_time=datetime.combine(request.end_date, outbound.departure_time.time()),
            arrival_time=datetime.combine(request.end_date, outbound.arrival_time.time()),
            duration_hours=outbound.duration_hours,
            price=outbound.price,
            stops=outbound.stops,
            cabin_class=outbound.cabin_class
        )
    
    def _create_metadata(self, data_source: str, duration: float) -> dict:
        """Create metadata"""
        return {
            "agent": self.name,
            "data_source": data_source,
            "execution_time_ms": int(duration),
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_confidence(self, source: str, data_quality_score: int) -> float:
        """Calculate confidence"""
        base_confidence = {
            "amadeus_api": 0.95,
            "api": 0.95,
            "seed": 0.80,
            "llm_fallback": 0.60,
            "no_airport": 0.0,
            "no_flights": 0.0
        }
        
        base = base_confidence.get(source, 0.50)
        quality_factor = min(data_quality_score / 100, 1.0)
        
        return base * quality_factor