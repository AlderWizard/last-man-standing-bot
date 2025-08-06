#!/usr/bin/env python3
"""
Startup script for Last Man Standing Bot
Handles environment setup and graceful error handling
"""

import sys
import os
import logging
from pathlib import Path

# Add the bot directory to Python path
bot_dir = Path(__file__).parent / "last_man_standing_bot"
sys.path.insert(0, str(bot_dir))

def check_environment():
    """Check if all required environment variables are set"""
    env_file = bot_dir / ".env"
    if not env_file.exists():
        print("[ERROR] .env file not found!")
        print(f"Expected location: {env_file}")
        return False
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(env_file)
    
    required_vars = ['TELEGRAM_BOT_TOKEN', 'FOOTBALL_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"[ERROR] Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("[OK] Environment variables configured")
    return True

def check_dependencies():
    """Check if all required packages are installed"""
    try:
        import telegram
        import requests
        import schedule
        print("[OK] All dependencies installed")
        return True
    except ImportError as e:
        print(f"[ERROR] Missing dependency - {e}")
        print("Run: pip install -r last_man_standing_bot/requirements.txt")
        return False

def main():
    """Main startup function"""
    print("Last Man Standing Bot - Starting Up...")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check database directory permissions
    try:
        test_file = bot_dir / "test_write.tmp"
        test_file.touch()
        test_file.unlink()
        print("[OK] Database directory writable")
    except Exception as e:
        print(f"[ERROR] Cannot write to database directory - {e}")
        sys.exit(1)
    
    print("=" * 50)
    print("Starting bot...")
    
    # Import and run the main bot
    try:
        from main import main as bot_main
        bot_main()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"[ERROR] Bot error: {e}")
        logging.exception("Bot crashed")
        sys.exit(1)

if __name__ == "__main__":
    main()
