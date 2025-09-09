import sys
import os
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock the config module
class MockConfig:
    FOOTBALL_API_KEY = "mock_key"
    DEFAULT_SEASON = 2025

sys.modules['config'] = MockConfig()

# Now import the FootballAPI class
from last_man_standing_bot.football_api import FootballAPI

def test_gameweek_detection():
    try:
        api = FootballAPI()
        current_gw = api.get_current_gameweek()
        logger.info(f"✅ Current gameweek detected: {current_gw}")
        return True
    except Exception as e:
        logger.error(f"❌ Error detecting gameweek: {e}")
        return False

if __name__ == "__main__":
    print("Testing gameweek detection...")
    success = test_gameweek_detection()
    sys.exit(0 if success else 1)
