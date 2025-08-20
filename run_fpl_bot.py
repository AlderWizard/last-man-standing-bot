#!/usr/bin/env python3
"""
Main runner for FPL Bot
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fpl_bot import FPLBot
from fpl_config import TELEGRAM_BOT_TOKEN, LOG_FORMAT, LOG_LEVEL

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        format=LOG_FORMAT,
        level=getattr(logging, LOG_LEVEL.upper()),
        handlers=[
            logging.FileHandler('fpl_bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main function"""
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Check for bot token
    token = TELEGRAM_BOT_TOKEN or os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("FPL_TELEGRAM_BOT_TOKEN environment variable not set")
        logger.error("Please copy fpl_env_example.env to .env and set your bot token")
        return 1
    
    try:
        # Create and run bot
        logger.info("Starting FPL Fantasy Football Bot...")
        bot = FPLBot(token)
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
