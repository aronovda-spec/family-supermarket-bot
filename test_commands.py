#!/usr/bin/env python3
"""
Test script to verify bot commands are being set properly
"""
import asyncio
import os
from telegram import Bot
from telegram import BotCommand

async def test_commands():
    """Test if bot commands can be set"""
    bot_token = os.getenv('BOT_TOKEN', '8156660168:AAFcnVqIObIbTdLp1LAxU7zk2Z7NbJEtZyg')
    
    bot = Bot(token=bot_token)
    
    # Test commands
    commands = [
        BotCommand("start", "🚀 Start using the bot"),
        BotCommand("menu", "📱 Show main menu"),
        BotCommand("help", "❓ Show help guide"),
    ]
    
    try:
        # Set commands
        result = await bot.set_my_commands(commands)
        print(f"✅ Commands set successfully: {result}")
        
        # Get commands to verify
        current_commands = await bot.get_my_commands()
        print(f"📋 Current commands: {current_commands}")
        
        # Test Hebrew commands
        hebrew_commands = [
            BotCommand("start", "🚀 התחל להשתמש בבוט"),
            BotCommand("menu", "📱 הצג תפריט ראשי"),
            BotCommand("help", "❓ הצג מדריך עזרה"),
        ]
        
        result_he = await bot.set_my_commands(hebrew_commands, language_code="he")
        print(f"✅ Hebrew commands set successfully: {result_he}")
        
    except Exception as e:
        print(f"❌ Error setting commands: {e}")

if __name__ == "__main__":
    asyncio.run(test_commands())
