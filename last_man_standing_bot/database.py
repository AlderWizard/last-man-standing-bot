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
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
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
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def add_user(self, user_id: int, username: str = None):
        """Add a new user or update existing one"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username)
                    VALUES (?, ?)
                ''', (user_id, username))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error adding user: {e}")
            raise
    
    def add_pick(self, user_id: int, round_number: int, team_name: str, team_id: int, match_id: int):
        """Add a pick for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO picks (user_id, round_number, team_name, team_id, match_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, round_number, team_name, team_id, match_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error adding pick: {e}")
            raise
    
    def has_used_team(self, user_id: int, team_id: int) -> bool:
        """Check if user has already used this team"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM picks 
                    WHERE user_id = ? AND team_id = ?
                ''', (user_id, team_id))
                count = cursor.fetchone()[0]
                return count > 0
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
    
    def get_current_survivors(self):
        """Get users who are still active"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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