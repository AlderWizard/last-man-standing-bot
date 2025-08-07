import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database import Database
from football_api import FootballAPI
from config import TELEGRAM_BOT_TOKEN, DEFAULT_LEAGUE
import asyncio
import schedule
import time
import threading
from datetime import datetime, timedelta
import random

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Initialize database and API
db = Database()
football_api = FootballAPI()

# Global application instance for reminders
application = None

# Savage elimination roast messages
ELIMINATION_ROASTS = [
    "💀 {username} just got ELIMINATED! Your football knowledge is as weak as your team choice! 🤡",
    "🚮 {username} is OUT! Maybe stick to watching Netflix instead of football? 📺💔",
    "⚰️ RIP {username} - eliminated faster than your team's hopes and dreams! 😂💀",
    "🤦‍♂️ {username} picked a LOSER and became one! Better luck in the Championship! 📉",
    "💸 {username} just threw away their chances like their team threw away the match! 🗑️",
    "🎪 {username} - the circus called, they want their clown back! Your pick was TERRIBLE! 🤡🎭",
    "📉 {username} is DONE! Your football predictions are worse than the weather forecast! ⛈️",
    "🍅 {username} got REKT! Time to delete your football apps and take up knitting! 🧶",
    "💥 BOOM! {username} is eliminated! Your team choice was more disappointing than your personality! 😈",
    "🏳️ {username} waves the white flag of DEFEAT! Maybe try supporting a different sport? 🏓",
    "🚨 ALERT: {username} has been DESTROYED! Your football IQ just hit rock bottom! 🪨",
    "⚡ {username} got ZAPPED out of existence! Your pick was shockingly bad! ⚡💀",
    "🎯 {username} missed the target completely! Time to find a new hobby! 🎨",
    "🌪️ {username} got swept away by their own terrible decision! Tornado of failure! 🌪️💔",
    "🔥 {username} went down in FLAMES! Your pick was hotter garbage than a dumpster fire! 🔥🗑️"
]

# Dynamic gameweek tracking
def get_current_gameweek():
    """Get current gameweek from API"""
    try:
        return football_api.get_current_gameweek()
    except Exception as e:
        logging.error(f"Error getting current gameweek: {e}")
        return 1  # Fallback to gameweek 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - register user and track groups"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Register user
    db.add_user(user.id, user.username)
    
    # Track group chats
    if chat.type in ['group', 'supergroup']:
        db.add_group(chat.id, chat.title, chat.type)
    
    welcome_message = f"""
🏆 Welcome to Last Man Standing! 🏆

How it works:
• Pick ONE team each round that you think will WIN
• You can only pick each team ONCE during the competition  
• A loss OR draw eliminates you
• Last person standing wins!

Commands:
/pick [team] - Make your pick (e.g., /pick Arsenal)
/mypicks - See your pick history
/survivors - See who's still alive
/round - Current round info
/help - Show this message

Good luck! ⚽
    """
    await update.message.reply_text(welcome_message)

async def pick_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle team picks"""
    user = update.effective_user
    
    try:
        if not context.args:
            await update.message.reply_text("Please specify a team! Example: /pick Arsenal")
            return
        
        team_name = " ".join(context.args)
        current_gameweek = get_current_gameweek()
        
        # Check if user is registered
        if not db.get_user(user.id):
            await update.message.reply_text("❌ Please use /start first to register!")
            return
        
        # Check if picks are allowed for current gameweek
        if not football_api.is_picks_allowed(current_gameweek):
            deadline = football_api.get_gameweek_deadline(current_gameweek)
            if deadline:
                deadline_str = deadline.strftime("%A %d %B at %H:%M")
                await update.message.reply_text(
                    f"❌ Picks are closed for Gameweek {current_gameweek}!\n"
                    f"Deadline was: {deadline_str}\n"
                    f"Picks will reopen when all matches are finished."
                )
            else:
                await update.message.reply_text(f"❌ Picks are currently closed for Gameweek {current_gameweek}!")
            return
        
        # Check if user is still active
        survivors = db.get_current_survivors()
        if user.id not in [s[0] for s in survivors]:
            await update.message.reply_text("❌ You've been eliminated and can't make picks!")
            return
        
        # Check if user already made a pick this gameweek
        existing_pick = db.get_user_pick_for_round(user.id, current_gameweek)
        if existing_pick:
            await update.message.reply_text(f"❌ You already picked {existing_pick[0]} for Gameweek {current_gameweek}!")
            return
        
        # Search for team
        try:
            team_info = football_api.search_team(team_name, DEFAULT_LEAGUE)
            if not team_info:
                await update.message.reply_text(f"❌ Couldn't find team '{team_name}'. Please check spelling.")
                return
        except Exception as e:
            logging.error(f"API error searching for team: {e}")
            await update.message.reply_text("❌ Error connecting to football API. Please try again later.")
            return
        
        # Check if user has already used this team
        if db.has_used_team(user.id, team_info['id']):
            await update.message.reply_text(f"❌ You've already picked {team_info['name']} in a previous round!")
            return
        
        # Add the pick
        db.add_pick(user.id, current_gameweek, team_info['name'], team_info['id'], None)
        
        # Get deadline info for confirmation message
        deadline = football_api.get_gameweek_deadline(current_gameweek)
        deadline_str = deadline.strftime("%A %d %B at %H:%M") if deadline else "TBD"
        
        await update.message.reply_text(
            f"✅ Pick confirmed: {team_info['name']} for Gameweek {current_gameweek}!\n"
            f"🕒 Deadline: {deadline_str}"
        )
        
    except Exception as e:
        logging.error(f"Error in pick_team: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def my_picks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's pick history"""
    user = update.effective_user
    picks = db.get_user_picks(user.id)
    
    if not picks:
        await update.message.reply_text("You haven't made any picks yet!")
        return
    
    message = "📊 Your Pick History:\n\n"
    for round_num, team, result in picks:
        status_emoji = {"win": "✅", "loss": "❌", "draw": "🟡", "pending": "⏳"}
        emoji = status_emoji.get(result, "❓")
        message += f"Round {round_num}: {team} {emoji}\n"
    
    await update.message.reply_text(message)

