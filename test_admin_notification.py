#!/usr/bin/env python3
"""
Test script to check admin notification functionality
"""
import asyncio
import os
from telegram import Bot
from database import Database

async def test_admin_notification():
    """Test if admin notification works"""
    bot_token = os.getenv('BOT_TOKEN', '8156660168:AAFcnVqIObIbTdLp1LAxU7zk2Z7NbJEtZyg')
    
    bot = Bot(token=bot_token)
    db = Database()
    
    # Check current users
    print("Current users in database:")
    all_users = db.get_all_users()
    for user in all_users:
        print(f"  ID: {user['user_id']}, Name: {user['first_name']}, Admin: {user['is_admin']}, Authorized: {user['is_authorized']}")
    
    # Check if Dani is admin
    dani_id = 1022850808
    is_dani_admin = db.is_user_admin(dani_id)
    print(f"\nDani (ID: {dani_id}) is admin: {is_dani_admin}")
    
    # Test sending a message to Dani
    try:
        test_message = "🧪 TEST MESSAGE\n\nThis is a test message to verify admin notifications are working.\n\nIf you receive this, the notification system is working correctly!"
        
        await bot.send_message(
            chat_id=dani_id,
            text=test_message,
            parse_mode='Markdown'
        )
        print("✅ Test message sent to Dani successfully!")
        
    except Exception as e:
        print(f"❌ Error sending test message to Dani: {e}")

if __name__ == "__main__":
    asyncio.run(test_admin_notification())
