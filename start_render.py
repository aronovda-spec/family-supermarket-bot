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
import requests
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

def keep_alive():
    """Keep-alive mechanism to prevent Render sleep (every 5 minutes)"""
    if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
        keep_alive_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/health"
        print(f"🔄 Sending Render keep-alive ping to: {keep_alive_url}")
        
        try:
            response = requests.get(keep_alive_url, timeout=10)
            if response.status_code == 200:
                print(f"✅ Render keep-alive ping successful at {datetime.now()}")
            else:
                print(f"⚠️ Render keep-alive ping failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Render keep-alive ping failed: {e}")
    else:
        print("🏠 Render keep-alive skipped - running locally")

def start_render_keep_alive():
    """Start Render keep-alive mechanism (only on Render)"""
    if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
        print("🔄 Starting Render keep-alive mechanism (every 5 minutes)")
        
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
        print("🏠 Render keep-alive mechanism disabled - running locally")

def run_bot():
    """Run the Telegram bot"""
    try:
        from bot import ShoppingBot
        # Create and run the bot directly
        bot = ShoppingBot()
        bot.run()
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()

def main():
    global shutdown_flag
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting Family Shopping List Bot on Render...")
    print(f"⏰ Started at: {datetime.now()}")
    print(f"🌐 Service type: Web Service (with health checks)")
    
    # Verify database connection
    print("\n📊 Database Connection:")
    try:
        from database import Database
        db = Database()
        if db.use_postgres:
            print("   ✅ Connected to PostgreSQL (Neon)")
            print("   ✅ All tables accessible")
            print("   ✅ Data will persist across restarts")
            
            # Verify tables exist
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """)
                table_count = cursor.fetchone()[0]
                print(f"   ✅ Found {table_count} tables in database")
        else:
            print("   ⚠️ Using SQLite (local file)")
            print("   ⚠️ Data will NOT persist on Render free tier")
            print("   💡 Set DATABASE_URL to use Neon PostgreSQL")
    except Exception as e:
        print(f"   ❌ Database connection error: {e}")
    
    # Start health check server in a separate thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Start Render keep-alive mechanism
    start_render_keep_alive()
    
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
