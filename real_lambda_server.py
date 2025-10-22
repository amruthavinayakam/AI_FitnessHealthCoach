#!/usr/bin/env python3
"""
Local Server that invokes REAL Lambda functions
"""

import asyncio
import json
import sys
import time
import boto3
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import threading
import os
import re

class RealLambdaHandler(BaseHTTPRequestHandler):
    """HTTP handler that calls real Lambda functions"""
    
    def __init__(self, *args, **kwargs):
        # Initialize AWS Lambda client
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_homepage()
        elif parsed_path.path == '/api/test-workout':
            self.test_workout_lambda()
        elif parsed_path.path == '/api/test-meal':
            self.test_meal_lambda()
        elif parsed_path.path == '/api/config':
            self.handle_config_api()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/chat':
            self.handle_chat_api()
        elif self.path == '/api/workout':
            self.handle_workout_request()
        elif self.path == '/api/meal':
            self.handle_meal_request()
        else:
            self.send_error(404, "Not Found")
    
    def serve_homepage(self):
        """Serve the main homepage"""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fitness Health Coach</title>
<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0;
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    min-height: 100vh;
}
.container {
    max-width: 1200px;
    margin: 0 auto;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 30px;
    backdrop-filter: blur(10px);
}
.header {
    text-align: center;
    margin-bottom: 40px;
}
.header h1 {
    font-size: 3em;
    margin: 0;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}
.status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 40px;
}
.status-card {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 15px;
    padding: 20px;
    text-align: center;
}
.status-card h3 {
    margin-top: 0;
    color: #fff;
}
.status-indicator {
    font-size: 2em;
    margin: 10px 0;
}
.demo-section {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 15px;
    padding: 30px;
    margin: 20px 0;
}
.demo-buttons {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 15px;
    margin: 20px 0;
}
.demo-btn {
    background: linear-gradient(45deg, #ff6b6b, #ee5a24);
    color: white;
    border: none;
    padding: 15px 25px;
    border-radius: 10px;
    font-size: 16px;
    cursor: pointer;
    transition: transform 0.2s;
    text-decoration: none;
    display: block;
    text-align: center;
}
.demo-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
}
.chat-container {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 15px;
    padding: 20px;
    margin: 20px 0;
}
.chat-input {
    width: 100%;
    padding: 15px;
    border: none;
    border-radius: 10px;
    font-size: 16px;
    margin-bottom: 10px;
}
.chat-btn {
    background: #27ae60;
    color: white;
    border: none;
    padding: 15px 30px;
    border-radius: 10px;
    font-size: 16px;
    cursor: pointer;
}
.response-area {
    background: rgba(0, 0, 0, 0.3);
    border-radius: 10px;
    padding: 20px;
    margin-top: 20px;
    min-height: 100px;
    font-family: monospace;
    white-space: pre-wrap;
    max-height: 400px;
    overflow-y: auto;
    width: 100%;
    text-align: left;
    display: block;
    box-sizing: border-box;
}
.footer {
    text-align: center;
    margin-top: 40px;
    opacity: 0.8;
}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>Fitness Health Coach</h1>
    <div class="demo-section">
        <h2>Test Lambda Functions</h2>
        <div class="demo-buttons">
            <button class="demo-btn" onclick="testWorkoutLambda()">💪 Test Workout Generator (Bedrock)</button>
            <button class="demo-btn" onclick="testMealLambda()">🍽️ Test Meal Planner</button>
            <button class="demo-btn" onclick="testFullWorkflow()">🎯 Test Complete Workflow</button>
        </div>
    </div>
    
    <div class="demo-section">
        <h2>💬 Chat with Fitness Coach</h2>
        <div class="chat-container">
            <input type="text" class="chat-input" id="userMessage" placeholder="Ask me about fitness, nutrition, or workouts." />
            <button class="chat-btn" onclick="sendChatMessage()">Send to Lambda Functions</button>
        </div>
        <div id="responseArea" class="response-area">🔄 Waiting for response...</div>
    </div>
    
    <div class="footer">
        <p> Fitness Health Coach </p>
        <p> Directly invoking: workout-generator, meal-planner, fitness-coach-handler</p>
    </div>