async def survivors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current survivors"""
    survivor_list = db.get_current_survivors()
    
    if not survivor_list:
        await update.message.reply_text("No survivors remaining!")
        return
    
    message = f"🏆 Current Survivors ({len(survivor_list)}):\n\n"
    for user_id, username in survivor_list:
        username_display = username if username else f"User {user_id}"
        message += f"• {username_display}\n"
    
    await update.message.reply_text(message)

async def round_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current gameweek information with dynamic deadlines"""
    try:
        current_gameweek = get_current_gameweek()
        deadline = football_api.get_gameweek_deadline(current_gameweek)
        picks_allowed = football_api.is_picks_allowed(current_gameweek)
        
        # Get fixture information for this gameweek
        fixtures = football_api.get_gameweek_fixtures(current_gameweek)
        
        message = f"📅 **Gameweek {current_gameweek} Information**\n\n"
        
        if deadline:
            deadline_str = deadline.strftime("%A %d %B at %H:%M")
            message += f"🕒 **Pick Deadline:** {deadline_str}\n"
        else:
            message += f"🕒 **Pick Deadline:** TBD\n"
        
        if picks_allowed:
            message += f"✅ **Status:** Picks are OPEN\n"
        else:
            message += f"❌ **Status:** Picks are CLOSED\n"
        
        message += f"⚽ **League:** Premier League\n\n"
        
        # Show some fixtures if available
        if fixtures:
            message += f"🏟️ **Upcoming Matches:**\n"
            for i, fixture in enumerate(fixtures[:3]):  # Show first 3 matches
                from datetime import datetime
                match_time = datetime.fromtimestamp(fixture['timestamp'])
                time_str = match_time.strftime("%a %H:%M")
                message += f"• {fixture['home_team']} vs {fixture['away_team']} ({time_str})\n"
            
            if len(fixtures) > 3:
                message += f"... and {len(fixtures) - 3} more matches\n"
        
        message += f"\n💡 **Remember:** Pick a team you think will WIN!\nDraws count as elimination!"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logging.error(f"Error in round_info: {e}")
        await update.message.reply_text("❌ Error getting gameweek information. Please try again.")

async def send_reminder_to_groups():
    """Send reminder message to all groups 24 hours before deadline"""
    try:
        current_gameweek = get_current_gameweek()
        deadline = football_api.get_gameweek_deadline(current_gameweek)
        
        if not deadline:
            return
        
        # Check if we should send reminder (24 hours before deadline)
        now = datetime.now()
        time_until_deadline = deadline - now
        
        # Send reminder if we're between 23-25 hours before deadline
        if timedelta(hours=23) <= time_until_deadline <= timedelta(hours=25):
            groups = db.get_active_groups()
            users_without_picks = db.get_users_without_picks(current_gameweek)
            
            if not users_without_picks:
                return  # Everyone has picked
            
            deadline_str = deadline.strftime("%A %d %B at %H:%M")
            
            # Create reminder message
            message = f"🚨 **PICK REMINDER - Gameweek {current_gameweek}** 🚨\n\n"
            message += f"⏰ **Deadline:** {deadline_str} (24 hours from now!)\n\n"
            message += f"📝 **Still need to pick:** {len(users_without_picks)} players\n"
            
            if len(users_without_picks) <= 10:  # Show names if not too many
                names = []
                for user_id, username in users_without_picks:
                    if username:
                        names.append(f"@{username}")
                    else:
                        names.append(f"User {user_id}")
                message += f"👥 {', '.join(names)}\n\n"
            
            message += f"💡 Use `/pick TeamName` to make your selection!\n"
            message += f"⚽ Remember: Pick a team you think will WIN!"
            
            # Send to all groups
            for chat_id, chat_title, chat_type in groups:
                try:
                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    logging.info(f"Sent reminder to group {chat_title} ({chat_id})")
                except Exception as e:
                    logging.error(f"Failed to send reminder to group {chat_id}: {e}")
                    
    except Exception as e:
        logging.error(f"Error in send_reminder_to_groups: {e}")

