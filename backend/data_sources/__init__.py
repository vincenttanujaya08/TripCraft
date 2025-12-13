"""
Data Sources Layer - 3-tier fallback strategy
APIs → Seed Data → LLM Fallback
"""

from .seed_loader import SeedLoader, get_seed_loader
from .opentripmap_client import OpenTripMapClient, get_opentripmap_client
from .llm_fallback import LLMFallback, get_llm_fallback
from .amadeus_client import AmadeusFlightClient, get_amadeus_client
from .smart_retriever import SmartRetriever, get_smart_retriever

__all__ = [
    "SeedLoader",
    "get_seed_loader",
    "OpenTripMapClient",
    "get_opentripmap_client",
    "LLMFallback",
    "get_llm_fallback",
    "AmadeusFlightClient",
    "get_amadeus_client",
    "SmartRetriever",
    "get_smart_retriever",
]