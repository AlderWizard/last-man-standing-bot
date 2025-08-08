#!/usr/bin/env python3
"""
Test script to find 2025 season fixtures
"""

import sys
import os
sys.path.append('last_man_standing_bot')

import requests
from config import FOOTBALL_API_KEY
from datetime import datetime

def test_2025_fixtures():
    """Test getting 2025 season fixtures"""
    print("Testing 2025 Season Fixtures")
    print("=" * 30)
    
    headers = {
        'X-RapidAPI-Key': FOOTBALL_API_KEY,
        'X-RapidAPI-Host': 'v3.football.api-sports.io'
    }
    
    # Test 1: Get upcoming fixtures for 2025 season
    print("\n1. Testing Upcoming Fixtures (2025 season):")
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        params = {
            'league': 39,
            'season': 2025,
            'next': 10
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        
        if 'response' in data and data['response']:
            print(f"   Found {len(data['response'])} upcoming fixtures:")
            for fixture in data['response'][:5]:
                match_date = datetime.fromisoformat(fixture['fixture']['date'].replace('Z', '+00:00'))
                print(f"   - {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}")
                print(f"     Date: {match_date.strftime('%A %d %B %Y at %H:%M')}")
                print(f"     Round: {fixture['league']['round']}")
                print(f"     Status: {fixture['fixture']['status']['short']}")
                print()
        else:
            print("   No upcoming fixtures found")
            
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Get fixtures by date range
    print("\n2. Testing Fixtures by Date Range (Aug 15-22, 2025):")
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        params = {
            'league': 39,
            'season': 2025,
            'from': '2025-08-15',
            'to': '2025-08-22'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        
        if 'response' in data and data['response']:
            print(f"   Found {len(data['response'])} fixtures for Aug 15-22:")
            for fixture in data['response']:
                match_date = datetime.fromisoformat(fixture['fixture']['date'].replace('Z', '+00:00'))
                print(f"   - {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}")
                print(f"     Date: {match_date.strftime('%A %d %B %Y at %H:%M')}")
                print(f"     Round: {fixture['league']['round']}")
                print()
        else:
            print("   No fixtures found for that date range")
            
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_2025_fixtures()
