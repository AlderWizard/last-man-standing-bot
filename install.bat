@echo off
echo 🏆 Last Man Standing Bot - Installation Script
echo ================================================

echo.
echo 📦 Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ❌ Failed to create virtual environment
    pause
    exit /b 1
)

echo.
echo 🔧 Activating virtual environment...
call .venv\Scripts\activate

echo.
echo 📥 Installing dependencies...
pip install -r last_man_standing_bot\requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ✅ Installation complete!
echo.
echo To run the bot:
echo 1. Activate virtual environment: .venv\Scripts\activate
echo 2. Run the bot: python run_bot.py
echo.
echo Or simply run: run_bot.py
echo.
pause
