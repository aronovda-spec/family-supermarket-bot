#!/usr/bin/env python3
"""
Test the fixed admin notification
"""
import asyncio
import os
from telegram import Bot
from database import Database

async def test_fixed_notification():
    """Test the fixed admin notification"""
    bot_token = os.getenv('BOT_TOKEN', '8156660168:AAFcnVqIObIbTdLp1LAxU7zk2Z7NbJEtZyg')
    
    bot = Bot(token=bot_token)
    db = Database()
    
    # Simulate a new user
    class MockUser:
        def __init__(self):
            self.id = 123456789
            self.first_name = "Test User"
            self.username = "testuser"
    
    mock_user = MockUser()
    
    # Create the fixed message
    user_name = mock_user.first_name or mock_user.username or f"User {mock_user.id}"
    username_display = f"@{mock_user.username}" if mock_user.username else "None"
    message = (
        f"👤 <b>New User Request</b>\n\n"
        f"Name: {user_name}\n"
        f"Username: {username_display}\n"
        f"ID: <code>{mock_user.id}</code>\n\n"
        f"To authorize: /authorize {mock_user.id}\n"
        f"To view all users: /users"
    )
    
    print("Testing fixed notification message:")
    print(message)
    print("\n" + "="*50)
    
    # Test sending to Dani
    dani_id = 1022850808
    try:
        await bot.send_message(
            chat_id=dani_id,
            text=message,
            parse_mode='HTML'
        )
        print("✅ Fixed notification sent to Dani successfully!")
        
    except Exception as e:
        print(f"❌ Error sending fixed notification: {e}")

if __name__ == "__main__":
    asyncio.run(test_fixed_notification())
