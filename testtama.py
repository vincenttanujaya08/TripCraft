"""
Test Script for Conversational System

Tests all major conversation flows:
1. Initial planning
2. Modifications
3. Undo/redo
4. Queries
5. Finalization

Run: python test_conversation.py
"""

import asyncio
import sys
sys.path.insert(0, '/path/to/tripcraft-lite')

from backend.conversational.conversation_manager import get_conversation_manager


async def test_conversation_flow():
    """Test complete conversation flow"""
    
    print("="*60)
    print("🧪 CONVERSATIONAL SYSTEM TEST")
    print("="*60)
    
    manager = get_conversation_manager()
    
    # Test 1: Create session & initial planning
    print("\n📝 Test 1: Initial Planning")
    print("-"*60)
    
    response = await manager.handle_message(
        session_id="test_session",
        message="Plan trip to Bali from 2026-07-15 to 2026-07-20, budget 15000000, 2 travelers"
    )
    
    print(f"✅ Response ({response.state}):")
    print(response.message[:500] + "..." if len(response.message) > 500 else response.message)
    print(f"\n📊 Has trip plan: {response.trip_plan is not None}")
    
    session_id = response.session_id
    
    # Test 2: Modification
    print("\n\n📝 Test 2: Modification - Change Hotel")
    print("-"*60)
    
    response = await manager.handle_message(
        session_id=session_id,
        message="Change hotel to cheaper option, max 500K per night"
    )
    
    print(f"✅ Response ({response.state}):")
    print(response.message)
    print(f"\n📋 Pending modifications: {response.pending_modifications}")
    
    # Test 3: Add more modifications
    print("\n\n📝 Test 3: Add More Modifications")
    print("-"*60)
    
    response = await manager.handle_message(
        session_id=session_id,
        message="Day 2 lunch must be vegetarian"
    )
    
    print(f"✅ Response ({response.state}):")
    print(response.message)
    
    # Test 4: Apply modifications
    print("\n\n📝 Test 4: Apply Modifications")
    print("-"*60)
    
    response = await manager.handle_message(
        session_id=session_id,
        message="Apply all changes"
    )
    
    print(f"✅ Response ({response.state}):")
    print(response.message[:500] + "..." if len(response.message) > 500 else response.message)
    
    # Test 5: Query
    print("\n\n📝 Test 5: Query Budget")
    print("-"*60)
    
    response = await manager.handle_message(
        session_id=session_id,
        message="Show budget breakdown"
    )
    
    print(f"✅ Response ({response.state}):")
    print(response.message)
    
    # Test 6: Undo
    print("\n\n📝 Test 6: Undo")
    print("-"*60)
    
    response = await manager.handle_message(
        session_id=session_id,
        message="Undo last change"
    )
    
    print(f"✅ Response ({response.state}):")
    print(response.message)
    
    # Test 7: Help
    print("\n\n📝 Test 7: Help")
    print("-"*60)
    
    response = await manager.handle_message(
        session_id=session_id,
        message="help"
    )
    
    print(f"✅ Response ({response.state}):")
    print(response.message[:300] + "..." if len(response.message) > 300 else response.message)
    
    # Test 8: Finalize
    print("\n\n📝 Test 8: Finalize")
    print("-"*60)
    
    response = await manager.handle_message(
        session_id=session_id,
        message="Finalize the plan"
    )
    
    print(f"✅ Response ({response.state}):")
    print(response.message)
    
    print("\n" + "="*60)
    print("🎉 ALL TESTS COMPLETED!")
    print("="*60)


async def test_intent_parsing():
    """Test intent parser with various messages"""
    
    print("\n\n"+"="*60)
    print("🧪 INTENT PARSING TEST")
    print("="*60)
    
    from backend.conversational.intent_parser import get_intent_parser
    from backend.conversational.session_store import get_session_store
    
    parser = get_intent_parser()
    session_store = get_session_store()
    session = session_store.create_session()
    
    test_messages = [
        "Plan trip to Tokyo",
        "Change hotel",
        "Day 3 lunch vegetarian",
        "Apply changes",
        "Show budget",
        "Undo",
        "Help",
        "Finalize",
        "What is the weather?",  # Unclear
    ]
    
    for msg in test_messages:
        print(f"\n📩 Message: '{msg}'")
        intent = await parser.parse(msg, session)
        print(f"   🎯 Type: {intent.type.value}")
        if intent.action:
            print(f"   ⚡ Action: {intent.action.value}")
        print(f"   📊 Confidence: {intent.confidence:.2f}")
        if intent.params:
            print(f"   📦 Params: {intent.params}")


async def test_image_fetching():
    """Test image fetching"""
    
    print("\n\n"+"="*60)
    print("🧪 IMAGE FETCHING TEST")
    print("="*60)
    
    from backend.conversational.image_fetcher import get_image_fetcher
    from backend.models.schemas import Hotel, Restaurant, Attraction
    
    fetcher = get_image_fetcher()
    
    # Create mock trip plan
    class MockTripPlan:
        class MockHotels:
            recommended_hotel = Hotel(
                name="Grand Bali Resort",
                type="resort",
                description="Luxury beachfront resort",
                price_per_night=800000,
                rating=4.5,
                amenities=["pool", "spa"]
            )
        
        class MockDining:
            restaurants = [
                Restaurant(
                    name="Warung Makan Bu Oka",
                    cuisine="Indonesian",
                    description="Traditional Balinese cuisine",
                    average_cost_per_person=50000,
                    rating=4.3,
                    price_range="$"
                )
            ]
        
        class MockDestination:
            attractions = [
                Attraction(
                    name="Tanah Lot Temple",
                    type="temple",
                    description="Iconic sea temple",
                    estimated_duration_hours=2.0
                )
            ]
        
        hotels = MockHotels()
        dining = MockDining()
        destination = MockDestination()
    
    mock_plan = MockTripPlan()
    
    print("\n🖼️  Starting image fetch...")
    image_states = await fetcher.fetch_all_images(mock_plan)
    
    print(f"✅ Started fetching {len(image_states)} images")
    
    # Wait a bit for async fetching
    await asyncio.sleep(3)
    
    # Check status
    batch = fetcher.get_image_batch_status()
    print(f"\n📊 Status:")
    print(f"   Total: {batch.total_count}")
    print(f"   Loaded: {batch.loaded_count}")
    print(f"   Failed: {batch.failed_count}")
    
    # Show results
    for item_id, state in batch.images.items():
        status_icon = "✅" if state.status.value == "loaded" else "❌" if state.status.value == "failed" else "⏳"
        print(f"   {status_icon} {item_id}: {state.status.value}")
        if state.url:
            print(f"      URL: {state.url[:60]}...")


if __name__ == "__main__":
    print("\n🚀 TripCraft Conversational System Tests\n")
    
    # Run tests
    asyncio.run(test_conversation_flow())
    asyncio.run(test_intent_parsing())
    asyncio.run(test_image_fetching())
    
    print("\n✅ All tests completed!")