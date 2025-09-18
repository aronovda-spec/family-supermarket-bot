#!/usr/bin/env python3
"""
Keep Alive Script for Render
This script helps prevent the bot from sleeping on Render's free tier
"""

import asyncio
import aiohttp
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ping_render():
    """Send a ping to keep the service alive"""
    try:
        # Get the Render service URL from environment
        service_url = os.getenv('RENDER_EXTERNAL_URL')
        if not service_url:
            logger.info("No RENDER_EXTERNAL_URL found, skipping ping")
            return
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{service_url}/health") as response:
                if response.status == 200:
                    logger.info(f"✅ Ping successful at {datetime.now()}")
                else:
                    logger.warning(f"⚠️ Ping returned status {response.status}")
    except Exception as e:
        logger.error(f"❌ Ping failed: {e}")

async def keep_alive_loop():
    """Main keep alive loop"""
    logger.info("🔄 Starting keep alive service...")
    
    while True:
        await ping_render()
        # Ping every 5 minutes (300 seconds)
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(keep_alive_loop())
