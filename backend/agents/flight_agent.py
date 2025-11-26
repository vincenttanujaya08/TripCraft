"""
Flight Agent - Handles flight search and booking
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from models.schemas import (
    TripRequest, 
    FlightOutput, 
    Flight,
)
from agents.base_agent import BaseAgent
from data_sources.smart_retriever import SmartRetriever

logger = logging.getLogger(f"agent.Flight")


class FlightAgent(BaseAgent):
    """Agent responsible for finding flight options"""
    
    def __init__(self, retriever: SmartRetriever):
        super().__init__("Flight", retriever)
        
    async def execute(self, request: TripRequest) -> FlightOutput:
        """
        Find suitable flights based on trip requirements
        
        Args:
            request: Trip planning request
            
        Returns:
            FlightOutput with flight options
        """
        self.logger.info("🚀 Flight agent starting...")
        start_time = datetime.now()
        
        try:
            # Retrieve flight options from data sources
            flights_data = await self.retriever.get_flights(
                origin=request.origin,
                destination=request.destination,
                departure_date=request.start_date,
                return_date=request.end_date,
                travelers=request.travelers
            )
            
            if not flights_data:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                self.logger.error(f"✗ Flight failed after {duration:.0f}ms: No flights found")
                
                return FlightOutput(
                    outbound_flights=[],
                    return_flights=[],
                    recommended_outbound=None,
                    recommended_return=None,
                    total_flight_cost=0.0,
                    warnings=[f"No flights found for {request.origin} → {request.destination}"],
                    metadata=self._create_metadata("llm_fallback", duration),
                    data_source="llm_fallback",
                    confidence=0
                )
            
            # Parse flights
            valid_flights = []
            for flight_data in flights_data:
                try:
                    flight = Flight.model_validate(flight_data)
                    valid_flights.append(flight)
                except Exception as e:
                    self.logger.warning(f"Failed to parse flight: {e}")
                    continue
            
            if not valid_flights:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                self.logger.error(f"✗ Flight failed after {duration:.0f}ms: No valid flights")
                
                return FlightOutput(
                    outbound_flights=[],
                    return_flights=[],
                    recommended_outbound=None,
                    recommended_return=None,
                    total_flight_cost=0.0,
                    warnings=[f"No valid flights found for route"],
                    metadata=self._create_metadata("llm_fallback", duration),
                    data_source="llm_fallback",
                    confidence=0
                )
            
            # Separate outbound and return flights
            outbound_flights = []
            return_flights = []
            
            # FIX: Use date object properties directly instead of split()
            departure_date_str = f"{request.start_date.year}-{str(request.start_date.month).zfill(2)}-{str(request.start_date.day).zfill(2)}"
            return_date_str = f"{request.end_date.year}-{str(request.end_date.month).zfill(2)}-{str(request.end_date.day).zfill(2)}"
            
            for flight in valid_flights:
                # Check if it's an outbound or return flight based on date
                if flight.departure_time.startswith(departure_date_str):
                    outbound_flights.append(flight)
                elif flight.departure_time.startswith(return_date_str):
                    return_flights.append(flight)
                else:
                    # If no exact date match, check origin/destination
                    if flight.origin == request.origin and flight.destination == request.destination:
                        outbound_flights.append(flight)
                    elif flight.origin == request.destination and flight.destination == request.origin:
                        return_flights.append(flight)
            
            # If we still don't have return flights, generate them from outbound
            if outbound_flights and not return_flights:
                for outbound in outbound_flights:
                    return_flight_data = outbound.model_dump()
                    # Swap origin and destination
                    return_flight_data['origin'] = outbound.destination
                    return_flight_data['destination'] = outbound.origin
                    return_flight_data['flight_number'] = outbound.flight_number.replace('OUT', 'RET')
                    # Update times for return date
                    return_flight_data['departure_time'] = f"{return_date_str}T{outbound.departure_time.split('T')[1]}"
                    return_flight_data['arrival_time'] = f"{return_date_str}T{outbound.arrival_time.split('T')[1]}"
                    
                    try:
                        return_flights.append(Flight.model_validate(return_flight_data))
                    except:
                        pass
            
            # Sort by price and then by convenience (shorter duration)
            outbound_flights.sort(key=lambda f: (f.price, f.duration_minutes))
            return_flights.sort(key=lambda f: (f.price, f.duration_minutes))
            
            # Select top options (max 3 each)
            selected_outbound = outbound_flights[:3]
            selected_return = return_flights[:3]
            
            # Recommend the best options (cheapest with reasonable timing)
            recommended_out = selected_outbound[0] if selected_outbound else None
            recommended_ret = selected_return[0] if selected_return else None
            
            # Calculate total cost
            total_cost = 0.0
            if recommended_out:
                total_cost += recommended_out.price * request.travelers
            if recommended_ret:
                total_cost += recommended_ret.price * request.travelers
            
            # Calculate confidence
            data_source = flights_data[0].get("_source", "seed") if flights_data else "seed"
            confidence = self._calculate_confidence(
                source=data_source,
                data_quality_score=(len(selected_outbound) + len(selected_return)) * 10
            )
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.info(
                f"✓ Flight completed in {duration:.0f}ms "
                f"(source: {data_source}, confidence: {confidence*100:.0f}%)"
            )
            
            return FlightOutput(
                outbound_flights=[Flight.model_validate(f.model_dump()) for f in selected_outbound],
                return_flights=[Flight.model_validate(f.model_dump()) for f in selected_return],
                recommended_outbound=Flight.model_validate(recommended_out.model_dump()) if recommended_out else None,
                recommended_return=Flight.model_validate(recommended_ret.model_dump()) if recommended_ret else None,
                total_flight_cost=total_cost,
                warnings=[],
                metadata=self._create_metadata(data_source, duration),
                data_source=data_source,
                confidence=confidence
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"✗ Flight failed after {duration:.0f}ms: {e}")
            raise