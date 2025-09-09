import requests
from datetime import datetime, timezone

# Get FPL data
response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
data = response.json()

# Get current and next gameweeks
current = next((e for e in data['events'] if e.get('is_current')), {})
next_gw = next((e for e in data['events'] if e.get('is_next')), {})

print(f"Current GW: {current.get('name')} (ID: {current.get('id')})")
print(f"Deadline: {current.get('deadline_time')} UTC")
print(f"Finished: {current.get('finished')}")
print(f"\nNext GW: {next_gw.get('name')} (ID: {next_gw.get('id')})")
print(f"Deadline: {next_gw.get('deadline_time')} UTC")

# Print current time for reference
print(f"\nCurrent time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
