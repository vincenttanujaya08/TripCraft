"""
FlightAgent - UPDATED with 5-Tier Strategy
- Tier 1: Amadeus API (real data)
- Tier 2: SmartRetriever seed data
- Tier 3: LLM Fallback (estimated flights)
- Tier 4: Ground Transport (train/bus/ferry)
- Tier 5: Empty with warning
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
    
    def __init__(self):
        """Initialize with Amadeus client, SmartRetriever, and LLM fallback"""
        super().__init__("Flight")
        
        # Tier 1: Amadeus API
        self.amadeus_client = get_amadeus_client()
        
        # Tier 2: SmartRetriever
        from backend.data_sources.smart_retriever import SmartRetriever
        self.retriever = SmartRetriever()
        
        # Tier 3: LLM (via amadeus_client which has Gemini)
        self.llm_enabled = self.amadeus_client.llm_enabled
        
        if self.amadeus_client.enabled:
            logger.info("✅ FlightAgent initialized with Amadeus API")
        else:
            logger.warning("⚠️  Amadeus API not available - using fallback only")
        
        if self.llm_enabled:
            logger.info("✅ LLM fallback enabled for flight estimation")
    
    def _map_accommodation_to_cabin(self, accommodation: str) -> str:
        """Map accommodation preference to flight cabin class"""
        mapping = {
            'budget': 'economy',
            'mid-range': 'economy',
            'luxury': 'business',
            'premium': 'first'
        }
        return mapping.get(accommodation.lower(), 'economy')
    
    async def execute(
        self, 
        request: TripRequest,
        max_budget: Optional[float] = None,
        context: Optional[Dict] = None
    ) -> FlightOutput:
        """
        Find suitable flights with 5-tier fallback strategy
        
        Args:
            request: Trip planning request
            max_budget: Maximum budget allocated for flights (optional)
            context: Shared context from orchestrator (optional)
            
        Returns:
            FlightOutput with flight options and warnings
        """
        self.logger.info("🚀 Flight agent starting...")
        start_time = datetime.now()
        
        warnings = []
        
        # Calculate budget if provided
        if max_budget:
            per_person_budget = max_budget / request.travelers
            self.logger.info(f"💰 Flight budget: Rp {max_budget:,.0f} (Rp {per_person_budget:,.0f}/person)")
        else:
            per_person_budget = None
        
        try:
            # Map accommodation to cabin class
            cabin_class = self._map_accommodation_to_cabin(
                request.preferences.accommodation
            )
            
            # TIER 1: Try Amadeus API
            flights_data, data_source = await self._try_amadeus_api(
                request, cabin_class, warnings
            )
            
            # TIER 2: Fallback to SmartRetriever if Amadeus failed
            if not flights_data:
                self.logger.warning("⚠️  Amadeus API failed/empty - trying SmartRetriever fallback")
                flights_data, data_source = await self._try_smart_retriever_fallback(
                    request, cabin_class
                )
            
            # TIER 3: LLM Fallback for flight estimation
            if not flights_data:
                self.logger.warning("⚠️  SmartRetriever empty - trying LLM fallback")
                flights_data, data_source = await self._try_llm_fallback(
                    request, cabin_class, warnings
                )
            
            # TIER 4: Check ground transport
            if not flights_data:
                self.logger.warning("⚠️  No flights available - checking ground transport")
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
            
            # Separate outbound and return flights
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
                
                # Check if ground transport is viable
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
                        f"Options: 1) Increase total budget, 2) Change dates, 3) Reduce hotel budget"
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
        """
        TIER 1: Try to get flights from Amadeus API
        
        Returns:
            (flights_data, data_source)
        """
        
        if not self.amadeus_client.enabled:
            self.logger.warning("Amadeus API not enabled")
            return [], "seed"
        
        try:
            # Resolve airport codes using LLM
            origin = request.origin or "Jakarta"
            destination = request.destination
            
            self.logger.info(f"🔍 [Tier 1] Resolving airport codes: {origin} → {destination}")
            
            origin_code = self.amadeus_client.get_airport_code(origin)
            dest_code = self.amadeus_client.get_airport_code(destination)
            
            if not origin_code:
                self.logger.warning(f"⚠️  Could not resolve origin airport code: {origin}")
                return [], "seed"
            
            if not dest_code:
                self.logger.warning(f"⚠️  Could not resolve destination airport code: {destination}")
                return [], "seed"
            
            self.logger.info(f"✅ Airport codes: {origin} ({origin_code}) → {destination} ({dest_code})")
            
            # Call Amadeus API
            self.logger.info(f"🛫 [Tier 1] Searching Amadeus API...")
            
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
                self.logger.info(f"✅ [Tier 1] Amadeus API returned {len(flights_data)} flight offers")
                return flights_data, "amadeus_api"
            else:
                self.logger.warning("⚠️  [Tier 1] Amadeus API returned no results")
                return [], "seed"
        
        except DateValidationError as e:
            # Date validation error - add to warnings but don't crash
            self.logger.error(f"❌ Date validation error: {e}")
            warnings.append(f"Date validation error: {str(e)}")
            return [], "seed"
        
        except Exception as e:
            self.logger.error(f"❌ [Tier 1] Amadeus API error: {e}")
            return [], "seed"
    
    async def _try_smart_retriever_fallback(
        self,
        request: TripRequest,
        cabin_class: str
    ) -> Tuple[List[dict], str]:
        """
        TIER 2: Fallback to SmartRetriever seed data
        
        Returns:
            (flights_data, data_source)
        """
        
        try:
            self.logger.info("🔄 [Tier 2] Using SmartRetriever fallback...")
            
            flights_data, data_source = await self.retriever.get_flights(
                origin=request.origin or "Jakarta",
                destination=request.destination,
                departure_date=request.start_date,
                return_date=request.end_date,
                travelers=request.travelers,
                travel_class=cabin_class
            )
            
            if flights_data:
                self.logger.info(f"✅ [Tier 2] SmartRetriever returned {len(flights_data)} flights")
            else:
                self.logger.warning("⚠️  [Tier 2] SmartRetriever returned no results")
            
            return flights_data, data_source
        
        except Exception as e:
            self.logger.error(f"❌ [Tier 2] SmartRetriever fallback error: {e}")
            return [], "seed"
    
    async def _try_llm_fallback(
        self,
        request: TripRequest,
        cabin_class: str,
        warnings: List[str]
    ) -> Tuple[List[dict], str]:
        """
        TIER 3: Use LLM to generate estimated flight prices
        
        Returns:
            (flights_data, data_source)
        """
        
        if not self.llm_enabled:
            self.logger.warning("LLM not available for fallback")
            return [], "llm_unavailable"
        
        try:
            self.logger.info("🧠 [Tier 3] Using LLM to estimate flight prices...")
            
            # Import Gemini
            import google.generativeai as genai
            
            origin = request.origin or "Jakarta"
            destination = request.destination
            
            # Create prompt for LLM
            prompt = f"""You are an aviation pricing expert. Estimate realistic flight prices for this route.

