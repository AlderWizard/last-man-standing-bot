#!/usr/bin/env python3
"""
Quick script to reset a user's status for testing purposes.
This will reactivate an eliminated user so they can participate again.
"""

import sqlite3
import sys

def reset_user_status(user_id):
    """Reset a user's status to active"""
    db_path = "last_man_standing_bot/lastman.db"
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Reactivate the user
            cursor.execute('''
                UPDATE users 
                SET is_active = 1 
                WHERE user_id = ?
            ''', (user_id,))
            
            # Check if user exists
            cursor.execute('SELECT username, first_name FROM users WHERE user_id = ?', (user_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                username, first_name = user_data
                print(f"SUCCESS: User {first_name} (@{username}) has been reactivated!")
                print(f"   User ID: {user_id}")
                print(f"   Status: Active")
                conn.commit()
            else:
                print(f"ERROR: User with ID {user_id} not found in database")
                
    except sqlite3.Error as e:
        print(f"ERROR: Database error: {e}")
    except Exception as e:
        print(f"ERROR: {e}")

def list_all_users():
    """List all users in the database"""
    db_path = "last_man_standing_bot/lastman.db"
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, first_name, is_active 
                FROM users 
                ORDER BY user_id
            ''')
            users = cursor.fetchall()
            
            if users:
                print("\nAll users in database:")
                print("-" * 50)
                for user_id, username, first_name, is_active in users:
                    status = "ACTIVE" if is_active else "ELIMINATED"
                    print(f"ID: {user_id} | {first_name} (@{username}) | {status}")
            else:
                print("No users found in database")
                
    except sqlite3.Error as e:
        print(f"ERROR: Database error: {e}")

if __name__ == "__main__":
    print("Last Man Standing - User Reset Tool")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_all_users()
        else:
            try:
                user_id = int(sys.argv[1])
                reset_user_status(user_id)
            except ValueError:
                print("❌ Please provide a valid user ID number")
    else:
        print("Usage:")
        print("  python reset_user.py <user_id>  - Reset specific user")
        print("  python reset_user.py list       - List all users")
        print("\nExample:")
        print("  python reset_user.py 123456789")
        
        # Show all users to help identify the right ID
        list_all_users()
