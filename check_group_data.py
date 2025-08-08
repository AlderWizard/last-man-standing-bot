#!/usr/bin/env python3
"""
Script to inspect group-specific data and debug survivor issues.
"""

import sqlite3
import sys

def check_group_data(user_id=None):
    """Check group-specific data for debugging"""
    db_path = "last_man_standing_bot/lastman.db"
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            print("=== USERS TABLE ===")
            cursor.execute('SELECT user_id, username, first_name, is_active FROM users')
            users = cursor.fetchall()
            for user_id_db, username, first_name, is_active in users:
                status = "ACTIVE" if is_active else "ELIMINATED"
                print(f"User: {first_name} (@{username}) | ID: {user_id_db} | Status: {status}")
            
            print("\n=== GROUPS TABLE ===")
            cursor.execute('SELECT chat_id, chat_title, chat_type FROM groups')
            groups = cursor.fetchall()
            if groups:
                for chat_id, chat_title, chat_type in groups:
                    print(f"Group: {chat_title} | ID: {chat_id} | Type: {chat_type}")
            else:
                print("No groups found in database")
            
            print("\n=== PICKS TABLE ===")
            cursor.execute('SELECT user_id, round_number, team_name, chat_id FROM picks ORDER BY round_number DESC LIMIT 10')
            picks = cursor.fetchall()
            if picks:
                for user_id_db, round_num, team_name, chat_id in picks:
                    print(f"User {user_id_db} | Round {round_num} | Team: {team_name} | Group: {chat_id}")
            else:
                print("No picks found in database")
            
            print("\n=== BLOCKED TEAMS TABLE ===")
            cursor.execute('SELECT user_id, team_id, chat_id FROM blocked_teams')
            blocked = cursor.fetchall()
            if blocked:
                for user_id_db, team_id, chat_id in blocked:
                    print(f"User {user_id_db} | Blocked Team ID: {team_id} | Group: {chat_id}")
            else:
                print("No blocked teams found")
            
            if user_id:
                print(f"\n=== SPECIFIC DATA FOR USER {user_id} ===")
                
                # Check user's picks
                cursor.execute('SELECT round_number, team_name, chat_id FROM picks WHERE user_id = ?', (user_id,))
                user_picks = cursor.fetchall()
                if user_picks:
                    print("User's picks:")
                    for round_num, team_name, chat_id in user_picks:
                        print(f"  Round {round_num}: {team_name} (Group: {chat_id})")
                else:
                    print("No picks found for this user")
                
                # Check user's blocked teams
                cursor.execute('SELECT team_id, chat_id FROM blocked_teams WHERE user_id = ?', (user_id,))
                user_blocked = cursor.fetchall()
                if user_blocked:
                    print("User's blocked teams:")
                    for team_id, chat_id in user_blocked:
                        print(f"  Team ID {team_id} (Group: {chat_id})")
                else:
                    print("No blocked teams for this user")
                    
    except sqlite3.Error as e:
        print(f"Database error: {e}")

def clear_user_data(user_id):
    """Clear all data for a specific user to start fresh"""
    db_path = "last_man_standing_bot/lastman.db"
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Clear picks
            cursor.execute('DELETE FROM picks WHERE user_id = ?', (user_id,))
            picks_deleted = cursor.rowcount
            
            # Clear blocked teams
            cursor.execute('DELETE FROM blocked_teams WHERE user_id = ?', (user_id,))
            blocked_deleted = cursor.rowcount
            
            # Ensure user is active
            cursor.execute('UPDATE users SET is_active = 1 WHERE user_id = ?', (user_id,))
            
            conn.commit()
            
            print(f"SUCCESS: Cleared data for user {user_id}")
            print(f"  - Deleted {picks_deleted} picks")
            print(f"  - Deleted {blocked_deleted} blocked teams")
            print(f"  - Set user status to ACTIVE")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "clear" and len(sys.argv) > 2:
            try:
                user_id = int(sys.argv[2])
                clear_user_data(user_id)
            except ValueError:
                print("Please provide a valid user ID number")
        else:
            try:
                user_id = int(sys.argv[1])
                check_group_data(user_id)
            except ValueError:
                print("Please provide a valid user ID number")
                check_group_data()
    else:
        print("Group Data Inspector")
        print("===================")
        check_group_data()
        print("\nUsage:")
        print("  python check_group_data.py <user_id>  - Check specific user data")
        print("  python check_group_data.py clear <user_id>  - Clear all user data")