Route: {origin} → {destination}
Departure Date: {request.start_date}
Return Date: {request.end_date}
Travelers: {request.travelers}
Cabin Class: {cabin_class}

CRITICAL RULES:
1. If this route has NO MAJOR AIRPORT at origin or destination, return exactly: NO_AIRPORT
2. Otherwise, estimate realistic prices in IDR (Indonesian Rupiah)
3. Consider: distance, route popularity, season, cabin class
4. Return ONLY valid JSON, no markdown, no explanations

If airports exist, return JSON:
{{
  "has_airport": true,
  "outbound_price_per_person": <number>,
  "return_price_per_person": <number>,
  "estimated_duration_hours": <number>,
  "airline_suggestion": "<airline name>",
  "confidence": "low|medium|high"
}}

If NO airport:
{{
  "has_airport": false,
  "reason": "No major airport in origin/destination"
}}

Examples:
Jakarta → Bali: {{"has_airport": true, "outbound_price_per_person": 1500000, "return_price_per_person": 1500000, "estimated_duration_hours": 2.0, "airline_suggestion": "Garuda Indonesia", "confidence": "high"}}
Jakarta → Malang: {{"has_airport": true, "outbound_price_per_person": 800000, "return_price_per_person": 800000, "estimated_duration_hours": 1.5, "airline_suggestion": "Lion Air", "confidence": "medium"}}
Jakarta → Small Village: {{"has_airport": false, "reason": "No major airport in destination"}}

