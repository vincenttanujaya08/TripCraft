import sys
sys.path.insert(0, 'backend')

# Read file
with open('backend/data_sources/seed_loader.py', 'r') as f:
    content = f.read()

# Fix line 127: Change "city" to check both "city" and "destination"
old_line = '''            if hotel.get("city", "").lower() != city_lower:
                continue'''

new_line = '''            hotel_city = hotel.get("city") or hotel.get("destination")
            if not hotel_city or hotel_city.lower() != city_lower:
                continue'''

content = content.replace(old_line, new_line)

# Fix line 162: Same for restaurants
old_rest = '''            if restaurant.get("city", "").lower() != city_lower:
                continue'''

new_rest = '''            rest_city = restaurant.get("city") or restaurant.get("destination")
            if not rest_city or rest_city.lower() != city_lower:
                continue'''

content = content.replace(old_rest, new_rest)

# Write back
with open('backend/data_sources/seed_loader.py', 'w') as f:
    f.write(content)

print("✅ Fixed seed_loader.py!")