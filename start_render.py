#!/usr/bin/env python3
"""
Enhanced startup script for Render Web Service deployment
Runs both the Telegram bot and health check server with better error handling
"""

import asyncio
import threading
import subprocess
import sys
import os
import time
import signal
from datetime import datetime

# Global flag for graceful shutdown
shutdown_flag = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_flag
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    shutdown_flag = True

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
    global shutdown_flag
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting Family Shopping List Bot on Render...")
    print(f"⏰ Started at: {datetime.now()}")
    print(f"🌐 Service type: Web Service (with health checks)")
    
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
