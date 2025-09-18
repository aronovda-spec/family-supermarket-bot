#!/usr/bin/env python3
"""
Combined startup script for Render deployment
Runs both the Telegram bot and health check server
"""

import asyncio
import threading
import subprocess
import sys
import os
import time
from datetime import datetime

def run_health_server():
    """Run the health check server in a separate thread"""
    try:
        import health_check
        health_check.run_health_server()
    except Exception as e:
        print(f"❌ Health server error: {e}")

def run_bot():
    """Run the Telegram bot"""
    try:
        import run_bot
        # This will run the bot
        asyncio.run(run_bot.main())
    except Exception as e:
        print(f"❌ Bot error: {e}")

def main():
    print("🚀 Starting Family Shopping List Bot on Render...")
    print(f"⏰ Started at: {datetime.now()}")
    
    # Start health check server in a separate thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Give health server time to start
    time.sleep(2)
    
    # Run the bot in the main thread
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
