import sqlite3
import sys
from datetime import datetime
from fpl_database import FPLDatabase
from lifelines import LifelineManager

# Initialize database and lifeline manager
db = FPLDatabase(":memory:")  # Use in-memory database for testing
lifeline_manager = LifelineManager(db.conn)

def test_initial_lifelines():
    """Test that a new user starts with all lifelines available."""
    print("\n=== Testing Initial Lifelines ===")
    lifelines = lifeline_manager.get_available_lifelines(123, 456, "test_league", "2024-25")
    
    expected = ['coinflip', 'goodluck', 'forcechange']
    assert set(lifelines.keys()) == set(expected), "Not all lifelines are available initially"
    
    for lifeline in lifelines.values():
        assert lifeline['remaining'] == 1, f"Lifeline {lifeline['name']} should have 1 use available"
    
    print("[PASS] Initial lifelines test passed!")

def test_use_coinflip():
    """Test using the coinflip lifeline."""
    print("\n=== Testing Coin Flip Lifeline ===")
    
    # First, make sure we can use the coinflip
    success, message = lifeline_manager.use_lifeline(
        chat_id=123,
        user_id=456,
        league_id="test_coinflip_league",  # Use a different league to avoid conflicts
        lifeline_type="coinflip",
        season="2024-25"
    )
    
    # The coinflip should always be recorded as used, regardless of outcome
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM lifeline_usage 
        WHERE user_id = 456 AND lifeline_type = 'coinflip' AND league_id = 'test_coinflip_league'
    """)
    assert cursor.fetchone()[0] == 1, "Lifeline usage not recorded"
    
    # The message should indicate the result
    assert "Heads!" in message or "Tails!" in message, "Should show coin flip result"
    assert "revived" in message.lower() or "didn't work" in message.lower(), "Should indicate success or failure"
    
    # Try to use it again (should fail)
    success, message = lifeline_manager.use_lifeline(
        chat_id=123, 
        user_id=456, 
        league_id="test_coinflip_league", 
        lifeline_type="coinflip", 
        season="2024-25"
    )
    assert not success, "Should not be able to use coinflip twice"
    
    print("[PASS] Coin flip test passed!")

def test_use_goodluck():
    """Test using the goodluck lifeline."""
    print("\n=== Testing Good Luck Lifeline ===")
    # Test without target (should fail)
    success, message = lifeline_manager.use_lifeline(123, 789, "test_league", "goodluck", "2024-25")
    assert not success, "Should require target user"
    
    # Test with target
    success, message = lifeline_manager.use_lifeline(
        chat_id=123,
        user_id=789,
        league_id="test_league",
        lifeline_type="goodluck",
        season="2024-25",
        target_user_id=101  # Using a numeric user ID instead of username
    )
    
    assert success, f"Failed to use goodluck: {message}"
    assert "pick a team from the bottom 6" in message.lower(), "Should mention bottom 6 teams"
    assert "101" in str(message), "Should mention target user ID"
    
    # Try to use it again (should fail)
    success, _ = lifeline_manager.use_lifeline(123, 789, "test_league", "goodluck", "2024-25", "@another_user")
    assert not success, "Should not be able to use goodluck twice"
    
    print("[PASS] Good luck test passed!")

def test_force_change():
    """Test using the force change lifeline."""
    print("\n=== Testing Force Change Lifeline ===")
    
    # Create a test league for force changes
    test_league = "force_change_test_league"
    
    # Test without target (should fail)
    success, message = lifeline_manager.use_lifeline(123, 101, test_league, "forcechange", "2024-25")
    assert not success, "Should require target user"
    
    # Mock the _get_user_team method to return a test team
    original_method = lifeline_manager._get_user_team
    lifeline_manager._get_user_team = lambda *args, **kwargs: "Test Team"
    
    try:
        # Test with target
        success, message = lifeline_manager.use_lifeline(
            chat_id=123,
            user_id=101,
            league_id=test_league,
            lifeline_type="forcechange",
            season="2024-25",
            target_user_id=202
        )
        
        assert success, f"Failed to use forcechange: {message}"
        assert "has been forced to change their team" in message, "Should indicate force change was applied"
        assert "202" in str(message), "Should mention target user ID"
        
        # Record a force change
        assert lifeline_manager._record_force_change(
            chat_id=123,
            user_id=101,  # user who initiated the force change
            league_id=test_league,
            original_team="Arsenal",
            new_team="Tottenham",
            season="2024-25",
            gameweek=5,
            target_user_id=202  # target user's ID
        ), "Failed to record force change"
        
        # Get force changes for gameweek
        changes = lifeline_manager.get_force_changes(123, test_league, 5)
        assert len(changes) == 1, "Should find one force change"
        assert changes[0]['user_id'] == 101, "Force change user ID mismatch"
        
        print("[PASS] Force change test passed!")
    finally:
        # Restore the original method
        lifeline_manager._get_user_team = original_method

if __name__ == "__main__":
    print("=== Starting lifeline tests... ===")
    
    # Run tests
    test_initial_lifelines()
    test_use_coinflip()
    test_use_goodluck()
    test_force_change()
    
    print("\n=== All tests completed successfully! ===")
    db.conn.close()
