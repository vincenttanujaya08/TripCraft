"""
Verifier Agent - Validates and checks trip plan quality
FIXED: Removed retriever parameter (not used), updated execute() to use context
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from backend.models.schemas import (
    TripRequest,
    VerificationOutput,
    ValidationIssue,
    DestinationOutput,
    HotelOutput,
    DiningOutput,
    FlightOutput,
    BudgetOutput,
    ItineraryOutput,
)
from backend.agents.base_agent import BaseAgent

logger = logging.getLogger(f"agent.Verifier")


class VerifierAgent(BaseAgent):
    """Agent responsible for verifying trip plan quality and completeness"""
    
    def __init__(self):
        """Initialize VerifierAgent - no retriever needed"""
        super().__init__("Verifier")
        
    async def execute(
        self,
        request: TripRequest,
        context: Optional[Dict] = None
    ) -> Tuple[VerificationOutput, Dict]:
        """
        Verify and validate the complete trip plan
        
        Args:
            request: Trip planning request
            context: Context dictionary with all agent outputs
            
        Returns:
            (VerificationOutput, metadata)
        """
        self.logger.info("🚀 Verifier agent starting...")
        start_time = datetime.now()
        
        # Extract outputs from context
        destination_output: Optional[DestinationOutput] = context.get('destination_output') if context else None
        hotel_output: Optional[HotelOutput] = context.get('hotel_output') if context else None
        dining_output: Optional[DiningOutput] = context.get('dining_output') if context else None
        flight_output: Optional[FlightOutput] = context.get('flight_output') if context else None
        budget_output: Optional[BudgetOutput] = context.get('budget_output') if context else None
        itinerary_output: Optional[ItineraryOutput] = context.get('itinerary_output') if context else None
        
        try:
            issues: List[ValidationIssue] = []
            
            # Check destination
            if not destination_output or not destination_output.destination:
                issues.append(ValidationIssue(
                    severity="error",
                    component="destination",
                    message="No destination information available",
                    suggestion="Ensure destination agent completed successfully"
                ))
            elif not destination_output.attractions:
                issues.append(ValidationIssue(
                    severity="warning",
                    component="destination",
                    message="No attractions found for destination",
                    suggestion="Consider adding popular attractions manually"
                ))
            
            # Check hotels
            if not hotel_output or not hotel_output.hotels:
                issues.append(ValidationIssue(
                    severity="error",
                    component="accommodation",
                    message="No hotel options available",
                    suggestion="Check hotel availability for the destination and dates"
                ))
            elif not hotel_output.recommended_hotel:
                issues.append(ValidationIssue(
                    severity="warning",
                    component="accommodation",
                    message="No recommended hotel selected",
                    suggestion="Review available hotels and select one"
                ))
            
            # Check dining
            if not dining_output or not dining_output.restaurants:
                issues.append(ValidationIssue(
                    severity="warning",
                    component="dining",
                    message="No restaurant recommendations available",
                    suggestion="Search for local restaurants manually"
                ))
            
            # Check flights
            if not flight_output or not flight_output.outbound_flights:
                issues.append(ValidationIssue(
                    severity="error",
                    component="transportation",
                    message="No outbound flight options available",
                    suggestion="Check flight availability for the route and dates"
                ))
            if flight_output and not flight_output.return_flights:
                issues.append(ValidationIssue(
                    severity="error",
                    component="transportation",
                    message="No return flight options available",
                    suggestion="Check return flight availability"
                ))
            
            # Check budget
            if not budget_output:
                issues.append(ValidationIssue(
                    severity="warning",
                    component="budget",
                    message="Budget analysis not available",
                    suggestion="Calculate budget breakdown manually"
                ))
            elif not budget_output.is_within_budget:
                # Calculate over amount
                over_amount = budget_output.breakdown.total - request.budget
                issues.append(ValidationIssue(
                    severity="error",
                    component="budget",
                    message=f"Budget exceeded by Rp {over_amount:,.0f}",
                    suggestion="Consider reducing accommodation costs or trip duration"
                ))
            
            # Check itinerary
            if not itinerary_output or not itinerary_output.days:
                issues.append(ValidationIssue(
                    severity="warning",
                    component="itinerary",
                    message="No itinerary generated",
                    suggestion="Create a daily schedule manually"
                ))
            elif itinerary_output:
                # Check for empty days
                empty_days = [day for day in itinerary_output.days if not day.activities]
                if empty_days:
                    issues.append(ValidationIssue(
                        severity="warning",
                        component="itinerary",
                        message=f"{len(empty_days)} day(s) have no planned activities",
                        suggestion="Add activities to fill empty days"
                    ))
            
            # Check data quality across all components
            low_confidence_components = []
            if destination_output and destination_output.confidence < 0.5:
                low_confidence_components.append("destination")
            if hotel_output and hotel_output.confidence < 0.5:
                low_confidence_components.append("accommodation")
            if dining_output and dining_output.confidence < 0.5:
                low_confidence_components.append("dining")
            if flight_output and flight_output.confidence < 0.5:
                low_confidence_components.append("flights")
            
            if low_confidence_components:
                issues.append(ValidationIssue(
                    severity="warning",
                    component="data_quality",
                    message=f"Low confidence data in: {', '.join(low_confidence_components)}",
                    suggestion="Verify information from multiple sources"
                ))
            
            # Determine if plan is valid
            critical_issues = [i for i in issues if i.severity == "error"]
            is_valid = len(critical_issues) == 0
            
            # Calculate overall quality score (0-100)
            quality_score = 100.0
            for issue in issues:
                if issue.severity == "error":
                    quality_score -= 20.0
                elif issue.severity == "warning":
                    quality_score -= 5.0
            quality_score = max(0.0, min(100.0, quality_score))
            
            # Calculate confidence based on completeness
            components_present = sum([
                1 if destination_output else 0,
                1 if hotel_output and hotel_output.hotels else 0,
                1 if dining_output and dining_output.restaurants else 0,
                1 if flight_output and flight_output.outbound_flights else 0,
                1 if budget_output else 0,
                1 if itinerary_output and itinerary_output.days else 0
            ])
            
            confidence_score = self._calculate_confidence(
                data_source="seed",
                data_quality_score=int((components_present / 6.0) * 100)
            )
            # Convert from 0-100 to 0-1
            confidence = confidence_score / 100.0
            
            # Generate summary
            if is_valid:
                if len(issues) == 0:
                    summary = "Trip plan is complete and valid with no issues"
                else:
                    summary = f"Trip plan is valid with {len(issues)} minor warning(s)"
            else:
                summary = f"Found {len(critical_issues)} critical issue(s) that must be resolved"
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.info(
                f"✓ Verifier completed in {duration:.0f}ms "
                f"(valid: {is_valid}, issues: {len(issues)}, confidence: {confidence*100:.0f}%)"
            )
            
            # Create output
            output = VerificationOutput(
                is_valid=is_valid,
                issues=issues,
                quality_score=quality_score,
                summary=summary,
                metadata=self._create_metadata("seed", duration),
                data_source="seed",
                confidence=confidence
            )
            
            # Metadata
            metadata = {
                "data_source": "seed",
                "confidence": confidence,
                "warnings": [issue.message for issue in issues if issue.severity == "warning"],
                "errors": [issue.message for issue in issues if issue.severity == "error"],
                "execution_time_ms": int(duration)
            }
            
            return output, metadata
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"✗ Verifier failed after {duration:.0f}ms: {e}")
            raise
    
    def _create_metadata(self, data_source: str, duration: float) -> dict:
        """Create metadata dictionary"""
        return {
            "agent": self.name,
            "data_source": data_source,
            "execution_time_ms": int(duration),
            "timestamp": datetime.now().isoformat()
        }