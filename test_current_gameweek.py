#!/usr/bin/env python3
"""
Test script to verify the current gameweek calculation is working correctly
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'last_man_standing_bot'))

from datetime import datetime
from last_man_standing_bot.football_api import FootballAPI
from last_man_standing_bot.config import DEFAULT_SEASON

def test_current_gameweek():
    """Test the current gameweek calculation"""
    print("=== Testing Current Gameweek Calculation ===")
    now = datetime.now()
    print(f"Current date: {now}")
    print(f"Configured season: {DEFAULT_SEASON}")
    
    # Manual calculation test
    season_start = datetime(2025, 8, 15)
    days_elapsed = (now - season_start).days
    print(f"Days since season start ({season_start.date()}): {days_elapsed}")
    
    # Test deadline logic
    gw1_deadline = datetime(2025, 8, 15, 18, 0, 0)
    gw2_deadline = datetime(2025, 8, 22, 18, 0, 0)
    
    print(f"GW1 deadline: {gw1_deadline}")
    print(f"GW2 deadline: {gw2_deadline}")
    print(f"Current time: {now}")
    print(f"Past GW1 deadline? {now > gw1_deadline}")
    print(f"Past GW2 deadline? {now > gw2_deadline}")
    
    # Expected gameweek based on deadlines
    if now <= gw1_deadline:
        expected_gw = 1
    elif now <= gw2_deadline:
        expected_gw = 2
    else:
        expected_gw = 3
    
    print(f"Expected gameweek based on deadlines: {expected_gw}")
    
    api = FootballAPI()
    
    try:
        current_gw = api.get_current_gameweek()
        print(f"API returned gameweek: {current_gw}")
        
        # Test specific gameweeks
        print("\n=== Testing specific gameweeks ===")
        for gw in [1, 2, 3]:
            deadline = api.get_gameweek_deadline(gw)
            if deadline:
                print(f"GW{gw} deadline: {deadline.strftime('%A %d %B at %H:%M')}")
                picks_allowed = api.is_picks_allowed(gw)
                print(f"GW{gw} picks allowed: {picks_allowed}")
            else:
                print(f"GW{gw}: No deadline found")
        
    except Exception as e:
        print(f"Error testing gameweek: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_current_gameweek()
