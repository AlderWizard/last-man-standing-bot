@echo off
echo 🚀 Last Man Standing Bot - GitHub Push Script
echo =============================================

echo.
echo 📝 Setting up Git repository...

REM Initialize git repository
git init

REM Configure git (you'll need to replace with your info)
echo Please enter your GitHub username:
set /p USERNAME=
echo Please enter your email:
set /p EMAIL=

git config user.name "%USERNAME%"
git config user.email "%EMAIL%"

REM Add all files
echo 📦 Adding files to repository...
git add .

REM Create initial commit
echo 💾 Creating initial commit...
git commit -m "Initial commit: Last Man Standing Telegram Bot"

REM Add remote origin (you'll need to replace with your repo URL)
echo Please enter your GitHub repository URL (e.g., https://github.com/yourusername/last-man-standing-bot.git):
set /p REPO_URL=
git remote add origin %REPO_URL%

REM Push to GitHub
echo 🚀 Pushing to GitHub...
git branch -M main
git push -u origin main

echo.
echo ✅ Successfully pushed to GitHub!
echo You can now deploy to Railway.app or other hosting platforms.
echo.
pause
