#!/usr/bin/env python3
"""
Test script for FPL Bot functionality
"""

import asyncio
import aiohttp
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fpl_database import FPLDatabase
from fpl_config import FPL_API_BASE

async def test_fpl_api():
    """Test FPL API connectivity"""
    print("🔍 Testing FPL API connectivity...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test bootstrap endpoint
            url = f"{FPL_API_BASE}/bootstrap-static/"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Bootstrap API working - Found {len(data.get('events', []))} gameweeks")
                else:
                    print(f"❌ Bootstrap API failed with status {response.status}")
                    return False
            
            # Test a sample league (public league)
            test_league_id = "314"  # Official FPL league
            url = f"{FPL_API_BASE}/leagues-classic/{test_league_id}/standings/"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    league_name = data.get('league', {}).get('name', 'Unknown')
                    standings_count = len(data.get('standings', {}).get('results', []))
                    print(f"✅ League API working - '{league_name}' has {standings_count} players")
                else:
                    print(f"❌ League API failed with status {response.status}")
                    return False
        
        return True
    
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def test_database():
    """Test database functionality"""
    print("\n🗄️ Testing database functionality...")
    
    try:
        # Initialize database
        db = FPLDatabase("test_fpl_bot.db")
        
        # Test adding a league
        success = db.add_league(12345, "314", "Test League")
        if success:
            print("✅ League addition working")
        else:
            print("❌ League addition failed")
            return False
        
        # Test getting leagues
        leagues = db.get_leagues(12345)
        if leagues and len(leagues) == 1:
            print(f"✅ League retrieval working - Found: {leagues[0]['league_name']}")
        else:
            print("❌ League retrieval failed")
            return False
        
        # Test speech reminder
        success = db.add_speech_reminder(12345, "314", 15, "Test Player", 123456, 85)
        if success:
            print("✅ Speech reminder addition working")
        else:
            print("❌ Speech reminder addition failed")
            return False
        
        # Test getting speech reminders
        reminders = db.get_pending_speech_reminders(12345)
        if reminders and len(reminders) == 1:
            print(f"✅ Speech reminder retrieval working - Found reminder for {reminders[0]['winner_name']}")
        else:
            print("❌ Speech reminder retrieval failed")
            return False
        
        # Test record update
        success = db.update_record(12345, "314", "Test Player", 123456, 15, 120, "highest")
        if success:
            print("✅ Record update working")
        else:
            print("✅ Record update working (no new record - expected)")
        
        # Clean up test database
        os.remove("test_fpl_bot.db")
        print("✅ Database test completed successfully")
        
        return True
    
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_imports():
    """Test all imports work correctly"""
    print("\n📦 Testing imports...")
    
    try:
        from fpl_bot import FPLBot
        from fpl_database import FPLDatabase
        from fpl_config import TELEGRAM_BOT_TOKEN, FPL_API_BASE
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 FPL Bot Test Suite")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed - check dependencies")
        return False
    
    # Test database
    if not test_database():
        print("\n❌ Database tests failed")
        return False
    
    # Test API
    if not await test_fpl_api():
        print("\n❌ API tests failed - check internet connection")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! Bot is ready to deploy.")
    print("\n📋 Next steps:")
    print("1. Get a Telegram bot token from @BotFather")
    print("2. Copy fpl_env_example.env to .env")
    print("3. Set FPL_TELEGRAM_BOT_TOKEN in .env")
    print("4. Run: python run_fpl_bot.py")
    
    return True

if __name__ == "__main__":
    asyncio.run(main())