Your JSON response:"""

            response = self.amadeus_client.llm_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_output_tokens": 300,
                }
            )
            
            # Parse JSON response
            import json
            text = response.text.strip()
            
            # Remove markdown if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            data = json.loads(text)
            
            # Check if route has airport
            if not data.get("has_airport", False):
                reason = data.get("reason", "No airport available")
                self.logger.warning(f"⚠️  [Tier 3] LLM says: {reason}")
                return [], "no_airport"
            
            # Generate estimated flights
            outbound_price = data.get("outbound_price_per_person", 1000000)
            return_price = data.get("return_price_per_person", 1000000)
            duration_hours = data.get("estimated_duration_hours", 2.0)
            airline = data.get("airline_suggestion", "Estimated Airline")
            
            # Create estimated flight data
            flights_data = []
            
            # Outbound flight
            departure_time = datetime.combine(request.start_date, datetime.min.time().replace(hour=8))
            arrival_time = departure_time + timedelta(hours=duration_hours)
            
            flights_data.append({
                "airline": airline,
                "flight_number": "EST-OUT",
                "departure_airport": origin[:3].upper(),
                "arrival_airport": destination[:3].upper(),
                "departure_time": departure_time.isoformat(),
                "arrival_time": arrival_time.isoformat(),
                "duration_hours": duration_hours,
                "price": outbound_price,
                "stops": 0,
                "cabin_class": cabin_class
            })
            
            # Return flight
            return_departure = datetime.combine(request.end_date, datetime.min.time().replace(hour=16))
            return_arrival = return_departure + timedelta(hours=duration_hours)
            
            flights_data.append({
                "airline": airline,
                "flight_number": "EST-RET",
                "departure_airport": destination[:3].upper(),
                "arrival_airport": origin[:3].upper(),
                "departure_time": return_departure.isoformat(),
                "arrival_time": return_arrival.isoformat(),
                "duration_hours": duration_hours,
                "price": return_price,
                "stops": 0,
                "cabin_class": cabin_class
            })
            
            self.logger.info(f"✅ [Tier 3] LLM generated {len(flights_data)} estimated flights")
            warnings.append("🤖 Flight prices are AI estimates based on typical routes - VERIFY before booking")
            
            return flights_data, "llm_fallback"
        
        except Exception as e:
            self.logger.error(f"❌ [Tier 3] LLM fallback error: {e}")
            return [], "llm_error"
    
    async def _try_ground_transport_fallback(
        self,
        request: TripRequest,
        warnings: List[str],
        data_source: str,
        duration: float
    ) -> FlightOutput:
        """
        TIER 4: Fallback to ground transport if flights not available
        """
        
        self.logger.info("🚂 [Tier 4] Checking ground transport as alternative...")
        
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
                    f"✈️  No flights available for this route. "
                    f"Alternative: {cheapest['transport_type'].title()} "
                    f"({cheapest['name']}) - Rp {cheapest['cost_per_person']:,.0f}/person "
                    f"({cheapest['duration_hours']}h). Contact travel agent to book."
                )
                self.logger.info(f"✅ [Tier 4] Ground transport available: {cheapest['transport_type']}")
        else:
            warnings.append(
                f"❌ No flights or ground transport found for {request.origin} → {request.destination}. "
                f"This route may not be directly accessible."
            )
            self.logger.warning("⚠️  [Tier 4] No ground transport available either")
        
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
                # Parse based on data source
                if data_source == "amadeus_api":
                    flight = self._parse_amadeus_flight(flight_data)
                else:
                    # Works for both SmartRetriever and LLM fallback
                    flight = self._parse_retriever_flight(flight_data)
                
                if flight:
                    flights.append(flight)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse flight: {e}")
                continue
        
        return flights
    
    def _parse_amadeus_flight(self, flight_data: dict) -> Optional[Flight]:
        """Parse Amadeus API flight format"""
        
        try:
            departure_time = datetime.fromisoformat(
                flight_data['departure_time'].replace('Z', '+00:00')
            )
            arrival_time = datetime.fromisoformat(
                flight_data['arrival_time'].replace('Z', '+00:00')
            )
            
            flight = Flight(
                airline=flight_data.get('airline', 'Unknown'),
                flight_number=flight_data.get('flight_number', 'UNKNOWN'),
                departure_airport=flight_data.get('departure_airport', ''),
                arrival_airport=flight_data.get('arrival_airport', ''),
                departure_time=departure_time,
                arrival_time=arrival_time,
                duration_hours=flight_data.get('duration_hours', 0),
                price=flight_data.get('price', 0),
                stops=flight_data.get('stops', 0),
                cabin_class=flight_data.get('cabin_class', 'economy')
            )
            
            return flight
            
        except Exception as e:
            self.logger.warning(f"Failed to parse Amadeus flight: {e}")
            return None
    
    def _parse_retriever_flight(self, flight_data: dict) -> Optional[Flight]:
        """Parse SmartRetriever/LLM flight format"""
        
        try:
            departure_time = datetime.fromisoformat(
                flight_data['departure_time'].replace('Z', '+00:00')
            )
            arrival_time = datetime.fromisoformat(
                flight_data['arrival_time'].replace('Z', '+00:00')
            )
            
            flight = Flight(
                airline=flight_data.get('airline', 'Unknown'),
                flight_number=flight_data.get('flight_number', 'UNKNOWN'),
                departure_airport=flight_data.get('departure_airport', ''),
                arrival_airport=flight_data.get('arrival_airport', ''),
                departure_time=departure_time,
                arrival_time=arrival_time,
                duration_hours=flight_data.get('duration_hours', 0),
                price=flight_data.get('price', 0),
                stops=flight_data.get('stops', 0),
                cabin_class=flight_data.get('cabin_class', 'economy')
            )
            
            return flight
            
        except Exception as e:
            self.logger.warning(f"Failed to parse retriever flight: {e}")
            return None
    
    def _generate_return_flight(self, outbound: Flight, request: TripRequest) -> Flight:
        """Generate return flight based on outbound"""
        
        return_flight = Flight(
            airline=outbound.airline,
            flight_number=outbound.flight_number.replace('OUT', 'RET'),
            departure_airport=outbound.arrival_airport,
            arrival_airport=outbound.departure_airport,
            departure_time=datetime.combine(
                request.end_date,
                outbound.departure_time.time()
            ),
            arrival_time=datetime.combine(
                request.end_date,
                outbound.arrival_time.time()
            ),
            duration_hours=outbound.duration_hours,
            price=outbound.price,
            stops=outbound.stops,
            cabin_class=outbound.cabin_class
        )
        
        return return_flight
    
    def _create_metadata(self, data_source: str, duration: float) -> dict:
        """Create metadata dictionary"""
        return {
            "agent": self.name,
            "data_source": data_source,
            "execution_time_ms": int(duration),
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_confidence(self, source: str, data_quality_score: int) -> float:
        """Calculate confidence score"""
        base_confidence = {
            "amadeus_api": 0.95,  # Highest - real API data
            "api": 0.95,
            "seed": 0.80,
            "llm_fallback": 0.60,  # Lower - AI estimates
            "no_airport": 0.0,
            "no_flights": 0.0
        }
        
        base = base_confidence.get(source, 0.50)
        quality_factor = min(data_quality_score / 100, 1.0)
        
        return base * quality_factor