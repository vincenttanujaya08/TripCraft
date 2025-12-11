"""
SQLAlchemy database models for TripCraft Lite
"""

from sqlalchemy import create_engine, Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import uuid
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tripcraft.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_id(prefix: str = "") -> str:
    """Generate unique ID with optional prefix"""
    return f"{prefix}{uuid.uuid4().hex[:16]}"


class Trip(Base):
    """Main trip record"""
    __tablename__ = "trips"
    
    trip_id = Column(String(50), primary_key=True, default=lambda: generate_id("trip_"))
    trace_id = Column(String(50), nullable=False, default=lambda: generate_id("trace_"))
    status = Column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed
    
    # Store original request
    request_data = Column(JSON, nullable=False)
    
    # Processing metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processing_time_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    agent_outputs = relationship("AgentOutput", back_populates="trip", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Trip {self.trip_id} - {self.status}>"


class AgentOutput(Base):
    """Individual agent execution results"""
    __tablename__ = "agent_outputs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(String(50), ForeignKey("trips.trip_id"), nullable=False)
    
    # Agent info
    agent_name = Column(String(50), nullable=False)  # destination, dining, hotel, etc.
    output_data = Column(JSON, nullable=False)
    
    # Execution metadata
    execution_time_ms = Column(Integer, nullable=True)
    data_source = Column(String(20), nullable=True)  # api, seed, llm_fallback
    confidence = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    trip = relationship("Trip", back_populates="agent_outputs")
    
    def __repr__(self):
        return f"<AgentOutput {self.agent_name} for {self.trip_id}>"


class ImageCache(Base):
    """Cache for image search results"""
    __tablename__ = "image_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Search key (hash of query)
    query_key = Column(String(100), unique=True, nullable=False, index=True)
    query_text = Column(String(500), nullable=False)
    
    # Image data
    image_url = Column(String(500), nullable=False)
    source = Column(String(20), nullable=False)  # unsplash, pexels, placeholder
    confidence = Column(Float, nullable=False)
    
    # Metadata
    image_metadata = Column(JSON, nullable=True)  # photographer, description, etc.
    
    # Cache management
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    hit_count = Column(Integer, default=0, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ImageCache {self.query_key} - {self.source}>"

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized")
