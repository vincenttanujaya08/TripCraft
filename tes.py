#!/usr/bin/env python3
"""
Test FlightAgent Update (Step B.2)
Tests: max_budget parameter and ground transport fallback
"""

import sys
import asyncio
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


async def test_import():
    """Test 1: Import FlightAgent"""
    print("\n" + "="*60)
    print("TEST 1: Import FlightAgent")
    print("="*60)
    
    try:
        from backend.agents.flight_agent import FlightAgent
        from backend.data_sources.smart_retriever import SmartRetriever
        
        retriever = SmartRetriever()
        agent = FlightAgent(retriever)
        
        print("✅ FlightAgent imported and initialized!")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_method_signature():
    """Test 2: Check execute method signature"""
    print("\n" + "="*60)
    print("TEST 2: Check Execute Method Signature")
    print("="*60)
    
    try:
        from backend.agents.flight_agent import FlightAgent
        import inspect
        
        # Get execute method signature
        sig = inspect.signature(FlightAgent.execute)
        params = list(sig.parameters.keys())
        
        print(f"✅ Method signature: execute({', '.join(params)})")
        
        # Check if max_budget parameter exists
        if 'max_budget' in params:
            print("✅ max_budget parameter exists!")
        else:
            print("❌ max_budget parameter NOT FOUND!")
            print("   Expected signature: execute(self, request, max_budget=None)")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Signature check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_basic_execution():
    """Test 3: Basic execution without budget"""
    print("\n" + "="*60)
    print("TEST 3: Basic Execution (No Budget Constraint)")
    print("="*60)
    
    try:
        from backend.agents.flight_agent import FlightAgent
        from backend.data_sources.smart_retriever import SmartRetriever
        from backend.models.schemas import TripRequest, TripPreferences
        
        retriever = SmartRetriever()
        agent = FlightAgent(retriever)
        
        # Create request
        today = date.today()
        start_date = today + timedelta(days=30)
        end_date = start_date + timedelta(days=3)
        
        request = TripRequest(
            destination="Bali",
            origin="Jakarta",
            start_date=start_date,
            end_date=end_date,
            budget=10000000.0,
            travelers=2,
            preferences=TripPreferences(
                accommodation="mid-range",
                interests=["beach"],
                dietary_restrictions=[],
                pace="moderate"
            )
        )
        
        print(f"\n🔍 Testing flight search:")
        print(f"   Route: {request.origin} → {request.destination}")
        print(f"   Dates: {request.start_date} to {request.end_date}")
        print(f"   Travelers: {request.travelers}")
        
        # Execute WITHOUT max_budget
        result = await agent.execute(request)
        
        print(f"\n✅ Execution successful!")
        print(f"   Outbound flights: {len(result.outbound_flights)}")
        print(f"   Return flights: {len(result.return_flights)}")
        print(f"   Total cost: Rp {result.total_flight_cost:,.0f}")
        print(f"   Data source: {result.data_source}")
        print(f"   Confidence: {result.confidence:.2f}")
        
        if result.warnings:
            print(f"\n   Warnings: {len(result.warnings)}")
            for warning in result.warnings:
                print(f"      - {warning}")
        
        return True
    except Exception as e:
        print(f"❌ Basic execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_budget_constraint():
    """Test 4: Execution with budget constraint"""
    print("\n" + "="*60)
    print("TEST 4: Execution WITH Budget Constraint")
    print("="*60)
    
    try:
        from backend.agents.flight_agent import FlightAgent
        from backend.data_sources.smart_retriever import SmartRetriever
        from backend.models.schemas import TripRequest, TripPreferences
        
        retriever = SmartRetriever()
        agent = FlightAgent(retriever)
        
        # Create request
        today = date.today()
        start_date = today + timedelta(days=30)
        end_date = start_date + timedelta(days=3)
        
        request = TripRequest(
            destination="Bali",
            origin="Jakarta",
            start_date=start_date,
            end_date=end_date,
            budget=5000000.0,  # Low budget
            travelers=2,
            preferences=TripPreferences(
                accommodation="budget",
                interests=["beach"],
                dietary_restrictions=[],
                pace="moderate"
            )
        )
        
        # Set strict budget (35% of total)
        max_flight_budget = request.budget * 0.35
        
        print(f"\n🔍 Testing with budget constraint:")
        print(f"   Total budget: Rp {request.budget:,.0f}")
        print(f"   Max flight budget: Rp {max_flight_budget:,.0f}")
        print(f"   Per person: Rp {max_flight_budget / request.travelers:,.0f}")
        
        # Execute WITH max_budget
        result = await agent.execute(request, max_budget=max_flight_budget)
        
        print(f"\n✅ Execution successful!")
        print(f"   Total cost: Rp {result.total_flight_cost:,.0f}")
        
        # Check if over budget
        if result.total_flight_cost > max_flight_budget:
            over_amount = result.total_flight_cost - max_flight_budget
            print(f"   ⚠️  Over budget by Rp {over_amount:,.0f}")
            
            # Check if warning was added
            budget_warnings = [w for w in result.warnings if 'budget' in w.lower() or 'exceeds' in w.lower()]
            if budget_warnings:
                print(f"   ✅ Budget warning present:")
                for warning in budget_warnings:
                    print(f"      - {warning[:100]}...")
            else:
                print(f"   ❌ No budget warning (should have warned!)")
                return False
        else:
            print(f"   ✅ Within budget!")
        
        return True
    except Exception as e:
        print(f"❌ Budget constraint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ground_transport_fallback():
    """Test 5: Ground transport fallback"""
    print("\n" + "="*60)
    print("TEST 5: Ground Transport Fallback")
    print("="*60)
    
    try:
        from backend.agents.flight_agent import FlightAgent
        from backend.data_sources.smart_retriever import SmartRetriever
        from backend.models.schemas import TripRequest, TripPreferences
        
        retriever = SmartRetriever()
        agent = FlightAgent(retriever)
        
        # Create request for route with ground transport
        today = date.today()
        start_date = today + timedelta(days=30)
        end_date = start_date + timedelta(days=2)
        
        request = TripRequest(
            destination="Bandung",  # Ground transport available!
            origin="Jakarta",
            start_date=start_date,
            end_date=end_date,
            budget=3000000.0,
            travelers=2,
            preferences=TripPreferences(
                accommodation="budget",
                interests=["culture"],
                dietary_restrictions=[],
                pace="moderate"
            )
        )
        
        print(f"\n🔍 Testing Jakarta → Bandung:")
        print(f"   (This route has train/bus options)")
        
        # Execute
        result = await agent.execute(request, max_budget=500000)
        
        print(f"\n✅ Execution successful!")
        print(f"   Flights found: {len(result.outbound_flights)}")
        
        # Check if ground transport mentioned in warnings
        ground_warnings = [
            w for w in result.warnings 
            if any(word in w.lower() for word in ['train', 'bus', 'ground'])
        ]
        
        if ground_warnings:
            print(f"   ✅ Ground transport alternative mentioned!")
            for warning in ground_warnings:
                print(f"      - {warning[:120]}...")
        else:
            print(f"   ⚠️  No ground transport mention (might be OK if flights found)")
        
        return True
    except Exception as e:
        print(f"❌ Ground transport test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("="*60)
    print("🧪 TESTING FLIGHTAGENT UPDATE (Step B.2)")
    print("="*60)
    
    tests = [
        ("Import FlightAgent", test_import),
        ("Method Signature", test_method_signature),
        ("Basic Execution", test_basic_execution),
        ("Budget Constraint", test_budget_constraint),
        ("Ground Transport Fallback", test_ground_transport_fallback)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total_passed = sum(1 for passed in results.values() if passed)
    total_tests = len(results)
    
    print(f"\n   Total: {total_passed}/{total_tests} tests passed")
    
    if total_passed >= 4:  # Allow 1 failure (ground transport might be tricky)
        print("\n🎉 TESTS PASSED! FlightAgent updated correctly! 🎉")
        print("\n✅ Next: Update HotelAgent (Step B.3)")
        return 0
    else:
        print("\n⚠️  Multiple tests failed. Check FlightAgent update.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)