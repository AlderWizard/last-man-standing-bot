# PostgreSQL Setup on Render

## Step 1: Create PostgreSQL Database on Render

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** → **"PostgreSQL"**
3. **Configure Database**:
   - **Name**: `last-man-standing-db` (or any name you prefer)
   - **Database**: `lastman` (database name)
   - **User**: `lastman` (username)
   - **Region**: Choose same as your web service
   - **PostgreSQL Version**: 15 (latest)
   - **Plan**: Free (0 GB storage, sufficient for bot data)

4. **Click "Create Database"**

## Step 2: Get Database Connection Details

After creation, you'll see:
- **Internal Database URL**: `postgresql://user:password@hostname:port/database`
- **External Database URL**: `postgresql://user:password@hostname:port/database`

**Copy the Internal Database URL** - this is what your bot will use.

## Step 3: Add Database URL to Web Service

1. **Go to your Web Service** in Render dashboard
2. **Click "Environment"** tab
3. **Add Environment Variable**:
   - **Key**: `DATABASE_URL`
   - **Value**: Paste the Internal Database URL from Step 2

4. **Click "Save Changes"**

## Step 4: Deploy Updated Bot

Your bot code is already updated to use PostgreSQL. When you deploy:

1. **Automatic Migration**: Bot will detect `DATABASE_URL` and use PostgreSQL
2. **Table Creation**: All tables will be created automatically on first run
3. **Data Persistence**: All user data, picks, and game state will persist across restarts

## Step 5: Verify Setup

After deployment:

1. **Check Logs**: Look for "Connected to PostgreSQL database" message
2. **Test Bot**: Add to Telegram group and run `/start`
3. **Make Picks**: Users can make picks with `/pick TeamName`
4. **Restart Test**: Redeploy the service - data should persist!

## Local Development

For local development, the bot will automatically use SQLite if no `DATABASE_URL` is set. This allows you to:

- **Develop locally** with SQLite (no PostgreSQL needed)
- **Deploy to production** with PostgreSQL automatically
- **No code changes** needed between environments

## Troubleshooting

**Connection Issues**:
- Ensure DATABASE_URL is correctly set in environment variables
- Check that PostgreSQL database is running in Render dashboard
- Verify the Internal Database URL (not External) is used

**Migration Issues**:
- Tables are created automatically on first connection
- If issues occur, check Render logs for SQLAlchemy errors
- Database will be empty initially (users need to re-register)

## Data Recovery

Since this is a migration from SQLite to PostgreSQL:
- **Previous data is lost** (SQLite was ephemeral on Render)
- **Users need to re-register** with `/start`
- **New picks will persist** across all future deployments/restarts
