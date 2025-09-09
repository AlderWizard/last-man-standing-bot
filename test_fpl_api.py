import requests
import sys
from datetime import datetime, timezone

# Set console output encoding to UTF-8
if sys.platform == 'win32':
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check_fpl_api():
    try:
        # Get current data from FPL API
        response = requests.get(
            "https://fantasy.premierleague.com/api/bootstrap-static/",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if 'events' not in data:
            print("Error: No events in FPL API response")
            return
        
        now = datetime.now(timezone.utc)
        print(f"Current time (UTC): {now}")
        
        # Print all gameweeks for debugging
        print("\nAll Gameweeks:")
        for event in sorted(data['events'], key=lambda x: x['id']):
            deadline = datetime.fromisoformat(event['deadline_time'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            print(f"\nGameweek {event['id']}:")
            print(f"  Name: {event['name']}")
            print(f"  Deadline: {deadline} (UTC)")
            print(f"  Is Current: {event.get('is_current', False)}")
            print(f"  Is Next: {event.get('is_next', False)}")
            print(f"  Finished: {event.get('finished', False)}")
            status = '[CURRENT]' if event.get('is_current') else '[NEXT]' if event.get('is_next') else ''
            print(f"  Status: {status}")
        
        # Find current and next gameweeks
        current_event = next((e for e in data['events'] if e.get('is_current')), None)
        next_event = next((e for e in data['events'] if e.get('is_next')), None)
        
        print("\nCurrent Gameweek Analysis:")
        if current_event:
            print(f"Current GW: {current_event['id']} ({current_event['name']})")
            deadline = datetime.fromisoformat(current_event['deadline_time'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            print(f"  Deadline: {deadline} (UTC)")
            print(f"  Finished: {current_event.get('finished', False)}")
            
            if current_event.get('finished') and next_event:
                next_deadline = datetime.fromisoformat(next_event['deadline_time'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
                if now > next_deadline:
                    print(f"\n⚠️ Current GW is finished and next GW deadline has passed")
                    print(f"  Next GW: {next_event['id']} (deadline: {next_deadline})")
                    print(f"  Current time: {now}")
                    print("  Should be using next GW!")
                    return next_event['id']
                else:
                    print(f"\nℹ️ Current GW is finished but next GW deadline is in the future")
                    print(f"  Next GW: {next_event['id']} (deadline: {next_deadline})")
            
            return current_event['id']
            
        elif next_event:
            print(f"No current GW, next GW is: {next_event['id']} ({next_event['name']})")
            return next_event['id']
            
        else:
            print("No current or next gameweek found!")
            
    except Exception as e:
        print(f"Error checking FPL API: {e}")
        raise

if __name__ == "__main__":
    current_gw = check_fpl_api()
    print(f"\n✅ Current Gameweek: {current_gw}")
