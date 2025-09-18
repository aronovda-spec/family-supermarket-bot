#!/usr/bin/env python3
"""
Family Shopping List Bot Runner
Simple script to start the bot with proper error handling
"""

import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from bot import ShoppingBot
    
    def main():
        """Main function to run the bot"""
        print("🛒 Starting Family Shopping List Bot...")
        print("Press Ctrl+C to stop the bot")
        print("-" * 50)
        
        try:
            bot = ShoppingBot()
            bot.run()
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
        except Exception as e:
            print(f"❌ Error running bot: {e}")
            logging.error(f"Bot error: {e}", exc_info=True)

    if __name__ == "__main__":
        main()

except ImportError as e:
    print("❌ Error importing bot modules:")
    print(f"   {e}")
    print("\n💡 Make sure you have:")
    print("   1. Installed requirements: pip install -r requirements.txt")
    print("   2. Created .env file with BOT_TOKEN and ADMIN_IDS")
    print("   3. All Python files are in the same directory")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    logging.error(f"Startup error: {e}", exc_info=True)
    sys.exit(1)
