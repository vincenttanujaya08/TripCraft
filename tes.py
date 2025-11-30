"""
Test Script for TripOrchestrator

Tests:
1. Basic trip planning (happy path)
2. Budget constraints (tight budget)
3. Progress tracking
4. Multiple destinations
5. Error scenarios

Run: python test_orchestrator.py
"""

import asyncio
import sys
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, '/Users/vincent/Downloads/tripcraft-lite 2')

from backend.models.schemas import TripRequest
from backend.orchestrator.trip_orchestrator import (
    TripOrchestrator,
    BudgetAllocationStrategy,
    ExecutionProgress
)


def print_header(title: str):
    """Print formatted test header"""
    print("\n" + "="*60)
    print(f"{title}")
    print("="*60 + "\n")


def print_trip_summary(trip_plan, metadata):
    """Print trip plan summary"""
    print("\n📋 TRIP PLAN SUMMARY")
    print("-" * 60)
    print(f"Destination: {trip_plan.destination.destination}")
    print(f"Duration: {len(trip_plan.itinerary.daily_itineraries)} days")
    print(f"\n💰 BUDGET:")
    print(f"  Total Cost: Rp {trip_plan.budget.total_cost:,.0f}")
    print(f"  Allocated: Rp {trip_plan.budget.budget_allocated:,.0f}")
    print(f"  Remaining: Rp {trip_plan.budget.remaining_budget:,.0f}")
    print(f"  Within Budget: {'✅ YES' if trip_plan.budget.within_budget else '⚠️  NO'}")
    
    print(f"\n✈️  FLIGHTS:")
    print(f"  Outbound: {len(trip_plan.flights.outbound_flights)} options")
    print(f"  Return: {len(trip_plan.flights.return_flights)} options")
    print(f"  Cost: Rp {trip_plan.flights.total_cost:,.0f}")
    
    print(f"\n🏨 HOTEL:")
    print(f"  Name: {trip_plan.hotels.recommended_hotel.name}")
    print(f"  Rating: {trip_plan.hotels.recommended_hotel.rating}⭐")
    print(f"  Cost: Rp {trip_plan.hotels.total_cost:,.0f}")
    
    print(f"\n🍽️  DINING:")
    print(f"  Meal Plans: {len(trip_plan.dining.meal_plan)} days")
    print(f"  Cost: Rp {trip_plan.dining.estimated_total_cost:,.0f}")
    
    print(f"\n📅 ITINERARY:")
    total_activities = sum(len(day.activities) for day in trip_plan.itinerary.daily_itineraries)
    print(f"  Days: {len(trip_plan.itinerary.daily_itineraries)}")
    print(f"  Activities: {total_activities}")
    
    print(f"\n✅ VERIFICATION:")
    print(f"  Overall Score: {trip_plan.verification.overall_score:.1f}/10")
    print(f"  Valid: {'✅ YES' if trip_plan.verification.is_valid else '❌ NO'}")
    
    print(f"\n🎯 CONFIDENCE:")
    print(f"  Overall: {trip_plan.overall_confidence:.2%}")
    
    if trip_plan.warnings:
        print(f"\n⚠️  WARNINGS ({len(trip_plan.warnings)}):")
        for i, warning in enumerate(trip_plan.warnings[:5], 1):
            print(f"  {i}. {warning}")
        if len(trip_plan.warnings) > 5:
            print(f"  ... and {len(trip_plan.warnings) - 5} more")


