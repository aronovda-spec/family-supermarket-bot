# 🚀 Deployment Guide for Family Shopping List Bot

## Deploy to Render.com

### Prerequisites
- GitHub account
- Render.com account (free)
- Bot token from @BotFather

### Step 1: Upload to GitHub

1. **Create a new repository on GitHub:**
   - Go to https://github.com/new
   - Repository name: `family-shopping-bot`
   - Make it **Public** (required for free Render)
   - Don't initialize with README

2. **Upload your files:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Family Shopping List Bot"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/family-shopping-bot.git
   git push -u origin main
   ```

### Step 2: Deploy on Render

1. **Go to Render.com:**
   - Visit https://render.com
   - Sign up/Login with GitHub

2. **Create New Worker Service:**
   - Click "New +" → "Background Worker"
   - Connect your GitHub repository
   - Select your `family-shopping-bot` repository

3. **Configure Service:**
   - **Name:** `family-shopping-bot`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python start_render.py`
   - **Plan:** Free
   - **Type:** Worker (not Web Service)

4. **Add Environment Variables:**
   - Click "Add Environment Variable"
   - **Key:** `BOT_TOKEN`
   - **Value:** Your bot token from @BotFather
   - Click "Add"

5. **Deploy:**
   - Click "Create Web Service"
   - Wait for deployment (2-3 minutes)
   - Your bot will be live!

### Step 3: Test Your Bot

1. **Find your bot on Telegram:**
   - Search for your bot username
   - Send `/start` command
   - Test all features!

### Files Included:
- `bot.py` - Main bot logic
- `config.py` - Configuration and messages
- `database.py` - Database operations
- `run_bot.py` - Bot runner
- `start_render.py` - Combined startup script for Render
- `health_check.py` - Health check server
- `keep_alive.py` - Keep alive script
- `requirements.txt` - Python dependencies
- `render.yaml` - Render configuration
- `Procfile` - Process configuration

### Features:
✅ Multi-language support (English/Hebrew)
✅ Family shopping list management
✅ Category-based item selection
✅ Search functionality
✅ Item suggestions with admin approval
✅ Broadcast messaging
✅ User management
✅ Persistent menu
✅ Weekly list reset

### Sleep Prevention:
The bot includes several features to prevent Render's free tier from sleeping:

1. **Worker Service**: Uses Background Worker instead of Web Service
2. **Health Check**: Runs a health check server on port 8000
3. **Keep Alive**: Automatically pings the service every 5 minutes
4. **Combined Startup**: Runs both bot and health check together

### Important Notes:
- **Free Tier**: Render's free tier may still sleep after 15 minutes of inactivity
- **Upgrade**: Consider upgrading to paid plan for 24/7 uptime
- **Monitoring**: Check Render dashboard for service status
- **Logs**: Monitor logs for any issues

### Support:
If you need help, check the logs in Render dashboard or contact support.
