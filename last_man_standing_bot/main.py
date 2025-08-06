import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database import Database
from football_api import FootballAPI
from config import TELEGRAM_BOT_TOKEN, DEFAULT_LEAGUE
import asyncio

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Initialize database and API
db = Database()
football_api = FootballAPI()

# Current round tracking
current_round = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - register user"""
    user = update.effective_user
    db.add_user(user.id, user.username)
    
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
        
        # Check if user is registered
        if not db.get_user(user.id):
            await update.message.reply_text("❌ Please use /start first to register!")
            return
        
        # Check if user is still active
        survivors = db.get_current_survivors()
        if user.id not in [s[0] for s in survivors]:
            await update.message.reply_text("❌ You've been eliminated and can't make picks!")
            return
        
        # Check if user already made a pick this round
        existing_pick = db.get_user_pick_for_round(user.id, current_round)
        if existing_pick:
            await update.message.reply_text(f"❌ You already picked {existing_pick[0]} for Round {current_round}!")
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
        db.add_pick(user.id, current_round, team_info['name'], team_info['id'], None)
        
        await update.message.reply_text(f"✅ Pick confirmed: {team_info['name']} for Round {current_round}!")
        
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
    """Show current round information"""
    message = f"""
📅 Current Round: {current_round}

🕐 Pick Deadline: Fridays 2:00 PM
⚽ League: Premier League

Remember: Pick a team you think will WIN!
Draws count as elimination! 
    """
    await update.message.reply_text(message)

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("pick", pick_team))
    application.add_handler(CommandHandler("mypicks", my_picks))
    application.add_handler(CommandHandler("survivors", survivors))
    application.add_handler(CommandHandler("round", round_info))
    
    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()