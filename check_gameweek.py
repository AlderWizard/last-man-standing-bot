#!/usr/bin/env python3
import aiohttp
import asyncio

async def get_current_gameweek():
    """Get the current gameweek from FPL API"""
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                events = data.get('events', [])
                
                # Find the current gameweek
                for event in events:
                    if event['is_current']:
                        return event['id']
                
                # If no current gameweek, find the next one
                for event in events:
                    if not event['finished']:
                        return event['id']
                
                # If all gameweeks are finished, return the last one
                return events[-1]['id'] if events else None
                
    except Exception as e:
        print(f"Error fetching gameweek: {e}")
        return None

if __name__ == "__main__":
    current_gw = asyncio.run(get_current_gameweek())
    print(f"Current Gameweek: {current_gw}")
