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
        """Get current gameweek information based on current date and Premier League schedule"""
        from datetime import datetime, timedelta
        
        try:
            # First, try to determine gameweek based on current date and known season structure
            now = datetime.now()
            
            # Premier League 2024-25 season started August 17, 2024
            # Premier League 2025-26 season starts August 15, 2025
            if season == 2025:  # 2024-25 season
                season_start = datetime(2024, 8, 17)
            elif season == 2026:  # 2025-26 season  
                season_start = datetime(2025, 8, 15)
            else:
                # For other seasons, try API approach as fallback
                return self._get_gameweek_from_api(league_id, season)
            
            # Calculate weeks since season start
            if now < season_start:
                return 1  # Season hasn't started yet
            
            # More accurate gameweek calculation based on Premier League schedule
            # Premier League typically has gameweeks every 7-10 days during the season
            days_elapsed = (now - season_start).days
            
            # Calculate gameweek based on deadlines, not just days
            # Check each gameweek's deadline to determine current gameweek
            estimated_gameweek = 1
            
            # Define gameweek deadlines for 2025-26 season
            gameweek_deadlines = {
                1: datetime(2025, 8, 15, 18, 0, 0),  # GW1: Friday Aug 15, 6 PM
                2: datetime(2025, 8, 22, 18, 0, 0),  # GW2: Friday Aug 22, 6 PM  
                3: datetime(2025, 8, 29, 18, 0, 0),  # GW3: Friday Aug 29, 6 PM
                4: datetime(2025, 9, 5, 18, 0, 0),   # GW4: Friday Sep 5, 6 PM
            }
            
            # Find the current gameweek based on which deadline we're closest to
            for gw in range(1, 39):  # Check all possible gameweeks
                if gw in gameweek_deadlines:
                    deadline = gameweek_deadlines[gw]
                else:
                    # For gameweeks beyond predefined ones, estimate weekly
                    weeks_offset = gw - 1
                    deadline = datetime(2025, 8, 15) + timedelta(weeks=weeks_offset)
                    deadline = deadline.replace(hour=18, minute=0, second=0, microsecond=0)
                    # Adjust to Friday
                    days_to_friday = (4 - deadline.weekday()) % 7
                    deadline += timedelta(days=days_to_friday)
                
                # If we haven't reached this gameweek's deadline yet, this is the current gameweek
                if now <= deadline:
                    estimated_gameweek = gw
                    break
                # If we've passed this deadline, we're in the next gameweek
                else:
                    estimated_gameweek = min(gw + 1, 38)
                    # Continue to check if there are more gameweeks to process
            
            logger.info(f"Days since season start ({season_start.date()}): {days_elapsed}, estimated gameweek: {estimated_gameweek}")
            
            # Now verify this estimate by checking fixtures around this gameweek
            for gw_check in range(max(1, estimated_gameweek - 1), min(39, estimated_gameweek + 3)):
                fixtures = self.get_gameweek_fixtures(gw_check, league_id, season)
                if fixtures:
                    # Check if this gameweek is currently active or upcoming
                    current_statuses = [f['status'] for f in fixtures]
                    
                    # If gameweek has matches that haven't started yet, or are in progress
                    if any(status in ['NS', 'TBD', '1H', 'HT', '2H', 'ET', 'P', 'LIVE'] for status in current_statuses):
                        # Check if deadline has passed for this gameweek
                        deadline = self.get_gameweek_deadline(gw_check, league_id, season)
                        if deadline and now <= deadline:
                            # We're before the deadline, this is the current gameweek for picks
                            logger.info(f"Current gameweek for picks: {gw_check} (deadline: {deadline})")
                            return gw_check
                        elif deadline and now > deadline:
                            # Past deadline but matches ongoing/upcoming - still current gameweek
                            if any(status in ['NS', 'TBD', '1H', 'HT', '2H', 'ET', 'P', 'LIVE'] for status in current_statuses):
                                logger.info(f"Current gameweek (past deadline): {gw_check}")
                                return gw_check
                    
                    # If all matches are finished, check next gameweek
                    if all(status == 'FT' for status in current_statuses):
                        continue
            
            # Fallback to estimated gameweek if API checks don't give clear answer
            logger.info(f"Using estimated gameweek: {estimated_gameweek}")
            return estimated_gameweek
            
        except Exception as e:
            logger.warning(f"Error in date-based gameweek calculation: {e}")
            # Fallback to API-based approach
            return self._get_gameweek_from_api(league_id, season)
    
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
        """Get pick deadline for gameweek (2 hours before first match)"""
        from datetime import datetime, timedelta
        
        def get_emergency_fallback_deadline():
            """Emergency fallback when all else fails - returns a reasonable deadline"""
            today = datetime.now()
            
            # Special handling for 2025-26 season start
            if season == 2026 and gameweek == 1:
                # 2025-26 Premier League season starts Friday August 15th, 2025
                season_start = datetime(2025, 8, 15, 18, 0, 0)  # Friday 6 PM deadline
                logger.info(f"Using emergency fallback for 2025-26 season start: {season_start}")
                return season_start
            
            # General emergency fallback - next Friday 6 PM
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0 and today.hour >= 18:  # If it's Friday after 6 PM
                days_until_friday = 7  # Next Friday
            emergency_deadline = today + timedelta(days=days_until_friday)
            emergency_deadline = emergency_deadline.replace(hour=18, minute=0, second=0, microsecond=0)
            
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