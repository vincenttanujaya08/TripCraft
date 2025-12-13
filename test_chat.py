import requests
import json
import time

BASE_URL = "http://localhost:8000/api/conversation"

def print_separator():
    print("-" * 50)

def chat(session_id, message):
    url = f"{BASE_URL}/chat"
    payload = {
        "session_id": session_id,
        "message": message
    }
    
    print(f"Me: {message}")
    start = time.time()
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        duration = time.time() - start
        
        print(f"Bot ({duration:.2f}s): {data['message']}")
        
        if data.get('trip_plan'):
            plan = data['trip_plan']
            dest = plan.get('destination', {}).get('destination', {}).get('name', 'Unknown')
            cost = plan.get('budget', {}).get('breakdown', {}).get('total', 0)
            print(f"   [Data] Trip to {dest} | Total Cost: Rp {cost:,.0f}")
            
        if data.get('pending_modifications'):
            print(f"   [Pending] {len(data['pending_modifications'])} modifications queued")
            
        print_separator()
        return data
        
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None

def main():
    print("🚀 Starting Simple Chat Test (Quota Saving Mode)")
    print_separator()
    
    # Session ID
    session_id = f"test_simple_{int(time.time())}"
    
    # Single request: Plan trip
    # This verifies:
    # 1. API connection works
    # 2. IntentParser works (LLM or fallback)
    # 3. Trip generation works
    print("\n📝 TEST: Simple Plan Trip to Bali")
    chat(session_id, "Plan a trip to Bali for 3 days")

if __name__ == "__main__":
    main()
