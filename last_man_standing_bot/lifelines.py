"""
Lifelines module for Last Man Standing Bot
Handles all lifeline-related functionality
"""
import json
import random
import traceback
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import logging
from sqlalchemy import text, exc

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
        try:
            with self.db_conn.connect() as conn:
                # Lifeline usage tracking
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS lifeline_usage (
                        id SERIAL PRIMARY KEY,
                        chat_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        league_id TEXT NOT NULL,
                        lifeline_type TEXT NOT NULL,
                        season TEXT NOT NULL,
                        used_at TIMESTAMP NOT NULL,
                        target_user_id BIGINT,
                        details TEXT,
                        UNIQUE(chat_id, user_id, league_id, season, lifeline_type)
                    )
                '''))
                
                # Track team assignments when Force Change is used
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS force_changes (
                        id SERIAL PRIMARY KEY,
                        chat_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        league_id TEXT NOT NULL,
                        original_team TEXT NOT NULL,
                        new_team TEXT,
                        gameweek INTEGER NOT NULL,
                        used_at TIMESTAMP NOT NULL,
                        season TEXT NOT NULL,
                        target_user_id BIGINT
                    )
                '''))
                conn.commit()
        except exc.SQLAlchemyError as e:
            logger.error(f"Error initializing lifeline tables: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def get_available_lifelines(self, chat_id: int, user_id: int, league_id: str, season: str) -> Dict:
        """Get available lifelines for a user in a league"""
        try:
            with self.db_conn.connect() as conn:
                # Get used lifelines for this user/league/season
                result = conn.execute(
                    text('''
                        SELECT lifeline_type, COUNT(*) as used_count 
                        FROM lifeline_usage 
                        WHERE chat_id = :chat_id AND user_id = :user_id AND league_id = :league_id AND season = :season
                        GROUP BY lifeline_type
                    '''),
                    {
                        'chat_id': chat_id,
                        'user_id': user_id, 
                        'league_id': league_id, 
                        'season': season
                    }
                )
                
                used_lifelines = {row[0]: row[1] for row in result.fetchall()}
                
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
        except exc.SQLAlchemyError as e:
            logger.error(f"Error getting available lifelines: {e}")
            logger.error(traceback.format_exc())
            # Return empty dict on error to avoid breaking the command
            return {}
    
    def use_lifeline(self, chat_id: int, user_id: int, league_id: str, 
                    lifeline_type: str, season: str, 
                    target_user_id: Optional[int] = None, 
                    details: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Attempt to use a lifeline
        
        Args:
            chat_id: The chat ID where the lifeline is being used
            user_id: The user ID using the lifeline
            league_id: The league ID where the lifeline is being used
            lifeline_type: Type of lifeline (must be in LIFELINES)
            season: The current season (e.g., '2023-2024')
            target_user_id: For lifelines that target another user (like Good Luck)
            details: Additional details about the lifeline usage
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        from sqlalchemy import text
        import json
        
        if lifeline_type not in self.LIFELINES:
            return False, "❌ Invalid lifeline type."
            
        # Check if user has any remaining uses of this lifeline
        available = self.get_available_lifelines(chat_id, user_id, league_id, season)
        if available[lifeline_type]['remaining'] <= 0:
            return False, f"❌ You've already used all your {self.LIFELINES[lifeline_type]['name']} lifelines this season."
        
        # Record the lifeline usage
        with self.db_conn.connect() as conn:
            try:
                conn.execute(
                    text('''
                        INSERT INTO lifeline_usage 
                        (chat_id, user_id, league_id, lifeline_type, season, used_at, target_user_id, details)
                        VALUES (:chat_id, :user_id, :league_id, :lifeline_type, :season, NOW(), :target_user_id, :details)
                    '''),
                    {
                        'chat_id': chat_id,
                        'user_id': user_id,
                        'league_id': league_id,
                        'lifeline_type': lifeline_type,
                        'season': season,
                        'target_user_id': target_user_id,
                        'details': json.dumps(details) if details else None
                    }
                )
                
                # Handle lifeline-specific logic
                if lifeline_type == 'coinflip':
                    if random.random() < 0.5:  # 50% chance
                        return True, "🎉 Heads! You've been revived and are back in the game!"
                    else:
                        return True, "💀 Tails! Better luck next time!"
                        
                elif lifeline_type == 'goodluck':
                    if not target_user_id:
                        return False, "❌ Please specify a target user for the Good Luck lifeline."
                    return True, f"✨ Good Luck has been cast on user {target_user_id}!"
                    
                elif lifeline_type == 'forcechange':
                    if not details or 'original_team' not in details or 'new_team' not in details:
                        return False, "❌ Invalid details for Force Change. Please specify original_team and new_team."
                    self._record_force_change(
                        chat_id=chat_id,
                        user_id=user_id,
                        league_id=league_id,
                        original_team=details['original_team'],
                        new_team=details['new_team'],
                        season=season,
                        gameweek=1,  # Replace with actual gameweek
                        target_user_id=target_user_id
                    )
                    return True, "🔄 Team change forced successfully!"
                    
                conn.commit()
                return True, f"✅ {self.LIFELINES[lifeline_type]['name']} lifeline used successfully!"
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Error using lifeline: {e}")
                return False, "❌ An error occurred while using the lifeline. Please try again."
    
    def _record_lifeline_usage(self, chat_id: int, user_id: int, league_id: str, 
                             lifeline_type: str, season: str, 
                             target_user_id: Optional[int] = None,
                             details: Optional[Dict] = None) -> bool:
        """
        Record lifeline usage in the database
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.db_conn.connect() as conn:
                conn.execute(
                    text('''
                        INSERT INTO lifeline_usage 
                        (chat_id, user_id, league_id, lifeline_type, season, used_at, target_user_id, details)
                        VALUES (:chat_id, :user_id, :league_id, :lifeline_type, :season, NOW(), :target_user_id, :details)
                    '''),
                    {
                        'chat_id': chat_id,
                        'user_id': user_id,
                        'league_id': league_id,
                        'lifeline_type': lifeline_type,
                        'season': season,
                        'target_user_id': target_user_id,
                        'details': json.dumps(details) if details else None
                    }
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error recording lifeline usage: {e}")
            return False
    
    def _record_force_change(self, chat_id: int, user_id: int, league_id: str, 
                           original_team: str, new_team: Optional[str], 
                           season: str, gameweek: int, target_user_id: Optional[int] = None) -> bool:
        """Record a force change action"""
        from sqlalchemy import text
        
        try:
            with self.db_conn.connect() as conn:
                conn.execute(
                    text('''
                        INSERT INTO force_changes 
                        (chat_id, user_id, league_id, original_team, new_team, gameweek, used_at, season, target_user_id)
                        VALUES (:chat_id, :user_id, :league_id, :original_team, :new_team, :gameweek, NOW(), :season, :target_user_id)
                    '''),
                    {
                        'chat_id': chat_id,
                        'user_id': user_id,
                        'league_id': league_id,
                        'original_team': original_team,
                        'new_team': new_team,
                        'gameweek': gameweek,
                        'season': season,
                        'target_user_id': target_user_id
                    }
                )
                conn.commit()
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
        """
        Get all force changes for a specific chat, league, and gameweek
        
        Returns:
            List[Dict]: List of force change records, or empty list on error
        """
        try:
            with self.db_conn.connect() as conn:
                result = conn.execute(
                    text('''
                        SELECT id, user_id, target_user_id, original_team, new_team, used_at
                        FROM force_changes
                        WHERE chat_id = :chat_id AND league_id = :league_id AND gameweek = :gameweek
                    '''),
                    {
                        'chat_id': chat_id,
                        'league_id': league_id,
                        'gameweek': gameweek
                    }
                )
                
                columns = ['id', 'user_id', 'target_user_id', 'original_team', 'new_team', 'used_at']
                return [dict(zip(columns, row)) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting force changes: {e}")
            return []

    def get_season(self) -> str:
        """Get current season in YYYY-YY format"""
        now = datetime.now()
        if now.month >= 8:  # August or later
            return f"{now.year}-{str(now.year + 1)[2:]}"
        else:
            return f"{now.year - 1}-{str(now.year)[2:]}"
