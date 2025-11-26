"""
TripCraft Lite - Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="TripCraft Lite API",
    description="Agentic Travel Planner with Multi-Agent RAG System",
    version="1.0.0",
    debug=os.getenv("DEBUG", "true").lower() == "true"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    from models.database import init_db
    init_db()
    print("✅ TripCraft Lite API started successfully!")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "TripCraft Lite API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    import os
    
    # Check if essential env vars are set
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    return {
        "status": "healthy",
        "database": "connected",
        "gemini_api": "configured" if gemini_key else "missing",
        "opentripmap_api": "configured" if os.getenv("OPENTRIPMAP_API_KEY") else "optional",
        "unsplash_api": "configured" if os.getenv("UNSPLASH_ACCESS_KEY") else "optional"
    }


# Import routers (we'll create these in next steps)
# from routers import trip, debug
# app.include_router(trip.router, prefix="/trip", tags=["trips"])
# app.include_router(debug.router, prefix="/debug", tags=["debug"])


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
