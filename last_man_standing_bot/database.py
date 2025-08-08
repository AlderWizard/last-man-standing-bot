import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = 'lastman.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Add new columns to existing users table if they don't exist
                try:
                    cursor.execute('ALTER TABLE users ADD COLUMN first_name TEXT')
                except sqlite3.OperationalError:
                    pass  # Column already exists
                
                try:
                    cursor.execute('ALTER TABLE users ADD COLUMN last_name TEXT')
                except sqlite3.OperationalError:
                    pass  # Column already exists
                
                # Picks table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS picks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        round_number INTEGER,
                        team_name TEXT NOT NULL,
                        team_id INTEGER,
                        match_id INTEGER,
                        result TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
                
                # Groups table for tracking which groups the bot is in
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS groups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER UNIQUE NOT NULL,
                        chat_title TEXT,
                        chat_type TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        rollover_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Competition tracking table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS competitions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        season INTEGER UNIQUE NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ended_at TIMESTAMP NULL
                    )
                ''')
                
                # Blocked teams table for tracking teams users can't use after changing picks (per competition)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS blocked_teams (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        team_id INTEGER,
                        team_name TEXT,
                        competition_id INTEGER,
                        blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (competition_id) REFERENCES competitions(id)
                    )
                ''')
                
                # Add competition_id to picks table if it doesn't exist
                try:
                    cursor.execute('ALTER TABLE picks ADD COLUMN competition_id INTEGER')
                except sqlite3.OperationalError:
                    pass  # Column already exists
                
                # Add chat_id to picks table for group isolation
                try:
                    cursor.execute('ALTER TABLE picks ADD COLUMN chat_id INTEGER')
                except sqlite3.OperationalError:
                    pass  # Column already exists
                
                # Add chat_id to blocked_teams table for group isolation
                try:
                    cursor.execute('ALTER TABLE blocked_teams ADD COLUMN chat_id INTEGER')
                except sqlite3.OperationalError:
                    pass  # Column already exists
                
                # Add chat_id to winners table for group isolation
                try:
                    cursor.execute('ALTER TABLE winners ADD COLUMN chat_id INTEGER')
                except sqlite3.OperationalError:
                    pass  # Column already exists
                
                # Winners table for tracking competition winners
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS winners (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        competition_id INTEGER,
                        won_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (competition_id) REFERENCES competitions(id)
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add a new user or update existing one"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error adding user: {e}")
            raise
    
    def add_pick(self, user_id: int, round_number: int, team_name: str, team_id: int, match_id: int, chat_id: int):
        """Add a pick for a user in the current competition for a specific group"""
        try:
            competition_id = self.get_current_competition_id()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO picks (user_id, round_number, team_name, team_id, match_id, competition_id, chat_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, round_number, team_name, team_id, match_id, competition_id, chat_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error adding pick: {e}")
            raise
    
    def has_used_team(self, user_id: int, team_id: int, chat_id: int) -> bool:
        """Check if user has already used this team or if it's blocked in current competition for this group"""
        try:
            competition_id = self.get_current_competition_id()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if team was used in picks for current competition in this group
                cursor.execute('''
                    SELECT COUNT(*) FROM picks 
                    WHERE user_id = ? AND team_id = ? AND chat_id = ? AND (competition_id = ? OR competition_id IS NULL)
                ''', (user_id, team_id, chat_id, competition_id))
                picks_count = cursor.fetchone()[0]
                
                # Check if team is blocked in current competition for this group
                cursor.execute('''
                    SELECT COUNT(*) FROM blocked_teams 
                    WHERE user_id = ? AND team_id = ? AND chat_id = ? AND competition_id = ?
                ''', (user_id, team_id, chat_id, competition_id))
                blocked_count = cursor.fetchone()[0]
                
                return picks_count > 0 or blocked_count > 0
        except sqlite3.Error as e:
            logger.error(f"Error checking team usage: {e}")
            return False
    
    def get_user_picks(self, user_id: int):
        """Get all picks for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT round_number, team_name, result
                    FROM picks 
                    WHERE user_id = ?
                    ORDER BY round_number
                ''', (user_id,))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting user picks: {e}")
            return []
    
    def get_current_survivors(self, chat_id: int = None):
        """Get users who are still active (globally or in a specific group context)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if chat_id is None:
                    # Global survivors (for backward compatibility)
                    cursor.execute('''
                        SELECT user_id, username
                        FROM users 
                        WHERE is_active = 1
                    ''')
                else:
                    # For group-specific context, return all active users
                    # The group isolation happens at the picks/blocked_teams level, not user level
                    cursor.execute('''
                        SELECT user_id, username
                        FROM users 
                        WHERE is_active = 1
                    ''')
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting survivors: {e}")
            return []
    
    def eliminate_user(self, user_id: int):
        """Mark a user as eliminated"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET is_active = 0 WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error eliminating user: {e}")
            raise
    
    def get_user(self, user_id: int):
        """Get user information by user_id"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, is_active, created_at
                    FROM users 
                    WHERE user_id = ?
                ''', (user_id,))
                return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_pick_for_round(self, user_id: int, round_number: int):
        """Get user's pick for a specific round"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT team_name, team_id, result
                    FROM picks 
                    WHERE user_id = ? AND round_number = ?
                ''', (user_id, round_number))
                return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error getting user pick for round: {e}")
            return None
    
    def add_group(self, chat_id: int, chat_title: str = None, chat_type: str = None):
        """Add or update a group chat"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO groups (chat_id, chat_title, chat_type)
                    VALUES (?, ?, ?)
                ''', (chat_id, chat_title, chat_type))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error adding group: {e}")
    
    def get_active_groups(self):
        """Get all active group chats"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT chat_id, chat_title, chat_type
                    FROM groups 
                    WHERE is_active = 1
                ''')
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting active groups: {e}")
            return []
    
    def get_users_without_picks(self, round_number: int):
        """Get active users who haven't made picks for this round"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.user_id, u.username
                    FROM users u
                    WHERE u.is_active = 1
                    AND u.user_id NOT IN (
                        SELECT p.user_id 
                        FROM picks p 
                        WHERE p.round_number = ?
                    )
                ''', (round_number,))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting users without picks: {e}")
            return []
    
    def get_users_with_picks_for_round(self, round_number: int, chat_id: int):
        """Get all users who made picks for this round in a specific group"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT u.user_id, u.username, u.first_name, u.last_name
                    FROM users u
                    JOIN picks p ON u.user_id = p.user_id
                    WHERE p.round_number = ? AND p.chat_id = ? AND u.is_active = 1
                ''', (round_number, chat_id))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting users with picks for round: {e}")
            return []
    
    def block_team_for_user(self, user_id: int, team_id: int, team_name: str, chat_id: int):
        """Block a team for a user in the current competition for a specific group"""
        try:
            competition_id = self.get_current_competition_id()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO blocked_teams (user_id, team_id, team_name, competition_id, chat_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, team_id, team_name, competition_id, chat_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error blocking team for user: {e}")
            raise
    
    def is_team_blocked(self, user_id: int, team_id: int, chat_id: int) -> bool:
        """Check if a team is blocked for a user in the current competition for a specific group"""
        try:
            competition_id = self.get_current_competition_id()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM blocked_teams 
                    WHERE user_id = ? AND team_id = ? AND competition_id = ? AND chat_id = ?
                ''', (user_id, team_id, competition_id, chat_id))
                count = cursor.fetchone()[0]
                return count > 0
        except sqlite3.Error as e:
            logger.error(f"Error checking if team is blocked: {e}")
            return False
    
    def change_user_pick(self, user_id: int, round_number: int, new_team_name: str, new_team_id: int, new_match_id: int, chat_id: int):
        """Change a user's pick for a round and block the old team in current competition for a specific group"""
        try:
            competition_id = self.get_current_competition_id()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get the old pick first
                cursor.execute('''
                    SELECT team_name, team_id FROM picks 
                    WHERE user_id = ? AND round_number = ? AND chat_id = ? AND (competition_id = ? OR competition_id IS NULL)
                ''', (user_id, round_number, chat_id, competition_id))
                old_pick = cursor.fetchone()
                
                if old_pick:
                    old_team_name, old_team_id = old_pick
                    
                    # Block the old team in current competition for this group
                    cursor.execute('''
                        INSERT INTO blocked_teams (user_id, team_id, team_name, competition_id, chat_id)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, old_team_id, old_team_name, competition_id, chat_id))
                    
                    # Update the pick
                    cursor.execute('''
                        UPDATE picks 
                        SET team_name = ?, team_id = ?, match_id = ?, competition_id = ?
                        WHERE user_id = ? AND round_number = ? AND chat_id = ? AND (competition_id = ? OR competition_id IS NULL)
                    ''', (new_team_name, new_team_id, new_match_id, competition_id, user_id, round_number, chat_id, competition_id))
                    
                    conn.commit()
                    return old_team_name
                else:
                    # No existing pick to change
                    return None
                    
        except sqlite3.Error as e:
            logger.error(f"Error changing user pick: {e}")
            raise
    
    def get_current_competition_id(self):
        """Get the current active competition ID, create one if none exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM competitions 
                    WHERE is_active = 1
                    ORDER BY id DESC LIMIT 1
                ''')
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                else:
                    # Create new competition for current season
                    from datetime import datetime
                    current_year = datetime.now().year
                    cursor.execute('''
                        INSERT INTO competitions (season, is_active)
                        VALUES (?, 1)
                    ''', (current_year,))
                    conn.commit()
                    return cursor.lastrowid
                    
        except sqlite3.Error as e:
            logger.error(f"Error getting current competition: {e}")
            return 1  # Fallback
    
    def add_winner(self, user_id: int, chat_id: int, competition_id: int = None):
        """Add a winner for a competition in a specific group"""
        try:
            if competition_id is None:
                competition_id = self.get_current_competition_id()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO winners (user_id, competition_id, chat_id)
                    VALUES (?, ?, ?)
                ''', (user_id, competition_id, chat_id))
                conn.commit()
                logger.info(f"Added winner: user {user_id} for competition {competition_id} in group {chat_id}")
        except sqlite3.Error as e:
            logger.error(f"Error adding winner: {e}")
            raise
    
    def get_winner_stats(self, chat_id: int):
        """Get winner statistics for all users in a specific group"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.user_id, u.username, u.first_name, u.last_name, COUNT(w.id) as wins
                    FROM users u
                    LEFT JOIN winners w ON u.user_id = w.user_id AND w.chat_id = ?
                    WHERE w.chat_id = ? OR w.chat_id IS NULL
                    GROUP BY u.user_id, u.username, u.first_name, u.last_name
                    HAVING COUNT(w.id) > 0
                    ORDER BY wins DESC, u.first_name ASC
                ''', (chat_id, chat_id))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting winner stats: {e}")
            return []
    
    def reset_competition(self):
        """Reset the competition - reactivate all users, clear picks and blocked teams"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # End current competition
                cursor.execute('''
                    UPDATE competitions 
                    SET is_active = 0, ended_at = CURRENT_TIMESTAMP
                    WHERE is_active = 1
                ''')
                
                # Create new competition
                from datetime import datetime
                current_year = datetime.now().year
                cursor.execute('''
                    INSERT INTO competitions (season, is_active)
                    VALUES (?, 1)
                ''', (current_year,))
                new_competition_id = cursor.lastrowid
                
                # Reactivate all users
                cursor.execute('''
                    UPDATE users SET is_active = 1
                ''')
                
                conn.commit()
                logger.info(f"Competition reset! New competition ID: {new_competition_id}")
                return new_competition_id
                
        except sqlite3.Error as e:
            logger.error(f"Error resetting competition: {e}")
            raise
    
    def get_display_name(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Get formatted display name for a user"""
        # If we don't have the name info, try to get it from database
        if first_name is None or last_name is None:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT username, first_name, last_name
                        FROM users WHERE user_id = ?
                    ''', (user_id,))
                    result = cursor.fetchone()
                    if result:
                        username, first_name, last_name = result
            except sqlite3.Error as e:
                logger.error(f"Error getting user display name: {e}")
        
        # Build display name with fallbacks
        display_parts = []
        if first_name:
            display_parts.append(first_name)
        if last_name:
            display_parts.append(last_name)
        
        if display_parts:
            display_name = " ".join(display_parts)
            # Add username in parentheses if available
            if username:
                return f"{display_name} (@{username})"
            else:
                return display_name
        elif username:
            return f"@{username}"
        else:
            return f"User {user_id}"
    
    def get_rollover_count(self, chat_id: int):
        """Get the current rollover count for a group"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT rollover_count FROM groups WHERE chat_id = ?
                ''', (chat_id,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Error getting rollover count: {e}")
            return 0
    
    def increment_rollover(self, chat_id: int):
        """Increment the rollover count for a group"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE groups 
                    SET rollover_count = rollover_count + 1
                    WHERE chat_id = ?
                ''', (chat_id,))
                conn.commit()
                logger.info(f"Incremented rollover count for group {chat_id}")
        except sqlite3.Error as e:
            logger.error(f"Error incrementing rollover: {e}")
            raise
    
    def reset_rollover(self, chat_id: int):
        """Reset the rollover count for a group (when competition resets)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE groups 
                    SET rollover_count = 0
                    WHERE chat_id = ?
                ''', (chat_id,))
                conn.commit()
                logger.info(f"Reset rollover count for group {chat_id}")
        except sqlite3.Error as e:
            logger.error(f"Error resetting rollover: {e}")
            raise
    
    def calculate_pot_value(self, chat_id: int):
        """Calculate the current pot value based on rollover count and active players"""
        try:
            rollover_count = self.get_rollover_count(chat_id)
            survivors = self.get_current_survivors(chat_id)
            player_count = len(survivors)
            
            if rollover_count == 0:
                # Base pot: £2 per player
                pot_value = player_count * 2
            elif rollover_count == 1:
                # First rollover: £5 per player
                pot_value = player_count * 5
            else:
                # Subsequent rollovers: £5 + (rollover_count - 1) * £5 per player
                pot_per_player = 5 + ((rollover_count - 1) * 5)
                pot_value = player_count * pot_per_player
            
            return pot_value, player_count, rollover_count
        except Exception as e:
            logger.error(f"Error calculating pot value: {e}")
            return 0, 0, 0
    
    def get_users_with_picks_for_round(self, round_number: int, chat_id: int):
        """Get all users who made picks for this round in a specific group"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current competition ID
                competition_id = self.get_current_competition_id()
                
                cursor.execute('''
                    SELECT DISTINCT p.user_id, u.username, u.first_name, u.last_name
                    FROM picks p
                    JOIN users u ON p.user_id = u.user_id
                    WHERE p.round_number = ? AND p.chat_id = ? AND p.competition_id = ?
                    AND u.is_active = 1
                ''', (round_number, chat_id, competition_id))
                
                users = []
                for row in cursor.fetchall():
                    user_id, username, first_name, last_name = row
                    display_name = self.get_display_name(user_id, username, first_name, last_name)
                    users.append({
                        'user_id': user_id,
                        'username': username,
                        'first_name': first_name,
                        'last_name': last_name,
                        'display_name': display_name
                    })
                
                return users
                
        except Exception as e:
            logger.error(f"Error getting users with picks for round {round_number}: {e}")
            return []