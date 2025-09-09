#!/usr/bin/env python3
"""
FPL API Integration for accurate gameweek detection and fixture data
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class FPLAPIClient:
    """Client for Fantasy Premier League API"""
    
    def __init__(self):
        self.base_url = "https://fantasy.premierleague.com/api"
        
    def get_bootstrap_data(self) -> Optional[Dict]:
        """Get general FPL information including events (gameweeks)"""
        try:
            response = requests.get(f"{self.base_url}/bootstrap-static/", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching FPL bootstrap data: {e}")
            return None
    
    def get_fixtures(self, event_id: Optional[int] = None) -> Optional[List[Dict]]:
        """Get fixtures, optionally filtered by gameweek (event_id)"""
        try:
            url = f"{self.base_url}/fixtures/"
            if event_id:
                url += f"?event={event_id}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching FPL fixtures: {e}")
            return None
    
    def get_current_gameweek(self) -> Tuple[Optional[int], Optional[Dict]]:
        """
        Get current gameweek number and info from FPL API
        Returns: (gameweek_number, gameweek_data)
        """
        bootstrap_data = self.get_bootstrap_data()
        if not bootstrap_data or 'events' not in bootstrap_data:
            return None, None
        
        events = bootstrap_data['events']
        now = datetime.now()
        
        # Find current gameweek based on FPL logic
        current_event = None
        
        for event in events:
            # FPL marks current gameweek with is_current=True
            if event.get('is_current', False):
                current_event = event
                break
        
        # Fallback: find gameweek based on deadline times
        if not current_event:
            for event in events:
                if event.get('deadline_time'):
                    deadline = datetime.fromisoformat(event['deadline_time'].replace('Z', '+00:00'))
                    # Convert to local time (assuming UTC from API)
                    deadline = deadline.replace(tzinfo=None)
                    
                    # If deadline hasn't passed, this is current gameweek
                    if now <= deadline:
                        current_event = event
                        break
                    # If we're past deadline but gameweek is still active
                    elif not event.get('finished', False):
                        current_event = event
                        break
        
        if current_event:
            return current_event['id'], current_event
        
        # Final fallback: return first unfinished gameweek
        for event in events:
            if not event.get('finished', False):
                return event['id'], event
        
        return None, None
    
    def get_gameweek_deadline(self, gameweek: int) -> Optional[datetime]:
        """Get deadline for specific gameweek from FPL API"""
        bootstrap_data = self.get_bootstrap_data()
        if not bootstrap_data or 'events' not in bootstrap_data:
            return None
        
        for event in bootstrap_data['events']:
            if event['id'] == gameweek and event.get('deadline_time'):
                try:
                    # FPL API returns UTC time in ISO format
                    deadline_str = event['deadline_time'].replace('Z', '+00:00')
                    deadline = datetime.fromisoformat(deadline_str)
                    # Convert to local time (remove timezone info for consistency)
                    return deadline.replace(tzinfo=None)
                except Exception as e:
                    logger.error(f"Error parsing deadline for GW{gameweek}: {e}")
                    return None
        
        return None
    
    def get_gameweek_fixtures(self, gameweek: int) -> List[Dict]:
        """Get all fixtures for a specific gameweek"""
        fixtures = self.get_fixtures(gameweek)
        if not fixtures:
            return []
        
        # Process fixtures to extract useful information
        processed_fixtures = []
        for fixture in fixtures:
            processed_fixtures.append({
                'id': fixture.get('id'),
                'kickoff_time': fixture.get('kickoff_time'),
                'team_h': fixture.get('team_h'),
                'team_a': fixture.get('team_a'),
                'team_h_score': fixture.get('team_h_score'),
                'team_a_score': fixture.get('team_a_score'),
                'finished': fixture.get('finished', False),
                'started': fixture.get('started', False),
                'event': fixture.get('event')  # gameweek number
            })
        
        return processed_fixtures
    
    def is_picks_allowed(self, gameweek: int) -> bool:
        """Check if picks are allowed for gameweek based on FPL deadline"""
        deadline = self.get_gameweek_deadline(gameweek)
        if not deadline:
            return True  # Allow picks if can't determine deadline
        
        now = datetime.now()
        return now <= deadline
    
    def get_team_name_mapping(self) -> Dict[int, str]:
        """Get mapping of team IDs to team names from FPL API"""
        bootstrap_data = self.get_bootstrap_data()
        if not bootstrap_data or 'teams' not in bootstrap_data:
            return {}
        
        team_mapping = {}
        for team in bootstrap_data['teams']:
            team_mapping[team['id']] = team['name']
        
        return team_mapping

def test_fpl_api():
    """Test the FPL API integration"""
    print("=== Testing FPL API Integration ===")
    
    client = FPLAPIClient()
    
    # Test current gameweek
    current_gw, gw_data = client.get_current_gameweek()
    if current_gw:
        print(f"Current gameweek: {current_gw}")
        if gw_data:
            print(f"  Name: {gw_data.get('name', 'N/A')}")
            print(f"  Deadline: {gw_data.get('deadline_time', 'N/A')}")
            print(f"  Finished: {gw_data.get('finished', False)}")
            print(f"  Is Current: {gw_data.get('is_current', False)}")
    else:
        print("Could not determine current gameweek")
    
    # Test deadline for current gameweek
    if current_gw:
        deadline = client.get_gameweek_deadline(current_gw)
        if deadline:
            print(f"Deadline for GW{current_gw}: {deadline}")
            picks_allowed = client.is_picks_allowed(current_gw)
            print(f"Picks allowed: {picks_allowed}")
    
    # Test fixtures
    if current_gw:
        fixtures = client.get_gameweek_fixtures(current_gw)
        print(f"Fixtures for GW{current_gw}: {len(fixtures)} matches")
        for fixture in fixtures[:3]:  # Show first 3
            print(f"  Match {fixture['id']}: Team {fixture['team_h']} vs Team {fixture['team_a']}")
    
    # Test team mapping
    teams = client.get_team_name_mapping()
    print(f"Teams available: {len(teams)}")
    for team_id, team_name in list(teams.items())[:5]:  # Show first 5
        print(f"  {team_id}: {team_name}")

if __name__ == "__main__":
    test_fpl_api()
