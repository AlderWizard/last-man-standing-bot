import requests
from datetime import datetime, timezone

# Get FPL data
response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
data = response.json()

# Get current time in UTC
now = datetime.now(timezone.utc)
print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC\n")

# Get all events
events = sorted(data['events'], key=lambda x: x['id'])

# Print all gameweeks and their status
print("All Gameweeks:")
for event in events:
    deadline = datetime.fromisoformat(event['deadline_time'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
    is_past = deadline < now
    
    print(f"\nGW{event['id']}: {event['name']}")
    print(f"  Deadline: {event['deadline_time']} UTC")
    print(f"  Status: {'PAST' if is_past else 'FUTURE'}")
    print(f"  Is Current: {event.get('is_current', False)}")
    print(f"  Is Next: {event.get('is_next', False)}")
    print(f"  Finished: {event.get('finished', False)}")

# Determine current gameweek logic
current_gw = None
for event in events:
    deadline = datetime.fromisoformat(event['deadline_time'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
    if deadline > now:
        current_gw = event
        break

# If no future deadlines, use the last gameweek
if current_gw is None and events:
    current_gw = events[-1]

if current_gw:
    print(f"\nCurrent Gameweek (determined by logic):")
    print(f"GW{current_gw['id']}: {current_gw['name']}")
    print(f"Deadline: {current_gw['deadline_time']} UTC")
    print(f"Is Current: {current_gw.get('is_current', False)}")
    print(f"Is Next: {current_gw.get('is_next', False)}")
    print(f"Finished: {current_gw.get('finished', False)}")
