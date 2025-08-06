# 24/7 Deployment Guide for Last Man Standing Bot

## Overview
To run your Telegram bot 24/7, you need a server or cloud service that stays online continuously. Here are your options:

## Option 1: Cloud Hosting (Recommended)

### A. Railway (Easiest)
1. **Sign up at [Railway.app](https://railway.app)**
2. **Connect your GitHub repository**
3. **Add environment variables in Railway dashboard:**
   - `TELEGRAM_BOT_TOKEN`: Your bot token
   - `FOOTBALL_API_KEY`: Your API key
4. **Deploy automatically**

### B. Heroku
1. **Install Heroku CLI**
2. **Create Heroku app:**
   ```bash
   heroku create your-bot-name
   ```
3. **Set environment variables:**
   ```bash
   heroku config:set TELEGRAM_BOT_TOKEN=your_token
   heroku config:set FOOTBALL_API_KEY=your_key
   ```
4. **Deploy:**
   ```bash
   git push heroku main
   ```

### C. DigitalOcean App Platform
1. **Create account at DigitalOcean**
2. **Create new App**
3. **Connect GitHub repository**
4. **Add environment variables**
5. **Deploy**

### D. AWS/Google Cloud/Azure
- More complex but highly scalable
- Use their container services or VM instances

## Option 2: VPS (Virtual Private Server)

### Recommended VPS Providers:
- **DigitalOcean Droplets** ($4-6/month)
- **Linode** ($5/month)
- **Vultr** ($2.50-6/month)
- **AWS EC2** (Free tier available)

### VPS Setup Steps:
1. **Create Ubuntu 20.04+ server**
2. **Install Python and dependencies**
3. **Upload your bot code**
4. **Set up systemd service (see below)**
5. **Configure firewall**

## Option 3: Local Server/Raspberry Pi

### Requirements:
- Stable internet connection
- Computer/Raspberry Pi running 24/7
- Static IP or dynamic DNS

## Deployment Files

I've created the following files to help with deployment:

### For Cloud Platforms:
- `Procfile` - Heroku/Railway deployment
- `requirements.txt` - Already exists
- `runtime.txt` - Python version specification
- `docker-compose.yml` - Docker deployment

### For VPS/Local:
- `bot.service` - Systemd service file
- `deploy.sh` - Deployment script
- `supervisor.conf` - Process management

## Database Considerations

### For Production:
- **SQLite** (current): Fine for small-medium usage
- **PostgreSQL**: Better for high traffic
- **Cloud Database**: AWS RDS, Railway PostgreSQL, etc.

## Monitoring & Maintenance

### Health Checks:
- Monitor bot uptime
- Check API quotas
- Database backups
- Log monitoring

### Recommended Tools:
- **UptimeRobot** - Free uptime monitoring
- **Sentry** - Error tracking
- **Grafana** - Advanced monitoring

## Cost Estimates

| Option | Monthly Cost | Complexity | Reliability |
|--------|-------------|------------|-------------|
| Railway | $5-10 | Low | High |
| Heroku | $7-25 | Low | High |
| VPS | $4-10 | Medium | High |
| Local/Pi | $0 | High | Medium |

## Quick Start Recommendation

**For beginners:** Use Railway.app
1. Push code to GitHub
2. Connect Railway to your repo
3. Add environment variables
4. Deploy automatically

**For experienced users:** Use a VPS with systemd service
