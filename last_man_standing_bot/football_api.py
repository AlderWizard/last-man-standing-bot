import requests
import logging
from config import FOOTBALL_API_KEY, DEFAULT_SEASON
from fuzzywuzzy import fuzz, process

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
            'leeds': {'id': 18, 'name': 'Leeds United'},
            'burnley': {'id': 44, 'name': 'Burnley'},
            'sunderland': {'id': 179, 'name': 'Sunderland'},
            'bournemouth': {'id': 35, 'name': 'AFC Bournemouth'}
        }
        
        # Common team nicknames and aliases for fuzzy matching
        self.team_aliases = {
            'spurs': 'tottenham',
            'city': 'manchester city', 
            'united': 'manchester united',
            'man city': 'manchester city',
            'man united': 'manchester united',
            'man u': 'manchester united',
            'manu': 'manchester united',
            'villa': 'aston villa',
            'palace': 'crystal palace',
            'forest': 'nottingham forest',
            'brighton': 'brighton',
            'newcastle': 'newcastle',
            'west ham': 'west ham',
            'wolves': 'wolves',
            'leeds united': 'leeds',
            'leeds utd': 'leeds',
            'hammers': 'west ham',
            'gunners': 'arsenal',
            'blues': 'chelsea',
            'reds': 'liverpool',
            'citizens': 'manchester city',
            'red devils': 'manchester united'
        }
    
    def fuzzy_search_team(self, user_input):
        """Enhanced team search with fuzzy matching and nickname support"""
        user_input = user_input.lower().strip()
        
        # 1. Check direct aliases first
        if user_input in self.team_aliases:
            team_key = self.team_aliases[user_input]
            if team_key in self.premier_league_teams:
                team_info = self.premier_league_teams[team_key]
                return {
                    'exact_match': True,
                    'team': team_info,
                    'confidence': 100,
                    'user_input': user_input
                }
        
        # 2. Check exact team name matches
        if user_input in self.premier_league_teams:
            team_info = self.premier_league_teams[user_input]
            return {
                'exact_match': True,
                'team': team_info,
                'confidence': 100,
                'user_input': user_input
            }
        
        # 3. Fuzzy matching against team names and keys
        all_team_options = []
        
        # Add team keys (short names)
        for key, team_info in self.premier_league_teams.items():
            all_team_options.append((key, team_info))
        
        # Add full team names
        for key, team_info in self.premier_league_teams.items():
            all_team_options.append((team_info['name'].lower(), team_info))
        
        # Add aliases
        for alias, team_key in self.team_aliases.items():
            if team_key in self.premier_league_teams:
                all_team_options.append((alias, self.premier_league_teams[team_key]))
        
        # Find best matches using fuzzy string matching
        search_strings = [option[0] for option in all_team_options]
        best_matches = process.extract(user_input, search_strings, limit=3, scorer=fuzz.ratio)
        
        # Filter matches with confidence > 60%
        good_matches = [(match, score) for match, score in best_matches if score >= 60]
        
        if good_matches:
            best_match, confidence = good_matches[0]
            # Find the team info for the best match
            for option_name, team_info in all_team_options:
                if option_name == best_match:
                    return {
                        'exact_match': confidence >= 90,
                        'team': team_info,
                        'confidence': confidence,
                        'user_input': user_input,
                        'matched_text': best_match,
                        'suggestions': [team_info for match, score in good_matches[:3] 
                                      for option_name, team_info in all_team_options 
                                      if option_name == match]
                    }
        
        # No good matches found
        return {
            'exact_match': False,
            'team': None,
            'confidence': 0,
            'user_input': user_input,
            'suggestions': []
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
    
    def get_current_gameweek(self, league_id=39, season=DEFAULT_SEASON):
        """Get current gameweek based on match schedules and FPL deadlines
        
        Returns:
            int: The current gameweek number that should be active for picks
        """
        try:
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            
            # First, try to get the current gameweek from FPL API
            try:
                # Get FPL data
                response = requests.get(
                    "https://fantasy.premierleague.com/api/bootstrap-static/",
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                # Find current and next gameweeks
                events = data.get('events', [])
                current_gw = next((e for e in events if e.get('is_current')), None)
                next_gw = next((e for e in events if e.get('is_next')), None)
                
                if current_gw and next_gw:
                    # Check if we're in the gap between gameweeks
                    current_deadline = datetime.fromisoformat(
                        current_gw['deadline_time'].replace('Z', '+00:00')
                    ).replace(tzinfo=timezone.utc)
                    
                    next_deadline = datetime.fromisoformat(
                        next_gw['deadline_time'].replace('Z', '+00:00')
                    ).replace(tzinfo=timezone.utc)
                    
                    # If we're past the current GW deadline, we're in the next GW
                    if now > current_deadline and now < next_deadline:
                        return int(next_gw['id'])
                    return int(current_gw['id'])
                
            except Exception as e:
                logger.warning(f"Couldn't get FPL data, falling back to direct API: {e}")
            
            # Fallback: Use direct API to determine gameweek
            url = f"{self.base_url}/fixtures"
            params = {
                'league': league_id,
                'season': season.split('-')[0],
                'timezone': 'Europe/London',
                'status': 'NS-1H-HT-2H-ET-P-BT-INT-LIVE-FT-AET-PEN-BT-ABD-CANC-PST-SUSP-INT_PEN'
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('response'):
                logger.error("No fixtures found in API response")
                return 1
            
            # Get all fixtures grouped by gameweek
            gw_fixtures = {}
            for fixture in data['response']:
                gw = int(fixture['league']['round'].split(' ')[-1])
                if gw not in gw_fixtures:
                    gw_fixtures[gw] = []
                gw_fixtures[gw].append(fixture)
            
            if not gw_fixtures:
                return 1
            
            # Find the most recent gameweek with completed matches
            current_gw = None
            for gw in sorted(gw_fixtures.keys()):
                fixtures = gw_fixtures[gw]
                # Check if all matches in this GW are finished
                if all(f['fixture']['status']['short'] in ['FT', 'AET', 'PEN'] 
                      for f in fixtures if f['fixture']['status']['short'] not in ['PST', 'CANC']):
                    current_gw = gw
            
            # If no completed gameweeks, return the first one
            if current_gw is None:
                return min(gw_fixtures.keys())
                
            # If we have a next gameweek, return it, otherwise stay on current
            next_gw = current_gw + 1
            return next_gw if next_gw in gw_fixtures else current_gw
            
        except Exception as e:
            logger.error(f"Error in get_current_gameweek: {e}")
            # Fallback: Use system date to estimate current gameweek
            # This is a very rough estimate and should only be used as last resort
            season_start = datetime(int(season.split('-')[0]), 8, 1)  # August 1st of season start year
            days_since_start = (now - season_start).days
            estimated_gw = (days_since_start // 7) + 1
            return max(1, min(38, estimated_gw))  # Clamp between 1 and 38
            
        except Exception as e:
            logger.error(f"Error getting current gameweek from football API: {e}")
            # Fallback to FPL API if the main API fails
            try:
                current_gw, _ = self._get_fpl_current_gameweek(season)
                if current_gw:
                    logger.info(f"FPL fallback returned gameweek: {current_gw}")
                    return current_gw
            except Exception as fpl_error:
                logger.error(f"FPL fallback also failed: {fpl_error}")
            
            # If all else fails, return a default value or raise an error
            logger.warning("Could not determine current gameweek, defaulting to 1")
            return 1
    
    def _get_fpl_current_gameweek(self, season=None):
        """Get current gameweek from FPL API with improved gameweek transition handling"""
        try:
            import requests
            from datetime import datetime, timezone, timedelta
            
            # Get current date in UTC
            now = datetime.now(timezone.utc)
            
            # Try to get data from FPL API
            response = requests.get(
                "https://fantasy.premierleague.com/api/bootstrap-static/",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if 'events' not in data:
                logger.error("No 'events' key in FPL API response")
                return None, None
                
            events = data['events']
            
            # Add datetime objects for each event's deadline
            for event in events:
                if 'deadline_time' in event:
                    try:
                        event['deadline_dt'] = datetime.fromisoformat(
                            event['deadline_time'].replace('Z', '+00:00')
                        ).replace(tzinfo=timezone.utc)
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Error parsing deadline time for event {event.get('id')}: {e}")
                        event['deadline_dt'] = None
            
            # Find current and next gameweeks
            current_gw = next((e for e in events if e.get('is_current')), None)
            next_gw = next((e for e in events if e.get('is_next')), None)
            
            # If we have a current gameweek with a deadline
            if current_gw and 'deadline_dt' in current_gw and current_gw['deadline_dt']:
                # If deadline has passed and we have a next gameweek, use that instead
                if now > current_gw['deadline_dt'] and next_gw and not current_gw.get('finished', False):
                    logger.info(f"Current gameweek {current_gw['id']} deadline has passed, moving to next gameweek {next_gw['id']}")
                    return next_gw['id'], next_gw
                
                # Otherwise, return the current gameweek
                return current_gw['id'], current_gw
            
            # Fallback: Find the next upcoming deadline
            upcoming_events = [e for e in events if 'deadline_dt' in e and e['deadline_dt'] and e['deadline_dt'] > now]
            if upcoming_events:
                next_upcoming = min(upcoming_events, key=lambda x: x['deadline_dt'])
                return next_upcoming['id'], next_upcoming
                
            # Fallback to first unfinished gameweek
            for event in events:
                if not event.get('finished', False):
                    return event['id'], event
            
            # If all else fails, return the last gameweek
            if events:
                return events[-1]['id'], events[-1]
                
            return None, None
            
        except Exception as e:
            logger.error(f"Error in _get_fpl_current_gameweek: {e}")
            raise RuntimeError(f"Failed to get current gameweek from FPL API: {e}")
    
    def _get_gameweek_fallback(self, season):
        """Fallback gameweek calculation based on date"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        # Season start dates
        if season == 2025:  # 2024-25 season
            season_start = datetime(2024, 8, 17)
        elif season == 2026:  # 2025-26 season  
            season_start = datetime(2025, 8, 15)
        else:
            return 1  # Default fallback
        
        if now < season_start:
            return 1
        
        # Simple weekly calculation
        days_elapsed = (now - season_start).days
        estimated_gameweek = min((days_elapsed // 7) + 1, 38)
        
        logger.info(f"Fallback calculation: GW{estimated_gameweek}")
        return estimated_gameweek
    
    def _get_gameweek_from_api(self, league_id=39, season=DEFAULT_SEASON):
        """Fallback method to get gameweek from API"""
        try:
            url = f"{self.base_url}/fixtures"
            params = {
                'league': league_id,
                'season': season,
                'next': 10  # Get next 10 fixtures to determine current gameweek
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'response' in data and data['response']:
                # Get the round from the first upcoming fixture
                first_fixture = data['response'][0]
                round_info = first_fixture['league']['round']
                
                # Extract gameweek number from round string (e.g., "Regular Season - 15")
                if 'Regular Season -' in round_info:
                    gameweek = int(round_info.split('- ')[1])
                    return gameweek
                    
            return 1  # Default to gameweek 1 if can't determine
            
        except Exception as e:
            logger.warning(f"Error getting gameweek from API: {e}")
            return 1
    
    def get_gameweek_fixtures(self, gameweek, league_id=39, season=DEFAULT_SEASON):
        """Get all fixtures for a specific gameweek"""
        try:
            url = f"{self.base_url}/fixtures"
            
            # Try multiple season formats in case the API uses different conventions
            season_formats = [season, 2025, 2024]  # Try current config, then common alternatives
            
            for season_try in season_formats:
                logger.info(f"Trying season format: {season_try}")
                
                # Try different round formats that the API might use
                round_formats = [
                    f"Regular Season - {gameweek}",
                    f"Matchday {gameweek}",
                    f"Round {gameweek}",
                    str(gameweek)
                ]
                
                fixtures = []
                for round_format in round_formats:
                    params = {
                        'league': league_id,
                        'season': season_try,
                        'round': round_format
                    }
                    
                    try:
                        response = requests.get(url, headers=self.headers, params=params, timeout=10)
                        response.raise_for_status()
                        
                        data = response.json()
                        if 'response' in data and data['response']:
                            logger.info(f"Found fixtures using season {season_try} and round format: {round_format}")
                            for fixture in data['response']:
                                fixtures.append({
                                    'id': fixture['fixture']['id'],
                                    'date': fixture['fixture']['date'],
                                    'timestamp': fixture['fixture']['timestamp'],
                                    'status': fixture['fixture']['status']['short'],
                                    'home_team': fixture['teams']['home']['name'],
                                    'away_team': fixture['teams']['away']['name'],
                                    'home_score': fixture['goals']['home'],
                                    'away_score': fixture['goals']['away']
                                })
                            return fixtures
                    except Exception as format_error:
                        logger.debug(f"Season {season_try}, round format '{round_format}' failed: {format_error}")
                        continue
            
            # If no round format worked, try getting current/upcoming fixtures without round filter
            logger.warning(f"No fixtures found for gameweek {gameweek} with any season/round format, trying date-based approach")
            return self._get_current_fixtures(league_id, season)
            
        except Exception as e:
            logger.error(f"Error getting gameweek fixtures: {e}")
            return []
    
    def _get_current_fixtures(self, league_id=39, season=DEFAULT_SEASON):
        """Fallback method to get current/upcoming fixtures"""
        try:
            from datetime import datetime, timedelta
            
            url = f"{self.base_url}/fixtures"
            # Get fixtures from today to next 7 days
            today = datetime.now().strftime('%Y-%m-%d')
            next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Try multiple season formats for the date-based approach too
            season_formats = [season, 2025, 2024]
            
            for season_try in season_formats:
                logger.info(f"Trying date-based approach with season: {season_try}")
                
                params = {
                    'league': league_id,
                    'season': season_try,
                    'from': today,
                    'to': next_week,
                    'status': 'NS'  # Not Started
                }
                
                try:
                    response = requests.get(url, headers=self.headers, params=params, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    if 'response' in data and data['response']:
                        fixtures = []
                        for fixture in data['response']:
                            fixtures.append({
                                'id': fixture['fixture']['id'],
                                'date': fixture['fixture']['date'],
                                'timestamp': fixture['fixture']['timestamp'],
                                'status': fixture['fixture']['status']['short'],
                                'home_team': fixture['teams']['home']['name'],
                                'away_team': fixture['teams']['away']['name'],
                                'home_score': fixture['goals']['home'],
                                'away_score': fixture['goals']['away']
                            })
                        logger.info(f"Found {len(fixtures)} upcoming fixtures using date-based approach with season {season_try}")
                        return fixtures
                except Exception as season_error:
                    logger.debug(f"Date-based approach failed for season {season_try}: {season_error}")
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"Error in fallback fixture method: {e}")
            return []

    def get_gameweek_deadline(self, gameweek, league_id=39, season=DEFAULT_SEASON):
        """Get pick deadline for gameweek from FPL API"""
        from datetime import datetime, timedelta
        
        # First try FPL API for accurate deadline
        deadline = self._get_fpl_gameweek_deadline(gameweek)
        if deadline:
            logger.info(f"FPL API deadline for GW{gameweek}: {deadline}")
            return deadline
        
        # Fallback to fixture-based calculation
        logger.warning(f"FPL API failed for GW{gameweek} deadline, using fixture fallback")
        return self._get_deadline_fallback(gameweek, league_id, season)
    
    def _get_fpl_gameweek_deadline(self, gameweek):
        """Get deadline from FPL API"""
        try:
            import requests
            from datetime import datetime
            response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'events' not in data:
                return None
            
            for event in data['events']:
                if event['id'] == gameweek and event.get('deadline_time'):
                    try:
                        deadline_str = event['deadline_time'].replace('Z', '+00:00')
                        deadline = datetime.fromisoformat(deadline_str)
                        # Convert to local time (remove timezone info for consistency)
                        return deadline.replace(tzinfo=None)
                    except Exception as e:
                        logger.error(f"Error parsing FPL deadline for GW{gameweek}: {e}")
                        return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching FPL deadline for GW{gameweek}: {e}")
            return None
    
    def _get_deadline_fallback(self, gameweek, league_id, season):
        """Fallback deadline calculation"""
        from datetime import datetime, timedelta
        
        def get_emergency_fallback_deadline():
            """Emergency fallback when all else fails - returns a reasonable deadline"""
            today = datetime.now()
            
            # Special handling for 2025-26 season start
            if season == 2026 and gameweek == 1:
                # 2025-26 Premier League season starts Friday August 15th, 2025
                season_start = datetime(2025, 8, 15, 17, 30, 0)  # Friday 5:30 PM (FPL actual deadline)
                logger.info(f"Using emergency fallback for 2025-26 season start: {season_start}")
                return season_start
            
            # General emergency fallback - next Friday 5:30 PM (typical FPL deadline)
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0 and today.hour >= 17:  # If it's Friday after 5:30 PM
                days_until_friday = 7  # Next Friday
            emergency_deadline = today + timedelta(days=days_until_friday)
            emergency_deadline = emergency_deadline.replace(hour=17, minute=30, second=0, microsecond=0)
            
            logger.warning(f"Using emergency fallback deadline for gameweek {gameweek}: {emergency_deadline}")
            return emergency_deadline
        
        try:
            fixtures = self.get_gameweek_fixtures(gameweek, league_id, season)
            if not fixtures:
                logger.warning(f"No fixtures found for gameweek {gameweek}, using season-aware fallback deadline")
                # Fallback: Use season-aware deadline based on known Premier League schedule
                
                today = datetime.now()
                
                # Special handling for 2025-26 season start
                if season == 2026:
                    season_start_date = datetime(2025, 8, 15)
                    days_since_start = (today - season_start_date).days
                    
                    # Calculate deadline based on gameweek and typical Premier League schedule
                    if gameweek == 1:
                        # GW1: August 15, 2025 (Friday 6 PM deadline)
                        deadline = datetime(2025, 8, 15, 18, 0, 0)
                    elif gameweek == 2:
                        # GW2: August 22, 2025 (Friday 6 PM deadline)
                        deadline = datetime(2025, 8, 22, 18, 0, 0)
                    elif gameweek == 3:
                        # GW3: August 29, 2025 (Friday 6 PM deadline)
                        deadline = datetime(2025, 8, 29, 18, 0, 0)
                    elif gameweek == 4:
                        # GW4: September 5, 2025 (Friday 6 PM deadline)
                        deadline = datetime(2025, 9, 5, 18, 0, 0)
                    else:
                        # For later gameweeks, estimate based on weekly schedule
                        weeks_offset = gameweek - 1
                        deadline = season_start_date + timedelta(weeks=weeks_offset)
                        deadline = deadline.replace(hour=18, minute=0, second=0, microsecond=0)
                        # Adjust to Friday if not already
                        days_to_friday = (4 - deadline.weekday()) % 7
                        deadline += timedelta(days=days_to_friday)
                    
                    logger.info(f"Using calculated 2025-26 season deadline for GW{gameweek}: {deadline}")
                    return deadline
                
                # General fallback for other gameweeks
                # Premier League gameweeks typically start on weekends, but can vary:
                # - Friday evening games (8:00 PM) 
                # - Saturday early (12:30 PM) or late (5:30 PM)
                # - Sunday games (2:00 PM, 4:30 PM)
                # - Monday evening games (rare, 8:00 PM)
                
                # Calculate intelligent fallback based on current day
                if today.weekday() <= 3:  # Monday to Thursday
                    # Next gameweek likely starts Friday evening, so deadline is Friday 6 PM
                    days_until_friday = (4 - today.weekday()) % 7
                    if days_until_friday == 0 and today.hour >= 18:  # If it's Friday after 6 PM
                        days_until_friday = 7  # Next Friday
                    fallback_deadline = today + timedelta(days=days_until_friday)
                    fallback_deadline = fallback_deadline.replace(hour=18, minute=0, second=0, microsecond=0)
                    
                elif today.weekday() == 4:  # Friday
                    if today.hour < 18:  # Before 6 PM Friday
                        fallback_deadline = today.replace(hour=18, minute=0, second=0, microsecond=0)
                    else:  # After 6 PM Friday, next gameweek
                        fallback_deadline = today + timedelta(days=7)
                        fallback_deadline = fallback_deadline.replace(hour=18, minute=0, second=0, microsecond=0)
                        
                else:  # Weekend (Saturday/Sunday)
                    # Gameweek likely in progress or just finished, next one starts next Friday
                    days_until_next_friday = (4 - today.weekday() + 7) % 7
                    if days_until_next_friday == 0:
                        days_until_next_friday = 7
                    fallback_deadline = today + timedelta(days=days_until_next_friday)
                    fallback_deadline = fallback_deadline.replace(hour=18, minute=0, second=0, microsecond=0)
                
                logger.info(f"Using intelligent fallback deadline for gameweek {gameweek}: {fallback_deadline}")
                return fallback_deadline
            
            # Filter out fixtures that have already started or finished
            upcoming_fixtures = [f for f in fixtures if f['status'] in ['NS', 'TBD']]  # Not Started, To Be Determined
            
            if not upcoming_fixtures:
                logger.warning(f"No upcoming fixtures found for gameweek {gameweek}")
                # If no upcoming fixtures, try all fixtures (might be in progress)
                upcoming_fixtures = fixtures
            
            # Find earliest fixture timestamp
            try:
                valid_timestamps = [fixture['timestamp'] for fixture in upcoming_fixtures if fixture.get('timestamp')]
                if not valid_timestamps:
                    logger.error(f"No valid timestamps found in fixtures for gameweek {gameweek}")
                    return get_emergency_fallback_deadline()
                
                earliest_timestamp = min(valid_timestamps)
            except (ValueError, TypeError) as e:
                logger.error(f"Error finding earliest timestamp: {e}")
                return get_emergency_fallback_deadline()
            
            # Convert to datetime and subtract 2 hours for deadline
            try:
                match_time = datetime.fromtimestamp(earliest_timestamp)
                deadline = match_time - timedelta(hours=2)
                
                logger.info(f"Calculated deadline for gameweek {gameweek}: {deadline}")
                return deadline
            except (ValueError, OSError) as e:
                logger.error(f"Error converting timestamp to datetime: {e}")
                return get_emergency_fallback_deadline()
                
        except Exception as e:
            logger.error(f"Unexpected error calculating gameweek deadline: {e}")
            return get_emergency_fallback_deadline()
    
    def is_gameweek_active(self, gameweek, league_id=39, season=DEFAULT_SEASON):
        """Check if gameweek is currently active (matches ongoing)"""
        fixtures = self.get_gameweek_fixtures(gameweek, league_id, season)
        if not fixtures:
            return False
        
        # Check if any matches are in progress or finished but not all finished
        statuses = [fixture['status'] for fixture in fixtures]
        
        # If any match is live (1H, HT, 2H, ET, P) or some finished but not all
        active_statuses = ['1H', 'HT', '2H', 'ET', 'P', 'LIVE']
        has_active = any(status in active_statuses for status in statuses)
        has_not_started = any(status == 'NS' for status in statuses)
        
        return has_active or (has_not_started and any(status == 'FT' for status in statuses))
    
    def is_picks_allowed(self, gameweek, league_id=39, season=DEFAULT_SEASON):
        """Check if picks are allowed for current gameweek"""
        from datetime import datetime
        
        # Get deadline
        deadline = self.get_gameweek_deadline(gameweek, league_id, season)
        if not deadline:
            return True  # Allow picks if can't determine deadline
        
        # Check if we're past deadline
        if datetime.now() > deadline:
            # Past deadline - only allow if gameweek is completely finished
            return not self.is_gameweek_active(gameweek, league_id, season)
        
        # Before deadline - always allow
        return True