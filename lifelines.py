"""
Lifelines module for Last Man Standing Bot
Handles all lifeline-related functionality
"""
import json
import random
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class LifelineManager:
    """Manages lifelines for players"""
    
    LIFELINES = {
        'coinflip': {
            'name': 'Coinflip',
            'description': '50% chance to revive and re-enter the current round',
            'usage_limit': 1  # Per season
        },
        'goodluck': {
            'name': 'Good Luck',
            'description': 'Pick another player to choose from bottom 6 teams',
            'usage_limit': 1
        },
        'forcechange': {
            'name': 'Force Change',
            'usage_limit': 1
        }
    }
    
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self._init_tables()
    
    def _init_tables(self):
        """Initialize lifeline tables in the database"""
        cursor = self.db_conn.cursor()
        
        # Lifeline usage tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lifeline_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                league_id TEXT NOT NULL,
                lifeline_type TEXT NOT NULL,
                season TEXT NOT NULL,
                used_at TEXT NOT NULL,
                target_user_id TEXT,
                details TEXT,
                UNIQUE(chat_id, user_id, league_id, season, lifeline_type)
            )
        ''')
        
        # Track team assignments when Force Change is used
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS force_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                league_id TEXT NOT NULL,
                original_team TEXT NOT NULL,
                new_team TEXT NOT NULL,
                gameweek INTEGER NOT NULL,
                used_at TEXT NOT NULL,
                season TEXT NOT NULL,
                target_user_id INTEGER
            )
        ''')
        
        self.db_conn.commit()
    
    def get_available_lifelines(self, chat_id: int, user_id: int, league_id: str, season: str) -> Dict:
        """Get available lifelines for a user in a league"""
        cursor = self.db_conn.cursor()
        
        # Get used lifelines for this user/league/season
        cursor.execute('''
            SELECT lifeline_type, COUNT(*) as used_count 
            FROM lifeline_usage 
            WHERE user_id = ? AND league_id = ? AND season = ?
            GROUP BY lifeline_type
        ''', (user_id, league_id, season))
        
        used_lifelines = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Calculate remaining lifelines
        available = {}
        for lifeline_id, lifeline in self.LIFELINES.items():
            used = used_lifelines.get(lifeline_id, 0)
            remaining = max(0, lifeline['usage_limit'] - used)
            
            available[lifeline_id] = {
                'name': lifeline['name'],
                'description': lifeline.get('description', ''),
                'remaining': remaining,
                'total_allowed': lifeline['usage_limit']
            }
        
        return available
    
    def use_lifeline(self, chat_id: int, user_id: int, league_id: str, 
                    lifeline_type: str, season: str, 
                    target_user_id: Optional[int] = None, 
                    details: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Attempt to use a lifeline
        Returns (success: bool, message: str)
        """
        if lifeline_type not in self.LIFELINES:
            return False, "❌ Invalid lifeline type"
        
        # Check if user has lifelines remaining
        available = self.get_available_lifelines(chat_id, user_id, league_id, season)
        if available[lifeline_type]['remaining'] <= 0:
            return False, f"❌ You've already used all your {self.LIFELINES[lifeline_type]['name']} lifelines this season"
        
        try:
            # Handle specific lifeline logic
            if lifeline_type == 'coinflip':
                success = random.random() < 0.5
                if success:
                    message = "🎉 Heads! You've been revived and can continue in the current round!"
                else:
                    message = "😢 Tails! The lifeline didn't work. Better luck next time!"
                
                # Record the lifeline usage regardless of success
                self._record_lifeline_usage(chat_id, user_id, league_id, lifeline_type, season, target_user_id, details)
                return success, message
                
            elif lifeline_type == 'goodluck':
                if not target_user_id:
                    return False, "❌ Please specify a target user for this lifeline"
                
                # Get bottom 6 teams (this would need to be implemented)
                bottom_teams = self._get_bottom_teams(league_id, season)
                details = {'bottom_teams': bottom_teams}
                
                self._record_lifeline_usage(chat_id, user_id, league_id, lifeline_type, season, target_user_id, details)
                return True, f"🎯 {target_user_id} must pick a team from the bottom 6: {', '.join(bottom_teams)}"
                
            elif lifeline_type == 'forcechange':
                # Get the target user's current team
                current_team = self._get_user_team(chat_id, target_user_id, league_id, season)
                if not current_team:
                    return False, "❌ Could not find the target user's current team"
                
                # Record the force change
                # Get current gameweek (you'll need to implement this or pass it in)
                current_gameweek = 1  # Default to 1, should be replaced with actual gameweek
                self._record_force_change(
                    chat_id=chat_id,
                    user_id=user_id,
                    league_id=league_id,
                    original_team=current_team,
                    new_team=None,
                    season=season,
                    gameweek=current_gameweek,
                    target_user_id=target_user_id
                )
                return True, f"🔄 {target_user_id} has been forced to change their team for the next round"
                
        except Exception as e:
            logger.error(f"Error using lifeline: {e}")
            return False, f"❌ An error occurred: {str(e)}"
    
    def _record_lifeline_usage(self, chat_id: int, user_id: int, league_id: str, 
                             lifeline_type: str, season: str, 
                             target_user_id: Optional[int] = None,
                             details: Optional[Dict] = None):
        """Record lifeline usage in the database"""
        cursor = self.db_conn.cursor()
        cursor.execute('''
            INSERT INTO lifeline_usage 
            (chat_id, user_id, league_id, lifeline_type, season, used_at, target_user_id, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chat_id, 
            user_id, 
            league_id, 
            lifeline_type, 
            season,
            datetime.now().isoformat(),
            target_user_id,
            json.dumps(details) if details else None
        ))
        self.db_conn.commit()
    
    def _record_force_change(self, chat_id: int, user_id: int, league_id: str, 
                           original_team: str, new_team: Optional[str], 
                           season: str, gameweek: int, target_user_id: Optional[int] = None) -> bool:
        """Record a force change action"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO force_changes 
                (chat_id, user_id, league_id, original_team, new_team, gameweek, used_at, season, target_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chat_id,
                user_id,
                league_id,
                original_team,
                new_team if new_team is not None else "",  # Provide empty string as default
                gameweek,
                datetime.now().isoformat(),
                season,
                target_user_id
            ))
            self.db_conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error recording force change: {e}")
            return False
    
    def _get_bottom_teams(self, league_id: str, season: str) -> List[str]:
        """Get the current bottom 6 teams in the league"""
        # This would need to be implemented to fetch actual standings
        # For now, return placeholder
        return ["Team A", "Team B", "Team C", "Team D", "Team E", "Team F"]
    
    def _get_user_team(self, chat_id: int, user_id: int, league_id: str, season: str) -> Optional[str]:
        """Get a user's current team"""
        # This would need to be implemented to fetch from your existing team tracking
        return None  # Replace with actual implementation
        
    def get_force_changes(self, chat_id: int, league_id: str, gameweek: int) -> List[Dict]:
        """Get all force changes for a specific chat, league, and gameweek"""
        cursor = self.db_conn.cursor()
        cursor.execute('''
            SELECT id, user_id, target_user_id, original_team, new_team, used_at
            FROM force_changes
            WHERE chat_id = ? AND league_id = ? AND gameweek = ?
        ''', (chat_id, league_id, gameweek))
        
        columns = ['id', 'user_id', 'target_user_id', 'original_team', 'new_team', 'used_at']
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_season(self) -> str:
        """Get current season in YYYY-YY format"""
        now = datetime.now()
        if now.month >= 8:  # August or later
            return f"{now.year}-{str(now.year + 1)[2:]}"
        else:
            return f"{now.year - 1}-{str(now.year)[2:]}"
