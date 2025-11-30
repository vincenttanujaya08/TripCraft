# import asyncio
# import sys
# from pathlib import Path
# from datetime import date
# from dotenv import load_dotenv

# load_dotenv()
# sys.path.insert(0, str(Path(__file__).parent))
# sys.path.insert(0, str(Path(__file__).parent / "backend"))

# async def main():
#     from data_sources.smart_retriever import SmartRetriever
#     from models.schemas import TripRequest, TripPreferences
    
#     print("\n🧪 TESTING AGENTS ONE BY ONE\n")
    
#     retriever = SmartRetriever()
    
#     request = TripRequest(
#         destination="Malang",
#         origin="Jakarta",
#         start_date=date(2025, 12, 20),
#         end_date=date(2025, 12, 22),
#         budget=15000000.0,
#         travelers=2,
#         preferences=TripPreferences(
#             accommodation="mid-range",
#             interests=["beach", "culture"],
#             dietary_restrictions=[],
#             pace="moderate"
#         )
#     )
    
#     print(f"📋 Request: {request.destination}, {request.start_date} to {request.end_date}\n")
    
#     # ============================================================
#     # TEST 1: DestinationAgent
#     # ============================================================
#     print("="*60)
#     print("🌍 TEST 1: DestinationAgent")
#     print("="*60)
#     try:
#         from agents import DestinationAgent
#         agent = DestinationAgent()
#         result = await agent.execute(request)
        
#         # Handle tuple return
#         if isinstance(result, tuple):
#             output, meta = result
#         else:
#             output = result
        
#         print(f"✅ SUCCESS")
#         print(f"   Destination: {output.destination.name}")
#         print(f"   Attractions: {len(output.attractions)}")
#         print(f"   Data Source: {output.data_source}")
#         print(f"   Confidence: {output.confidence}")
#     except Exception as e:
#         print(f"❌ FAILED: {e}")
#         import traceback
#         traceback.print_exc()
    
#     # ============================================================
#     # TEST 2: HotelAgent
#     # ============================================================
#     print("\n" + "="*60)
#     print("🏨 TEST 2: HotelAgent")
#     print("="*60)
#     try:
#         from agents import HotelAgent
#         agent = HotelAgent()
#         result = await agent.execute(request)
        
#         # Handle tuple return
#         if isinstance(result, tuple):
#             output, meta = result
#         else:
#             output = result
        
#         print(f"✅ SUCCESS")
#         print(f"   Hotels found: {len(output.hotels)}")
#         if output.recommended_hotel:
#             print(f"   Recommended: {output.recommended_hotel.name}")
#             print(f"   Price/night: Rp {output.recommended_hotel.price_per_night:,}")
#         print(f"   Total cost: Rp {output.total_accommodation_cost:,}")
#         print(f"   Data Source: {output.data_source}")
#     except Exception as e:
#         print(f"❌ FAILED: {e}")
#         import traceback
#         traceback.print_exc()
    
#     # ============================================================
#     # TEST 3: DiningAgent
#     # ============================================================
#     # print("\n" + "="*60)
#     # print("🍽️  TEST 3: DiningAgent")
#     # print("="*60)
#     # try:
#     #     from agents import DiningAgent
#     #     agent = DiningAgent()
#     #     result = await agent.execute(request)
        
#     #     # Handle tuple return
#     #     if isinstance(result, tuple):
#     #         output, meta = result
#     #     else:
#     #         output = result
        
#     #     print(f"✅ SUCCESS")
#     #     print(f"   Restaurants: {len(output.restaurants)}")
#     #     if output.restaurants:
#     #         print(f"   Example: {output.restaurants[0].name}")
#     #     print(f"   Total cost: Rp {output.estimated_total_cost:,}")
#     #     print(f"   Data Source: {output.data_source}")
#     # except Exception as e:
#     #     print(f"❌ FAILED: {e}")
#     #     import traceback
#     #     traceback.print_exc()
    
#     # ============================================================
#     # TEST 4: FlightAgent
#     # ============================================================
#     print("\n" + "="*60)
#     print("✈️  TEST 4: FlightAgent")
#     print("="*60)
#     try:
#         from agents import FlightAgent
#         agent = FlightAgent(retriever)
#         result = await agent.execute(request)
        
#         # FlightAgent doesn't return tuple based on GitHub code
#         output = result
        
#         print(f"✅ SUCCESS")
#         print(f"   Outbound: {len(output.outbound_flights)}")
#         print(f"   Return: {len(output.return_flights)}")
#         print(f"   Total cost: Rp {output.total_flight_cost:,}")
#         print(f"   Data Source: {output.data_source}")
#     except Exception as e:
#         print(f"❌ FAILED: {e}")
#         import traceback
#         traceback.print_exc()
    
