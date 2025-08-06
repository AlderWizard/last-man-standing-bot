import os
from dotenv import load_dotenv

load_dotenv()

# Get these from your .env file
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY')

# League settings
DEFAULT_LEAGUE = 39  # Premier League ID
PICK_DEADLINE_HOUR = 14  # 2 PM on match day