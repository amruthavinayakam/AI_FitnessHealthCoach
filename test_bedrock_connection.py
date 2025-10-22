#!/usr/bin/env python3
"""
Test Bedrock connection directly and check deployment status
"""

import boto3
import json
import os
from botocore.exceptions import ClientError, NoCredentialsError

def test_bedrock_direct():
    """Test direct Bedrock connection"""
    print("🔍 Testing Direct Bedrock Connection")
    print("=" * 50)
    
    try:
        # Initialize Bedrock client
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Test prompt
        prompt = "Generate a simple 3-day workout plan for a beginner."
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "temperature": 0.3,
            "top_p": 0.9,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        print("🔄 Calling Bedrock directly...")
        
        response = bedrock_client.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        print("✅ SUCCESS - Bedrock is working!")
        print(f"Response length: {len(content)} characters")
        print(f"First 200 chars: {content[:200]}...")
        
        return True
        
    except NoCredentialsError:
        print("❌ AWS credentials not configured")
        print("Run: aws configure")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDeniedException':
            print("❌ Access denied to Bedrock")
            print("You need to request access to Claude models in AWS Bedrock console")
        else:
            print(f"❌ AWS Error: {error_code}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def check_lambda_functions():
    """Check if Lambda functions are deployed"""
    print("\n🔍 Checking Lambda Functions")
    print("=" * 50)
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        # Check workout generator
        try:
            response = lambda_client.get_function(FunctionName='workout-generator')
            print("✅ workout-generator Lambda exists")
        except ClientError:
            print("❌ workout-generator Lambda not found")
        
        # Check fitness coach handler
        try:
            response = lambda_client.get_function(FunctionName='fitness-coach-handler')
            print("✅ fitness-coach-handler Lambda exists")
        except ClientError:
            print("❌ fitness-coach-handler Lambda not found")
            
        # Check meal planner
        try:
            response = lambda_client.get_function(FunctionName='meal-planner')
            print("✅ meal-planner Lambda exists")
        except ClientError:
            print("❌ meal-planner Lambda not found")
            
    except Exception as e:
        print(f"❌ Error checking Lambda functions: {str(e)}")

def check_api_gateway():
    """Check API Gateway deployment"""
    print("\n🔍 Checking API Gateway")
    print("=" * 50)
    
    try:
        apigateway = boto3.client('apigateway', region_name='us-east-1')
        
        # List REST APIs
        apis = apigateway.get_rest_apis()
        
        fitness_api = None
        for api in apis['items']:
            if 'fitness' in api['name'].lower():
                fitness_api = api
                break
        
        if fitness_api:
            print(f"✅ Found API: {fitness_api['name']}")
            print(f"   ID: {fitness_api['id']}")
            
            # Check deployments
            deployments = apigateway.get_deployments(restApiId=fitness_api['id'])
            if deployments['items']:
                print(f"✅ API has {len(deployments['items'])} deployments")
                latest = max(deployments['items'], key=lambda x: x['createdDate'])
                print(f"   Latest deployment: {latest['id']}")
            else:
                print("❌ No deployments found")
        else:
            print("❌ No fitness API found")
            
    except Exception as e:
        print(f"❌ Error checking API Gateway: {str(e)}")

def test_lambda_direct():
    """Test Lambda function directly"""
    print("\n🔍 Testing Lambda Function Directly")
    print("=" * 50)
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        payload = {
            'body': json.dumps({
                'username': 'test_user',
                'userId': 'test_123',
                'query': 'I want to build muscle. Give me a simple workout plan.'
            })
        }
        
        print("🔄 Invoking workout-generator Lambda directly...")
        
        response = lambda_client.invoke(
            FunctionName='workout-generator',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        if response_payload.get('statusCode') == 200:
            body = json.loads(response_payload['body'])
            if body.get('success'):
                print("✅ SUCCESS - Lambda function works!")
                workout_plan = body.get('data', {}).get('workoutPlan')
                if workout_plan:
                    print(f"Generated plan type: {workout_plan.get('plan_type')}")
                    print("🎉 This proves Bedrock integration is working in Lambda!")
                else:
                    print("❌ No workout plan in response")
            else:
                print(f"❌ Lambda returned error: {body.get('error')}")
        else:
            print(f"❌ Lambda returned status {response_payload.get('statusCode')}")
            
    except ClientError as e:
        print(f"❌ Lambda error: {e.response['Error']['Code']}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🎯 AWS Bedrock & Lambda Diagnostic Tool")
    print("=" * 60)
    
    # Test 1: Direct Bedrock connection
    bedrock_works = test_bedrock_direct()
    
    # Test 2: Check Lambda functions
    check_lambda_functions()
    
    # Test 3: Check API Gateway
    check_api_gateway()
    
    # Test 4: Test Lambda directly (if Bedrock works)
    if bedrock_works:
        test_lambda_direct()
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS COMPLETE")
    print("=" * 60)