async def roast_eliminated_users(eliminated_users, gameweek):
    """Send savage elimination messages to all groups"""
    try:
        if not eliminated_users:
            return
        
        groups = db.get_active_groups()
        if not groups:
            return
        
        # Create elimination message
        if len(eliminated_users) == 1:
            user_id, username = eliminated_users[0]
            display_name = f"@{username}" if username else f"User {user_id}"
            
            # Pick random roast message
            roast_template = random.choice(ELIMINATION_ROASTS)
            message = roast_template.format(username=display_name)
            message += f"\n\n📊 **Gameweek {gameweek} Casualty Report** 📊"
            
        else:
            # Multiple eliminations
            names = []
            for user_id, username in eliminated_users:
                if username:
                    names.append(f"@{username}")
                else:
                    names.append(f"User {user_id}")
            
            message = f"💥 **MASS ELIMINATION EVENT!** 💥\n\n"
            message += f"💀 The following {len(eliminated_users)} clowns got DESTROYED in Gameweek {gameweek}:\n"
            message += f"🎪 {', '.join(names)}\n\n"
            message += f"🤡 What a bunch of muppets! Your football knowledge is TRAGIC! 💸\n"
            message += f"🚮 Time to stick to something easier... like tic-tac-toe! ❌⭕"
        
        # Send to all groups
        for chat_id, chat_title, chat_type in groups:
            try:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=message
                )
                logging.info(f"Sent elimination roast to group {chat_title} ({chat_id})")
            except Exception as e:
                logging.error(f"Failed to send elimination roast to group {chat_id}: {e}")
                
    except Exception as e:
        logging.error(f"Error in roast_eliminated_users: {e}")

async def check_for_eliminations():
    """Check if gameweek has ended and process eliminations with roasting"""
    try:
        current_gameweek = get_current_gameweek()
        
        # Check if current gameweek is finished
        if not football_api.is_gameweek_active(current_gameweek):
            # Get all picks for this gameweek
            fixtures = football_api.get_gameweek_fixtures(current_gameweek)
            
            if not fixtures:
                return
            
            # Check if all matches are finished
            all_finished = all(fixture['status'] == 'FT' for fixture in fixtures)
            
            if all_finished:
                # Process eliminations for this gameweek
                eliminated_users = []
                
                # Get all users who made picks this gameweek
                users_with_picks = db.get_users_with_picks_for_round(current_gameweek)
                
                for user_id, username, team_name, team_id in users_with_picks:
                    # Check if their team won
                    team_won = False
                    
                    for fixture in fixtures:
                        if (fixture['home_team'].lower() in team_name.lower() or 
                            team_name.lower() in fixture['home_team'].lower()):
                            # User picked home team
                            if fixture['home_score'] is not None and fixture['away_score'] is not None:
                                if fixture['home_score'] > fixture['away_score']:
                                    team_won = True
                            break
                        elif (fixture['away_team'].lower() in team_name.lower() or 
                              team_name.lower() in fixture['away_team'].lower()):
                            # User picked away team
                            if fixture['home_score'] is not None and fixture['away_score'] is not None:
                                if fixture['away_score'] > fixture['home_score']:
                                    team_won = True
                            break
                    
                    # If team didn't win (lost or drew), eliminate user
                    if not team_won:
                        db.eliminate_user(user_id)
                        eliminated_users.append((user_id, username))
                        logging.info(f"Eliminated user {username} ({user_id}) - team {team_name} didn't win")
                
                # Send roasting messages if anyone was eliminated
                if eliminated_users:
                    await roast_eliminated_users(eliminated_users, current_gameweek)
                    
    except Exception as e:
        logging.error(f"Error in check_for_eliminations: {e}")

def check_and_send_reminders():
    """Wrapper function for scheduler"""
    if application:
        asyncio.create_task(send_reminder_to_groups())
        asyncio.create_task(check_for_eliminations())

def run_scheduler():
    """Run the scheduler in a separate thread"""
    # Check for reminders every hour
    schedule.every().hour.do(check_and_send_reminders)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def main():
    """Start the bot"""
    global application
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("pick", pick_team))
    application.add_handler(CommandHandler("mypicks", my_picks))
    application.add_handler(CommandHandler("survivors", survivors))
    application.add_handler(CommandHandler("round", round_info))
    
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logging.info("Reminder scheduler started")
    
    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
