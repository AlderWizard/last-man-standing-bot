#!/bin/bash

# Last Man Standing Bot - One-Command Raspberry Pi Deployment
# Copy and paste this entire script into your Pi terminal

echo "🏆 Last Man Standing Bot - Raspberry Pi Deployment"
echo "=================================================="

# Clone the repository
echo "📥 Cloning bot code from GitHub..."
cd /home/raspberrypi
git clone https://github.com/AlderWizard/last-man-standing-bot.git
cd last-man-standing-bot

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
echo "🐍 Installing Python and dependencies..."
sudo apt install -y python3 python3-pip python3-venv git

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
    echo "✅ Environment file created!"
fi

# Copy and setup systemd service
echo "🔧 Setting up systemd service..."
sudo cp bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bot.service
sudo systemctl start bot.service

echo "🎉 Deployment complete!"
echo "📊 Checking bot status..."
sudo systemctl status bot.service

echo ""
echo "✅ Your bot is now running 24/7!"
echo "🔄 It will automatically restart if it crashes"
echo "🚀 It will start automatically when Pi boots"
echo ""
echo "To check logs: sudo journalctl -u bot.service -f"
echo "To restart: sudo systemctl restart bot.service"
echo "To stop: sudo systemctl stop bot.service"
