#!/usr/bin/env python3
"""
Simple Health Check for Render
Minimal HTTP server for health checks
"""

import os
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'service': 'shopping-bot'
            }
            
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logs

def run_health_server():
    port = int(os.getenv('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), SimpleHealthHandler)
    print(f"🏥 Health server started on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    run_health_server()
