#!/usr/bin/env python3
"""
Fix the workout generator Lambda function by creating a simplified version
"""

import os

def create_simple_workout_handler():
    """Create a simplified workout generator that works in Lambda"""
    
    handler_code = '''# Simplified Lambda function for workout plan generation using AWS Bedrock
import json
import logging
import os
import boto3
from typing import Dict, Any
from datetime import datetime
import re

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class BedrockWorkoutGenerator:
    """AWS Bedrock client for generating structured workout plans."""
    
    def __init__(self):
        """Initialize Bedrock client."""
        self.bedrock_client = boto3.client('bedrock-runtime')
        self.model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        self.max_tokens = int(os.environ.get('BEDROCK_MAX_TOKENS', '2000'))
        self.temperature = float(os.environ.get('BEDROCK_TEMPERATURE', '0.3'))
        
    def generate_workout_plan(self, user_query: str, username: str, user_id: str) -> Dict[str, Any]:
        """
        Generate a structured workout plan using AWS Bedrock.
        
        Args:
            user_query: User's workout request
            username: Username
            user_id: User ID
            
        Returns:
            Dict: Workout plan data
        """
        try:
            # Create structured prompt
            prompt = self._create_workout_prompt(user_query)
            
            # Call Bedrock API
            response = self._call_bedrock_api(prompt)
            logger.info(f"\n----- RAW BEDROCK RESPONSE START -----\n{response[:2000]}\n----- RAW BEDROCK RESPONSE END -----")
            
            # Parse and validate response
            workout_plan = self._parse_workout_response(response, user_id)
            
            logger.info(f"Successfully generated workout plan for user {user_id}")
            return workout_plan
            
        except Exception as e:
            logger.error(f"Error generating workout plan: {str(e)}")
            raise
    
    def _create_workout_prompt(self, user_query: str) -> str:
        """Create structured prompt for consistent workout plan generation."""
        prompt = f"""You are a professional fitness coach creating a personalized 7-day workout plan. 

USER REQUEST: {user_query}

REQUIREMENTS:
- Create exactly 7 daily workouts (Monday through Sunday)
- Each workout should be 30-60 minutes total
- Include 4-8 exercises per day
- Vary muscle groups across the week
- Consider progressive overload principles
- Include rest or active recovery days as appropriate

RESPONSE FORMAT (JSON):
{{
    "plan_type": "string (e.g., 'Strength Training', 'Weight Loss', 'Muscle Building')",
    "duration_weeks": 1,
    "daily_workouts": [
        {{
            "day": "Monday",
            "total_duration": 45,
            "notes": "Focus on upper body strength",
            "exercises": [
                {{
                    "name": "Push-ups",
                    "sets": 3,
                    "reps": "12-15",
                    "duration": 8,
                    "muscle_groups": ["chest", "triceps", "shoulders"]
                }},
                {{
                    "name": "Plank",
                    "sets": 3,
                    "reps": "30-60 seconds",
                    "duration": 5,
                    "muscle_groups": ["core", "shoulders"]
                }}
            ]
        }}
    ]
}}

Generate a complete 7-day workout plan following this exact JSON format:"""

        return prompt
    
    def _call_bedrock_api(self, prompt: str) -> str:
        """Call AWS Bedrock API with the structured prompt."""
        try:
            # Prepare request body for Claude 3 Haiku
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": 0.9,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if 'content' not in response_body or not response_body['content']:
                raise Exception("Empty response from Bedrock")
            
            # Extract text content
            content = response_body['content'][0]['text']
            
            logger.info(f"Bedrock API call successful, response length: {len(content)}")
            return content
            
        except Exception as e:
            logger.error(f"Bedrock API call failed: {str(e)}")
            raise Exception(f"Failed to generate workout plan: {str(e)}")
    
    def _parse_workout_response(self, response: str, user_id: str) -> Dict[str, Any]:
        """Parse Bedrock response into structured workout plan."""
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_match = re.search(r'```json\\s*(.*?)\\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without markdown
                json_match = re.search(r'\\{.*\\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise Exception("No valid JSON found in Bedrock response")
            
            # Parse JSON
            workout_data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['plan_type', 'duration_weeks', 'daily_workouts']
            for field in required_fields:
                if field not in workout_data:
                    raise Exception(f"Missing required field: {field}")
            
            # Add metadata
            workout_plan = {
                "user_id": user_id,
                "plan_type": workout_data['plan_type'],
                "duration_weeks": workout_data['duration_weeks'],
                "daily_workouts": workout_data['daily_workouts'],
                "created_at": datetime.utcnow().isoformat(),
                "generated_by": "bedrock"
            }
            
            logger.info(f"Successfully parsed workout plan with {len(workout_data['daily_workouts'])} days")
            return workout_plan
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            raise Exception(f"Invalid JSON in Bedrock response: {str(e)}")
        except Exception as e:
            logger.error(f"Workout response parsing error: {str(e)}")
            raise Exception(f"Failed to parse workout plan: {str(e)}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generate workout plans using AWS Bedrock.
    
    Expected event format:
    {
        "body": "{\\"username\\": \\"string\\", \\"userId\\": \\"string\\", \\"query\\": \\"string\\"}"
    }
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Validate input
        if not event or 'body' not in event:
            raise Exception("Missing request body")
        
        # Parse request body
        if isinstance(event['body'], str):
            body = json.loads(event['body'])
        else:
            body = event['body']
        
        # Validate required fields
        required_fields = ['username', 'userId', 'query']
        for field in required_fields:
            if field not in body:
                raise Exception(f"Missing required field: {field}")
        
        logger.info(f"Processing workout request for user {body['userId']}")
        
        # Generate workout plan
        generator = BedrockWorkoutGenerator()
        workout_plan = generator.generate_workout_plan(
            user_query=body['query'],
            username=body['username'],
            user_id=body['userId']
        )
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'data': {
                    'workoutPlan': workout_plan
                },
                'message': 'Workout plan generated successfully'
            })
        }
        
    except Exception as e:
        logger.error(f"Error in workout generator: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'message': 'Failed to generate workout plan'
            })
        }
'''
    
    return handler_code

def update_workout_generator():
    """Update the workout generator with simplified code"""
    print("🔧 Creating simplified workout generator...")
    
    # Create simplified handler
    handler_code = create_simple_workout_handler()
    
    # Write to the Lambda directory
    handler_path = "src/lambda/workout_generator/handler.py"
    
    # Backup original
    if os.path.exists(handler_path):
        backup_path = handler_path + ".backup"
        with open(handler_path, 'r') as f:
            original_content = f.read()
        with open(backup_path, 'w') as f:
            f.write(original_content)
        print(f"✅ Backed up original to {backup_path}")
    
    # Write simplified version
    with open(handler_path, 'w') as f:
        f.write(handler_code)
    
    print(f"✅ Updated {handler_path} with simplified version")
    print("🚀 Now redeploy with: cdk deploy")

if __name__ == "__main__":
    print("🎯 Fixing Workout Generator Lambda Function")
    print("=" * 60)
    
    update_workout_generator()
    
    print("\n" + "=" * 60)
    print("✅ FIXED! Next steps:")
    print("1. Run: cdk deploy")
    print("2. Test with: py test_real_workout_generation.py")
    print("3. Your system will use REAL Bedrock (not MCP fallback)!")