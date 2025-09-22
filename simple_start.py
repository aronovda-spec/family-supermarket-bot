#!/usr/bin/env python3
"""
Simple startup script for Render
Runs bot with minimal health check
"""

import os
import threading
import time
import requests
from datetime import datetime

def run_health():
    """Run simple health check server"""
    try:
        import simple_health
        simple_health.run_health_server()
    except Exception as e:
        print(f"❌ Health server error: {e}")

def keep_alive():
    """Keep-alive mechanism to prevent Render sleep (every 5 minutes)"""
    if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
        keep_alive_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/health"
        print(f"🔄 Sending keep-alive ping to: {keep_alive_url}")
        
        try:
            response = requests.get(keep_alive_url, timeout=10)
            if response.status_code == 200:
                print(f"✅ Keep-alive ping successful at {datetime.now()}")
            else:
                print(f"⚠️ Keep-alive ping failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Keep-alive ping failed: {e}")
    else:
        print("🏠 Keep-alive skipped - running locally")

def start_keep_alive():
    """Start keep-alive mechanism (only on Render)"""
    if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
        print("🔄 Starting aggressive keep-alive mechanism (every 5 minutes)")
        
        # Initial keep-alive after 30 seconds to ensure server is ready
        def delayed_keep_alive():
            time.sleep(30)  # Wait 30 seconds
            keep_alive()
        
        # Start delayed keep-alive in background
        threading.Thread(target=delayed_keep_alive, daemon=True).start()
        
        # Then every 5 minutes (more aggressive than 15-minute sleep threshold)
        def periodic_keep_alive():
            while True:
                time.sleep(5 * 60)  # 5 minutes
                keep_alive()
        
        # Start periodic keep-alive in background
        threading.Thread(target=periodic_keep_alive, daemon=True).start()
    else:
        print("🏠 Keep-alive mechanism disabled - running locally")

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
    print(f"🌐 Service type: Web Service (with keep-alive mechanism)")
    
    # Start health server in background
    health_thread = threading.Thread(target=run_health, daemon=True)
    health_thread.start()
    
    # Start keep-alive mechanism
    start_keep_alive()
    
    # Wait a moment for health server to start
    time.sleep(3)
    
    # Run bot
    run_bot()

if __name__ == "__main__":
    main()