async def test_basic_trip():
    """Test 1: Basic trip planning (happy path)"""
    print_header("TEST 1: Basic Trip Planning (Happy Path)")
    
    print("🔍 Creating trip request:")
    print("   Destination: Bali")
    print("   Origin: Jakarta")
    print("   Duration: 4 days")
    print("   Budget: Rp 15,000,000")
    print("   Travelers: 2")
    
    request = TripRequest(
        destination="Bali",
        origin="Jakarta",
        duration_days=4,
        start_date="2024-07-15",
        end_date="2024-07-18",
        budget=15000000.0,
        num_travelers=2,
        preferences={
            "accommodation_type": "hotel",
            "interests": ["culture", "beach", "food"]
        }
    )
    
    # Show budget allocation
    print(f"\n💰 Budget Allocation Strategy:")
    allocation = BudgetAllocationStrategy.allocate(request.budget)
    print(BudgetAllocationStrategy.get_allocation_summary(request.budget))
    
    print("\n🚀 Starting orchestration...")
    print("-" * 60)
    
    orchestrator = TripOrchestrator()
    
    # Progress tracking
    progress_updates = []
    def on_progress(progress: ExecutionProgress):
        progress_updates.append({
            'step': progress.current_step,
            'agent': progress.current_agent,
            'percentage': progress.get_progress_percentage(),
            'message': progress.messages[-1] if progress.messages else ""
        })
        print(f"  [{progress.get_progress_percentage():5.1f}%] {progress.messages[-1]}")
    
    try:
        trip_plan, metadata = await orchestrator.plan_trip(request, on_progress)
        
        print("\n✅ Orchestration completed!")
        print_trip_summary(trip_plan, metadata)
        
        # Verify execution
        assert metadata['success'] == True, "Execution should succeed"
        assert trip_plan.destination is not None, "Should have destination"
        assert trip_plan.flights is not None, "Should have flights"
        assert trip_plan.hotels is not None, "Should have hotels"
        assert trip_plan.dining is not None, "Should have dining"
        assert trip_plan.budget is not None, "Should have budget"
        assert trip_plan.itinerary is not None, "Should have itinerary"
        assert trip_plan.verification is not None, "Should have verification"
        
        print("\n✅ PASS - Basic Trip Planning")
        return True
        
    except Exception as e:
        print(f"\n❌ FAIL - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_tight_budget():
    """Test 2: Tight budget scenario"""
    print_header("TEST 2: Tight Budget Scenario")
    
    print("🔍 Creating trip request with tight budget:")
    print("   Destination: Bali")
    print("   Origin: Jakarta")
    print("   Duration: 4 days")
    print("   Budget: Rp 5,000,000 (very tight!)")
    print("   Travelers: 2")
    
    request = TripRequest(
        destination="Bali",
        origin="Jakarta",
        duration_days=4,
        start_date="2024-07-15",
        end_date="2024-07-18",
        budget=5000000.0,  # Tight budget
        num_travelers=2,
        preferences={
            "accommodation_type": "hostel",
            "interests": ["culture", "beach"]
        }
    )
    
    print(f"\n💰 Budget Allocation:")
    allocation = BudgetAllocationStrategy.allocate(request.budget)
    print(f"  Flights: Rp {allocation['flight']:,.0f}")
    print(f"  Hotels: Rp {allocation['hotel']:,.0f}")
    print(f"  Food: Rp {allocation['food']:,.0f}")
    
    print("\n🚀 Starting orchestration...")
    
    orchestrator = TripOrchestrator()
    
    try:
        trip_plan, metadata = await orchestrator.plan_trip(request)
        
        print("\n✅ Orchestration completed!")
        print_trip_summary(trip_plan, metadata)
        
        # Check for budget warnings
        has_budget_warnings = any('budget' in w.lower() or 'exceed' in w.lower() 
                                  for w in trip_plan.warnings)
        print(f"\n📊 Budget Warnings: {'✅ YES' if has_budget_warnings else '⚠️  NONE'}")
        
        # Verify execution
        assert metadata['success'] == True, "Should complete even with tight budget"
        assert len(trip_plan.warnings) > 0, "Should have warnings for tight budget"
        
        print("\n✅ PASS - Tight Budget Scenario")
        return True
        
    except Exception as e:
        print(f"\n❌ FAIL - Error: {str(e)}")
        return False


async def test_progress_tracking():
    """Test 3: Progress tracking"""
    print_header("TEST 3: Progress Tracking")
    
    request = TripRequest(
        destination="Yogyakarta",
        origin="Jakarta",
        duration_days=3,
        start_date="2024-08-01",
        end_date="2024-08-03",
        budget=8000000.0,
        num_travelers=2
    )
    
    print("🔍 Testing progress tracking...")
    print("   Tracking all 7 agent executions\n")
    
    orchestrator = TripOrchestrator()
    
    progress_log = []
    
    def on_progress(progress: ExecutionProgress):
        if progress.messages:
            latest = progress.messages[-1]
            progress_log.append({
                'step': progress.current_step,
                'percentage': progress.get_progress_percentage(),
                'message': latest
            })
            print(f"[{progress.current_step}/7] {progress.get_progress_percentage():5.1f}% - {latest}")
    
    try:
        trip_plan, metadata = await orchestrator.plan_trip(request, on_progress)
        
        print(f"\n✅ Orchestration completed!")
        print(f"\n📊 Progress Log Analysis:")
        print(f"   Total messages: {len(progress_log)}")
        print(f"   Steps tracked: {max(p['step'] for p in progress_log)}/7")
        
        # Verify progress tracking
        assert len(progress_log) > 0, "Should have progress messages"
        assert max(p['step'] for p in progress_log) == 7, "Should track all 7 steps"
        
        print("\n✅ PASS - Progress Tracking")
        return True
        
    except Exception as e:
        print(f"\n❌ FAIL - Error: {str(e)}")
        return False


async def test_multiple_destinations():
    """Test 4: Different destinations"""
    print_header("TEST 4: Multiple Destinations")
    
    destinations = [
        ("Bali", "Jakarta"),
        ("Yogyakarta", "Jakarta"),
        ("Lombok", "Jakarta")
    ]
    
    results = []
    
    for dest, origin in destinations:
        print(f"\n🔍 Testing: {origin} → {dest}")
        
        request = TripRequest(
            destination=dest,
            origin=origin,
            duration_days=3,
            start_date="2024-07-15",
            end_date="2024-07-17",
            budget=10000000.0,
            num_travelers=2
        )
        
        orchestrator = TripOrchestrator()
        
        try:
            trip_plan, metadata = await orchestrator.plan_trip(request)
            
            print(f"   ✅ Success: Rp {trip_plan.budget.total_cost:,.0f}, "
                  f"Confidence: {trip_plan.overall_confidence:.2%}")
            
            results.append({
                'destination': dest,
                'success': True,
                'cost': trip_plan.budget.total_cost,
                'confidence': trip_plan.overall_confidence
            })
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
            results.append({
                'destination': dest,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n📊 Results Summary:")
    successful = sum(1 for r in results if r['success'])
    print(f"   Successful: {successful}/{len(destinations)}")
    
    for result in results:
        if result['success']:
            print(f"   ✅ {result['destination']}: "
                  f"Rp {result['cost']:,.0f}, {result['confidence']:.2%}")
        else:
            print(f"   ❌ {result['destination']}: {result.get('error', 'Unknown error')}")
    
    assert successful == len(destinations), f"Should succeed for all destinations"
    
    print("\n✅ PASS - Multiple Destinations")
    return True


async def test_budget_allocation():
    """Test 5: Budget allocation validation"""
    print_header("TEST 5: Budget Allocation Validation")
    
    test_budgets = [
        5000000,   # 5M
        10000000,  # 10M
        20000000,  # 20M
        50000000,  # 50M
    ]
    
    print("🔍 Testing budget allocation percentages:\n")
    
    for budget in test_budgets:
        allocation = BudgetAllocationStrategy.allocate(budget)
        total = sum(allocation.values())
        
        print(f"Budget: Rp {budget:,.0f}")
        print(f"  Flights: Rp {allocation['flight']:,.0f} (35%)")
        print(f"  Hotels: Rp {allocation['hotel']:,.0f} (30%)")
        print(f"  Food: Rp {allocation['food']:,.0f} (20%)")
        print(f"  Activities: Rp {allocation['activities']:,.0f} (10%)")
        print(f"  Misc: Rp {allocation['misc']:,.0f} (5%)")
        print(f"  Total: Rp {total:,.0f} ({'✅' if abs(total - budget) < 1 else '❌'})")
        print()
        
        # Verify
        assert abs(total - budget) < 1, f"Allocation should sum to budget"
        assert allocation['flight'] == budget * 0.35, "Flight should be 35%"
        assert allocation['hotel'] == budget * 0.30, "Hotel should be 30%"
        assert allocation['food'] == budget * 0.20, "Food should be 20%"
        assert allocation['activities'] == budget * 0.10, "Activities should be 10%"
        assert allocation['misc'] == budget * 0.05, "Misc should be 5%"
    
    print("✅ PASS - Budget Allocation Validation")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 TRIPORCHESTRATOR TEST SUITE")
    print("="*60)
    
    tests = [
        ("Basic Trip Planning", test_basic_trip),
        ("Tight Budget Scenario", test_tight_budget),
        ("Progress Tracking", test_progress_tracking),
        ("Multiple Destinations", test_multiple_destinations),
        ("Budget Allocation", test_budget_allocation),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Final summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! 🎉")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)