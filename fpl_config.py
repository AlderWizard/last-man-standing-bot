#!/usr/bin/env python3
"""
Configuration file for FPL Bot
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('FPL_TELEGRAM_BOT_TOKEN')
DATABASE_PATH = os.getenv('FPL_DATABASE_PATH', 'fpl_bot.db')

# FPL API Configuration
FPL_API_BASE = "https://fantasy.premierleague.com/api"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# Bot Settings
MAX_LEAGUES_PER_CHAT = 10
SPEECH_REMINDER_DAYS = 3  # Days after which to escalate reminders
RECORDS_UPDATE_INTERVAL = 3600  # 1 hour in seconds
SPEECH_CHECK_INTERVAL = 86400   # 24 hours in seconds

# Message Templates
WELCOME_MESSAGE = """🏆 **Premier League Fantasy Football Bot** 🏆

Welcome! I can help you track your FPL league stats.

**Commands:**
• `/addleague <league_id>` - Add a league to track
• `/leagues` - View tracked leagues
• `/stats <league_id>` - Show league standings
• `/records` - Show highest/lowest scores
• `/speech` - Check speech reminders
• `/speechdone <league_id> <gameweek>` - Mark speech as completed
• `/help` - Show this help message

To get started, add a league with `/addleague <your_league_id>`"""

ERROR_MESSAGES = {
    'league_not_found': "❌ Could not find league with ID: {league_id}\nPlease check the league ID and try again.",
    'no_leagues': "No leagues tracked yet. Add one with `/addleague <league_id>`",
    'invalid_league_id': "Please provide a valid league ID. Example: `/addleague 123456`",
    'database_error': "❌ Database error occurred. Please try again later.",
    'api_error': "❌ Failed to fetch data from FPL API. Please try again later.",
    'invalid_gameweek': "Gameweek must be a number between 1 and 38.",
}

SUCCESS_MESSAGES = {
    'league_added': "✅ Successfully added league: **{league_name}**\nLeague ID: `{league_id}`\n\nUse `/stats {league_id}` to view standings!",
    'speech_completed': "✅ Speech reminder marked as completed for League {league_id}, GW{gameweek}!",
    'records_updated': "📊 Records updated successfully!",
}

# Logging Configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'
