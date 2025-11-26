#!/usr/bin/env python3
"""
Fix restaurants.json by adding missing average_cost_per_person field
"""
import json
import sys
from pathlib import Path

def fix_restaurants(json_file_path):
    """Add average_cost_per_person to all restaurants"""
    
    print(f"📝 Reading {json_file_path}...")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {json_file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    
    # Cost mapping based on price range
    cost_map = {
        '$': 50000,      # Budget-friendly
        '$$': 150000,    # Mid-range
        '$$$': 300000,   # Upscale
        '$$$$': 600000   # Fine dining
    }
    
    restaurants = data.get('restaurants', [])
    updated_count = 0
    
    print(f"🔍 Processing {len(restaurants)} restaurants...")
    
    for restaurant in restaurants:
        if 'average_cost_per_person' not in restaurant:
            # Get price range or default to mid-range
            price_range = restaurant.get('price_range', '$$')
            cost = cost_map.get(price_range, 150000)
            
            restaurant['average_cost_per_person'] = cost
            updated_count += 1
            
            print(f"  ✓ {restaurant.get('name', 'Unknown')}: {price_range} → Rp {cost:,}")
    
    if updated_count > 0:
        # Backup original file
        backup_path = str(json_file_path) + '.backup'
        print(f"\n💾 Creating backup: {backup_path}")
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Write updated data
        print(f"💾 Writing updated file: {json_file_path}")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Successfully updated {updated_count} restaurants!")
        return True
    else:
        print(f"\n✅ All restaurants already have average_cost_per_person field!")
        return True


if __name__ == "__main__":
    # Try to find the restaurants.json file
    possible_paths = [
        Path("seed_data/restaurants.json"),
        Path("../seed_data/restaurants.json"),
        Path("~/Downloads/tripcraft-lite 2/seed_data/restaurants.json").expanduser(),
    ]
    
    json_file = None
    for path in possible_paths:
        if path.exists():
            json_file = path
            break
    
    if json_file is None:
        print("❌ Could not find restaurants.json")
        print("Please run this script from the tripcraft-lite 2 directory")
        sys.exit(1)
    
    success = fix_restaurants(json_file)
    sys.exit(0 if success else 1)