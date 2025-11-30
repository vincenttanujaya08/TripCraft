"""
Ground Transport Database - Hardcoded for TOP Indonesian routes
Covers ~80% of domestic travel use cases
"""

from typing import Dict, Optional, List

# Format: (origin, destination) -> transport options
GROUND_TRANSPORT_DB: Dict[tuple, Dict] = {
    # ========================================
    # JAVA CORRIDOR (Train Available)
    # ========================================
    ("Jakarta", "Bandung"): {
        "train": {
            "name": "Argo Parahyangan",
            "operator": "KAI",
            "cost_per_person": 200000,
            "duration_hours": 3.5,
            "frequency": "Multiple daily",
            "class_available": ["Eksekutif", "Bisnis"]
        },
        "bus": {
            "name": "Various operators",
            "cost_per_person": 80000,
            "duration_hours": 4.0,
            "frequency": "Every 30 mins",
            "class_available": ["AC", "Non-AC"]
        }
    },
    
    ("Jakarta", "Yogyakarta"): {
        "train": {
            "name": "Taksaka / Argo Dwipangga",
            "operator": "KAI",
            "cost_per_person": 300000,
            "duration_hours": 7.5,
            "frequency": "2-3 daily",
            "class_available": ["Eksekutif"]
        },
        "bus": {
            "name": "Various operators",
            "cost_per_person": 150000,
            "duration_hours": 10.0,
            "frequency": "Multiple daily",
            "class_available": ["AC", "Non-AC"]
        }
    },
    
    ("Jakarta", "Surabaya"): {
        "train": {
            "name": "Argo Bromo Anggrek",
            "operator": "KAI",
            "cost_per_person": 350000,
            "duration_hours": 8.0,
            "frequency": "Daily",
            "class_available": ["Eksekutif"]
        },
        "bus": {
            "name": "Various operators",
            "cost_per_person": 180000,
            "duration_hours": 12.0,
            "frequency": "Multiple daily",
            "class_available": ["AC", "Non-AC"]
        }
    },
    
    ("Jakarta", "Solo"): {
        "train": {
            "name": "Argo Lawu",
            "operator": "KAI",
            "cost_per_person": 280000,
            "duration_hours": 6.5,
            "frequency": "Daily",
            "class_available": ["Eksekutif"]
        }
    },
    
    ("Jakarta", "Semarang"): {
        "train": {
            "name": "Argo Muria",
            "operator": "KAI",
            "cost_per_person": 250000,
            "duration_hours": 6.0,
            "frequency": "Daily",
            "class_available": ["Eksekutif"]
        }
    },
    
    ("Bandung", "Yogyakarta"): {
        "train": {
            "name": "Via Jakarta (transfer)",
            "operator": "KAI",
            "cost_per_person": 400000,
            "duration_hours": 10.0,
            "frequency": "Daily",
            "class_available": ["Eksekutif"]
        }
    },
    
    ("Surabaya", "Yogyakarta"): {
        "train": {
            "name": "Gajayana",
            "operator": "KAI",
            "cost_per_person": 200000,
            "duration_hours": 4.5,
            "frequency": "Daily",
            "class_available": ["Eksekutif"]
        }
    },
    
    ("Surabaya", "Malang"): {
        "train": {
            "name": "Gajayana",
            "operator": "KAI",
            "cost_per_person": 100000,
            "duration_hours": 2.5,
            "frequency": "Multiple daily",
            "class_available": ["Eksekutif", "Bisnis"]
        }
    },
    
    # ========================================
    # FERRY ROUTES
    # ========================================
    ("Surabaya", "Bali"): {
        "ferry": {
            "name": "Ketapang-Gilimanuk Ferry",
            "operator": "ASDP",
            "cost_per_person": 50000,
            "duration_hours": 2.0,
            "frequency": "Every 30 mins",
            "class_available": ["Economy"]
        },
        "bus": {
            "name": "Travel bus (including ferry)",
            "cost_per_person": 250000,
            "duration_hours": 6.0,
            "frequency": "Multiple daily",
            "class_available": ["AC"]
        }
    },
    
    # ========================================
    # SUMATRA (Limited options)
    # ========================================
    ("Jakarta", "Lampung"): {
        "bus": {
            "name": "DAMRI / Private operators",
            "cost_per_person": 200000,
            "duration_hours": 8.0,
            "frequency": "Multiple daily",
            "class_available": ["AC"]
        }
    },
}


def get_ground_transport(origin: str, destination: str) -> Optional[Dict]:
    """
    Get ground transport options between two cities
    
    Args:
        origin: Origin city name
        destination: Destination city name
        
    Returns:
        Dict with transport options or None if not available
    """
    
    # Normalize city names
    origin_norm = origin.strip().title()
    dest_norm = destination.strip().title()
    
    # Try direct lookup
    key = (origin_norm, dest_norm)
    if key in GROUND_TRANSPORT_DB:
        return GROUND_TRANSPORT_DB[key]
    
    # Try reverse (some routes are bidirectional)
    reverse_key = (dest_norm, origin_norm)
    if reverse_key in GROUND_TRANSPORT_DB:
        return GROUND_TRANSPORT_DB[reverse_key]
    
    return None


def get_cheapest_option(origin: str, destination: str) -> Optional[Dict]:
    """
    Get the cheapest ground transport option
    
    Returns:
        Dict with transport_type, cost, duration, name
    """
    
    options = get_ground_transport(origin, destination)
    if not options:
        return None
    
    cheapest = None
    min_cost = float('inf')
    
    for transport_type, details in options.items():
        cost = details.get('cost_per_person', float('inf'))
        if cost < min_cost:
            min_cost = cost
            cheapest = {
                'transport_type': transport_type,
                'cost_per_person': cost,
                'duration_hours': details.get('duration_hours'),
                'name': details.get('name'),
                'operator': details.get('operator')
            }
    
    return cheapest


def is_ground_transport_viable(origin: str, destination: str, max_hours: float = 12.0) -> bool:
    """
    Check if ground transport is viable (< max_hours)
    
    Args:
        origin: Origin city
        destination: Destination city
        max_hours: Maximum acceptable travel time
        
    Returns:
        True if viable option exists
    """
    
    options = get_ground_transport(origin, destination)
    if not options:
        return False
    
    for details in options.values():
        if details.get('duration_hours', 999) <= max_hours:
            return True
    
    return False