"""
Last Man Standing Telegram Bot

A Telegram bot for running Last Man Standing football competitions with group isolation.
Each Telegram group runs its own independent competition with:
- Group-specific survivors and eliminations
- Independent winner tracking and leaderboards  
- Isolated pick history and team blocking
- Automatic competition resets per group
- Savage roasting messages for eliminations and deadline misses

Author: Windsurf AI Assistant
Version: 2.0 - Multi-Group Support
"""

# Standard library imports
import asyncio
import logging
import random
import re
import threading
import time
import traceback
import schedule
from datetime import datetime, timedelta
from sqlalchemy import text
import os
import requests

# Third-party imports
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

# Local imports
import os
import sys

# Add the parent directory to the path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from last_man_standing_bot.config import TELEGRAM_BOT_TOKEN, DEFAULT_LEAGUE
from last_man_standing_bot.database_postgres import DatabasePostgres as Database
from last_man_standing_bot.football_api import FootballAPI
from last_man_standing_bot.lifelines import LifelineManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set up logging for other modules
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Global variables
global db, football_api, lifeline_manager, application

# Initialize core components
db = None
football_api = None
lifeline_manager = None
application = None

# ============================================================================
# GLOBAL VARIABLES AND CONSTANTS
# ============================================================================

# Global application instance for background tasks
application = None

# ============================================================================
# ROAST MESSAGE CONSTANTS
# ============================================================================

# Savage elimination roast messages for when users get eliminated
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

# Funny deadline miss roast messages for users who forget to pick
DEADLINE_MISS_ROASTS = [
    "🤦‍♂️ What a fool {username} didn't pick in time! Too busy watching paint dry? 🎨😴",
    "⏰ {username} missed the deadline! Did your alarm clock break or is your brain broken? 🧠💔",
    "🐌 {username} was slower than a snail! Maybe set 47 alarms next time? ⏰⏰⏰",
    "🤡 {username} forgot to pick! Your memory is worse than your football knowledge! 🧠🗑️",
    "😴 {username} was probably napping while the deadline passed! Wake up, sleepyhead! 💤",
    "🎪 Ladies and gentlemen, {username} - the master of missing deadlines! 👏🤡",
    "⚡ BREAKING: {username} discovered how to lose without even playing! Revolutionary! 📰",
    "🏃‍♂️ {username} ran out of time faster than their last team ran out of goals! 💨",
    "🧠 {username}'s brain.exe stopped working at deadline time! Have you tried turning it off and on again? 💻",
    "🎯 {username} missed the deadline like their teams miss the goal! Consistently disappointing! ⚽",
    "🚨 ALERT: {username} has been eliminated by their own laziness! Self-destruction complete! 💥",
    "📱 {username} probably saw the reminder and thought 'I'll do it later'... Famous last words! ⚰️",
    "🤖 {username} set a new record: eliminated without even trying! Efficiency at its finest! 🏆",
    "🎭 {username} performed the classic disappearing act when it mattered most! Houdini would be proud! 🎩",
    "🕰️ {username} exists in a different timezone... the 'Too Late' timezone! Geography lesson needed! 🌍"
]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_current_gameweek():
    """Get current gameweek from API with error handling."""
    try:
        return football_api.get_current_gameweek()
    except Exception as e:
        logger.error(f"Error getting current gameweek: {e}")
        return 1  # Fallback to gameweek 1

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_season():
    """Get the current season in YYYY-YY format"""
    import datetime
    now = datetime.datetime.now()
    # If month is before July, it's the second half of the season
    if now.month < 7:
        return f"{now.year-1}-{str(now.year)[2:]}"
    else:
        return f"{now.year}-{str(now.year+1)[2:]}"

# ============================================================================
# TELEGRAM COMMAND HANDLERS
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - register user and track groups"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name
    
    # Add user to database with display name info
    db.add_user(user_id, username, first_name, last_name)
    
    # Track group chats and add user to group
    if update.effective_chat.type in ['group', 'supergroup']:
        chat_id = update.effective_chat.id
        chat_title = update.effective_chat.title
        chat_type = update.effective_chat.type
        db.add_group(chat_id, chat_title, chat_type)
        db.add_user_to_group(user_id, chat_id)
    
    current_gameweek = get_current_gameweek()
    
    # Get user's display name for personalized welcome
    display_name = db.get_display_name(user_id, username, first_name, last_name)
    
    welcome_message = f"🏆 **Welcome to Last Man Standing, {display_name}!** ⚽\n\n"
    welcome_message += f"📅 **Current Gameweek:** {current_gameweek}\n"
    welcome_message += f"🎯 **Your Mission:** Pick a team each week that you think will WIN\n"
    welcome_message += f"💀 **The Catch:** If your team loses or draws, you're OUT!\n"
    welcome_message += f"🏅 **The Goal:** Be the last survivor!\n\n"
    welcome_message += f"**Commands:**\n"
    welcome_message += f"• `/pick TeamName` - Make your weekly pick\n"
    welcome_message += f"• `/change TeamName` - Change your pick (blocks old team for this competition)\n"
    welcome_message += f"• `/mypicks` - View your pick history\n"
    welcome_message += f"• `/survivors` - See who's still alive\n"
    welcome_message += f"• `/winners` - Hall of fame leaderboard\n"
    welcome_message += f"• `/round` - Current gameweek info\n"
    welcome_message += f"• `/lifelines` - View available lifelines\n\n"
    welcome_message += f"🔹 **Lifelines (one-time use per season):**\n"
    welcome_message += f"• **Coinflip** - 50% chance to revive and re-enter the current round\n"
    welcome_message += f"• **Good Luck** - Pick another player to choose from bottom 6 teams\n"
    welcome_message += f"• **Force Change** - Force a team change (conditions apply)\n\n"
    welcome_message += f"💡 **Remember:** You can only use each team ONCE per competition!\n"
    welcome_message += f"🚫 **Warning:** If ALL survivors draw/lose in a round, EVERYONE is eliminated!\n"
    welcome_message += f"🔄 **Auto-Reset:** When all players are out, a new competition starts automatically!\n"
    welcome_message += f"\nUse `/lifelines` to see your available lifelines and how to use them. Good luck! 🍀"
    
    await update.message.reply_text(welcome_message)

