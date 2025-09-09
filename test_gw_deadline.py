import sys
import os
import logging
from datetime import datetime, timezone, timedelta

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

def test_gameweek_deadline():
    try:
        api = FootballAPI()
        
        # Get current gameweek info
        current_gw, gw_data = api._get_fpl_current_gameweek()
        logger.info(f"Current gameweek: {current_gw}")
        
        # Get fixtures for the current gameweek
        fixtures_response = requests.get(
            "https://fantasy.premierleague.com/api/fixtures/",
            timeout=10
        )
        fixtures_response.raise_for_status()
        all_fixtures = fixtures_response.json()
        
        # Get fixtures for current GW
        gw_fixtures = [f for f in all_fixtures if f.get('event') == current_gw]
        
        if not gw_fixtures:
            logger.error("No fixtures found for current gameweek")
            return False
        
        # Find the first match
        first_match = min(
            (f for f in gw_fixtures if f.get('kickoff_time')),
            key=lambda x: x['kickoff_time']
        )
        
        first_kickoff = datetime.fromisoformat(
            first_match['kickoff_time'].replace('Z', '+00:00')
        ).replace(tzinfo=timezone.utc)
        
        # Calculate expected deadline (90 minutes before first match)
        expected_deadline = (first_kickoff - timedelta(minutes=90)).strftime('%Y-%m-%dT%H:%M:%SZ')
        actual_deadline = gw_data['deadline_time']
        
        logger.info(f"First match kickoff: {first_kickoff} (UTC)")
        logger.info(f"Expected deadline:   {expected_deadline} (90 mins before kickoff)")
        logger.info(f"Actual deadline:     {actual_deadline}")
        
        if expected_deadline != actual_deadline:
            logger.error("Deadline does not match expected value!")
            return False
            
        logger.info("✅ Deadline is correctly set to 90 minutes before first match")
        return True
        
    except Exception as e:
        logger.error(f"Error testing gameweek deadline: {e}")
        return False

if __name__ == "__main__":
    import requests  # Import here to avoid mock issues
    print("Testing gameweek deadline calculation...")
    success = test_gameweek_deadline()
    sys.exit(0 if success else 1)
