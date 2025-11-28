"""
Debug Amadeus [400] Error
Find exact cause of Bad Request
"""

import os
import sys
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("🔍 DEBUGGING AMADEUS [400] ERROR")
print("=" * 60)

# Step 1: Check imports
print("\n1️⃣ Checking imports...")
try:
    from amadeus import Client, ResponseError
    print("✅ Amadeus SDK imported")
except ImportError as e:
    print(f"❌ Amadeus import failed: {e}")
    sys.exit(1)

# Step 2: Check credentials
print("\n2️⃣ Checking credentials...")
api_key = os.getenv("AMADEUS_API_KEY")
api_secret = os.getenv("AMADEUS_API_SECRET")

if not api_key or not api_secret:
    print("❌ Missing credentials")
    sys.exit(1)

print(f"✅ API Key: {api_key[:10]}...")
print(f"✅ API Secret: {api_secret[:10]}...")

# Step 3: Initialize client
print("\n3️⃣ Initializing client...")
try:
    client = Client(
        client_id=api_key,
        client_secret=api_secret,
        hostname='test'
    )
    print("✅ Client initialized")
except Exception as e:
    print(f"❌ Client init failed: {e}")
    sys.exit(1)

# Step 4: Test authentication
print("\n4️⃣ Testing authentication...")
try:
    response = client.reference_data.locations.get(
        keyword='NYC',
        subType='CITY'
    )
    print("✅ Authentication works")
except ResponseError as e:
    print(f"❌ Auth failed: [{e.response.status_code}] {e.description}")
    sys.exit(1)

# Step 5: Test date validation
print("\n5️⃣ Testing date parameters...")

today = date.today()
print(f"   Today: {today}")

# Test dates
test_dates = [
    ("Past date (INVALID)", today - timedelta(days=1)),
    ("Today (might be INVALID)", today),
    ("Tomorrow (VALID)", today + timedelta(days=1)),
    ("1 week from now (VALID)", today + timedelta(days=7)),
    ("1 month from now (VALID)", today + timedelta(days=30)),
    ("1 year from now (INVALID)", today + timedelta(days=365)),
]

for desc, test_date in test_dates:
    date_str = test_date.strftime("%Y-%m-%d")
    days_from_now = (test_date - today).days
    
    print(f"\n   Testing: {desc}")
    print(f"   Date: {date_str} ({days_from_now} days from now)")
    
    try:
        response = client.shopping.flight_offers_search.get(
            originLocationCode='CGK',
            destinationLocationCode='DPS',
            departureDate=date_str,
            adults=1,
            max=1
        )
        
        if hasattr(response, 'data') and response.data:
            print(f"   ✅ VALID - Found {len(response.data)} offers")
        else:
            print(f"   ⚠️  VALID but no offers")
            
    except ResponseError as e:
        print(f"   ❌ INVALID - [{e.response.status_code}] {e.description}")
    except Exception as e:
        print(f"   ❌ ERROR - {e}")

# Step 6: Test your actual request date
print("\n6️⃣ Testing YOUR request date...")
your_date_str = "2024-12-20"  # From your test

try:
    your_date = datetime.strptime(your_date_str, "%Y-%m-%d").date()
    days_from_now = (your_date - today).days
    
    print(f"   Your date: {your_date_str}")
    print(f"   Days from now: {days_from_now}")
    
    if days_from_now < 0:
        print(f"   ❌ PROBLEM: Date is in the PAST!")
        print(f"   📅 Current date: {today}")
        print(f"   📅 Your request: {your_date}")
        print(f"   🔧 FIX: Use a future date (tomorrow or later)")
    elif days_from_now > 330:
        print(f"   ❌ PROBLEM: Date is too far (>330 days)")
        print(f"   🔧 FIX: Use a date within 330 days")
    else:
        print(f"   ✅ Date is in valid range (1-330 days)")
        
        # Try actual search
        print(f"\n   🔍 Testing actual search...")
        try:
            response = client.shopping.flight_offers_search.get(
                originLocationCode='CGK',
                destinationLocationCode='DPS',
                departureDate=your_date_str,
                adults=2,  # Your test uses 2 adults
                travelClass='ECONOMY',
                currencyCode='IDR',
                max=5
            )
            
            if hasattr(response, 'data') and response.data:
                print(f"   ✅ SUCCESS! Found {len(response.data)} offers")
                
                # Show first offer
                first = response.data[0]
                price = first.get('price', {}).get('total', 'N/A')
                currency = first.get('price', {}).get('currency', 'N/A')
                print(f"   💰 Example price: {price} {currency}")
            else:
                print(f"   ⚠️  Request worked but no offers found")
                
        except ResponseError as e:
            print(f"   ❌ FAILED: [{e.response.status_code}]")
            print(f"   📋 Details: {e.description}")
            
            # Parse error details
            if hasattr(e, 'response') and hasattr(e.response, 'result'):
                errors = e.response.result.get('errors', [])
                for error in errors:
                    print(f"   ⚠️  Error: {error.get('detail', 'No details')}")
                    print(f"      Code: {error.get('code', 'N/A')}")
                    print(f"      Source: {error.get('source', {})}")
            
except Exception as e:
    print(f"   ❌ Error parsing date: {e}")

# Step 7: Summary
print("\n" + "=" * 60)
print("📊 SUMMARY")
print("=" * 60)

print("\n🔧 COMMON CAUSES OF [400] ERROR:")
print("   1. Date in the past")
print("   2. Date too far in future (>330 days)")
print("   3. Invalid date format")
print("   4. Invalid airport code")
print("   5. Invalid travel class")
print("   6. Invalid number of passengers (max 9)")

print("\n💡 RECOMMENDED FIX:")
print("   Use dates that are 1-330 days from today")
print(f"   ✅ Valid range: {today + timedelta(days=1)} to {today + timedelta(days=330)}")

print("\n" + "=" * 60)