async def pick_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle team picks"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Only allow in groups
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This bot only works in group chats! Add me to a group to play.")
        return
    
    try:
        if not context.args:
            await update.message.reply_text("Please specify a team! Example: /pick Arsenal")
            return
        
        team_name = " ".join(context.args)
        current_gameweek = get_current_gameweek()
        
        # Auto-register new users when they make their first pick
        if not db.get_user(user.id):
            # Register the user automatically
            db.add_user(user.id, user.username, user.first_name, user.last_name)
            
            # Also register the group if needed
            chat_title = update.effective_chat.title
            chat_type = update.effective_chat.type
            db.add_group(chat_id, chat_title, chat_type)
            
            # Add user to this group
            db.add_user_to_group(user.id, chat_id)
            
            # Send welcome message for new users
            display_name = db.get_display_name(user.id, user.username, user.first_name, user.last_name)
            welcome_msg = f"🎉 Welcome to Last Man Standing, {display_name}! 🏆\n"
            welcome_msg += f"📝 You've been automatically registered. Let's make your first pick!"
            await update.message.reply_text(welcome_msg)
        
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
        
        # Ensure user is properly registered in this group (in case they ran /start but weren't added properly)
        db.add_user_to_group(user.id, chat_id)
        
        # Check if user is still active in this group
        survivors = db.get_current_survivors(chat_id)
        logger.info(f"Survivors check: User {user.id} in group {chat_id}. Survivors: {survivors}")
        
        if user.id not in [s[0] for s in survivors]:
            await update.message.reply_text("❌ You've been eliminated from this group's competition and can't make picks!")
            return
        
        # Check if user already made a pick this gameweek
        existing_pick = db.get_user_pick_for_round(user.id, current_gameweek)
        if existing_pick:
            await update.message.reply_text(f"❌ You already picked {existing_pick[0]} for Gameweek {current_gameweek}!")
            return
        
        # Enhanced fuzzy team search
        try:
            search_result = football_api.fuzzy_search_team(team_name)
            
            if not search_result['team']:
                await update.message.reply_text(
                    f"❌ Couldn't find team '{team_name}'.\\n"
                    f"💡 Try: Arsenal, Chelsea, Liverpool, City, United, Spurs, etc."
                )
                return
            
            team_info = search_result['team']
            
            # If fuzzy match with low confidence, ask for confirmation
            if not search_result['exact_match'] and search_result['confidence'] < 90:
                confirmation_msg = f"🤔 Did you mean **{team_info['name']}**?\\n"
                confirmation_msg += f"📝 You typed: '{search_result['user_input']}'\\n"
                confirmation_msg += f"🎯 Confidence: {search_result['confidence']}%\\n\\n"
                confirmation_msg += f"Reply with `/pick {team_info['name']}` to confirm."
                
                await update.message.reply_text(confirmation_msg)
                return
                
        except Exception as e:
            logger.error(f"Error in fuzzy team search: {e}")
            await update.message.reply_text("❌ Error searching for team. Please try again.")
            return
        
        # Check if user has already used this team in this group
        if db.has_used_team(user.id, team_info['id'], chat_id):
            await update.message.reply_text(f"❌ You've already picked {team_info['name']} in this group's competition!")
            return
        
        # Add the pick for this group
        db.add_pick(user.id, current_gameweek, team_info['name'], team_info['id'], None, chat_id)
        
        # Get deadline info for confirmation message
        deadline = football_api.get_gameweek_deadline(current_gameweek)
        deadline_str = deadline.strftime("%A %d %B at %H:%M") if deadline else "TBD"
        
        await update.message.reply_text(
            f"✅ Pick confirmed: {team_info['name']} for Gameweek {current_gameweek}!\n"
            f"🕒 Deadline: {deadline_str}"
        )
        
    except Exception as e:
        logger.error(f"Error in pick_team: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def my_picks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's pick history"""
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    if not chat_id:
        await update.message.reply_text("❌ Error: Could not determine chat ID. Please try again in a group chat.")
        return
        
    picks = db.get_user_picks(user_id=user.id, chat_id=chat_id)
    
    if not picks:
        await update.message.reply_text("You haven't made any picks yet!")
        return
    
    message = "📊 Your Pick History:\n\n"
    for round_num, team, result in picks:
        status_emoji = {"win": "✅", "loss": "❌", "draw": "🟡", "pending": "⏳"}
        emoji = status_emoji.get(result, "❓")
        message += f"Round {round_num}: {team} {emoji}\n"
    
    await update.message.reply_text(message)

async def change_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow users to change their pick (blocks old team for rest of competition)"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Only allow in groups
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This bot only works in group chats! Add me to a group to play.")
        return
    
    try:
        if not context.args:
            await update.message.reply_text("Please specify a team! Example: /change Arsenal")
            return
        
        team_name = " ".join(context.args)
        current_gameweek = get_current_gameweek()
        
        # Check if user is registered
        if not db.get_user(user.id):
            await update.message.reply_text("❌ Please use /start first to register!")
            return
        
        # Check if picks are still allowed for this gameweek
        if not football_api.is_picks_allowed(current_gameweek):
            await update.message.reply_text("❌ Picks are no longer allowed for this gameweek!")
            return
        
        # Check if user is still active in this group
        survivors = db.get_current_survivors(chat_id)
        if user.id not in [s[0] for s in survivors]:
            await update.message.reply_text("❌ You've been eliminated from this group's competition and can't change picks!")
            return
        
        # Check if user has a pick for this round to change
        existing_pick = db.get_user_pick_for_round(user.id, current_gameweek)
        if not existing_pick:
            await update.message.reply_text(f"❌ You haven't made a pick for Gameweek {current_gameweek} yet! Use /pick instead.")
            return
        
        old_team_name, old_team_id, _ = existing_pick
        
        # Search for new team
        try:
            team_info = football_api.search_team(team_name, DEFAULT_LEAGUE)
            if not team_info:
                await update.message.reply_text(f"❌ Couldn't find team '{team_name}'. Please check spelling.")
                return
        except Exception as e:
            logger.error(f"API error searching for team: {e}")
            await update.message.reply_text("❌ Error connecting to football API. Please try again later.")
            return
        
        # Check if new team is the same as old team
        if team_info['id'] == old_team_id:
            await update.message.reply_text(f"❌ You already picked {team_info['name']}! Choose a different team.")
            return
        
        # Check if user has already used the new team in this group
        if db.has_used_team(user.id, team_info['id'], chat_id):
            await update.message.reply_text(f"❌ You've already used {team_info['name']} in this group's competition!")
            return
        
        # Update the pick and block the old team for this group
        db.change_user_pick(user.id, current_gameweek, team_info['name'], team_info['id'], old_team_id, chat_id)
        
        # Get deadline info for confirmation message
        deadline = football_api.get_gameweek_deadline(current_gameweek)
        deadline_str = deadline.strftime("%A %d %B at %H:%M") if deadline else "TBD"
        
        await update.message.reply_text(
            f"🔄 Pick changed successfully!\n\n"
            f"❌ Old pick: {old_team_name} (now blocked permanently)\n"
            f"✅ New pick: {team_info['name']} for Gameweek {current_gameweek}\n\n"
            f"🚫 **Important:** You can never use {old_team_name} again in this competition!\n"
            f"🕒 Deadline: {deadline_str}"
        )
        
    except Exception as e:
        logger.error(f"Error in change_pick: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def survivors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current survivors in this group"""
    chat_id = update.effective_chat.id
    
    # Only allow in groups
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This bot only works in group chats! Add me to a group to play.")
        return
    
    survivor_list = db.get_current_survivors(chat_id)
    
    if not survivor_list:
        await update.message.reply_text("💀 No survivors remaining in this group! The competition is over!")
        return
    
    message = f"🏆 **Current Survivors in this group ({len(survivor_list)}):**\n\n"
    for user_id, username, first_name, last_name in survivor_list:
        # Use first_name if available, otherwise username, otherwise user_id
        if first_name:
            display_name = first_name
            if last_name:
                display_name += f" {last_name}"
        elif username:
            display_name = username
        else:
            display_name = f"User {user_id}"
        message += f"• {display_name}\n"
    
    message += f"\n💪 Keep fighting, survivors!"
    await update.message.reply_text(message)

async def winners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show winner statistics for this group"""
    chat_id = update.effective_chat.id
    
    # Only allow in groups
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This bot only works in group chats! Add me to a group to play.")
        return
    
    winner_stats = db.get_winner_stats(chat_id)
    
    if not winner_stats:
        await update.message.reply_text("🏆 No winners yet in this group! Be the first to win a competition!")
        return
    
    message = f"🏆 **Hall of Fame - Competition Winners (This Group):**\n\n"
    
    for user_id, username, first_name, last_name, wins in winner_stats:
        # Use first_name if available, otherwise username
        if first_name:
            display_name = first_name
            if last_name:
                display_name += f" {last_name}"
        elif username:
            display_name = username
        else:
            display_name = f"User {user_id}"
        
        # Add trophy emojis based on number of wins
        if wins >= 5:
            trophy = "🏆👑"  # Crown for 5+ wins
        elif wins >= 3:
            trophy = "🏆🥇"  # Gold medal for 3+ wins
        elif wins >= 2:
            trophy = "🏆🥈"  # Silver medal for 2+ wins
        else:
            trophy = "🏆🥉"  # Bronze medal for 1 win
        
        plural = "win" if wins == 1 else "wins"
        message += f"{trophy} {display_name} - {wins} {plural}\n"
    
    message += f"\n🎯 **Compete to climb this group's leaderboard!**"
    await update.message.reply_text(message)

async def pot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current prize pot for this group"""
    chat_id = update.effective_chat.id
    
    # Only allow in groups
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This bot only works in group chats! Add me to a group to play.")
        return
    
    try:
        pot_value, player_count, rollover_count = db.calculate_pot_value(chat_id)
        
        message = f"💰 **Current Prize Pot (This Group):**\n\n"
        message += f"🏆 **Total Pot:** £{pot_value}\n"
        message += f"👥 **Active Players:** {player_count}\n"
        message += f"🔄 **Rollovers:** {rollover_count}\n\n"
        
        if rollover_count == 0:
            message += f"💡 **Base pot:** £2 per player\n"
        elif rollover_count == 1:
            message += f"💡 **After 1 rollover:** £5 per player\n"
        else:
            pot_per_player = 5 + ((rollover_count - 1) * 5)
            message += f"💡 **After {rollover_count} rollovers:** £{pot_per_player} per player\n"
        
        message += f"\n🎯 **Winner takes all!**"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error in pot command: {e}")
        await update.message.reply_text("❌ Error calculating pot value. Please try again.")

async def rollover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Increment rollover count and show updated pot (admin command)"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Only allow in groups
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This bot only works in group chats! Add me to a group to play.")
        return
    
    try:
        # Get chat member to check if user is admin
        chat_member = await context.bot.get_chat_member(chat_id, user.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Only group administrators can use the /rollover command!")
            return
        
        # Increment rollover count
        db.increment_rollover(chat_id)
        
        # Get updated pot information
        pot_value, player_count, rollover_count = db.calculate_pot_value(chat_id)
        
        message = f"🔄 **Rollover Applied!**\n\n"
        message += f"💰 **New Prize Pot:** £{pot_value}\n"
        message += f"👥 **Active Players:** {player_count}\n"
        message += f"🔄 **Total Rollovers:** {rollover_count}\n\n"
        
        if rollover_count == 1:
            message += f"💡 **Pot increased to:** £5 per player\n"
        else:
            pot_per_player = 5 + ((rollover_count - 1) * 5)
            message += f"💡 **Pot increased to:** £{pot_per_player} per player\n"
        
        message += f"\n🎯 **The stakes just got higher!**"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error in rollover command: {e}")
        await update.message.reply_text("❌ Error applying rollover. Please try again.")

async def debug_user_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to check user and group status in database"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        # Get user info from database
        user_info = db.get_user_info(user_id, chat_id)
        survivors = db.get_current_survivors(chat_id)
        current_gameweek = get_current_gameweek()
        user_pick = db.get_user_pick_for_round(user_id, current_gameweek)
        
        message = f"🔍 **Debug Info for User {user_id}**\\n\\n"
        message += f"📊 **User in DB:** {'Yes' if user_info else 'No'}\\n"
        message += f"👥 **Current Survivors:** {len(survivors)}\\n"
        message += f"🎯 **Current Gameweek:** {current_gameweek}\\n"
        message += f"⚽ **User Pick:** {user_pick[0] if user_pick else 'None'}\\n"
        
        if user_info:
            message += f"👤 **Username:** {user_info[1]}\\n"
            message += f"🏆 **Status:** {'Survivor' if any(s[0] == user_id for s in survivors) else 'Eliminated'}\\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in debug command: {e}")
        await update.message.reply_text(f"❌ Debug error: {e}")

async def export_data_to_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TEMPORARY: Export ALL database data to logs for migration from Render"""
    try:
        import sqlite3
        import json
        
        # Connect to database
        conn = sqlite3.connect("lastman.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        data = {}
        total_rows = 0
        
        # Export each table with detailed logging
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            data[table] = [dict(row) for row in rows]
            total_rows += len(rows)
            logger.info(f"Exported {len(rows)} rows from table '{table}'")
        
        # Log summary first
        logger.info(f"=== EXPORT SUMMARY ===")
        logger.info(f"Total tables: {len(tables)}")
        logger.info(f"Total rows: {total_rows}")
        logger.info(f"Tables: {', '.join(tables)}")
        
        # Log the complete data (this will appear in Render logs)
        logger.info("=== DATABASE EXPORT START ===")
        logger.info(json.dumps(data, indent=2, default=str))
        logger.info("=== DATABASE EXPORT END ===")
        
        conn.close()
        
        await update.message.reply_text(f"✅ Complete data exported to logs!\n📊 {len(tables)} tables, {total_rows} total rows\n📋 Tables: {', '.join(tables)}\n\nCheck Render logs for JSON data between START/END markers.")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Export failed: {str(e)}")
        logger.error(f"Export command error: {e}")

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
        logger.error(f"Error in round_info: {e}")
        await update.message.reply_text("❌ Error getting gameweek information. Please try again.")

async def kill_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only command to eliminate a user from current competition (only @ineedauser)"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Only allow in groups
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This bot only works in group chats! Add me to a group to play.")
        return
    
    # Check if user is @ineedauser (replace with actual username check)
    if user.username != "ineedauser":
        await update.message.reply_text("❌ Only @ineedauser can use this command!")
        return
    
    try:
        # Check if a target user was specified
        if not context.args:
            await update.message.reply_text("❌ Please specify a user to eliminate!\nUsage: /kill @username or /kill firstname")
            return
        
        target_input = " ".join(context.args).strip()
        
        # Remove @ if present
        if target_input.startswith("@"):
            target_input = target_input[1:]
        
        # Get all current survivors in this group
        survivors = db.get_current_survivors(chat_id)
        
        # Find the target user
        target_user = None
        for user_id, username, first_name, last_name in survivors:
            if (username and username.lower() == target_input.lower()) or \
               (first_name and first_name.lower() == target_input.lower()) or \
               (last_name and last_name.lower() == target_input.lower()):
                target_user = (user_id, username, first_name, last_name)
                break
        
        if not target_user:
            await update.message.reply_text(f"❌ User '{target_input}' not found in current survivors!")
            return
        
        user_id, username, first_name, last_name = target_user
        display_name = first_name if first_name else username
        
        # Eliminate the user from this group only
        db.eliminate_user(user_id, chat_id)
        
        # Send confirmation message
        await update.message.reply_text(f"💀 **ADMIN ELIMINATION**\n\n{display_name} has been eliminated from the current competition by admin command!\n\n⚰️ RIP {display_name} - eliminated by the powers that be!")
        
        logger.info(f"Admin {user.username} eliminated user {display_name} ({user_id}) from group {chat_id}")
        
    except Exception as e:
        logger.error(f"Error in kill command: {e}")
        await update.message.reply_text(f"❌ Error eliminating user: {str(e)}")

async def revive_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only command to restore a user to current competition (only @ineedauser)"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Only allow in groups
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This bot only works in group chats! Add me to a group to play.")
        return
    
    # Check if user is @ineedauser
    if user.username != "ineedauser":
        await update.message.reply_text("❌ Only @ineedauser can use this command!")
        return
    
    try:
        # Check if a target user was specified
        if not context.args:
            await update.message.reply_text("❌ Please specify a user to revive!\nUsage: /revive @username or /revive firstname")
            return
        
        target_input = " ".join(context.args).strip()
        
        # Remove @ if present
        if target_input.startswith("@"):
            target_input = target_input[1:]
        
        # Get all group members (including eliminated ones)
        session = db.Session()
        try:
            from database_postgres import GroupMember, User
            
            # Find eliminated group members
            eliminated_members = session.query(GroupMember, User).join(
                User, GroupMember.user_id == User.user_id
            ).filter(
                GroupMember.chat_id == chat_id,
                GroupMember.is_active == False
            ).all()
            
            # Find the target user
            target_user = None
            for member, user_obj in eliminated_members:
                if (user_obj.username and user_obj.username.lower() == target_input.lower()) or \
                   (user_obj.first_name and user_obj.first_name.lower() == target_input.lower()) or \
                   (user_obj.last_name and user_obj.last_name.lower() == target_input.lower()):
                    target_user = (member.user_id, user_obj.username, user_obj.first_name, user_obj.last_name)
                    break
            
            if not target_user:
                await update.message.reply_text(f"❌ Eliminated user '{target_input}' not found in this group!")
                return
            
            user_id, username, first_name, last_name = target_user
            display_name = first_name if first_name else username
            
            # Revive the user (reactivate in group)
            member = session.query(GroupMember).filter_by(
                user_id=user_id, 
                chat_id=chat_id
            ).first()
            
            if member:
                member.is_active = True
                
                # Also reactivate the user globally if needed
                user_obj = session.query(User).filter_by(user_id=user_id).first()
                if user_obj:
                    user_obj.is_active = True
                
                session.commit()
                
                # Send confirmation message
                await update.message.reply_text(f"🔥 **ADMIN REVIVAL**\n\n{display_name} has been brought back from the dead!\n\n✨ Welcome back to the competition, {display_name}! You've been given a second chance!")
                
                logger.info(f"Admin {user.username} revived user {display_name} ({user_id}) in group {chat_id}")
            else:
                await update.message.reply_text(f"❌ Could not find group membership for {display_name}")
                
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Error in revive command: {e}")
        await update.message.reply_text(f"❌ Error reviving user: {str(e)}")

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
                    display_name = db.get_display_name(user_id, username)
                    names.append(display_name)
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
                    logger.info(f"Sent reminder to group {chat_title} ({chat_id})")
                except Exception as e:
                    logger.error(f"Failed to send reminder to group {chat_id}: {e}")
                    
    except Exception as e:
        logger.error(f"Error in send_reminder_to_groups: {e}")

async def send_winner_announcement(winner_name, gameweek, chat_id):
    """Send winner announcement to specific group"""
    try:
        message = f"🏆 **WE HAVE A WINNER!** 🏆\n\n"
        message += f"🎉 **CONGRATULATIONS {winner_name.upper()}!** 🎉\n\n"
        message += f"🥇 You are the LAST MAN STANDING after Gameweek {gameweek}!\n\n"
        message += f"👑 **CHAMPION OF THE COMPETITION!** 👑\n"
        message += f"🏆 Your name will be forever remembered in the Hall of Fame!\n\n"
        message += f"🎆 **VICTORY CELEBRATION!** 🎆\n"
        message += f"🍾 Pop the champagne, {winner_name}! You've earned it!\n\n"
        message += f"🔄 A new competition will begin shortly...\n"
        message += f"🎯 Will anyone be able to dethrone our champion?"
        
        # Send to specific group
        try:
            await application.bot.send_message(
                chat_id=chat_id,
                text=message
            )
            logger.info(f"Sent winner announcement to group {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send winner announcement to group {chat_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in send_winner_announcement: {e}")

async def send_competition_reset_announcement(chat_id):
    """Send competition reset announcement to specific group"""
    try:
        message = f"🔄 **COMPETITION RESET!** 🔄\n\n"
        message += f"🎉 A new Last Man Standing competition has begun!\n\n"
        message += f"✅ **Everyone can rejoin!**\n"
        message += f"🔓 **All teams are available again!**\n"
        message += f"🚫 **Blocked teams have been cleared!**\n\n"
        message += f"💡 Use `/start` to rejoin the competition\n"
        message += f"⚽ Use `/pick TeamName` to make your first pick\n\n"
        message += f"🏆 **Good luck, survivors!** 🍀"
        
        # Send to specific group
        try:
            await application.bot.send_message(
                chat_id=chat_id,
                text=message
            )
            logger.info(f"Sent competition reset announcement to group {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send reset announcement to group {chat_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in send_competition_reset_announcement: {e}")

async def roast_deadline_missers(missed_users, gameweek, chat_id):
    """Send funny roast messages for users who missed the deadline to specific group"""
    try:
        if not missed_users:
            return
        
        # Create roast message for deadline missers
        if len(missed_users) == 1:
            user_id, username, first_name, last_name = missed_users[0]
            display_name = first_name if first_name else username
            
            # Pick random deadline roast message
            roast_template = random.choice(DEADLINE_MISS_ROASTS)
            message = roast_template.format(username=display_name)
            message += f"\n\n⏰ **Gameweek {gameweek} Deadline Miss Report** ⏰"
            
        else:
            # Multiple deadline missers
            names = []
            for user_id, username, first_name, last_name in missed_users:
                display_name = first_name if first_name else username
                names.append(display_name)
            
            message = f"🤦‍♂️ **MASS DEADLINE DISASTER!** 🤦‍♂️\n\n"
            message += f"⏰ The following {len(missed_users)} muppets forgot to pick for Gameweek {gameweek}:\n"
            message += f"🤡 {', '.join(names)}\n\n"
            message += f"📱 Did you all lose your phones? Set some alarms next time! ⏰\n"
            message += f"⚰️ All eliminated for deadline negligence! ⚰️"
        
        # Send to specific group
        try:
            await application.bot.send_message(
                chat_id=chat_id,
                text=message
            )
            logger.info(f"Sent deadline miss roast to group {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send deadline roast to group {chat_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in roast_deadline_missers: {e}")

async def roast_eliminated_users(eliminated_users, gameweek, chat_id, all_eliminated=False):
    """Send savage elimination messages to specific group"""
    try:
        if not eliminated_users:
            return
        
        # Special message if everyone was eliminated (no joint winners rule)
        if all_eliminated:
            names = []
            for user_id, username, first_name, last_name in eliminated_users:
                display_name = first_name if first_name else username
                names.append(display_name)
            
            message = f"💀 **TOTAL ANNIHILATION!** 💀\n\n"
            message += f"🚫 **NO JOINT WINNERS ALLOWED!** 🚫\n\n"
            message += f"💥 ALL {len(eliminated_users)} remaining players have been ELIMINATED in Gameweek {gameweek}!\n\n"
            message += f"🎪 The fallen: {', '.join(names)}\n\n"
            message += f"🤡 Nobody won, so EVERYBODY LOSES! What a disaster! 💸\n"
            message += f"🏆 **THE COMPETITION IS OVER!** 🏆\n"
            message += f"🗑️ Better luck next season, you absolute muppets! 📺"
            
        # Create elimination message for normal eliminations
        elif len(eliminated_users) == 1:
            user_id, username, first_name, last_name = eliminated_users[0]
            display_name = first_name if first_name else username
            
            # Pick random roast message
            roast_template = random.choice(ELIMINATION_ROASTS)
            message = roast_template.format(username=display_name)
            message += f"\n\n📊 **Gameweek {gameweek} Casualty Report** 📊"
            
        else:
            # Multiple eliminations (but not everyone)
            names = []
            for user_id, username, first_name, last_name in eliminated_users:
                display_name = first_name if first_name else username
                names.append(display_name)
            
            message = f"💥 **MASS ELIMINATION EVENT!** 💥\n\n"
            message += f"💀 The following {len(eliminated_users)} clowns got DESTROYED in Gameweek {gameweek}:\n"
            message += f"🎪 {', '.join(names)}\n\n"
            message += f"🤡 What a bunch of muppets! Your football knowledge is TRAGIC! 💸\n"
            message += f"🗑️ Time to stick to something easier... like tic-tac-toe! ❌⭕"
        
        # Send to specific group
        try:
            await application.bot.send_message(
                chat_id=chat_id,
                text=message
            )
            logger.info(f"Sent elimination roast to group {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send elimination roast to group {chat_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in roast_eliminated_users: {e}")

async def lifelines_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available and used lifelines with details"""
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Get lifeline manager
        if 'lifeline_manager' not in context.bot_data or context.bot_data['lifeline_manager'] is None:
            await update.message.reply_text("❌ Lifelines are not properly initialized. Please contact the bot administrator.")
            return
        
        lifeline_manager = context.bot_data['lifeline_manager']
        league_id = "global"
        season = get_season()
        
        try:
            # Get available lifelines
            lifelines = lifeline_manager.get_available_lifelines(chat_id, user_id, league_id, season)
            
            # Get used lifelines
            used_lifelines = []
            with db.engine.connect() as conn:
                result = conn.execute(text('''
                    SELECT lifeline_type, used_at, target_user_id, details
                    FROM lifeline_usage
                    WHERE chat_id = :chat_id 
                    AND user_id = :user_id 
                    AND league_id = :league_id 
                    AND season = :season
                    ORDER BY used_at DESC
                '''), {
                    'chat_id': chat_id,
                    'user_id': user_id,
                    'league_id': league_id,
                    'season': season
                })
                used_lifelines = result.fetchall()
            
            # Build response
            response = "🎮 *Your Lifelines* 🎮\n\n"
            
            # Show available lifelines
            response += "*Available Lifelines:*\n"
            if lifelines:
                for lifeline_id, lifeline in lifelines.items():
                    status = "✅ Available" if lifeline['remaining'] > 0 else "❌ Used up"
                    response += (
                        f"• *{lifeline['name']}* - {status}\n"
                        f"  {lifeline['description']}\n"
                        f"  Uses left: {lifeline['remaining']}/{lifeline['total_allowed']}\n\n"
                    )
            else:
                response += "No lifelines available for this season.\n\n"
            
            # Show used lifelines
            if used_lifelines:
                response += "\n*Used Lifelines:*\n"
                for lifeline in used_lifelines:
                    lifeline_type, used_at, target_id, details = lifeline
                    lifeline_info = {
                        'coinflip': {'name': 'Coinflip', 'description': '50% chance to revive in current round'},
                        'goodluck': {'name': 'Good Luck', 'description': 'Forced opponent to pick from bottom 6'},
                        'forcechange': {'name': 'Force Change', 'description': 'Forced opponent to change their pick'}
                    }.get(lifeline_type, {'name': lifeline_type, 'description': ''})
                    
                    used_time = used_at.strftime("%Y-%m-%d %H:%M")
                    target_info = f" on <user>{target_id}</user>" if target_id else ""
                    details_text = f"\n   - {details}" if details else ""
                    
                    response += (
                        f"• *{lifeline_info['name']}* (Used: {used_time}{target_info}){details_text}\n"
                    )
            
            # Add usage instructions
            response += "\n💡 *How to use lifelines:*\n"
            response += "• `/uselifeline coinflip` - 50/50 chance to revive in current round\n"
            response += "• `/uselifeline goodluck @username` - Force user to pick from bottom 6 teams\n"
            response += "• `/uselifeline forcechange @username` - Force user to change their team"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in lifelines command: {e}")
            await update.message.reply_text("❌ An error occurred while retrieving lifelines. Please try again later.")
            
    except Exception as e:
        logger.error(f"Error in lifelines command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again later.")

async def use_lifeline_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Use a lifeline"""
    if not context.args:
        await update.message.reply_text(
            "Please specify a lifeline to use.\n"
            "Available lifelines: coinflip, goodluck, forcechange\n"
            "Example: `/uselifeline coinflip` or `/uselifeline goodluck @username`",
            parse_mode='Markdown'
        )
        return
    
    lifeline_type = context.args[0].lower()
    target_user = None
    
    # Check if a target user was mentioned
    if len(context.args) > 1:
        # Extract username from mention or use as is
        mention = context.args[1]
        if mention.startswith('@'):
            target_user = mention[1:]
        else:
            target_user = mention
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    season = get_season()
    
    # For now, use a default league ID
    league_id = "global"
    
    # Use the lifeline
    success, message = lifeline_manager.use_lifeline(
        chat_id=chat_id,
        user_id=user_id,
        league_id=league_id,
        lifeline_type=lifeline_type,
        season=season,
        target_user_id=target_user
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def check_for_eliminations():
    """Check if gameweek has ended and process eliminations with roasting per group"""
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
                # Get all groups to process eliminations per group
                groups = db.get_all_groups()
                
                for chat_id, chat_title, chat_type in groups:
                    # Process eliminations for this specific group
                    eliminated_users = []
                    surviving_users = []
                    missed_deadline_users = []
                    
                    # Get all active users in this group and check who made picks
                    all_active_users = db.get_current_survivors(chat_id)
                    users_with_picks = db.get_users_with_picks_for_round(current_gameweek, chat_id)
                    
                    # SAFETY CHECK: If database is wiped/empty, don't process eliminations
                    # This prevents false elimination messages when there are no users or picks
                    if not all_active_users and not users_with_picks:
                        logging.info(f"Skipping elimination processing for group {chat_title} - no active users or picks found (possible database wipe)")
                        continue
                    
                    # ADDITIONAL SAFETY: If there are users but no picks at all, it might be a fresh start
                    # Only skip if ALL users have no picks (indicating fresh competition or database issue)
                    if all_active_users and not users_with_picks:
                        logging.info(f"Skipping elimination processing for group {chat_title} - users exist but no picks found for gameweek {current_gameweek} (possible fresh start or database issue)")
                        continue
                    
                    # Find users who missed the deadline in this group
                    users_with_picks_ids = {user_id for user_id, _, _, _ in users_with_picks}
                    for user_id, username, first_name, last_name in all_active_users:
                        if user_id not in users_with_picks_ids:
                            missed_deadline_users.append((user_id, username, first_name, last_name))
                            eliminated_users.append((user_id, username, first_name, last_name))
                            display_name = first_name if first_name else username
                            logging.info(f"Eliminated user {display_name} ({user_id}) from group {chat_title} - missed deadline")
                
                    # Process users who made picks in this group
                    for user_id, username, first_name, last_name in users_with_picks:
                        # Get the user's pick for this round
                        pick_info = db.get_user_pick_for_round(user_id, current_gameweek)
                        if not pick_info:
                            continue
                        
                        team_name, team_id, result = pick_info
                        
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
                        
                        # Categorize users based on their team's performance
                        if team_won:
                            surviving_users.append((user_id, username, first_name, last_name))
                        else:
                            eliminated_users.append((user_id, username, first_name, last_name))
                            display_name = first_name if first_name else username
                            logging.info(f"Eliminated user {display_name} ({user_id}) from group {chat_title} - team {team_name} didn't win")
                    
                    # Send deadline miss roasts first if anyone missed the deadline in this group
                    if missed_deadline_users:
                        await roast_deadline_missers(missed_deadline_users, current_gameweek, chat_id)
                    
                    # Check if we have a single winner in this group
                    if len(surviving_users) == 1 and eliminated_users:
                        winner_user_id, winner_username, winner_first_name, winner_last_name = surviving_users[0]
                        winner_display_name = winner_first_name if winner_first_name else winner_username
                        
                        # Add winner to winners table for this group
                        db.add_winner(winner_user_id, chat_id)
                        
                        # Eliminate all users in this group and reset competition for this group
                        for user_id, username in eliminated_users:
                            db.eliminate_user(user_id)
                        db.eliminate_user(winner_user_id)  # Winner also gets "eliminated" to reset
                        
                        # Send winner announcement to this group
                        await send_winner_announcement(winner_display_name, current_gameweek, chat_id)
                        
                        # Reset the competition automatically for this group
                        try:
                            new_competition_id = db.reset_competition(chat_id)
                            # Reset rollover count for this group
                            db.reset_rollover(chat_id)
                            logging.info(f"Competition won by {winner_display_name} in group {chat_title}! New competition ID: {new_competition_id}")
                            
                            # Send reset announcement to this group
                            await send_competition_reset_announcement(chat_id)
                            
                        except Exception as e:
                            logger.error(f"Error resetting competition for group {chat_id}: {e}")
                    
                    # NO JOINT WINNERS RULE: If no one won in this group, eliminate everyone
                    elif not surviving_users and eliminated_users:
                        logging.info(f"No winners in gameweek {current_gameweek} in group {chat_title} - all remaining players eliminated!")
                        # All users are already in eliminated_users, just eliminate them
                        for user_id, username in eliminated_users:
                            db.eliminate_user(user_id)
                        
                        # Send special message for total elimination to this group
                        await roast_eliminated_users(eliminated_users, current_gameweek, chat_id, all_eliminated=True)
                        
                        # Reset the competition automatically for this group
                        try:
                            new_competition_id = db.reset_competition(chat_id)
                            # Reset rollover count for this group
                            db.reset_rollover(chat_id)
                            logging.info(f"Competition automatically reset for group {chat_title}! New competition ID: {new_competition_id}")
                            
                            # Send reset announcement to this group
                            await send_competition_reset_announcement(chat_id)
                            
                        except Exception as e:
                            logger.error(f"Error resetting competition for group {chat_id}: {e}")
                        
                    elif eliminated_users:
                        # Normal elimination - some won, some lost in this group
                        for user_id, username in eliminated_users:
                            db.eliminate_user(user_id)
                    
                    # Send normal roasting messages to this group (excluding deadline missers as they were roasted separately)
                    non_deadline_eliminated = [(uid, uname) for uid, uname in eliminated_users if (uid, uname) not in missed_deadline_users]
                    if non_deadline_eliminated:
                        await roast_eliminated_users(non_deadline_eliminated, current_gameweek, chat_id)
                    
    except Exception as e:
        logger.error(f"Error in check_for_eliminations: {e}")

def check_and_send_reminders():
    """Wrapper function for scheduler"""
    if application:
        asyncio.create_task(send_reminder_to_groups())
        asyncio.create_task(check_for_eliminations())

# ============================================================================
# BACKGROUND SCHEDULER
# ============================================================================

def keep_alive():
    """Ping the health endpoint to keep Render service awake"""
    try:
        # Only ping if we're on Render (PORT env var exists)
        if os.environ.get('PORT'):
            port = os.environ.get('PORT')
            # Try multiple endpoints to ensure activity
            endpoints = ['/health', '/']
            for endpoint in endpoints:
                try:
                    response = requests.get(f"http://localhost:{port}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        logger.info(f"Keep-alive ping successful to {endpoint}")
                        break
                except:
                    continue
            
            # Also ping external health check services (optional)
            try:
                # Ping a reliable external service to generate network activity
                requests.get("https://httpbin.org/status/200", timeout=5)
                logger.debug("External keep-alive ping sent")
            except:
                pass  # External ping is optional
                
    except Exception as e:
        logger.debug(f"Keep-alive ping failed (this is normal): {e}")

def check_automatic_rollovers():
    """Check all groups for competitions that should automatically rollover"""
    try:
        current_gameweek = get_current_gameweek()
        
        # Get all active groups
        all_groups = db.get_all_groups()
        
        for chat_id, chat_title, chat_type in all_groups:
            try:
                # Check if picks are closed for current gameweek (meaning round is over)
                picks_allowed = football_api.is_picks_allowed(current_gameweek)
                
                if not picks_allowed:  # Round is over
                    # Get survivors for this group
                    survivors = db.get_current_survivors(chat_id)
                    
                    # If multiple survivors, automatic rollover needed
                    if len(survivors) > 1:
                        logger.info(f"Auto-rollover detected for group {chat_id}: {len(survivors)} survivors")
                        
                        # Increment rollover count
                        db.increment_rollover(chat_id)
                        
                        # Reset competition to start fresh round
                        db.reset_competition(chat_id)
                        
                        # Send notification to group
                        if application:
                            message = f"🔄 **Automatic Rollover Applied!**\\n\\n"
                            message += f"👥 **{len(survivors)} survivors remain**\\n"
                            message += f"💰 **Pot increased for next competition!**\\n\\n"
                            message += f"🎯 **New competition starting - good luck!**"
                            
                            # Send message to group
                            asyncio.create_task(
                                application.bot.send_message(chat_id=chat_id, text=message)
                            )
                            
                    elif len(survivors) == 1:
                        # Single winner - competition complete, reset rollover
                        winner_id, winner_username = survivors[0]
                        logger.info(f"Winner detected for group {chat_id}: {winner_username} ({winner_id})")
                        
                        # Add winner to winners table
                        db.add_winner(winner_id, chat_id)
                        
                        # Reset rollover count (winner found)
                        db.reset_rollover(chat_id)
                        
                        # Reset competition for new season
                        db.reset_competition(chat_id)
                        
                        # Send winner notification
                        if application:
                            message = f"🏆 **WINNER FOUND!**\\n\\n"
                            message += f"👑 **{winner_username or f'User{winner_id}'} wins the competition!**\\n\\n"
                            message += f"💰 **Congratulations on your victory!**\\n"
                            message += f"🎯 **New competition starting with fresh pot!**"
                            
                            asyncio.create_task(
                                application.bot.send_message(chat_id=chat_id, text=message)
                            )
                            
            except Exception as e:
                logger.error(f"Error checking rollover for group {chat_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in automatic rollover check: {e}")

def run_scheduler():
    """Run the reminder and elimination scheduler in a separate thread."""
    # Check for reminders and eliminations every hour
    schedule.every().hour.do(check_and_send_reminders)
    
    # Check for automatic rollovers daily at 10 AM
    schedule.every().day.at("10:00").do(check_automatic_rollovers)
    
    # Aggressive keep-alive strategy for Render free tier
    if os.environ.get('PORT'):
        # Multiple keep-alive intervals to prevent sleeping
        schedule.every(5).minutes.do(keep_alive)   # Every 5 minutes
        schedule.every(10).minutes.do(keep_alive)  # Every 10 minutes (backup)
        schedule.every(14).minutes.do(keep_alive)  # Just before 15min timeout
        logger.info("Aggressive keep-alive schedule activated for Render deployment")
    else:
        # Less frequent for local development
        schedule.every(30).minutes.do(keep_alive)
        logger.info("Standard keep-alive schedule for local development")
    
    while True:
        schedule.run_pending()
        time.sleep(30)  # Check every 30 seconds for more responsive keep-alive

# ============================================================================
# HEALTH CHECK SERVER (for Render deployment)
# ============================================================================

class HealthHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks"""
    
    def do_GET(self):
        """Handle GET requests for health checks"""
        if self.path in ['/', '/health']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'status': 'healthy',
                'service': 'Last Man Standing Bot',
                'timestamp': datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to reduce logging noise"""
        pass

def continuous_keep_alive():
    """Continuous background keep-alive thread for maximum uptime"""
    if not os.environ.get('PORT'):
        return  # Only run on Render
    
    port = os.environ.get('PORT')
    logger.info("Starting continuous keep-alive monitor")
    
    while True:
        try:
            # Self-ping every 3 minutes as a safety net
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                logger.debug("Continuous keep-alive successful")
            time.sleep(180)  # 3 minutes
        except Exception as e:
            logger.debug(f"Continuous keep-alive failed: {e}")
            time.sleep(60)  # Retry in 1 minute if failed

def run_health_server():
    """Run the health check server in a separate thread"""
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting health server on 0.0.0.0:{port}")
    
    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        logger.info(f"Health server successfully bound to port {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Failed to start health server: {e}")
        raise

async def admin_add_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to manually add a pick for a player
    
    Usage: /addpick @username TeamName [Gameweek]
    """
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Only allow in groups
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in group chats!")
        return
    
    # Check if user is admin
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Only administrators can use this command!")
            return
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        await update.message.reply_text("❌ Error verifying admin status.")
        return
    
    # Check command format
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Invalid format. Usage: /addpick @username TeamName [Gameweek]\n"
            "Example: /addpick @john_doe Liverpool"
        )
        return
    
    # Parse command arguments
    try:
        username = context.args[0].lstrip('@')
        team_name = ' '.join(context.args[1:-1]) if len(context.args) > 2 else context.args[1]
        gameweek = int(context.args[-1]) if len(context.args) > 2 and context.args[-1].isdigit() else get_current_gameweek()
        
        # Get user ID from username
        user_id = None
        if username.isdigit():
            user_id = int(username)
        else:
            # Search for user by username
            chat_members = await context.bot.get_chat_members(chat_id)
            for member in chat_members:
                if member.user.username and member.user.username.lower() == username.lower():
                    user_id = member.user.id
                    break
            
            if not user_id:
                await update.message.reply_text(f"❌ Could not find user @{username} in this group.")
                return
        
        # Search for team
        team_info = football_api.search_team(team_name, DEFAULT_LEAGUE)
        if not team_info:
            await update.message.reply_text(f"❌ Could not find team '{team_name}'. Please check spelling.")
            return
        
        # Add pick to database
        db.add_pick(user_id, gameweek, team_info['name'], team_info['id'], None, chat_id)
        
        # Get user's display name
        member = await context.bot.get_chat_member(chat_id, user_id)
        display_name = member.user.first_name
        if member.user.last_name:
            display_name += f" {member.user.last_name}"
        
        await update.message.reply_text(
            f"✅ Successfully added pick for {display_name}:\n"
            f"🏆 Team: {team_info['name']}\n"
            f"📅 Gameweek: {gameweek}\n"
            f"👤 User: @{member.user.username or 'N/A'}"
        )
        
    except Exception as e:
        logger.error(f"Error in admin_add_pick: {e}")
        await update.message.reply_text("❌ An error occurred while adding the pick. Please check the format and try again.")

async def debug_picks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to check pick-related issues"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    response = f"🔍 *Debugging Picks* 🔍\n\n"
    
    # Check if user exists in database
    user_data = db.get_user(user.id)
    if not user_data:
        response += "❌ *User not found in database*\n"
    else:
        response += f"✅ *User found in database* (ID: {user.id})\n"
    
    # Check if chat exists in database
    session = db.Session()
    chat_exists = session.query(Group).filter_by(chat_id=chat_id).first() is not None
    session.close()
    
    if not chat_exists:
        response += "❌ *Chat/Group not found in database*\n"
    else:
        response += f"✅ *Chat/Group found in database* (ID: {chat_id})\n"
    
    # Check user's picks
    picks = db.get_user_picks(user_id=user.id, chat_id=chat_id)
    
    if not picks:
        response += "\n❌ *No picks found* for your account in this chat.\n"
        
        # Check if there are any picks in the database at all
        session = db.Session()
        all_picks = session.query(Pick).filter_by(chat_id=chat_id).all()
        session.close()
        
        if all_picks:
            response += f"\nℹ️ Found {len(all_picks)} picks in this chat for other users.\n"
            
            # Check if user has picks in other chats
            user_picks_elsewhere = db.get_user_picks(user_id=user.id)
            if user_picks_elsewhere:
                response += f"\nℹ️ You have {len(user_picks_elsewhere)} picks in other chats.\n"
    else:
        response += f"\n✅ *Found {len(picks)} picks* in this chat.\n\n"
        response += "*Your Picks:*\n"
        for round_num, team, result in picks:
            status_emoji = {"win": "✅", "loss": "❌", "draw": "🟡", "pending": "⏳"}
            emoji = status_emoji.get(result, "❓")
            response += f"• Round {round_num}: {team} {emoji}\n"
    
    # Add database connection info
    response += "\n*Database Info:*\n"
    if hasattr(db, 'engine') and db.engine:
        response += f"• Database: {db.engine.url.database}\n"
    else:
        response += "• Database connection not properly initialized\n"
    
    await update.message.reply_text(response, parse_mode='Markdown')

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Initialize and start the Last Man Standing bot."""
    global application, db, football_api, lifeline_manager
    
    logger.info("Initializing Last Man Standing bot...")
    
    # Initialize database and core components
    db = Database()
    football_api = FootballAPI()
    
    # Create Telegram application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Initialize lifeline manager and store it in bot_data
    lifeline_manager = LifelineManager(db.engine)
    application.bot_data['lifeline_manager'] = lifeline_manager
    
    # Start health check server for Render (if PORT is set)
    if os.environ.get('PORT'):
        logger.info("Starting health check server for Render deployment...")
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.start()
        logger.info(f"Health server started on port {os.environ.get('PORT')}")
        
        # Start continuous keep-alive monitor for maximum uptime
        keep_alive_thread = threading.Thread(target=continuous_keep_alive, daemon=True)
        keep_alive_thread.start()
        logger.info("Continuous keep-alive monitor started")
    lifeline_manager = LifelineManager(db.engine)
    application.bot_data['lifeline_manager'] = lifeline_manager
    
    # Register command handlers
    command_handlers = [
        ("start", start),
        ("help", start),  # Help uses same handler as start
        ("pick", pick_team),
        ("change", change_pick),
        ("mypicks", my_picks),
        ("survivors", survivors),
        ("winners", winners),
        ("pot", pot),
        ("rollover", rollover),
        ("round", round_info),
        ("debug", debug_user_status),  # Debug command
        ("debug_picks", debug_picks),  # Debug picks command
        ("exportdata", export_data_to_logs),  # Temporary export command for migration
        ("kill", kill_user),  # Admin-only elimination command
        ("revive", revive_user),  # Admin-only revival command
        ("addpick", admin_add_pick),  # Admin-only add pick command
        ("lifelines", lifelines_command),  # Show available lifelines
        ("uselifeline", use_lifeline_command),  # Use a lifeline
    ]
    
    for command, handler in command_handlers:
        application.add_handler(CommandHandler(command, handler))
    
    logger.info(f"Registered {len(command_handlers)} command handlers")
    
    # Start background scheduler for reminders and eliminations
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Background scheduler started")
    
    # Start the bot
    logger.info("Last Man Standing bot is now running! 🏆⚽")
    try:
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise

if __name__ == '__main__':
    main()