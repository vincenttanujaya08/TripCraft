#!/usr/bin/env python3
"""
Fix ALL Seed Data Prices: USD → IDR
Converts hotels, activities, and flight prices to Indonesian Rupiah

Usage:
    python fix_all_seed_prices.py
"""

import json
import os
import shutil
from datetime import datetime

USD_TO_IDR = 15000  # Conversion rate

def backup_file(filepath):
    """Create backup with timestamp"""
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}.backup_{timestamp}"
        shutil.copy2(filepath, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return True
    return False

def fix_hotels(filepath="seed_data/hotels.json"):
    """Fix hotel prices: USD → IDR"""
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    print(f"\n📍 Fixing {filepath}...")
    backup_file(filepath)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    changed = 0
    
    for destination in data:
        hotels = destination.get('hotels', [])
        
        for hotel in hotels:
            price = hotel.get('price_per_night', 0)
            
            # If price < 10,000 → assume USD
            if 0 < price < 10000:
                old_price = price
                new_price = price * USD_TO_IDR
                hotel['price_per_night'] = new_price
                
                print(f"   ✏️  {hotel['name']}: ${old_price} → Rp {new_price:,.0f}")
                changed += 1
    
    if changed > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Fixed {changed} hotel prices")
    else:
        print(f"ℹ️  No changes needed (prices already in IDR)")
    
    return True

def fix_activities(filepath="seed_data/activities.json"):
    """Fix activity prices: USD → IDR"""
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    print(f"\n📍 Fixing {filepath}...")
    backup_file(filepath)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    changed = 0
    
    for destination in data:
        activities = destination.get('activities', [])
        
        for activity in activities:
            price = activity.get('price_per_person', 0)
            
            # If price < 10,000 → assume USD
            if 0 < price < 10000:
                old_price = price
                new_price = price * USD_TO_IDR
                activity['price_per_person'] = new_price
                
                print(f"   ✏️  {activity['name']}: ${old_price} → Rp {new_price:,.0f}")
                changed += 1
    
    if changed > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Fixed {changed} activity prices")
    else:
        print(f"ℹ️  No changes needed (prices already in IDR)")
    
    return True

def fix_flights(filepath="seed_data/flights.json"):
    """Fix flight prices: USD → IDR"""
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    print(f"\n📍 Fixing {filepath}...")
    backup_file(filepath)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    changed = 0
    
    for flight in data:
        # Check both min and max
        for field in ['price_range_min', 'price_range_max']:
            price = flight.get(field, 0)
            
            # If price < 10,000 → assume USD
            if 0 < price < 10000:
                old_price = price
                new_price = price * USD_TO_IDR
                flight[field] = new_price
                
                print(f"   ✏️  {flight['route']} ({field}): ${old_price} → Rp {new_price:,.0f}")
                changed += 1
    
    if changed > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Fixed {changed} flight price fields")
    else:
        print(f"ℹ️  No changes needed (prices already in IDR)")
    
    return True

def main():
    """Run all fixes"""
    
    print("="*60)
    print("🔧 FIXING ALL SEED DATA PRICES (USD → IDR)")
    print("="*60)
    print(f"Conversion rate: 1 USD = Rp {USD_TO_IDR:,.0f}")
    
    # Change to project directory
    if os.path.exists("seed_data"):
        print("✅ Found seed_data directory")
    else:
        print("❌ seed_data directory not found!")
        print("   Please run this script from project root: 'tripcraft-lite 2'")
        return
    
    # Fix each file
    success_count = 0
    
    if fix_hotels():
        success_count += 1
    
    if fix_activities():
        success_count += 1
    
    if fix_flights():
        success_count += 1
    
    # Summary
    print("\n" + "="*60)
    print(f"✅ COMPLETE! Fixed {success_count}/3 files")
    print("="*60)
    print("\n📝 NEXT STEPS:")
    print("1. Test the app: python generate.py")
    print("2. Check PDF prices are now in millions (Rp 2,550,000 not Rp 2,550)")
    print("3. If still wrong, check Agent code (HotelAgent, ActivityAgent)")
    print("\n💾 Backups saved with timestamp in seed_data/")

if __name__ == "__main__":
    main()