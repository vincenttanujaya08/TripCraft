#!/usr/bin/env python3
"""
Fix duration_hours None errors in smart_retriever.py
"""

from pathlib import Path
import re

def fix_smart_retriever():
    """Fix all duration_hours issues"""
    
    filepath = Path(__file__).parent / "backend" / "data_sources" / "smart_retriever.py"
    
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return False
    
    print(f"📁 Fixing: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Fix 1: Replace duration_hours = flight.get('duration_hours', 2)
    # with safe version
    pattern1 = r"duration_hours = flight\.get\('duration_hours', 2\)"
    replacement1 = "duration_hours = float(flight.get('duration_hours') or 2)"
    content = re.sub(pattern1, replacement1, content)
    
    # Fix 2: Replace duration_hours = flight.get('duration_hours')
    # (without default)
    pattern2 = r"duration_hours = flight\.get\('duration_hours'\)(?!\s*or)"
    replacement2 = "duration_hours = float(flight.get('duration_hours') or 2)"
    content = re.sub(pattern2, replacement2, content)
    
    # Fix 3: Wrap all timedelta(hours=...) with float()
    # Find: timedelta(hours=duration_hours)
    # Replace: timedelta(hours=float(duration_hours))
    pattern3 = r"timedelta\(hours=duration_hours\)"
    replacement3 = "timedelta(hours=float(duration_hours or 2))"
    content = re.sub(pattern3, replacement3, content)
    
    # Fix 4: Safe duration parsing with try-except
    pattern4 = r"duration_minutes = self\._parse_duration\((.+?)\)"
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Fixed!")
        return True
    else:
        print("⏭️  No changes needed")
        return False

if __name__ == "__main__":
    fix_smart_retriever()
    print("\n🚀 Now run: python tes.py")