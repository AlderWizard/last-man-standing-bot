import requests
import logging
from config import FOOTBALL_API_KEY

logger = logging.getLogger(__name__)

class FootballAPI:
    def __init__(self):
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'X-RapidAPI-Key': FOOTBALL_API_KEY,
            'X-RapidAPI-Host': 'v3.football.api-sports.io'
        }
        
        # Fallback team data for when API is unavailable
        self.premier_league_teams = {
            'arsenal': {'id': 42, 'name': 'Arsenal'},
            'chelsea': {'id': 49, 'name': 'Chelsea'},
            'liverpool': {'id': 40, 'name': 'Liverpool'},
            'manchester city': {'id': 50, 'name': 'Manchester City'},
            'manchester united': {'id': 33, 'name': 'Manchester United'},
            'tottenham': {'id': 47, 'name': 'Tottenham'},
            'newcastle': {'id': 34, 'name': 'Newcastle United'},
            'brighton': {'id': 51, 'name': 'Brighton & Hove Albion'},
            'aston villa': {'id': 66, 'name': 'Aston Villa'},
            'west ham': {'id': 48, 'name': 'West Ham United'},
            'crystal palace': {'id': 52, 'name': 'Crystal Palace'},
            'fulham': {'id': 36, 'name': 'Fulham'},
            'wolves': {'id': 39, 'name': 'Wolverhampton Wanderers'},
            'everton': {'id': 45, 'name': 'Everton'},
            'brentford': {'id': 55, 'name': 'Brentford'},
            'nottingham forest': {'id': 65, 'name': 'Nottingham Forest'},
            'luton': {'id': 163, 'name': 'Luton Town'},
            'burnley': {'id': 44, 'name': 'Burnley'},
            'sheffield united': {'id': 62, 'name': 'Sheffield United'},
            'bournemouth': {'id': 35, 'name': 'AFC Bournemouth'}
        }
    
    def get_fixtures(self, league_id, season, round_number=None):
        """Get fixtures for a specific league and season"""
        url = f"{self.base_url}/fixtures"
        params = {
            'league': league_id,
            'season': season
        }
        if round_number:
            params['round'] = f"Regular Season - {round_number}"
        
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    def get_match_result(self, fixture_id):
        """Get result for a specific match"""
        url = f"{self.base_url}/fixtures"
        params = {'id': fixture_id}
        
        response = requests.get(url, headers=self.headers, params=params)
        data = response.json()
        
        if data['results'] > 0:
            match = data['response'][0]
            return {
                'home_team': match['teams']['home']['name'],
                'away_team': match['teams']['away']['name'],
                'home_score': match['goals']['home'],
                'away_score': match['goals']['away'],
                'status': match['fixture']['status']['short'],
                'winner': match['teams']['home']['winner']
            }
        return None
    
    def search_team(self, team_name, league_id):
        """Find team ID by name in specific league"""
        try:
            # First try the API
            url = f"{self.base_url}/teams"
            params = {
                'league': league_id,
                'season': 2024  # Current season
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'response' in data and data['response']:
                teams = data['response']
                
                for team_data in teams:
                    team = team_data['team']
                    if team_name.lower() in team['name'].lower():
                        return {
                            'id': team['id'],
                            'name': team['name']
                        }
        
        except Exception as e:
            logger.warning(f"API search failed: {e}. Using fallback data.")
        
        # Fallback to local team data
        team_key = team_name.lower().strip()
        
        # Direct match
        if team_key in self.premier_league_teams:
            return self.premier_league_teams[team_key]
        
        # Partial match
        for key, team_info in self.premier_league_teams.items():
            if team_key in key or key in team_key:
                return team_info
            # Also check against the full team name
            if team_key in team_info['name'].lower():
                return team_info
        
        return None