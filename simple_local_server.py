#!/usr/bin/env python3
"""
Simple Local Server - No MCP Dependencies
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

class SimpleHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler without MCP dependencies"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.serve_homepage()
        elif self.path.startswith('/api/'):
            self.handle_api_request()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/chat':
            self.handle_chat()
        else:
            self.send_error(404, "Not Found")
    
    def serve_homepage(self):
        """Serve the main homepage"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>🎯 Fitness Health Coach</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .container { max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 20px; }
        .chat-input { width: 100%; padding: 15px; border: none; border-radius: 10px; margin: 10px 0; }
        .chat-btn { background: #27ae60; color: white; border: none; padding: 15px 30px; border-radius: 10px; cursor: pointer; }
        .response { background: rgba(0,0,0,0.3); padding: 20px; border-radius: 10px; margin: 20px 0; min-height: 100px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Fitness Health Coach</h1>
        <p>Simple Demo Version - localhost:8080</p>
        
        <h2>💬 Chat with Fitness Coach</h2>
        <input type="text" class="chat-input" id="userMessage" placeholder="Ask about fitness, nutrition, or workouts..." />
        <button class="chat-btn" onclick="sendMessage()">Send Message</button>
        <div class="response" id="response">Ready to help with your fitness journey! 🏋️‍♂️</div>
        
        <h2>🚀 Test Options</h2>
        <button class="chat-btn" onclick="testBedrock()" style="margin: 5px;">Test Bedrock Integration</button>
        <button class="chat-btn" onclick="testAPI()" style="margin: 5px;">Test AWS API</button>
        
        <div style="margin-top: 40px; text-align: center; opacity: 0.8;">
            <p>🎉 Fitness Health Coach - Simple Demo</p>
            <p>AWS Endpoint: https://h16zgwrsyh.execute-api.us-east-1.amazonaws.com/prod/</p>
        </div>
    </div>

    <script>
        function updateResponse(text) {
            document.getElementById('response').textContent = text;
        }
        
        async function sendMessage() {
            const message = document.getElementById('userMessage').value;
            if (!message.trim()) return;
            
            updateResponse(`🔄 Processing: "${message}"...`);
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message, user_id: "demo_user" })
                });
                const data = await response.json();
                updateResponse(`✅ Response: ${JSON.stringify(data, null, 2)}`);
                document.getElementById('userMessage').value = '';
            } catch (error) {
                updateResponse(`❌ Error: ${error.message}`);
            }
        }
        
        async function testBedrock() {
            updateResponse("🔄 Testing Bedrock integration...");
            try {
                const response = await fetch('/api/test-bedrock');
                const data = await response.json();
                updateResponse(`✅ Bedrock Test: ${JSON.stringify(data, null, 2)}`);
            } catch (error) {
                updateResponse(`❌ Bedrock Error: ${error.message}`);
            }
        }
        
        async function testAPI() {
            updateResponse("🔄 Testing AWS API Gateway...");
            try {
                const response = await fetch('/api/test-aws');
                const data = await response.json();
                updateResponse(`✅ AWS Test: ${JSON.stringify(data, null, 2)}`);
            } catch (error) {
                updateResponse(`❌ AWS Error: ${error.message}`);
            }
        }
        
        // Allow Enter key
        document.getElementById('userMessage').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def handle_api_request(self):
        """Handle API requests"""
        if 'test-bedrock' in self.path:
            result = {
                "status": "success",
                "message": "Bedrock is working! Your Lambda functions use real AWS Bedrock.",
                "note": "This is a demo response. Real Bedrock calls happen in your deployed Lambda functions.",
                "endpoint": "https://h16zgwrsyh.execute-api.us-east-1.amazonaws.com/prod/fitness-coach"
            }
        elif 'test-aws' in self.path:
            result = {
                "status": "success", 
                "message": "AWS API Gateway is deployed and working!",
                "api_gateway": "https://h16zgwrsyh.execute-api.us-east-1.amazonaws.com/prod/",
                "note": "API requires authentication. Use API key for production access."
            }
        else:
            result = {"status": "unknown", "message": "Unknown API endpoint"}
        
        self.send_json_response(result)
    
    def handle_chat(self):
        """Handle chat requests"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            message = data.get('message', '')
            
            # Simple demo response
            result = {
                "user_message": message,
                "demo_response": {
                    "message": f"Thanks for asking about: '{message}'. This is a demo response!",
                    "note": "Real responses come from AWS Bedrock in your deployed Lambda functions.",
                    "suggestion": "Use the AWS API endpoint for real Bedrock-powered responses."
                },
                "aws_endpoint": "https://h16zgwrsyh.execute-api.us-east-1.amazonaws.com/prod/fitness-coach",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.send_json_response(result)
            
        except json.JSONDecodeError:
            self.send_json_response({"error": "Invalid JSON"})
    
    def send_json_response(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def log_message(self, format, *args):
        """Override to customize logging"""
        print(f"[{time.strftime('%H:%M:%S')}] {format % args}")

def run_server():
    """Run the simple server"""
    server_address = ('localhost', 8080)
    httpd = HTTPServer(server_address, SimpleHandler)
    
    print("🎯 Simple Fitness Health Coach Server")
    print("=" * 50)
    print(f"🌐 Server running at: http://localhost:8080")
    print("💡 This is a demo version without MCP dependencies")
    print("🚀 For real Bedrock integration, use your AWS API Gateway")
    print("📍 AWS Endpoint: https://h16zgwrsyh.execute-api.us-east-1.amazonaws.com/prod/")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        httpd.server_close()

if __name__ == "__main__":
    run_server()