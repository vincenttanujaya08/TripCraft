from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.models.schemas import TripRequest, TripPlan
from backend.orchestrator.trip_orchestrator import TripOrchestrator
import logging

router = APIRouter(prefix="/trip", tags=["trip"])
logger = logging.getLogger(__name__)

orchestrator = TripOrchestrator()

@router.post("/plan", response_model=TripPlan)
async def plan_trip(request: TripRequest):
    """
    Plan a trip based on user request.
    This behaves as a synchronous endpoint for the frontend's simple fetch implementation.
    """
    try:
        logger.info(f"Received trip request for {request.destination}")
        # Note: In a real production app, this should be a background task with polling
        # But for this demo, we await the result directly
        trip_plan, metadata = await orchestrator.plan_trip(request)
        return trip_plan
    except Exception as e:
        logger.error(f"Trip planning failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
