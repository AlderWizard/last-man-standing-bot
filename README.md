# Last Man Standing Football Bot

A Telegram bot for running Last Man Standing football competitions with group isolation.

## Webhook Test
Testing instant deployment via GitHub webhooks - this should trigger auto-update on Pi!

## How It Works
- Players pick ONE team each round that they think will win
- Each team can only be picked ONCE during the entire competition
- A loss OR draw eliminates the player
- Last person standing wins!

## Setup

### 1. Install Dependencies
```bash
# Create virtual environment (if not exists)
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r last_man_standing_bot/requirements.txt
```

### 2. Configure Environment
The `.env` file is already configured with API keys. If you need to update them:
- `TELEGRAM_BOT_TOKEN`: Get from @BotFather on Telegram
- `FOOTBALL_API_KEY`: Get from https://api-sports.io/

### 3. Run the Bot
```bash
cd last_man_standing_bot
python main.py
```

## Bot Commands
- `/start` - Register and see game rules
- `/pick [team]` - Make your team selection (e.g., `/pick Arsenal`)
- `/mypicks` - View your pick history
- `/survivors` - See who's still alive
- `/round` - Current round information
- `/help` - Show help message

## Requirements
- Python 3.8+
- Active internet connection
- Valid Telegram Bot Token
- Valid Football API key with sufficient quota

## Database
The bot automatically creates a SQLite database (`lastman.db`) to store:
- User registrations
- Team picks
- Match results
- Elimination status