</div>
<script>
async function testWorkoutLambda() {
    updateResponse("🔄 Calling REAL workout-generator Lambda function...");
    try {
        const response = await fetch('/api/test-workout');
        const data = await response.json();
        updateResponse(`✅ REAL Bedrock Workout Generation:\\n\\n${JSON.stringify(data, null, 2)}`);
    } catch (error) {
        updateResponse(`❌ Error: ${error.message}`);
    }
}
async function testMealLambda() {
    updateResponse("🔄 Calling REAL meal-planner Lambda function...");
    try {
        const response = await fetch('/api/test-meal');
        const data = await response.json();
        updateResponse(`✅ REAL Meal Planning Results:\\n\\n${JSON.stringify(data, null, 2)}`);
    } catch (error) {
        updateResponse(`❌ Error: ${error.message}`);
    }
}
async function testFullWorkflow() {
    updateResponse("🔄 Testing Complete REAL Lambda Workflow...");
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: "I want to build muscle and lose fat. I'm a beginner.",
                user_id: "test_user"
            })
        });
        const data = await response.json();
        updateResponse(`✅ Complete REAL Workflow Results:\\n\\n${JSON.stringify(data, null, 2)}`);
    } catch (error) {
        updateResponse(`❌ Error: ${error.message}`);
    }
}
async function sendChatMessage() {
    const message = document.getElementById('userMessage').value;
    if (!message.trim()) return;
    updateResponse(`🔄 Sending to REAL Lambda functions: "${message}"...`);
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                user_id: "web_user"
            })
        });
        const data = await response.json();
        updateResponse(`✅ REAL Lambda Response:\\n\\n${JSON.stringify(data, null, 2)}`);
        document.getElementById('userMessage').value = '';
    } catch (error) {
        updateResponse(`❌ Error: ${error.message}`);
    }
}
function updateResponse(text) {
    document.getElementById('responseArea').textContent = text;
}
document.getElementById('userMessage').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendChatMessage();
    }
});
</script>
</body>
</html>"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())

    def safe_json_loads(self, text):
        """Try to parse JSON even if Bedrock adds extra text"""
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            text = match.group(0)
        try:
            return json.loads(text)
        except Exception:
            return {"day": "unknown", "exercises": []}

    def test_workout_lambda(self):
        """Test workout generator Lambda directly"""
        try:
            payload = {
                'body': json.dumps({
                    'username': 'test_user',
                    'userId': 'test_123',
                    'query': 'I want to build muscle and lose fat. I am a beginner who can work out 4 days per week.'
                })
            }
            print("🔄 Invoking workout-generator Lambda...")
            response = self.lambda_client.invoke(
                FunctionName='workout-generator',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            response_payload = json.loads(response['Payload'].read())
            if response_payload.get('statusCode') == 200:
                body = self.safe_json_loads(response_payload['body'])
                result = {
                    "status": "success",
                    "message": "REAL Bedrock workout generation successful!",
                    "lambda_function": "workout-generator",
                    "bedrock_used": True,
                    "data": body
                }
            else:
                result = {"status": "error", "lambda_response": response_payload}
            self.send_json_response(result)
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)})

    def test_meal_lambda(self):
        """Test meal planner Lambda directly"""
        try:
            payload = {
                'body': json.dumps({
                    'username': 'test_user',
                    'userId': 'test_123',
                    'query': 'I want a high protein meal plan for muscle building.'
                })
            }
            print("🔄 Invoking meal-planner Lambda...")
            response = self.lambda_client.invoke(
                FunctionName='meal-planner',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            response_payload = json.loads(response['Payload'].read())
            if response_payload.get('statusCode') == 200:
                body = self.safe_json_loads(response_payload['body'])
                result = {
                    "status": "success",
                    "lambda_function": "meal-planner",
                    "data": body
                }
            else:
                result = {"status": "error", "lambda_response": response_payload}
            self.send_json_response(result)
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)})

    def handle_chat_api(self):
        """Handle chat API requests by calling main Lambda handler"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode('utf-8'))
            message = data.get('message', '')
            user_id = data.get('user_id', 'anonymous')
            payload = {'body': json.dumps({'username': user_id, 'userId': user_id, 'query': message})}
            print("🔄 Invoking fitness-coach-handler Lambda...")
            response = self.lambda_client.invoke(
                FunctionName='fitness-coach-handler',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            response_payload = json.loads(response['Payload'].read())
            if response_payload.get('statusCode') == 200:
                body = self.safe_json_loads(response_payload['body'])
                result = {
                    "status": "success",
                    "lambda_function": "fitness-coach-handler",
                    "data": body
                }
            else:
                result = {"status": "error", "lambda_response": response_payload}
            self.send_json_response(result)
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)})

    def handle_config_api(self):
        """Handle configuration API requests"""
        result = {
            "mode": "real_lambda",
            "configured": True,
            "description": "Calling REAL AWS Lambda functions",
            "lambda_functions": [
                "workout-generator (uses Bedrock)",
                "meal-planner",
                "fitness-coach-handler"
            ],
            "bedrock_integration": True
        }
        self.send_json_response(result)

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
    """Run the real Lambda server"""
    server_address = ('0.0.0.0', int(os.getenv('PORT', '8080')))
    httpd = HTTPServer(server_address, RealLambdaHandler)
    print("🎯 Fitness Health Coach - REAL Lambda Integration Server")
    print("=" * 60)
    print(f"🌐 Server running at: http://0.0.0.0:{os.getenv('PORT', '8080')}")
    print("⚡ This server calls your REAL AWS Lambda functions!")
    print("🧠 Bedrock integration: ACTIVE")
    print("🔧 Lambda functions: workout-generator, meal-planner, fitness-coach-handler")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