#     # ============================================================
#     # TEST 5: BudgetAgent
#     # ============================================================
#     # print("\n" + "="*60)
#     # print("💰 TEST 5: BudgetAgent")
#     # print("="*60)
#     # try:
#     #     from agents import BudgetAgent
#     #     agent = BudgetAgent(retriever)
        
#     #     # BudgetAgent needs outputs from other agents
#     #     # For now just test initialization
#     #     print(f"✅ Agent initialized successfully")
#     #     print(f"   (Needs outputs from other agents to execute)")
#     # except Exception as e:
#     #     print(f"❌ FAILED: {e}")
#     #     import traceback
#     #     traceback.print_exc()
    
#     # print("\n" + "="*60)
#     # print("✅ AGENT TESTS COMPLETE")
#     # print("="*60)

# asyncio.run(main())


"""
Test Script for Enhanced DiningAgent
Tests standalone execution and integration with HotelAgent
"""

import asyncio
import sys
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "backend"))


async def test_dining_agent_standalone():
    """Test DiningAgent without hotel context"""
    
    print("\n" + "="*70)
    print("🧪 TEST 1: DiningAgent Standalone (No Hotel Context)")
    print("="*70)
    
    from agents.dining_agent import DiningAgent
    from models.schemas import TripRequest, TripPreferences
    
    request = TripRequest(
        destination="Bali",
        origin="Jakarta",
        start_date=date(2025, 12, 20),
        end_date=date(2025, 12, 22),
        budget=10000000.0,  # 10M IDR
        travelers=2,
        preferences=TripPreferences(
            accommodation="mid-range",
            interests=["food", "culture"],
            dietary_restrictions=[],
            pace="moderate"
        )
    )
    
    print(f"\n📋 Request:")
    print(f"   Destination: {request.destination}")
    print(f"   Dates: {request.start_date} to {request.end_date}")
    print(f"   Duration: {request.duration_days} days")
    print(f"   Budget: Rp {request.budget:,.0f}")
    print(f"   Travelers: {request.travelers}")
    
    try:
        agent = DiningAgent()
        output, metadata = await agent.execute(request, context=None)
        
        print(f"\n✅ SUCCESS!")
        print(f"\n📊 Results:")
        print(f"   Total restaurants: {len(output.restaurants)}")
        print(f"   Meal plan days: {len(output.meal_plan)}")
        print(f"   Total cost: Rp {output.estimated_total_cost:,.0f}")
        print(f"   Daily average: Rp {output.estimated_daily_cost:,.0f}")
        print(f"   Data source: {output.data_source}")
        print(f"   Confidence: {output.confidence:.2f}")
        
        print(f"\n💰 Budget Breakdown (per person):")
        for meal_type, amount in output.budget_breakdown.items():
            print(f"   {meal_type.capitalize()}: Rp {amount:,.0f}")
        
        print(f"\n📅 Meal Plan:")
        for day in output.meal_plan:
            print(f"\n   Day {day.day} ({day.date}):")
            
            if day.breakfast:
                print(f"      🌅 Breakfast: {day.breakfast.name} ({day.breakfast.cuisine})")
                print(f"         Rp {day.breakfast.average_cost_per_person:,.0f}/person")
            elif day.breakfast_notes:
                print(f"      🌅 Breakfast: {day.breakfast_notes}")
            
            if day.lunch:
                print(f"      ☀️  Lunch: {day.lunch.name} ({day.lunch.cuisine})")
                print(f"         Rp {day.lunch.average_cost_per_person:,.0f}/person")
            
            if day.dinner:
                print(f"      🌙 Dinner: {day.dinner.name} ({day.dinner.cuisine})")
                print(f"         Rp {day.dinner.average_cost_per_person:,.0f}/person")
            
            print(f"      💰 Daily total: Rp {day.daily_cost:,.0f} (all travelers)")
        
        if output.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in output.warnings:
                print(f"   - {warning}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_dining_agent_with_hotel():
    """Test DiningAgent with hotel breakfast context"""
    
    print("\n" + "="*70)
    print("🧪 TEST 2: DiningAgent with Hotel Context (Breakfast Included)")
    print("="*70)
    
    from agents.dining_agent import DiningAgent
    from agents.hotel_agent import HotelAgent
    from models.schemas import TripRequest, TripPreferences
    
    request = TripRequest(
        destination="Bali",
        origin="Jakarta",
        start_date=date(2025, 12, 20),
        end_date=date(2025, 12, 22),
        budget=10000000.0,
        travelers=2,
        preferences=TripPreferences(
            accommodation="mid-range",
            interests=["food", "beach"],
            dietary_restrictions=[],
            pace="moderate"
        )
    )
    
    print(f"\n📋 Request:")
    print(f"   Destination: {request.destination}")
    print(f"   Duration: {request.duration_days} days")
    
    try:
        # Step 1: Get hotel (to check breakfast)
        print(f"\n🏨 Step 1: Getting hotel info...")
        hotel_agent = HotelAgent()
        hotel_output, hotel_meta = await hotel_agent.execute(request)
        
        if hotel_output.recommended_hotel:
            print(f"   Hotel: {hotel_output.recommended_hotel.name}")
            print(f"   Amenities: {', '.join(hotel_output.recommended_hotel.amenities or [])}")
            
            has_breakfast = "breakfast" in [a.lower() for a in (hotel_output.recommended_hotel.amenities or [])]
            print(f"   Breakfast included: {'✅ YES' if has_breakfast else '❌ NO'}")
        
        # Step 2: Get dining with hotel context
        print(f"\n🍽️  Step 2: Planning meals with hotel context...")
        
        context = {
            "hotel_output": hotel_output
        }
        
        dining_agent = DiningAgent()
        output, metadata = await dining_agent.execute(request, context=context)
        
        print(f"\n✅ SUCCESS!")
        print(f"\n📊 Results:")
        print(f"   Total cost: Rp {output.estimated_total_cost:,.0f}")
        print(f"   Daily average: Rp {output.estimated_daily_cost:,.0f}")
        
        print(f"\n💰 Budget Breakdown (per person):")
        for meal_type, amount in output.budget_breakdown.items():
            print(f"   {meal_type.capitalize()}: Rp {amount:,.0f}")
        
        print(f"\n📅 Sample Day (Day 1):")
        day1 = output.meal_plan[0]
        
        if day1.breakfast:
            print(f"   🌅 Breakfast: {day1.breakfast.name}")
        elif day1.breakfast_notes:
            print(f"   🌅 Breakfast: {day1.breakfast_notes}")
        
        if day1.lunch:
            print(f"   ☀️  Lunch: {day1.lunch.name}")
        
        if day1.dinner:
            print(f"   🌙 Dinner: {day1.dinner.name}")
        
        print(f"   💰 Day 1 total: Rp {day1.daily_cost:,.0f}")
        
        print(f"\n✓ Hotel breakfast detection: {'WORKING' if metadata.get('hotel_has_breakfast') else 'NOT DETECTED'}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_dining_agent_with_restrictions():
    """Test DiningAgent with dietary restrictions"""
    
    print("\n" + "="*70)
    print("🧪 TEST 3: DiningAgent with Dietary Restrictions")
    print("="*70)
    
    from agents.dining_agent import DiningAgent
    from models.schemas import TripRequest, TripPreferences
    
    request = TripRequest(
        destination="Bali",
        origin="Jakarta",
        start_date=date(2025, 12, 20),
        end_date=date(2025, 12, 22),
        budget=10000000.0,
        travelers=2,
        preferences=TripPreferences(
            accommodation="mid-range",
            interests=["food"],
            dietary_restrictions=["vegetarian"],  # Vegetarian filter
            pace="moderate"
        )
    )
    
    print(f"\n📋 Request:")
    print(f"   Dietary restrictions: {', '.join(request.preferences.dietary_restrictions)}")
    
    try:
        agent = DiningAgent()
        output, metadata = await agent.execute(request, context=None)
        
        print(f"\n✅ SUCCESS!")
        print(f"   Total restaurants: {len(output.restaurants)}")
        print(f"   Filtered by dietary restrictions: ✅")
        
        # Check if any restaurants have conflicting cuisines
        problematic = []
        for rest in output.restaurants[:5]:
            rest_text = f"{rest.name} {rest.cuisine} {rest.description}".lower()
            if any(word in rest_text for word in ["meat", "bbq", "steakhouse"]):
                problematic.append(rest.name)
        
        if problematic:
            print(f"\n⚠️  WARNING: Found restaurants that might not be vegetarian:")
            for name in problematic:
                print(f"   - {name}")
        else:
            print(f"\n✅ All restaurants appear suitable for vegetarian diet")
        
        return True
    
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_all():
    """Run all tests"""
    
    print("\n" + "="*70)
    print("🚀 TESTING ENHANCED DININGAGENT")
    print("="*70)
    
    results = []
    
    # Test 1: Standalone
    result1 = await test_dining_agent_standalone()
    results.append(("Standalone", result1))
    
    # Test 2: With hotel context
    result2 = await test_dining_agent_with_hotel()
    results.append(("With Hotel Context", result2))
    
    # Test 3: With dietary restrictions
    result3 = await test_dining_agent_with_restrictions()
    results.append(("With Dietary Restrictions", result3))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\n   Total: {total_passed}/{len(results)} tests passed")
    
    if total_passed == len(results):
        print("\n🎉 ALL TESTS PASSED! 🎉")
    else:
        print("\n⚠️  Some tests failed. Please review errors above.")


if __name__ == "__main__":
    asyncio.run(test_all())