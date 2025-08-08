#!/usr/bin/env python3
"""
Test script to debug the deadline issue
"""

import sys
import os
sys.path.append('last_man_standing_bot')

from football_api import FootballAPI
from datetime import datetime

def test_deadline_issue():
    """Test the deadline calculation issue"""
    print("Testing Deadline Issue")
    print("=" * 30)
    
    # Initialize API
    api = FootballAPI()
    
    # Test current gameweek
    print("\n1. Testing Current Gameweek:")
    current_gameweek = api.get_current_gameweek()
    print(f"   Current gameweek: {current_gameweek}")
    
    # Test gameweek fixtures
    print(f"\n2. Testing Gameweek {current_gameweek} Fixtures:")
    fixtures = api.get_gameweek_fixtures(current_gameweek)
    print(f"   Found {len(fixtures)} fixtures")
    
    if fixtures:
        print("   First few fixtures:")
        for i, fixture in enumerate(fixtures[:3]):
            match_time = datetime.fromtimestamp(fixture['timestamp']) if fixture['timestamp'] else "No timestamp"
            print(f"   - {fixture['home_team']} vs {fixture['away_team']} ({match_time}) [{fixture['status']}]")
    else:
        print("   No fixtures found!")
        
        # Try different gameweeks
        print("\n   Trying other gameweeks:")
        for gw in [1, 2, 3]:
            test_fixtures = api.get_gameweek_fixtures(gw)
            print(f"   Gameweek {gw}: {len(test_fixtures)} fixtures")
    
    # Test deadline calculation
    print(f"\n3. Testing Deadline Calculation:")
    deadline = api.get_gameweek_deadline(current_gameweek)
    print(f"   Deadline for gameweek {current_gameweek}: {deadline}")
    
    if deadline is None:
        print("   ❌ Deadline is None - this is the issue!")
        
        # Try manual deadline calculation
        print("\n   Trying manual deadline calculation:")
        if fixtures:
            timestamps = [f['timestamp'] for f in fixtures if f['timestamp']]
            if timestamps:
                earliest = min(timestamps)
                manual_deadline = datetime.fromtimestamp(earliest)
                print(f"   Earliest match: {manual_deadline}")
                print(f"   Manual deadline (2h before): {manual_deadline}")
            else:
                print("   No valid timestamps found in fixtures")
    else:
        print(f"   ✅ Deadline calculated successfully: {deadline}")

if __name__ == "__main__":
    test_deadline_issue()
