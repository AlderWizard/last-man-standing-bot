#!/usr/bin/env python3
"""
Database module for FPL Bot
Handles persistent storage of league data, speech reminders, and records
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class FPLDatabase:
    def __init__(self, db_path: str = "fpl_bot.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.init_database()
        
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        cursor = self.conn.cursor()
        
        # Leagues table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leagues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                league_id TEXT NOT NULL,
                league_name TEXT NOT NULL,
                added_date TEXT NOT NULL,
                UNIQUE(chat_id, league_id)
            )
        ''')
            
        # Speech reminders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS speech_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                league_id TEXT NOT NULL,
                gameweek INTEGER NOT NULL,
                winner_name TEXT NOT NULL,
                winner_entry_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                reminder_date TEXT NOT NULL,
                completed BOOLEAN DEFAULT FALSE,
                notified BOOLEAN DEFAULT FALSE
            )
        ''')
            
        # Records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                league_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                entry_id INTEGER NOT NULL,
                gameweek INTEGER NOT NULL,
                score INTEGER NOT NULL,
                record_type TEXT NOT NULL, -- 'highest' or 'lowest'
                date_recorded TEXT NOT NULL
            )
        ''')
        
        # Gameweek tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gameweek_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                league_id TEXT NOT NULL,
                gameweek INTEGER NOT NULL,
                processed BOOLEAN DEFAULT FALSE,
                processed_date TEXT,
                UNIQUE(chat_id, league_id, gameweek)
            )
        ''')
            
        self.conn.commit()
    
    def add_league(self, chat_id: int, league_id: str, league_name: str) -> bool:
        """Add a league to track"""
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO leagues 
                    (chat_id, league_id, league_name, added_date)
                    VALUES (?, ?, ?, ?)
                ''', (chat_id, league_id, league_name, datetime.now().isoformat()))
            return True
        except Exception as e:
            logger.error(f"Error adding league: {e}")
            return False
    
    def get_leagues(self, chat_id: int) -> List[Dict]:
        """Get all leagues for a chat"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT id, league_id, league_name, added_date
                FROM leagues
                WHERE chat_id = ?
            ''', (chat_id,))
            
            leagues = []
            for row in cursor.fetchall():
                leagues.append({
                    'id': row[0],
                    'league_id': row[1],
                    'league_name': row[2],
                    'added_date': row[3]
                })
            return leagues
        except Exception as e:
            logger.error(f"Error getting leagues: {e}")
            return []
    
    def add_speech_reminder(self, chat_id: int, league_id: str, gameweek: int,
                          winner_name: str, winner_entry_id: int, score: int) -> bool:
        """Add a speech reminder"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO speech_reminders 
                (chat_id, league_id, gameweek, winner_name, winner_entry_id, score, reminder_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                chat_id, league_id, gameweek, winner_name, 
                winner_entry_id, score, datetime.now().isoformat()
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding speech reminder: {e}")
            return False
    
    def get_pending_speeches(self, chat_id: Optional[int] = None) -> List[Dict]:
        """Get all pending speech reminders"""
        cursor = self.conn.cursor()
        
        if chat_id is not None:
            cursor.execute('''
                SELECT id, chat_id, league_id, gameweek, winner_name, score, reminder_date
                FROM speech_reminders
                WHERE chat_id = ? AND completed = FALSE
                ORDER BY reminder_date
            ''', (chat_id,))
        else:
            cursor.execute('''
                SELECT id, chat_id, league_id, gameweek, winner_name, score, reminder_date
                FROM speech_reminders
                WHERE completed = FALSE
                ORDER BY reminder_date
            ''')
        
        speeches = []
        for row in cursor.fetchall():
            reminder_date = datetime.fromisoformat(row[6])
            days_since = (datetime.now() - reminder_date).days
            
            speeches.append({
                'id': row[0],
                'chat_id': row[1],
                'league_id': row[2],
                'gameweek': row[3],
                'winner_name': row[4],
                'score': row[5],
                'days_since': days_since,
                'league_name': self.get_league(row[1], row[2])['league_name'] if self.get_league(row[1], row[2]) else 'Unknown League'
            })
        
        return speeches
    
    def mark_speech_completed(self, chat_id: int, league_id: str, gameweek: int) -> bool:
        """Mark a speech reminder as completed"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE speech_reminders
                SET completed = TRUE
                WHERE chat_id = ? AND league_id = ? AND gameweek = ?
            ''', (chat_id, league_id, gameweek))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking speech completed: {e}")
            return False
    
    def remove_league(self, chat_id: int, league_id: str) -> bool:
        """Remove a league from tracking"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                DELETE FROM leagues
                WHERE chat_id = ? AND league_id = ?
            ''', (chat_id, league_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking speech notified: {e}")
            return False
    
    def update_record(self, chat_id: int, league_id: str, player_name: str, 
                     entry_id: int, gameweek: int, score: int, 
                     record_type: str) -> bool:
        """Update a record (highest or lowest score)"""
        try:
            cursor = self.conn.cursor()
            
            # Check if we already have a record of this type
            cursor.execute('''
                SELECT id, score 
                FROM records 
                WHERE chat_id = ? AND league_id = ? AND record_type = ?
                LIMIT 1
            ''', (chat_id, league_id, record_type))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update if new score is better
                existing_id, existing_score = existing
                if (record_type == 'highest' and score > existing_score) or \
                   (record_type == 'lowest' and score < existing_score):
                    cursor.execute('''
                        UPDATE records
                        SET player_name = ?, entry_id = ?, gameweek = ?, 
                            score = ?, date_recorded = ?
                        WHERE id = ?
                    ''', (
                        player_name, entry_id, gameweek, score, 
                        datetime.now().isoformat(), existing_id
                    ))
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO records 
                    (chat_id, league_id, player_name, entry_id, 
                     gameweek, score, record_type, date_recorded)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chat_id, league_id, player_name, entry_id,
                    gameweek, score, record_type, datetime.now().isoformat()
                ))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating record: {e}")
            return False
    
    def get_records(self, chat_id: int, league_id: Optional[str] = None) -> Dict:
        """Get all records for a chat/league"""
        cursor = self.conn.cursor()
        
        if league_id:
            cursor.execute('''
                SELECT player_name, entry_id, gameweek, score, record_type
                FROM records
                WHERE chat_id = ? AND league_id = ?
            ''', (chat_id, league_id))
        else:
            cursor.execute('''
                SELECT player_name, entry_id, gameweek, score, record_type
                FROM records
                WHERE chat_id = ?
            ''', (chat_id,))
        
        records = {'highest_score': None, 'lowest_score': None}
        
        for row in cursor.fetchall():
            record = {
                'player': row[0],
                'entry_id': row[1],
                'gameweek': row[2],
                'score': row[3]
            }
            
            if row[4] == 'highest':
                records['highest_score'] = record
            elif row[4] == 'lowest':
                records['lowest_score'] = record
        
        return records
    
    def is_gameweek_processed(self, chat_id: int, league_id: str, gameweek: int) -> bool:
        """Check if a gameweek has already been processed"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 1 
            FROM gameweek_tracking 
            WHERE chat_id = ? AND league_id = ? AND gameweek = ? AND processed = TRUE
        ''', (chat_id, league_id, gameweek))
        
        return cursor.fetchone() is not None
    
    def mark_gameweek_processed(self, chat_id: int, league_id: str, gameweek: int) -> bool:
        """Mark a gameweek as processed"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO gameweek_tracking 
                (chat_id, league_id, gameweek, processed, processed_date)
                VALUES (?, ?, ?, TRUE, ?)
            ''', (chat_id, league_id, gameweek, datetime.now().isoformat()))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking gameweek processed: {e}")
            return False
