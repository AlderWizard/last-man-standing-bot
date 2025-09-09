import requests
from datetime import datetime

def check_fpl_status():
    print("=== FPL API Status Check ===")
    
    # Fetch data from FPL API
    try:
        response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/")
        response.raise_for_status()
        data = response.json()
        
        # Print current time
        print(f"Current time: {datetime.now()}")
        
        # Print gameweek info
        if 'events' in data:
            print("\nGameweeks:")
            for event in data['events']:
                print(f"\nGameweek {event['id']} - {event['name']}")
                print(f"Deadline: {event['deadline_time']}")
                print(f"Finished: {event['finished']}")
                print(f"Is Current: {event['is_current']}")
                print(f"Is Next: {event['is_next']}")
                
        # Print current gameweek from the API
        if 'current-event' in data and data['current-event'] is not None:
            print(f"\nCurrent Gameweek from API: {data['current-event']}")
        
        # Print next deadline
        if 'next-event' in data and data['next-event'] is not None:
            print(f"Next Gameweek from API: {data['next-event']}")
            
    except Exception as e:
        print(f"Error fetching FPL API: {e}")

if __name__ == "__main__":
    check_fpl_status()
