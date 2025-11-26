#!/usr/bin/env python3
"""
Setup verification script for TripCraft Lite
Run this to check if everything is configured correctly
"""
import os
import sys
from pathlib import Path

def check_files():
    """Check if all required files exist"""
    print("🔍 Checking file structure...")
    
    required_files = [
        "backend/requirements.txt",
        "backend/main.py",
        "backend/models/schemas.py",
        "backend/models/database.py",
        "seed_data/destinations.json",
        "seed_data/hotels.json",
        "seed_data/restaurants.json",
        "seed_data/flights.json",
        ".env.example"
    ]
    
    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)
    
    if missing:
        print(f"❌ Missing files: {', '.join(missing)}")
        return False
    else:
        print("✅ All required files present")
        return True


def check_env():
    """Check environment variables"""
    print("\n🔍 Checking environment variables...")
    
    if not Path(".env").exists():
        print("⚠️  .env file not found. Copy from .env.example and fill in your API keys:")
        print("   cp .env.example .env")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_key or gemini_key == "your_gemini_api_key_here":
        print("❌ GEMINI_API_KEY not configured in .env")
        print("   Get your key from: https://ai.google.dev/")
        return False
    else:
        print(f"✅ GEMINI_API_KEY configured ({gemini_key[:10]}...)")
    
    # Optional keys
    opentripmap = os.getenv("OPENTRIPMAP_API_KEY")
    unsplash = os.getenv("UNSPLASH_ACCESS_KEY")
    
    if opentripmap:
        print(f"✅ OPENTRIPMAP_API_KEY configured (optional)")
    else:
        print("⚠️  OPENTRIPMAP_API_KEY not set (optional, but recommended)")
    
    if unsplash:
        print(f"✅ UNSPLASH_ACCESS_KEY configured (optional)")
    else:
        print("⚠️  UNSPLASH_ACCESS_KEY not set (optional, but recommended)")
    
    return True


def check_dependencies():
    """Check if Python dependencies are installed"""
    print("\n🔍 Checking Python dependencies...")
    
    try:
        import fastapi
        import pydantic
        import sqlalchemy
        import httpx
        print("✅ Core dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e.name}")
        print("   Run: pip install -r backend/requirements.txt")
        return False


def check_database():
    """Check if database can be initialized"""
    print("\n🔍 Checking database...")
    
    try:
        sys.path.insert(0, 'backend')
        from models.database import init_db, get_session
        
        init_db()
        session = get_session()
        print("✅ Database initialized successfully")
        session.close()
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def check_seed_data():
    """Validate seed data JSON files"""
    print("\n🔍 Validating seed data...")
    
    import json
    
    files_to_check = {
        "destinations": "seed_data/destinations.json",
        "hotels": "seed_data/hotels.json",
        "restaurants": "seed_data/restaurants.json",
        "flights": "seed_data/flights.json"
    }
    
    all_valid = True
    for name, path in files_to_check.items():
        try:
            with open(path) as f:
                data = json.load(f)
                count = len(data.get(name, []))
                print(f"✅ {name}.json: {count} entries")
        except Exception as e:
            print(f"❌ {name}.json: {e}")
            all_valid = False
    
    return all_valid


def main():
    """Run all checks"""
    print("=" * 60)
    print("TripCraft Lite - Setup Verification")
    print("=" * 60)
    
    checks = [
        ("File Structure", check_files),
        ("Environment Variables", check_env),
        ("Python Dependencies", check_dependencies),
        ("Database", check_database),
        ("Seed Data", check_seed_data)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ {name} check failed: {e}")
            results[name] = False
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All checks passed! You're ready to run the backend:")
        print("   cd backend")
        print("   python main.py")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
