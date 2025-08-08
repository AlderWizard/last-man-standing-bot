#!/bin/bash

# Last Man Standing Bot - VPS Deployment Script
# Run this script on your VPS to deploy the bot

set -e

echo "🏆 Last Man Standing Bot - VPS Deployment"
echo "=========================================="

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
echo "🐍 Installing Python and dependencies..."
sudo apt install -y python3 python3-pip python3-venv git

# Clone or update repository
if [ -d "last_man_standing_bot" ]; then
    echo "📁 Updating existing repository..."
    cd last_man_standing_bot
    git pull
else
    echo "📥 Cloning repository..."
    git clone <YOUR_REPO_URL> last_man_standing_bot
    cd last_man_standing_bot
fi

# Create virtual environment
echo "🔧 Setting up virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python packages..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f "last_man_standing_bot/.env" ]; then
    echo "⚙️ Creating .env file..."
    echo "Please enter your Telegram Bot Token:"
    read -r BOT_TOKEN
    echo "Please enter your Football API Key:"
    read -r API_KEY
    
    cat > last_man_standing_bot/.env << EOF
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
FOOTBALL_API_KEY=$API_KEY
EOF
    echo "✅ .env file created"
fi

# Set up systemd service
echo "🔧 Setting up systemd service..."
sudo cp bot.service /etc/systemd/system/
sudo sed -i "s|/home/ubuntu|$HOME|g" /etc/systemd/system/bot.service
sudo sed -i "s|ubuntu|$USER|g" /etc/systemd/system/bot.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable bot.service
sudo systemctl start bot.service

echo "✅ Deployment complete!"
echo ""
echo "Bot status: $(sudo systemctl is-active bot.service)"
echo ""
echo "Useful commands:"
echo "  Check status: sudo systemctl status bot.service"
echo "  View logs: sudo journalctl -u bot.service -f"
echo "  Restart bot: sudo systemctl restart bot.service"
echo "  Stop bot: sudo systemctl stop bot.service"
