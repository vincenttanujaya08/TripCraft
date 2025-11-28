import asyncio
import sys
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "backend"))

async def main():
    from data_sources.smart_retriever import SmartRetriever
    from models.schemas import TripRequest, TripPreferences
    
    print("\n🧪 TESTING AGENTS ONE BY ONE\n")
    
    retriever = SmartRetriever()
    
    request = TripRequest(
        destination="Malang",
        origin="Jakarta",
        start_date=date(2025, 12, 20),
        end_date=date(2025, 12, 22),
        budget=15000000.0,
        travelers=2,
        preferences=TripPreferences(
            accommodation="mid-range",
            interests=["beach", "culture"],
            dietary_restrictions=[],
            pace="moderate"
        )
    )
    
    print(f"📋 Request: {request.destination}, {request.start_date} to {request.end_date}\n")
    
    # ============================================================
    # TEST 1: DestinationAgent
    # ============================================================
    print("="*60)
    print("🌍 TEST 1: DestinationAgent")
    print("="*60)
    try:
        from agents import DestinationAgent
        agent = DestinationAgent()
        result = await agent.execute(request)
        
        # Handle tuple return
        if isinstance(result, tuple):
            output, meta = result
        else:
            output = result
        
        print(f"✅ SUCCESS")
        print(f"   Destination: {output.destination.name}")
        print(f"   Attractions: {len(output.attractions)}")
        print(f"   Data Source: {output.data_source}")
        print(f"   Confidence: {output.confidence}")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # ============================================================
    # TEST 2: HotelAgent
    # ============================================================
    print("\n" + "="*60)
    print("🏨 TEST 2: HotelAgent")
    print("="*60)
    try:
        from agents import HotelAgent
        agent = HotelAgent()
        result = await agent.execute(request)
        
        # Handle tuple return
        if isinstance(result, tuple):
            output, meta = result
        else:
            output = result
        
        print(f"✅ SUCCESS")
        print(f"   Hotels found: {len(output.hotels)}")
        if output.recommended_hotel:
            print(f"   Recommended: {output.recommended_hotel.name}")
            print(f"   Price/night: Rp {output.recommended_hotel.price_per_night:,}")
        print(f"   Total cost: Rp {output.total_accommodation_cost:,}")
        print(f"   Data Source: {output.data_source}")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # ============================================================
    # TEST 3: DiningAgent
    # ============================================================
    # print("\n" + "="*60)
    # print("🍽️  TEST 3: DiningAgent")
    # print("="*60)
    # try:
    #     from agents import DiningAgent
    #     agent = DiningAgent()
    #     result = await agent.execute(request)
        
    #     # Handle tuple return
    #     if isinstance(result, tuple):
    #         output, meta = result
    #     else:
    #         output = result
        
    #     print(f"✅ SUCCESS")
    #     print(f"   Restaurants: {len(output.restaurants)}")
    #     if output.restaurants:
    #         print(f"   Example: {output.restaurants[0].name}")
    #     print(f"   Total cost: Rp {output.estimated_total_cost:,}")
    #     print(f"   Data Source: {output.data_source}")
    # except Exception as e:
    #     print(f"❌ FAILED: {e}")
    #     import traceback
    #     traceback.print_exc()
    
    # ============================================================
    # TEST 4: FlightAgent
    # ============================================================
    print("\n" + "="*60)
    print("✈️  TEST 4: FlightAgent")
    print("="*60)
    try:
        from agents import FlightAgent
        agent = FlightAgent(retriever)
        result = await agent.execute(request)
        
        # FlightAgent doesn't return tuple based on GitHub code
        output = result
        
        print(f"✅ SUCCESS")
        print(f"   Outbound: {len(output.outbound_flights)}")
        print(f"   Return: {len(output.return_flights)}")
        print(f"   Total cost: Rp {output.total_flight_cost:,}")
        print(f"   Data Source: {output.data_source}")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # ============================================================
    # TEST 5: BudgetAgent
    # ============================================================
    # print("\n" + "="*60)
    # print("💰 TEST 5: BudgetAgent")
    # print("="*60)
    # try:
    #     from agents import BudgetAgent
    #     agent = BudgetAgent(retriever)
        
    #     # BudgetAgent needs outputs from other agents
    #     # For now just test initialization
    #     print(f"✅ Agent initialized successfully")
    #     print(f"   (Needs outputs from other agents to execute)")
    # except Exception as e:
    #     print(f"❌ FAILED: {e}")
    #     import traceback
    #     traceback.print_exc()
    
    # print("\n" + "="*60)
    # print("✅ AGENT TESTS COMPLETE")
    # print("="*60)

asyncio.run(main())
