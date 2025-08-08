#!/usr/bin/env python3
"""
Debug script to test the football API and find the correct season/league parameters
"""

import sys
import os
sys.path.append('last_man_standing_bot')

from football_api import FootballAPI
import requests
from config import FOOTBALL_API_KEY

def debug_api():
    """Debug the football API to find correct parameters"""
    print("Football API Debug")
    print("=" * 30)
    
    api = FootballAPI()
    
    # Test 1: Check available leagues
    print("\n1. Testing Available Leagues:")
    try:
        url = "https://v3.football.api-sports.io/leagues"
        headers = {
            'X-RapidAPI-Key': FOOTBALL_API_KEY,
            'X-RapidAPI-Host': 'v3.football.api-sports.io'
        }
        params = {'country': 'England'}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        
        if 'response' in data:
            print(f"   Found {len(data['response'])} English leagues:")
            for league in data['response'][:5]:  # Show first 5
                print(f"   - {league['league']['name']} (ID: {league['league']['id']}) - Season: {league['seasons'][-1]['year'] if league['seasons'] else 'N/A'}")
    except Exception as e:
        print(f"   Error getting leagues: {e}")
    
    # Test 2: Check Premier League seasons
    print("\n2. Testing Premier League Seasons:")
    try:
        url = "https://v3.football.api-sports.io/leagues"
        params = {'id': 39}  # Premier League ID
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        
        if 'response' in data and data['response']:
            seasons = data['response'][0]['seasons']
            print(f"   Available seasons for Premier League:")
            for season in seasons[-5:]:  # Show last 5 seasons
                print(f"   - {season['year']} (Start: {season['start']}, End: {season['end']})")
    except Exception as e:
        print(f"   Error getting seasons: {e}")
    
    # Test 3: Try different season formats
    print("\n3. Testing Different Season Formats:")
    seasons_to_try = [2024, 2025, 2026]
    
    for season in seasons_to_try:
        print(f"\n   Testing season {season}:")
        try:
            url = "https://v3.football.api-sports.io/fixtures"
            params = {
                'league': 39,
                'season': season,
                'next': 5
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            if 'response' in data and data['response']:
                print(f"   ✅ Season {season}: Found {len(data['response'])} upcoming fixtures")
                for fixture in data['response'][:2]:
                    print(f"      - {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']} ({fixture['fixture']['date']})")
            else:
                print(f"   ❌ Season {season}: No fixtures found")
                
        except Exception as e:
            print(f"   ❌ Season {season}: Error - {e}")
    
    # Test 4: Try getting current gameweek
    print("\n4. Testing Current Gameweek Detection:")
    current_gw = api.get_current_gameweek()
    print(f"   Current gameweek: {current_gw}")
    
    # Test 5: Try getting fixtures for gameweek 1
    print(f"\n5. Testing Gameweek 1 Fixtures:")
    fixtures = api.get_gameweek_fixtures(1)
    print(f"   Found {len(fixtures)} fixtures for gameweek 1")
    
    if fixtures:
        for fixture in fixtures[:3]:
            print(f"   - {fixture['home_team']} vs {fixture['away_team']} ({fixture['date']}) [{fixture['status']}]")
    
    # Test 6: Try getting deadline
    print(f"\n6. Testing Deadline Calculation:")
    deadline = api.get_gameweek_deadline(1)
    print(f"   Deadline for gameweek 1: {deadline}")

if __name__ == "__main__":
    debug_api()
