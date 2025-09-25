# 🛠️ Developer Mode Setup Guide

## 🎯 Overview

This setup allows you to run a separate developer bot for testing without interfering with your production bot.

## 📋 Setup Steps

### **Step 1: Create Developer Bot**

1. **Go to @BotFather on Telegram**
2. **Create a new bot**: `/newbot`
3. **Choose a name**: `YourBotName Dev` (or similar)
4. **Get the token**: Save the token you receive

### **Step 2: Configure Environment**

1. **Copy the developer template**:
   ```bash
   cp bot_config.env.developer bot_config.env
   ```

2. **Edit `bot_config.env`**:
   ```env
   DEVELOPER_MODE=true
   DEV_BOT_TOKEN=your_developer_bot_token_here
   DEV_DATABASE_PATH=shopping_bot_dev.db
   ADMIN_IDS=your_user_id_here
   ```

### **Step 3: Run Developer Mode**

```bash
# Run in developer mode
python dev_start.py
```

You should see:
```
🛠️ Running in DEVELOPER MODE
📁 Using developer database: shopping_bot_dev.db
🛠️ Starting Shopping Bot in DEVELOPER MODE
```

## 🔄 Development Workflow

### **Testing New Features:**

1. **Develop locally** with `python dev_start.py`
2. **Test thoroughly** with your developer bot
3. **Commit changes** to `develop` branch
4. **Merge to `main`** when ready for production

### **Easy Merge Process:**

✅ **No file renaming needed!** The same files work for both modes:
- `bot.py` - Same code, different config
- `config.py` - Automatically detects mode
- `database.py` - Uses different database file

## 🚀 Production Deployment

### **Option 1: Environment Variable (Recommended)**
Set `DEVELOPER_MODE=false` in your production environment.

### **Option 2: Direct Production**
Just use your production `bot_config.env` without `DEVELOPER_MODE=true`.

## 📊 What's Different in Developer Mode

| Aspect | Developer Mode | Production Mode |
|--------|----------------|-----------------|
| **Bot Token** | `DEV_BOT_TOKEN` | `BOT_TOKEN` |
| **Database** | `shopping_bot_dev.db` | `shopping_bot.db` |
| **Users** | Test users only | Real users |
| **Data** | Safe to experiment | Real data |

## 🛡️ Safety Features

- **Separate databases** - No risk of corrupting production data
- **Separate bot tokens** - No interference with production bot
- **Environment detection** - Automatic mode switching
- **Clear logging** - Always know which mode you're in

## 🔧 Troubleshooting

### **"DEV_BOT_TOKEN not found"**
- Make sure `DEVELOPER_MODE=true` in `bot_config.env`
- Check that `DEV_BOT_TOKEN` is set correctly

### **"Database locked"**
- Make sure no other instance is running
- Check if `shopping_bot_dev.db` is being used by another process

### **Bot not responding**
- Verify the developer bot token is correct
- Check that the bot is running in developer mode
- Look for error messages in the console

## 🎉 Benefits

✅ **Safe testing** - No risk to production bot
✅ **Easy switching** - Same code, different config
✅ **Clean separation** - Developer and production data isolated
✅ **Simple deployment** - Just change environment variables
✅ **No file conflicts** - Same files work for both modes

---

**Happy developing!** 🚀
