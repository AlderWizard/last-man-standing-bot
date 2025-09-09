import sys
import os
from datetime import datetime, timezone

# Add parent directory to path to import football_api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from last_man_standing_bot.football_api import FootballAPI

def print_fixture(fixture):
    """Print formatted fixture information"""
    home_team = fixture.get('teams', {}).get('home', {}).get('name', 'Unknown')
    away_team = fixture.get('teams', {}).get('away', {}).get('name', 'Unknown')
    home_score = fixture.get('goals', {}).get('home')
    away_score = fixture.get('goals', {}).get('away')
    status = fixture.get('fixture', {}).get('status', {}).get('short')
    
    # Format the score or time
    if home_score is not None and away_score is not None:
        score_str = f"{home_score} - {away_score}"
    else:
        # Try to get kickoff time
        try:
            kickoff = fixture.get('fixture', {}).get('date')
            if kickoff:
                dt = datetime.fromisoformat(kickoff.replace('Z', '+00:00'))
                score_str = dt.strftime('%a %d %b %H:%M')
            else:
                score_str = "Time TBD"
        except:
            score_str = "Time TBD"
    
    # Add status indicator
    status_emoji = {
        'NS': '⏰',  # Not Started
        '1H': '▶️',  # First Half
        'HT': '⏸️',  # Halftime
        '2H': '▶️',  # Second Half
        'ET': '⏳',  # Extra Time
        'P':  '⏳',  # Penalties
        'FT': '✅',  # Full Time
        'PST': '⏭️', # Postponed
        'CANC': '❌', # Cancelled
        'SUSP': '⏸️', # Suspended
        'AWD': '🏆',  # Awarded
        'ABD': '⛔'   # Abandoned
    }.get(status, f"({status})")
    
    print(f"{status_emoji} {home_team:25} {score_str:^9} {away_team}")

def track_teams(team_names=None, league_id=39, season=2025):
    """Track specific teams' matches"""
    api = FootballAPI()
    
    # Get current gameweek
    current_gw = api.get_current_gameweek()
    print(f"\n📅 Current Gameweek: {current_gw}")
    
    # Get all teams for reference
    teams = api.get_teams()
    
    # If no teams specified, show all matches for current gameweek
    if not team_names:
        print(f"\n🔍 Showing all matches for Gameweek {current_gw}")
        fixtures = api.get_gameweek_fixtures(current_gw, league_id, season)
        if not fixtures:
            print("No fixtures found for this gameweek.")
            return
            
        for fixture in fixtures:
            print_fixture(fixture)
        return
    
    # Track specific teams
    for team_name in team_names:
        team_id = None
        
        # Find team ID by name (case-insensitive)
        for id, name in teams.items():
            if team_name.lower() in name.lower():
                team_id = id
                team_name = name  # Use the exact name from API
                break
        
        if not team_id:
            print(f"\n❌ Team '{team_name}' not found. Available teams:")
            print(", ".join(teams.values()))
            continue
            
        print(f"\n🔍 Tracking {team_name} (ID: {team_id})")
        print("-" * 50)
        
        # Get team's next match
        next_match = api.get_next_match(team_id, league_id, season)
        if next_match:
            print("\n⏭️  NEXT MATCH:")
            print_fixture(next_match)
        else:
            print("\nℹ️  No upcoming matches found")
        
        # Get team's last match
        last_match = api.get_last_match(team_id, league_id, season)
        if last_match:
            print("\n⏮️  LAST MATCH:")
            print_fixture(last_match)
        
        # Get team's next 5 fixtures
        upcoming = api.get_team_fixtures(team_id, league_id, season, next=5)
        if upcoming:
            print("\n📅 NEXT 5 FIXTURES:")
            for fixture in upcoming[:5]:  # Limit to next 5
                print_fixture(fixture)

if __name__ == "__main__":
    # Example usage:
    # python track_teams.py "Manchester United" "Manchester City"
    # Or with no arguments to see all matches for current gameweek
    
    if len(sys.argv) > 1:
        track_teams(sys.argv[1:])
    else:
        track_teams()
