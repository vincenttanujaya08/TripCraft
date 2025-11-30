"""
FlightAgent - UPDATED with budget allocation and ground transport fallback
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict, Any
from backend.models.schemas import (
    TripRequest, 
    FlightOutput, 
    Flight,
    GroundTransportOption,
    GroundTransportRoute
)
from backend.agents.base_agent import BaseAgent
from backend.data_sources.smart_retriever import SmartRetriever

logger = logging.getLogger(f"agent.Flight")


class FlightAgent(BaseAgent):
    """Agent responsible for finding flight options with budget awareness"""
    
    def __init__(self, retriever: SmartRetriever):
        super().__init__("Flight")
        self.retriever = retriever
    
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
        max_budget: Optional[float] = None
    ) -> FlightOutput:
        """
        Find suitable flights with budget constraints
        
        NEW: Added max_budget parameter and ground transport fallback
        
        Args:
            request: Trip planning request
            max_budget: Maximum budget allocated for flights (optional)
            
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
            
            # TIER 1: Try flights via SmartRetriever
            flights_data, data_source = await self.retriever.get_flights(
                origin=request.origin or "Jakarta",
                destination=request.destination,
                departure_date=request.start_date,
                return_date=request.end_date,
                travelers=request.travelers,
                travel_class=cabin_class
            )
            
            if not flights_data:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                self.logger.error(f"✗ Flight failed after {duration:.0f}ms: No flights found")
                
                # FALLBACK: Check ground transport
                return await self._try_ground_transport_fallback(
                    request, warnings, data_source, duration
                )
            
            # Parse flights
            valid_flights = self._parse_flights(flights_data, request)
            
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
                    f"⚠️ Flight over budget: Rp {total_cost:,.0f} > Rp {max_budget:,.0f} "
                    f"(+{over_pct:.1f}%)"
                )
                
                # Check if ground transport is viable
                ground_data, _ = self.retriever.get_ground_transport(
                    origin=request.origin or "Jakarta",
                    destination=request.destination
                )
                
                if ground_data:
                    from constants.ground_transport import get_cheapest_option
                    cheapest = get_cheapest_option(
                        request.origin or "Jakarta",
                        request.destination
                    )
                    
                    if cheapest:
                        warnings.append(
                            f"⚠️ Flight exceeds budget by Rp {over_amount:,.0f} ({over_pct:.1f}%). "
                            f"Consider {cheapest['transport_type']}: Rp {cheapest['cost_per_person']:,.0f}/person "
                            f"({cheapest['duration_hours']}h)"
                        )
                else:
                    warnings.append(
                        f"⚠️ Flight exceeds budget by Rp {over_amount:,.0f} ({over_pct:.1f}%). "
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
                warnings.append("Flight estimates generated by AI - verify before booking")
            
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
    
    async def _try_ground_transport_fallback(
        self,
        request: TripRequest,
        warnings: List[str],
        data_source: str,
        duration: float
    ) -> FlightOutput:
        """
        Fallback to ground transport if flights not available/too expensive
        """
        
        self.logger.info("🚂 Checking ground transport as fallback...")
        
        ground_data, _ = self.retriever.get_ground_transport(
            origin=request.origin or "Jakarta",
            destination=request.destination
        )
        
        if ground_data:
            from constants.ground_transport import get_cheapest_option
            cheapest = get_cheapest_option(
                request.origin or "Jakarta",
                request.destination
            )
            
            if cheapest:
                warnings.append(
                    f"✈️ No flights found. Alternative: {cheapest['transport_type'].title()} "
                    f"({cheapest['name']}) - Rp {cheapest['cost_per_person']:,.0f}/person "
                    f"({cheapest['duration_hours']}h). Contact travel agent to book."
                )
        else:
            warnings.append(
                f"No flights or ground transport found for {request.origin} → {request.destination}. "
                f"This route may not be directly accessible."
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
    
    def _parse_flights(self, flights_data: List[dict], request: TripRequest) -> List[Flight]:
        """Parse flight data to Flight objects"""
        
        flights = []
        
        for flight_data in flights_data:
            try:
                # Parse datetime
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
                
                flights.append(flight)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse flight: {e}")
                continue
        
        return flights
    
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
            "api": 0.95,
            "seed": 0.80,
            "llm_fallback": 0.60
        }
        
        base = base_confidence.get(source, 0.50)
        quality_factor = min(data_quality_score / 100, 1.0)
        
        return base * quality_factor