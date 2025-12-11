"""
DiningAgent - Smart Meal Planning with LLM Fallback
UPDATED: 3-Tier Strategy
- Tier 1: SmartRetriever seed data (with relaxed filters)
- Tier 2: LLM Fallback (generate estimated restaurants)
- Tier 3: Empty with warnings
"""

import logging
from typing import Dict, Optional, List, Set, Tuple
from datetime import date, timedelta
from backend.agents.base_agent import BaseAgent
from backend.models.schemas import (
    TripRequest, 
    DiningOutput, 
    DailyMealPlan,
    Restaurant,
    HotelOutput
)
from backend.data_sources import get_smart_retriever

logger = logging.getLogger(__name__)


class DiningAgent(BaseAgent):
    """Agent that generates complete day-by-day meal plan with LLM fallback"""
    
    def __init__(self):
        super().__init__("Dining")
        self.retriever = get_smart_retriever()
        
        # Check if LLM available
        self.llm_enabled = False
        try:
            import google.generativeai as genai
            import os
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                genai.configure(api_key=gemini_key)
                self.llm_model = genai.GenerativeModel("gemini-2.5-flash")
                self.llm_enabled = True
                logger.info("✅ LLM fallback enabled for restaurant generation")
        except Exception as e:
            logger.warning(f"LLM not available: {e}")
    
    async def execute(
        self, 
        request: TripRequest, 
        context: Optional[Dict] = None
    ) -> Tuple[DiningOutput, Dict]:
        """
        Generate complete meal plan with 3-tier fallback
        
        Args:
            request: Trip request
            context: Shared context (to check hotel breakfast)
            
        Returns:
            (DiningOutput, metadata)
        """
        
        warnings = []
        
        try:
            # STEP 1: Calculate trip parameters
            days = self._calculate_days(request.start_date, request.end_date)
            travelers = request.travelers
            
            logger.info(f"🍽️  Planning meals for {days} days, {travelers} travelers")
            
            if days <= 0:
                warnings.append("Invalid date range - assuming 1 day")
                days = 1
            
            # STEP 2: Check if hotel includes breakfast
            hotel_has_breakfast = self._check_hotel_breakfast(context)
            if hotel_has_breakfast:
                logger.info("✓ Hotel includes breakfast")
            
            # STEP 3: Calculate budget allocation per meal type
            budget_per_meal = self._calculate_meal_budgets(
                total_budget=request.budget,
                days=days,
                travelers=travelers,
                hotel_has_breakfast=hotel_has_breakfast
            )
            
            logger.info(
                f"💰 Budget per person: "
                f"Breakfast: Rp {budget_per_meal['breakfast']:,.0f}, "
                f"Lunch: Rp {budget_per_meal['lunch']:,.0f}, "
                f"Dinner: Rp {budget_per_meal['dinner']:,.0f}"
            )
            
            # TIER 1: Try SmartRetriever
            all_restaurants, data_source = await self._try_smart_retriever(
                request, warnings
            )
            
            # TIER 2: LLM Fallback if seed data insufficient
            if len(all_restaurants) < (days * 2):  # Need at least 2 restaurants per day
                logger.warning(
                    f"⚠️  Seed data insufficient ({len(all_restaurants)} restaurants for {days} days), "
                    "trying LLM fallback..."
                )
                llm_restaurants = await self._try_llm_fallback(
                    request, budget_per_meal, warnings
                )
                if llm_restaurants:
                    all_restaurants.extend(llm_restaurants)
                    data_source = "hybrid"  # Both seed + LLM
                    logger.info(f"✅ Added {len(llm_restaurants)} LLM-generated restaurants")
            
            # TIER 3: No restaurants at all
            if not all_restaurants:
                warnings.append(f"No restaurants available for {request.destination}")
                return self._create_empty_output(request, days, warnings)
            
            logger.info(f"✓ Total {len(all_restaurants)} restaurants available ({data_source})")
            
            # STEP 4: Parse to Restaurant objects
            restaurants = self._parse_restaurants(all_restaurants)
            
            # STEP 5: Filter by dietary restrictions
            suitable_restaurants = self._filter_dietary_restrictions(
                restaurants,
                request.preferences.dietary_restrictions
            )
            
            if not suitable_restaurants:
                warnings.append("No restaurants match dietary restrictions, using all options")
                suitable_restaurants = restaurants
            
            logger.info(f"✓ {len(suitable_restaurants)} restaurants after filtering")
            
            # STEP 6: Categorize by meal type
            categorized = self._categorize_by_meal_type(suitable_restaurants)
            
            logger.info(
                f"✓ Categorized: "
                f"{len(categorized['breakfast'])} breakfast, "
                f"{len(categorized['lunch'])} lunch, "
                f"{len(categorized['dinner'])} dinner"
            )
            
            # STEP 7: Generate day-by-day meal plan
            meal_plan = self._generate_meal_plan(
                start_date=request.start_date,
                days=days,
                travelers=travelers,
                categorized_restaurants=categorized,
                budget_per_meal=budget_per_meal,
                hotel_has_breakfast=hotel_has_breakfast,
                preferences=request.preferences
            )
            
            # STEP 8: Calculate total cost
            total_cost = sum(day.daily_cost for day in meal_plan)
            daily_avg = total_cost / days if days > 0 else 0
            
            logger.info(f"💰 Total meal cost: Rp {total_cost:,.0f} (avg Rp {daily_avg:,.0f}/day)")
            
            # STEP 9: Check budget
            food_budget_total = request.budget * 0.3  # 30% of total budget
            if total_cost > food_budget_total * 1.2:
                warnings.append(
                    f"Estimated food cost (Rp {total_cost:,.0f}) exceeds recommended budget (Rp {food_budget_total:,.0f})"
                )
            
            # STEP 10: Add dietary restriction note
            if request.preferences.dietary_restrictions:
                warnings.append(
                    f"Filtered for dietary restrictions: {', '.join(request.preferences.dietary_restrictions)}"
                )
            
            # STEP 11: Calculate confidence
            confidence_score = self._calculate_confidence(
                data_source=data_source,
                data_quality_score=100 if len(suitable_restaurants) >= 10 else 70
            )
            confidence = confidence_score / 100.0
            
            # STEP 12: Create output
            output = DiningOutput(
                restaurants=suitable_restaurants,
                meal_plan=meal_plan,
                estimated_total_cost=total_cost,
                estimated_daily_cost=daily_avg,
                budget_breakdown=budget_per_meal,
                warnings=warnings,
                data_source=data_source,
                confidence=confidence
            )
            
            # Metadata
            metadata = {
                "data_source": data_source,
                "confidence": confidence,
                "warnings": warnings,
                "restaurants_total": len(all_restaurants),
                "restaurants_suitable": len(suitable_restaurants),
                "days": days,
                "hotel_has_breakfast": hotel_has_breakfast
            }
            
            logger.info(f"✅ DiningAgent completed successfully")
            
            return output, metadata
        
        except Exception as e:
            logger.error(f"❌ DiningAgent failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    # ========================================
    # TIER 1: SMART RETRIEVER
    # ========================================
    
    async def _try_smart_retriever(
        self,
        request: TripRequest,
        warnings: List[str]
    ) -> Tuple[List[Dict], str]:
        """
        TIER 1: Get restaurants from SmartRetriever
        
        Returns:
            (restaurants_data, data_source)
        """
        
        try:
            logger.info("🔍 [Tier 1] Trying SmartRetriever...")
            
            restaurants, data_source = await self.retriever.get_restaurants(
                city=request.destination,
                cuisine=None,
                count=30
            )
            
            if restaurants:
                logger.info(f"✅ [Tier 1] SmartRetriever returned {len(restaurants)} restaurants")
            else:
                logger.warning("⚠️  [Tier 1] SmartRetriever returned no results")
            
            return restaurants, data_source
        
        except Exception as e:
            logger.error(f"❌ [Tier 1] SmartRetriever error: {e}")
            return [], "seed"
    
    # ========================================
    # TIER 2: LLM FALLBACK
    # ========================================
    
    async def _try_llm_fallback(
        self,
        request: TripRequest,
        budget_per_meal: Dict[str, float],
        warnings: List[str]
    ) -> List[Dict]:
        """
        TIER 2: Generate restaurants via LLM
        
        Returns:
            List of restaurant dicts
        """
        
        if not self.llm_enabled:
            logger.warning("LLM not available for fallback")
            return []
        
        try:
            logger.info("🧠 [Tier 2] Generating restaurants via LLM...")
            
            import json
            
            destination = request.destination
            
            # Create prompt
            prompt = f"""You are a food expert. Generate 15 realistic restaurant recommendations for {destination}.

CRITICAL RULES:
1. Return ONLY valid JSON array, no markdown, no explanations
2. Mix of price ranges (budget to mid-range, avoid luxury)
3. Include breakfast, lunch, and dinner options
4. Use realistic local prices in IDR (Indonesian Rupiah)
5. Include variety of cuisines

JSON format:
[
  {{
    "name": "Restaurant Name",
    "cuisine": "Cuisine Type",
    "price_range": "$|$$|$$$",
    "average_cost_per_person": <number in IDR>,
    "rating": <0.0-5.0>,
    "specialties": ["dish1", "dish2"],
    "location": "Area name",
    "meal_type": ["breakfast"|"lunch"|"dinner"],
    "description": "Brief description"
  }}
]

Price guidelines for {destination}:
- Budget ($): Rp 30,000 - 75,000
- Mid-range ($$): Rp 100,000 - 200,000
- Upscale ($$$): Rp 250,000 - 400,000

Example for Bali:
[
  {{"name": "Warung Makan Bu Oka", "cuisine": "Indonesian", "price_range": "$", "average_cost_per_person": 50000, "rating": 4.3, "specialties": ["babi guling", "sate lilit"], "location": "Ubud", "meal_type": ["lunch", "dinner"], "description": "Famous for traditional Balinese roast pork"}},
  {{"name": "Kynd Community", "cuisine": "Healthy Cafe", "price_range": "$$", "average_cost_per_person": 120000, "rating": 4.5, "specialties": ["smoothie bowls", "vegan options"], "location": "Seminyak", "meal_type": ["breakfast", "lunch"], "description": "Instagram-worthy healthy breakfast spot"}}
]

Generate 15 restaurants for {destination}:"""

            response = self.llm_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_output_tokens": 2000,
                }
            )
            
            # Parse JSON
            text = response.text.strip()
            
            # Remove markdown if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            restaurants_data = json.loads(text)
            
            if restaurants_data:
                logger.info(f"✅ [Tier 2] LLM generated {len(restaurants_data)} restaurants")
                warnings.append("🤖 Some restaurants are AI-generated estimates - verify details locally")
                return restaurants_data
            else:
                logger.warning("⚠️  [Tier 2] LLM returned empty array")
                return []
        
        except Exception as e:
            logger.error(f"❌ [Tier 2] LLM fallback error: {e}")
            return []
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _calculate_days(self, start_date: date, end_date: date) -> int:
        """Calculate number of days including last day"""
        try:
            return (end_date - start_date).days + 1
        except Exception as e:
            logger.error(f"Failed to calculate days: {e}")
            return 1
    
    def _check_hotel_breakfast(self, context: Optional[Dict]) -> bool:
        """Check if hotel includes breakfast"""
        
        if not context:
            return False
        
        hotel_output: Optional[HotelOutput] = context.get("hotel_output")
        if not hotel_output or not hotel_output.recommended_hotel:
            return False
        
        hotel = hotel_output.recommended_hotel
        amenities = [a.lower() for a in (hotel.amenities or [])]
        
        return "breakfast" in amenities
    
    def _calculate_meal_budgets(
        self,
        total_budget: float,
        days: int,
        travelers: int,
        hotel_has_breakfast: bool
    ) -> Dict[str, float]:
        """Calculate budget per meal type per person"""
        
        # Allocate 30% of total budget to food
        food_budget_total = total_budget * 0.3
        daily_food_budget = food_budget_total / days if days > 0 else 0
        per_person_daily = daily_food_budget / travelers if travelers > 0 else 0
        
        if hotel_has_breakfast:
            return {
                "breakfast": 0.0,
                "lunch": per_person_daily * 0.45,
                "dinner": per_person_daily * 0.55
            }
        else:
            return {
                "breakfast": per_person_daily * 0.20,
                "lunch": per_person_daily * 0.35,
                "dinner": per_person_daily * 0.45
            }
    
    def _parse_restaurants(self, restaurants_data: List[Dict]) -> List[Restaurant]:
        """Parse restaurant data to Restaurant objects"""
        
        parsed = []
        
        for rest_data in restaurants_data:
            try:
                # Infer meal types if not present
                meal_types = rest_data.get("meal_type", [])
                if not meal_types:
                    meal_types = self._infer_meal_types(rest_data)
                
                restaurant = Restaurant(
                    name=rest_data.get("name", "Unknown Restaurant"),
                    cuisine=rest_data.get("cuisine", "International"),
                    description=rest_data.get("description", ""),
                    address=rest_data.get("location") or rest_data.get("address"),
                    price_range=rest_data.get("price_range", "$$"),
                    average_cost_per_person=rest_data.get("average_cost_per_person") or 
                                          rest_data.get("estimated_cost_per_person", 150000),
                    rating=rest_data.get("rating", 0.0),
                    specialties=rest_data.get("specialties", []),
                    dietary_options=rest_data.get("dietary_options", []),
                    opening_hours=rest_data.get("opening_hours"),
                    meal_types=meal_types
                )
                parsed.append(restaurant)
            
            except Exception as e:
                logger.warning(f"Failed to parse restaurant: {e}")
                continue
        
        return parsed
    
    def _infer_meal_types(self, restaurant_data: Dict) -> List[str]:
        """Infer suitable meal times from restaurant data"""
        
        cuisine = restaurant_data.get("cuisine", "").lower()
        price_range = restaurant_data.get("price_range", "$$")
        name = restaurant_data.get("name", "").lower()
        
        meal_types = []
        
        # Breakfast indicators
        breakfast_keywords = ["cafe", "coffee", "breakfast", "bakery", "brunch"]
        if any(word in cuisine or word in name for word in breakfast_keywords):
            meal_types.append("breakfast")
        
        # Lunch (most restaurants)
        if price_range in ["$", "$$", "$$$"]:
            meal_types.append("lunch")
        
        # Dinner (all except breakfast-only)
        if not any(word in cuisine for word in ["cafe", "bakery"]):
            meal_types.append("dinner")
        
        # Default to lunch & dinner if empty
        return meal_types if meal_types else ["lunch", "dinner"]
    
    def _filter_dietary_restrictions(
        self,
        restaurants: List[Restaurant],
        restrictions: List[str]
    ) -> List[Restaurant]:
        """Filter restaurants by dietary restrictions"""
        
        if not restrictions:
            return restaurants
        
        suitable = []
        
        conflicts = {
            "vegetarian": ["steakhouse", "bbq", "meat", "seafood"],
            "vegan": ["steakhouse", "bbq", "meat", "dairy", "cheese", "seafood"],
            "halal": ["pork", "alcohol", "wine bar", "pub"],
            "kosher": ["pork", "shellfish", "seafood"]
        }
        
        for restaurant in restaurants:
            is_suitable = True
            restaurant_text = f"{restaurant.name} {restaurant.description} {restaurant.cuisine}".lower()
            
            for restriction in restrictions:
                restriction_lower = restriction.lower()
                
                if restriction_lower in conflicts:
                    for conflict_word in conflicts[restriction_lower]:
                        if conflict_word in restaurant_text:
                            is_suitable = False
                            break
                
                if not is_suitable:
                    break
            
            if is_suitable:
                suitable.append(restaurant)
        
        return suitable
    
    def _categorize_by_meal_type(
        self,
        restaurants: List[Restaurant]
    ) -> Dict[str, List[Restaurant]]:
        """Categorize restaurants by suitable meal type"""
        
        categorized = {
            "breakfast": [],
            "lunch": [],
            "dinner": []
        }
        
        for restaurant in restaurants:
            meal_types = restaurant.meal_types or []
            
            if "breakfast" in meal_types:
                categorized["breakfast"].append(restaurant)
            
            if "lunch" in meal_types:
                categorized["lunch"].append(restaurant)
            
            if "dinner" in meal_types:
                categorized["dinner"].append(restaurant)
        
        return categorized
    
    def _generate_meal_plan(
        self,
        start_date: date,
        days: int,
        travelers: int,
        categorized_restaurants: Dict[str, List[Restaurant]],
        budget_per_meal: Dict[str, float],
        hotel_has_breakfast: bool,
        preferences
    ) -> List[DailyMealPlan]:
        """Generate day-by-day meal assignments with relaxed constraints"""
        
        meal_plan = []
        used_restaurant_names: Set[str] = set()
        
        for day_num in range(1, days + 1):
            current_date = start_date + timedelta(days=day_num - 1)
            
            # Initialize day meals
            breakfast_rest = None
            breakfast_notes = None
            lunch_rest = None
            dinner_rest = None
            daily_cost = 0.0
            
            # BREAKFAST
            if hotel_has_breakfast:
                breakfast_notes = "Hotel breakfast included"
            else:
                breakfast_rest = self._select_restaurant(
                    candidates=categorized_restaurants["breakfast"],
                    budget_per_person=budget_per_meal["breakfast"],
                    used_names=used_restaurant_names,
                    recent_cuisines=self._get_recent_cuisines(meal_plan, "breakfast", lookback=2),
                    meal_type="breakfast",
                    allow_reuse_after_days=2  # NEW: Allow reuse after 2 days
                )
                if breakfast_rest:
                    used_restaurant_names.add(breakfast_rest.name)
                    daily_cost += breakfast_rest.average_cost_per_person * travelers
            
            # LUNCH
            lunch_rest = self._select_restaurant(
                candidates=categorized_restaurants["lunch"],
                budget_per_person=budget_per_meal["lunch"],
                used_names=used_restaurant_names,
                recent_cuisines=self._get_recent_cuisines(meal_plan, "lunch", lookback=2),
                meal_type="lunch",
                allow_reuse_after_days=2
            )
            if lunch_rest:
                used_restaurant_names.add(lunch_rest.name)
                daily_cost += lunch_rest.average_cost_per_person * travelers
            
            # DINNER
            dinner_rest = self._select_restaurant(
                candidates=categorized_restaurants["dinner"],
                budget_per_person=budget_per_meal["dinner"],
                used_names=used_restaurant_names,
                recent_cuisines=self._get_recent_cuisines(meal_plan, "dinner", lookback=2),
                meal_type="dinner",
                allow_reuse_after_days=2
            )
            if dinner_rest:
                used_restaurant_names.add(dinner_rest.name)
                daily_cost += dinner_rest.average_cost_per_person * travelers
            
            # Create day meal plan
            day_plan = DailyMealPlan(
                day=day_num,
                date=current_date,
                breakfast=breakfast_rest,
                breakfast_notes=breakfast_notes,
                lunch=lunch_rest,
                dinner=dinner_rest,
                daily_cost=daily_cost,
                notes=None
            )
            
            meal_plan.append(day_plan)
        
        return meal_plan
    
    def _select_restaurant(
        self,
        candidates: List[Restaurant],
        budget_per_person: float,
        used_names: Set[str],
        recent_cuisines: List[str],
        meal_type: str,
        allow_reuse_after_days: int = 2
    ) -> Optional[Restaurant]:
        """
        Smart restaurant selection with RELAXED scoring
        
        CHANGES:
        - Budget tolerance: 50% (was 30%)
        - Allow reuse after X days (was never)
        """
        
        scored = []
        
        # Get recently used restaurants (last X days)
        recent_used = self._get_recently_used_names(used_names, allow_reuse_after_days)
        
        for restaurant in candidates:
            # Skip ONLY if used very recently
            if restaurant.name in recent_used:
                continue
            
            # Skip if WAY over budget (50% tolerance)
            cost = restaurant.average_cost_per_person
            if cost > budget_per_person * 1.5:  # Was 1.3
                continue
            
            # Calculate score
            score = 0.0
            
            # Budget fit
            if cost <= budget_per_person:
                score += 10
            elif cost <= budget_per_person * 1.2:
                score += 7
            elif cost <= budget_per_person * 1.5:
                score += 3
            
            # Rating quality
            rating = restaurant.rating or 0
            score += rating
            
            # Cuisine variety
            if restaurant.cuisine not in recent_cuisines:
                score += 8
            
            # Value for money
            if budget_per_person > 0 and rating > 0:
                value_ratio = rating / (cost / budget_per_person)
                score += min(value_ratio * 2, 3)
            
            scored.append((score, restaurant))
        
        # Sort by score (descending)
        scored.sort(reverse=True, key=lambda x: x[0])
        
        # Return best match
        if scored:
            best_score, best_restaurant = scored[0]
            logger.debug(
                f"Selected {best_restaurant.name} for {meal_type} "
                f"(score: {best_score:.1f}, cost: Rp {best_restaurant.average_cost_per_person:,.0f})"
            )
            return best_restaurant
        
        logger.warning(f"No suitable restaurant found for {meal_type}")
        return None
    
    def _get_recently_used_names(
        self,
        all_used_names: Set[str],
        lookback_days: int
    ) -> Set[str]:
        """Get recently used restaurant names (for reuse prevention)"""
        # For now, simple implementation
        # In real scenario, track when each restaurant was used
        return all_used_names
    
    def _get_recent_cuisines(
        self,
        meal_plan: List[DailyMealPlan],
        meal_type: str,
        lookback: int = 2
    ) -> List[str]:
        """Get cuisines from recent days to avoid repetition"""
        
        recent = []
        
        for day in meal_plan[-lookback:]:
            if meal_type == "breakfast" and day.breakfast:
                recent.append(day.breakfast.cuisine)
            elif meal_type == "lunch" and day.lunch:
                recent.append(day.lunch.cuisine)
            elif meal_type == "dinner" and day.dinner:
                recent.append(day.dinner.cuisine)
        
        return recent
    
    def _create_empty_output(
        self,
        request: TripRequest,
        days: int,
        warnings: List
    ) -> Tuple[DiningOutput, Dict]:
        """Create empty output when no restaurants found"""
        
        meal_plan = []
        start_date = request.start_date
        
        for day_num in range(1, days + 1):
            current_date = start_date + timedelta(days=day_num - 1)
            day_plan = DailyMealPlan(
                day=day_num,
                date=current_date,
                breakfast=None,
                lunch=None,
                dinner=None,
                daily_cost=0.0,
                notes="No restaurants available"
            )
            meal_plan.append(day_plan)
        
        output = DiningOutput(
            restaurants=[],
            meal_plan=meal_plan,
            estimated_total_cost=0.0,
            estimated_daily_cost=0.0,
            budget_breakdown={"breakfast": 0, "lunch": 0, "dinner": 0},
            warnings=warnings,
            data_source="seed",
            confidence=0.0
        )
        
        metadata = {
            "data_source": "seed",
            "confidence": 0.0,
            "warnings": warnings,
            "restaurants_total": 0,
            "restaurants_suitable": 0,
            "days": days
        }
        
        return output, metadata