#!/usr/bin/env python3
"""
Simple startup script for Render
Runs bot with minimal health check
"""

import os
import threading
import time
from datetime import datetime

def run_health():
    """Run simple health check server"""
    try:
        import simple_health
        simple_health.run_health_server()
    except Exception as e:
        print(f"❌ Health server error: {e}")

def run_bot():
    """Run the Telegram bot"""
    try:
        from bot import ShoppingBot
        bot = ShoppingBot()
        bot.run()
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🚀 Starting Shopping Bot...")
    print(f"⏰ Started at: {datetime.now()}")
    
    # Start health server in background
    health_thread = threading.Thread(target=run_health, daemon=True)
    health_thread.start()
    
    # Wait a moment for health server to start
    time.sleep(3)
    
    # Run bot
    run_bot()

if __name__ == "__main__":
    main()
