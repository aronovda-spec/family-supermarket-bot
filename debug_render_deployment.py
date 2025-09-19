#!/usr/bin/env python3
"""
Debug script to check Render deployment status
"""
import requests
import json

def check_render_deployment():
    """Check if the latest changes are deployed"""
    print("🔍 Checking Render deployment status...")
    
    # You'll need to replace this with your actual Render service URL
    service_url = "https://your-service-name.onrender.com"
    
    try:
        # Check health endpoint
        response = requests.get(f"{service_url}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Service is running: {health_data}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Cannot reach service: {e}")
        print("💡 Make sure to:")
        print("   1. Replace 'your-service-name' with your actual Render service name")
        print("   2. Check Render dashboard for deployment status")
        print("   3. Verify the service is running")

if __name__ == "__main__":
    check_render_deployment()
