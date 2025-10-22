#!/usr/bin/env python3
"""
Check CloudWatch logs for Lambda function errors
"""

import boto3
import json
from datetime import datetime, timedelta

def get_recent_lambda_logs(function_name, minutes=10):
    """Get recent CloudWatch logs for a Lambda function"""
    print(f"🔍 Checking CloudWatch logs for {function_name}")
    print("=" * 60)
    
    try:
        logs_client = boto3.client('logs', region_name='us-east-1')
        
        # Calculate time range (last 10 minutes)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)
        
        log_group_name = f"/aws/lambda/{function_name}"
        
        print(f"Log Group: {log_group_name}")
        print(f"Time Range: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}")
        
        # Get log events
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000),
            limit=50
        )
        
        events = response.get('events', [])
        
        if not events:
            print("❌ No recent log events found")
            return
        
        print(f"📋 Found {len(events)} log events:")
        print("-" * 60)
        
        for event in events[-10:]:  # Show last 10 events
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            
            # Highlight errors
            if any(keyword in message.lower() for keyword in ['error', 'exception', 'failed', 'traceback']):
                print(f"🔴 {timestamp.strftime('%H:%M:%S')} ERROR: {message}")
            elif 'import' in message.lower() and ('failed' in message.lower() or 'error' in message.lower()):
                print(f"🟡 {timestamp.strftime('%H:%M:%S')} IMPORT: {message}")
            else:
                print(f"ℹ️  {timestamp.strftime('%H:%M:%S')} INFO: {message}")
        
        # Look for specific error patterns
        error_messages = [event['message'] for event in events if any(keyword in event['message'].lower() for keyword in ['error', 'exception', 'traceback'])]
        
        if error_messages:
            print("\n🚨 ERROR ANALYSIS:")
            print("-" * 60)
            for error in error_messages[-3:]:  # Show last 3 errors
                print(f"❌ {error.strip()}")
                
                # Analyze common issues
                if 'import' in error.lower():
                    print("   💡 This looks like a module import error")
                elif 'bedrock' in error.lower():
                    print("   💡 This is a Bedrock-related error")
                elif 'permission' in error.lower() or 'access' in error.lower():
                    print("   💡 This looks like a permissions issue")
                elif 'timeout' in error.lower():
                    print("   💡 This is a timeout error")
        
    except Exception as e:
        print(f"❌ Error reading logs: {str(e)}")

def check_lambda_configuration(function_name):
    """Check Lambda function configuration"""
    print(f"\n⚙️ Checking {function_name} Configuration")
    print("=" * 60)
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        response = lambda_client.get_function(FunctionName=function_name)
        config = response['Configuration']
        
        print(f"Runtime: {config.get('Runtime')}")
        print(f"Handler: {config.get('Handler')}")
        print(f"Timeout: {config.get('Timeout')} seconds")
        print(f"Memory: {config.get('MemorySize')} MB")
        print(f"Last Modified: {config.get('LastModified')}")
        
        # Check environment variables
        env_vars = config.get('Environment', {}).get('Variables', {})
        print(f"\nEnvironment Variables:")
        for key, value in env_vars.items():
            if 'key' in key.lower() or 'secret' in key.lower():
                print(f"  {key}: [HIDDEN]")
            else:
                print(f"  {key}: {value}")
        
        # Check IAM role
        role_arn = config.get('Role')
        print(f"\nIAM Role: {role_arn}")
        
    except Exception as e:
        print(f"❌ Error checking configuration: {str(e)}")

if __name__ == "__main__":
    print("🔍 Lambda Function Diagnostics")
    print("=" * 70)
    
    # Check workout generator logs and config
    get_recent_lambda_logs('workout-generator', minutes=15)
    check_lambda_configuration('workout-generator')
    
    print("\n" + "=" * 70)
    print("💡 COMMON FIXES:")
    print("=" * 70)
    print("1. Import Error: Missing dependencies in Lambda layer")
    print("2. Bedrock Error: Check IAM permissions for bedrock:InvokeModel")
    print("3. Timeout: Increase Lambda timeout (currently 30s)")
    print("4. Memory: Increase Lambda memory if needed")
    print("5. Handler: Verify handler path matches file structure")