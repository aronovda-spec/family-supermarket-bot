#!/usr/bin/env python3
"""
Developer Mode Startup Script
Runs the bot in developer mode with separate token and database
"""

import os
import sys
from datetime import datetime

def main():
    print("🛠️ Starting Shopping Bot in DEVELOPER MODE")
    print(f"⏰ Started at: {datetime.now()}")
    print("=" * 50)
    
    # Set developer mode environment variable
    os.environ['DEVELOPER_MODE'] = 'true'
    
    # Check if developer config exists
    if not os.path.exists('bot_config.env'):
        print("❌ bot_config.env not found!")
        print("📝 Please copy bot_config.env.developer to bot_config.env")
        print("🔧 Then edit bot_config.env with your developer bot token")
        sys.exit(1)
    
    # Start Supabase keep-alive mechanism (optional, won't fail if not configured)
    try:
        from supabase_keep_alive import start_supabase_keep_alive
        start_supabase_keep_alive()
    except Exception as e:
        print(f"⚠️ Supabase keep-alive not started: {e}")
    
    # Import and run the bot
    try:
        from bot import ShoppingBot
        bot = ShoppingBot()
        bot.run()
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
