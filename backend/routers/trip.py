from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from backend.models.schemas import TripRequest, TripPlan
from backend.orchestrator.trip_orchestrator import TripOrchestrator
import logging
import uuid
import os

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


@router.post("/pdf")
async def generate_trip_pdf(trip_plan: TripPlan):
    """
    Generate PDF from trip plan data
    
    Args:
        trip_plan: Complete trip plan (sent from frontend)
    
    Returns:
        PDF file (application/pdf)
    """
    try:
        logger.info("Received PDF generation request")
        
        # Import PDF generator
        from backend.utils.pdf_generator import generate_trip_pdf as gen_pdf
        
        # Create unique filename
        pdf_filename = f"trip_{uuid.uuid4().hex[:8]}.pdf"
        pdf_path = f"outputs/{pdf_filename}"
        
        # Ensure outputs directory exists
        os.makedirs("outputs", exist_ok=True)
        
        # Generate PDF
        logger.info(f"Generating PDF at {pdf_path}")
        gen_pdf(trip_plan, pdf_path)
        
        logger.info("✅ PDF generated successfully")
        
        # Return as downloadable file
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename="TripCraft_Itinerary.pdf"
        )
        
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
