"""
BaseAgent - Abstract base class for all travel planning agents
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from models.schemas import TripRequest

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, name: str):
        """
        Initialize base agent
        
        Args:
            name: Agent name
        """
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self.logger.info(f"{name} agent initialized")
    
    @abstractmethod
    async def execute(self, request: TripRequest, context: Optional[Dict] = None) -> tuple[Any, Dict]:
        """
        Execute agent logic
        
        Args:
            request: Trip request from user
            context: Shared context from previous agents (optional)
            
        Returns:
            (agent_output, metadata) where metadata includes:
                - execution_time_ms: Time taken to execute
                - data_source: Where data came from (api/seed/llm_fallback)
                - confidence: Confidence score (0.0-1.0)
                - warnings: List of warning messages
        """
        pass
    
    async def run(self, request: TripRequest, context: Optional[Dict] = None) -> tuple[Any, Dict]:
        """
        Run agent with timing and error handling
        
        Args:
            request: Trip request
            context: Shared context
            
        Returns:
            (output, metadata)
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"🚀 {self.name} agent starting...")
            
            # Execute agent logic
            output, metadata = await self.execute(request, context)
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            metadata["execution_time_ms"] = execution_time_ms
            
            # Ensure required metadata fields
            if "data_source" not in metadata:
                metadata["data_source"] = "unknown"
            if "confidence" not in metadata:
                metadata["confidence"] = 0.50  # Default medium confidence (0-1 scale)
            if "warnings" not in metadata:
                metadata["warnings"] = []
            
            self.logger.info(
                f"✓ {self.name} completed in {execution_time_ms}ms "
                f"(source: {metadata['data_source']}, "
                f"confidence: {metadata['confidence']:.0%})"
            )
            
            return output, metadata
        
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.logger.error(f"✗ {self.name} failed after {execution_time_ms}ms: {e}")
            
            # Return error metadata
            metadata = {
                "execution_time_ms": execution_time_ms,
                "data_source": "error",
                "confidence": 0.0,
                "warnings": [f"Agent execution failed: {str(e)}"],
                "error": str(e)
            }
            
            return None, metadata
    
    def _calculate_confidence(
        self,
        data_source: str,
        data_quality_score: int = 100
    ) -> float:
        """
        Calculate confidence score based on data source and quality
        
        Args:
            data_source: Where data came from (api/seed/llm_fallback)
            data_quality_score: Additional quality adjustment (0-100)
            
        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence by source (0-1 scale)
        base_confidence = {
            "api": 0.90,
            "seed": 0.85,
            "llm_fallback": 0.70,
            "unknown": 0.50
        }
        
        base = base_confidence.get(data_source, 0.50)
        
        # Adjust by data quality
        adjusted = base * (data_quality_score / 100.0)
        
        return max(0.0, min(1.0, adjusted))
    
    def _add_warning(self, warnings: list, message: str, severity: str = "info"):
        """
        Add warning message to list
        
        Args:
            warnings: List to append to
            message: Warning message
            severity: Severity level (info/warning/error)
        """
        warnings.append({
            "severity": severity,
            "message": message,
            "agent": self.name
        })
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"