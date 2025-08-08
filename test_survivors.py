#!/usr/bin/env python3
"""
Test script to verify the survivor logic fix works correctly.
"""

import sys
import os
sys.path.append('last_man_standing_bot')

from database import Database

def test_survivor_logic():
    """Test the fixed survivor logic"""
    print("Testing Survivor Logic Fix")
    print("=" * 30)
    
    # Initialize database
    db = Database()
    
    # Test global survivors
    print("\n1. Testing Global Survivors:")
    global_survivors = db.get_current_survivors()
    print(f"   Found {len(global_survivors)} global survivors:")
    for user_id, username in global_survivors:
        print(f"   - User {user_id} (@{username})")
    
    # Test group-specific survivors (your group ID from the data inspection)
    group_id = -1002623027562  # "Last Man Standing" group
    print(f"\n2. Testing Group-Specific Survivors (Group {group_id}):")
    group_survivors = db.get_current_survivors(group_id)
    print(f"   Found {len(group_survivors)} group survivors:")
    for user_id, username in group_survivors:
        print(f"   - User {user_id} (@{username})")
    
    # Check if your user ID is in the survivors
    your_user_id = 1151403579
    global_survivor_ids = [user_id for user_id, username in global_survivors]
    group_survivor_ids = [user_id for user_id, username in group_survivors]
    
    print(f"\n3. Checking Your User Status (ID: {your_user_id}):")
    print(f"   In global survivors: {'YES' if your_user_id in global_survivor_ids else 'NO'}")
    print(f"   In group survivors: {'YES' if your_user_id in group_survivor_ids else 'NO'}")
    
    if your_user_id in global_survivor_ids and your_user_id in group_survivor_ids:
        print("   ✅ SUCCESS: You should be able to make picks!")
    else:
        print("   ❌ ISSUE: You're still not showing as a survivor")
        
        # Check user status directly
        user_data = db.get_user(your_user_id)
        if user_data:
            print(f"   User data: {user_data}")
        else:
            print("   User not found in database")
    
    print(f"\n4. Summary:")
    print(f"   - Global survivors: {len(global_survivors)}")
    print(f"   - Group survivors: {len(group_survivors)}")
    print(f"   - Should be equal after fix: {'YES' if len(global_survivors) == len(group_survivors) else 'NO'}")

if __name__ == "__main__":
    test_survivor_logic()
