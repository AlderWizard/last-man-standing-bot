#!/usr/bin/env python3
"""
Test script to verify gameweek progression and elimination logic
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'last_man_standing_bot'))

from datetime import datetime, timedelta
from last_man_standing_bot.football_api import FootballAPI
from last_man_standing_bot.config import DEFAULT_SEASON

def test_gameweek_progression():
    """Test automatic gameweek progression"""
    print("=== Testing Gameweek Progression ===")
    
    api = FootballAPI()
    
    # Test current time (should be GW2)
    current_time = datetime.now()
    print(f"Current time: {current_time}")
    
    current_gw = api.get_current_gameweek()
    print(f"Current gameweek: {current_gw}")
    
    # Test future dates to verify GW3 progression
    test_dates = [
        datetime(2025, 8, 22, 17, 0, 0),  # Before GW2 deadline
        datetime(2025, 8, 22, 19, 0, 0),  # After GW2 deadline
        datetime(2025, 8, 29, 17, 0, 0),  # Before GW3 deadline
        datetime(2025, 8, 29, 19, 0, 0),  # After GW3 deadline
        datetime(2025, 9, 5, 17, 0, 0),   # Before GW4 deadline
    ]
    
    print("\n=== Testing Future Gameweek Transitions ===")
    for test_date in test_dates:
        # Simulate the date by temporarily modifying the logic
        print(f"\nSimulating date: {test_date}")
        
        # Check deadlines
        for gw in [2, 3, 4]:
            deadline = api.get_gameweek_deadline(gw)
            if deadline:
                status = "BEFORE" if test_date <= deadline else "AFTER"
                print(f"  GW{gw} deadline ({deadline.strftime('%a %d %b %H:%M')}): {status}")
        
        # Determine expected gameweek
        gw2_deadline = datetime(2025, 8, 22, 18, 0, 0)
        gw3_deadline = datetime(2025, 8, 29, 18, 0, 0)
        gw4_deadline = datetime(2025, 9, 5, 18, 0, 0)
        
        if test_date <= gw2_deadline:
            expected_gw = 2
        elif test_date <= gw3_deadline:
            expected_gw = 3
        elif test_date <= gw4_deadline:
            expected_gw = 4
        else:
            expected_gw = 5
            
        print(f"  Expected gameweek: {expected_gw}")

def test_elimination_messages():
    """Test that elimination messages are properly configured"""
    print("\n=== Testing Elimination Messages ===")
    
    # Check if elimination roast messages are available
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'last_man_standing_bot'))
        from last_man_standing_bot.main import ELIMINATION_ROASTS, DEADLINE_MISS_ROASTS
        
        print(f"Elimination roasts available: {len(ELIMINATION_ROASTS)}")
        print(f"Deadline miss roasts available: {len(DEADLINE_MISS_ROASTS)}")
        
        # Show sample messages
        print(f"\nSample elimination roast:")
        print(f"  {ELIMINATION_ROASTS[0].format(username='TestUser')}")
        
        print(f"\nSample deadline miss roast:")
        print(f"  {DEADLINE_MISS_ROASTS[0].format(username='TestUser')}")
        
    except ImportError as e:
        print(f"Could not import roast messages: {e}")

def test_picks_allowed_logic():
    """Test the picks allowed logic for different gameweeks"""
    print("\n=== Testing Picks Allowed Logic ===")
    
    api = FootballAPI()
    
    for gw in [1, 2, 3, 4]:
        deadline = api.get_gameweek_deadline(gw)
        picks_allowed = api.is_picks_allowed(gw)
        
        if deadline:
            now = datetime.now()
            time_to_deadline = deadline - now
            
            print(f"GW{gw}:")
            print(f"  Deadline: {deadline.strftime('%a %d %b at %H:%M')}")
            print(f"  Picks allowed: {picks_allowed}")
            print(f"  Time to deadline: {time_to_deadline}")
            
            if time_to_deadline.total_seconds() > 0:
                print(f"  Status: OPEN (deadline in {time_to_deadline})")
            else:
                print(f"  Status: CLOSED (deadline was {abs(time_to_deadline)} ago)")

if __name__ == "__main__":
    test_gameweek_progression()
    test_elimination_messages()
    test_picks_allowed_logic()
