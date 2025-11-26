"""
DiningAgent - Finds restaurant recommendations based on preferences
"""

from typing import Dict, Optional, List
from datetime import datetime
from .base_agent import BaseAgent
from models.schemas import TripRequest, DiningOutput, Restaurant
from data_sources import get_smart_retriever


class DiningAgent(BaseAgent):
    """Agent that finds and recommends restaurants"""
    
    def __init__(self):
        super().__init__("Dining")
        self.retriever = get_smart_retriever()
    
    async def execute(
        self, 
        request: TripRequest, 
        context: Optional[Dict] = None
    ) -> tuple[DiningOutput, Dict]:
        """
        Find restaurants based on preferences and dietary restrictions
        
        Args:
            request: Trip request
            context: Shared context from previous agents
            
        Returns:
            (DiningOutput, metadata)
        """
        
        warnings = []
        
        # Calculate trip days
        days = self._calculate_days(request.start_date, request.end_date)
        
        if days <= 0:
            self._add_warning(warnings, "Invalid date range - assuming 1 day", "warning")
            days = 1
        
        # Get budget allocation (assume 30% for food)
        total_budget = request.budget
        food_budget_total = total_budget * 0.3
        daily_food_budget = food_budget_total / days
        
        # Get cuisine preference from interests (if any)
        cuisine_preference = self._extract_cuisine_preference(request.preferences.interests)
        
        # Get restaurants
        restaurants_data, data_source = await self.retriever.get_restaurants(
            city=request.destination,
            cuisine=cuisine_preference,
            count=8
        )
        
        if not restaurants_data:
            self._add_warning(
                warnings,
                f"No restaurants found for {request.destination}",
                "warning"
            )
        
        # Parse restaurants
        restaurants = []
        for rest_data in restaurants_data:
            try:
                # Check dietary restrictions
                if not self._check_dietary_restrictions(
                    rest_data, 
                    request.preferences.dietary_restrictions
                ):
                    continue
                
                restaurant = Restaurant(
                    name=rest_data.get("name", "Unknown Restaurant"),
                    cuisine=rest_data.get("cuisine", "International"),
                    price_range=rest_data.get("price_range", "$$"),
                    estimated_cost_per_person=rest_data.get("estimated_cost_per_person", 0),
                    rating=rest_data.get("rating", 0.0),
                    specialties=rest_data.get("specialties", []),
                    location=rest_data.get("location", request.destination),
                    meal_type=rest_data.get("meal_type", ["lunch", "dinner"]),
                    description=rest_data.get("description", ""),
                    image_url=rest_data.get("image_url")  # Optional
                )
                restaurants.append(restaurant)
            
            except Exception as e:
                self.logger.warning(f"Failed to parse restaurant: {e}")
        
        # Diversify restaurant selection
        restaurants = self._diversify_restaurants(restaurants)
        
        # Calculate estimated daily food cost
        estimated_daily_cost = self._estimate_daily_food_cost(
            restaurants,
            request.travelers
        )
        
        # Check budget
        if estimated_daily_cost > daily_food_budget * 1.2:
            self._add_warning(
                warnings,
                f"Estimated daily food cost (${estimated_daily_cost:.0f}) exceeds budget (${daily_food_budget:.0f})",
                "warning"
            )
        
        # Add dietary restriction note if applicable
        if request.preferences.dietary_restrictions:
            self._add_warning(
                warnings,
                f"Filtered for dietary restrictions: {', '.join(request.preferences.dietary_restrictions)}",
                "info"
            )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            data_source=data_source,
            data_quality_score=100 if restaurants else 60
        )
        
        # Create output
        output = DiningOutput(
            restaurants=restaurants,
            estimated_daily_food_cost=estimated_daily_cost,
            warnings=warnings,
            data_source=data_source,
            confidence=confidence
        )
        
        # Metadata
        metadata = {
            "data_source": data_source,
            "confidence": confidence,
            "warnings": warnings,
            "restaurants_count": len(restaurants),
            "daily_budget": daily_food_budget
        }
        
        return output, metadata
    
    def _calculate_days(self, start_date: str, end_date: str) -> int:
        """Calculate number of days in trip"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            return (end - start).days + 1  # Include last day
        except Exception as e:
            self.logger.error(f"Failed to calculate days: {e}")
            return 1
    
    def _extract_cuisine_preference(self, interests: List[str]) -> Optional[str]:
        """Extract cuisine preference from interests"""
        cuisine_keywords = {
            "food": None,
            "cuisine": None,
            "culinary": None,
            "dining": None,
            "italian": "italian",
            "french": "french",
            "japanese": "japanese",
            "chinese": "chinese",
            "indian": "indian",
            "thai": "thai",
            "mexican": "mexican"
        }
        
        for interest in interests:
            interest_lower = interest.lower()
            for keyword, cuisine in cuisine_keywords.items():
                if keyword in interest_lower:
                    return cuisine
        
        return None
    
    def _check_dietary_restrictions(
        self, 
        restaurant_data: Dict, 
        restrictions: List[str]
    ) -> bool:
        """
        Check if restaurant accommodates dietary restrictions
        
        For now, simple keyword check. In production, would need better logic.
        """
        if not restrictions:
            return True
        
        # Simple heuristic: skip restaurants with conflicting keywords
        restaurant_text = f"{restaurant_data.get('name', '')} {restaurant_data.get('description', '')} {restaurant_data.get('cuisine', '')}".lower()
        
        conflicts = {
            "vegetarian": ["steakhouse", "bbq", "meat"],
            "vegan": ["steakhouse", "bbq", "meat", "dairy", "cheese"],
            "halal": ["pork", "alcohol", "wine bar"],
            "kosher": ["pork", "shellfish"]
        }
        
        for restriction in restrictions:
            restriction_lower = restriction.lower()
            if restriction_lower in conflicts:
                for conflict_word in conflicts[restriction_lower]:
                    if conflict_word in restaurant_text:
                        return False
        
        return True
    
    def _diversify_restaurants(self, restaurants: List[Restaurant]) -> List[Restaurant]:
        """
        Diversify restaurant selection by cuisine and price range
        
        Returns:
            Diversified list (max 6 restaurants)
        """
        if len(restaurants) <= 6:
            return restaurants
        
        # Group by cuisine
        cuisine_groups = {}
        for rest in restaurants:
            cuisine = rest.cuisine
            if cuisine not in cuisine_groups:
                cuisine_groups[cuisine] = []
            cuisine_groups[cuisine].append(rest)
        
        # Pick top restaurant from each cuisine
        diverse_list = []
        for cuisine, group in cuisine_groups.items():
            # Sort by rating
            group_sorted = sorted(group, key=lambda x: x.rating, reverse=True)
            diverse_list.append(group_sorted[0])
            
            if len(diverse_list) >= 6:
                break
        
        # Fill remaining slots with highest-rated
        if len(diverse_list) < 6:
            remaining = [r for r in restaurants if r not in diverse_list]
            remaining_sorted = sorted(remaining, key=lambda x: x.rating, reverse=True)
            diverse_list.extend(remaining_sorted[:6 - len(diverse_list)])
        
        return diverse_list[:6]
    
    def _estimate_daily_food_cost(
        self, 
        restaurants: List[Restaurant],
        travelers: int
    ) -> float:
        """
        Estimate daily food cost per person
        
        Assumes 3 meals per day
        """
        if not restaurants:
            return 0.0
        
        # Calculate average cost per meal
        total_cost = sum(r.estimated_cost_per_person for r in restaurants)
        avg_cost_per_meal = total_cost / len(restaurants) if restaurants else 0
        
        # 3 meals per day per person
        daily_cost_per_person = avg_cost_per_meal * 3
        
        return daily_cost_per_person
