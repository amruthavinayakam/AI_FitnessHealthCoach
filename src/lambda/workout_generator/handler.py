# Lambda function for workout plan generation using AWS Bedrock
import json
import logging
import os
import boto3
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re

# Import shared models
import sys
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append('../shared')    # Local development path

try:
    from models import WorkoutPlan, DailyWorkout, Exercise, UserProfile
    from logging_utils import (
        get_logger, log_api_request, log_function_call, 
        log_external_service_call, log_performance_metric
    )
except ImportError:
    # Fallback for local development
    import importlib.util
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_path = os.path.join(current_dir, "..", "..", "shared", "models.py")
    spec = importlib.util.spec_from_file_location("models", models_path)
    models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models)
    WorkoutPlan = models.WorkoutPlan
    DailyWorkout = models.DailyWorkout
    Exercise = models.Exercise
    UserProfile = models.UserProfile
    
    # Import logging utils
    logging_path = os.path.join(current_dir, "..", "..", "shared", "logging_utils.py")
    spec = importlib.util.spec_from_file_location("logging_utils", logging_path)
    logging_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logging_utils)
    get_logger = logging_utils.get_logger
    log_api_request = logging_utils.log_api_request
    log_function_call = logging_utils.log_function_call
    log_external_service_call = logging_utils.log_external_service_call
    log_performance_metric = logging_utils.log_performance_metric

# Import Fitness MCP Server
try:
    from fitness_knowledge_server import FitnessKnowledgeMCPServer
except ImportError:
    # Fallback for local development
    import importlib.util
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    fitness_server_path = os.path.join(current_dir, "..", "..", "mcp_servers", "fitness_knowledge", "server.py")
    spec = importlib.util.spec_from_file_location("fitness_knowledge_server", fitness_server_path)
    fitness_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fitness_module)
    FitnessKnowledgeMCPServer = fitness_module.FitnessKnowledgeMCPServer

# Initialize structured logger
logger = get_logger('workout-generator')

class BedrockWorkoutGenerator:
    """AWS Bedrock client for generating structured workout plans enhanced with Fitness MCP Server."""
    
    def __init__(self):
        """Initialize Bedrock client and Fitness MCP Server."""
        self.bedrock_client = boto3.client('bedrock-runtime')
        self.model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        self.max_tokens = int(os.environ.get('BEDROCK_MAX_TOKENS', '2000'))
        self.temperature = float(os.environ.get('BEDROCK_TEMPERATURE', '0.3'))
        #self.fitness_mcp = FitnessKnowledgeMCPServer()
        
    def generate_workout_plan(self, user_profile: UserProfile) -> WorkoutPlan:
        """
        Generate a structured workout plan using AWS Bedrock enhanced with Fitness MCP Server.
        
        Args:
            user_profile: User profile with query and preferences
            
        Returns:
            WorkoutPlan: Enhanced workout plan object with form descriptions and safety guidelines
            
        Raises:
            Exception: If Bedrock API call fails or response parsing fails
        """
        try:
            # Create structured prompt
            prompt = self._create_workout_prompt(user_profile)
            
            # Call Bedrock API
            response = self._call_bedrock_api(prompt)
            
            # Parse and validate response
            workout_plan = self._parse_workout_response(response, user_profile)
            
            # Enhance workout plan with MCP server data
            enhanced_workout_plan = asyncio.run(self._enhance_workout_with_mcp(workout_plan))
            
            logger.info(f"Successfully generated enhanced workout plan for user {user_profile.user_id}")
            return enhanced_workout_plan
            
        except Exception as e:
            logger.error(f"Error generating workout plan: {str(e)}")
            raise
    
    def _create_workout_prompt(self, user_profile: UserProfile) -> str:
        """
        Create structured prompt for consistent workout plan generation.
        
        Args:
            user_profile: User profile with query and preferences
            
        Returns:
            str: Formatted prompt for Bedrock
        """
        prompt = f"""You are a professional fitness coach creating a personalized 7-day workout plan. 

USER REQUEST: {user_profile.query}

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

GUIDELINES:
- Use realistic rep ranges (e.g., "8-12", "30 seconds", "10 per side")
- Duration should be in minutes for each exercise
- Muscle groups should be lowercase (e.g., "chest", "back", "legs", "core", "shoulders", "biceps", "triceps")
- Include compound and isolation exercises
- Balance push/pull movements
- Consider user's apparent fitness level from their request
- Focus on common exercises that have detailed form descriptions available
- Prioritize exercises like: push-ups, pull-ups, squats, deadlifts, bench press, overhead press
- Include both bodyweight and equipment-based exercises when appropriate

ENHANCEMENT NOTE: This workout will be enhanced with detailed form descriptions, safety guidelines, and progressive overload recommendations from our fitness knowledge database.

Generate a complete 7-day workout plan following this exact JSON format:"""

        return prompt
    
    def _call_bedrock_api(self, prompt: str) -> str:
        """
        Call AWS Bedrock API with the structured prompt.
        
        Args:
            prompt: Formatted prompt string
            
        Returns:
            str: Raw response from Bedrock
            
        Raises:
            Exception: If Bedrock API call fails
        """
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
    
    def _parse_workout_response(self, response: str, user_profile: UserProfile) -> WorkoutPlan:
        """
        Parse Bedrock response into structured WorkoutPlan object.
        
        Args:
            response: Raw response from Bedrock
            user_profile: User profile for workout plan
            
        Returns:
            WorkoutPlan: Validated workout plan object
            
        Raises:
            Exception: If response parsing or validation fails
        """
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without markdown
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
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
            
            # Parse daily workouts
            daily_workouts = []
            expected_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            for workout_data_item in workout_data['daily_workouts']:
                # Validate day
                if workout_data_item['day'] not in expected_days:
                    raise Exception(f"Invalid day: {workout_data_item['day']}")
                
                # Parse exercises
                exercises = []
                for ex_data in workout_data_item['exercises']:
                    exercise = Exercise(
                        name=ex_data['name'],
                        sets=int(ex_data['sets']),
                        reps=str(ex_data['reps']),
                        duration=int(ex_data['duration']),
                        muscle_groups=ex_data['muscle_groups']
                    )
                    exercises.append(exercise)
                
                # Create daily workout
                daily_workout = DailyWorkout(
                    day=workout_data_item['day'],
                    exercises=exercises,
                    total_duration=int(workout_data_item['total_duration']),
                    notes=workout_data_item.get('notes')
                )
                daily_workouts.append(daily_workout)
            
            # Create workout plan
            workout_plan = WorkoutPlan(
                user_id=user_profile.user_id,
                plan_type=workout_data['plan_type'],
                duration_weeks=int(workout_data['duration_weeks']),
                daily_workouts=daily_workouts
            )
            
            logger.info(f"Successfully parsed workout plan with {len(daily_workouts)} days")
            return workout_plan
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            raise Exception(f"Invalid JSON in Bedrock response: {str(e)}")
        except Exception as e:
            logger.error(f"Workout response parsing error: {str(e)}")
            raise Exception(f"Failed to parse workout plan: {str(e)}")
    
    async def _enhance_workout_with_mcp(self, workout_plan: WorkoutPlan) -> WorkoutPlan:
        """
        Enhance workout plan with detailed exercise information from Fitness MCP Server.
        
        Args:
            workout_plan: Basic workout plan from Bedrock
            
        Returns:
            WorkoutPlan: Enhanced workout plan with form descriptions and safety guidelines
        """
        try:
            enhanced_daily_workouts = []
            
            for daily_workout in workout_plan.daily_workouts:
                enhanced_exercises = []
                
                for exercise in daily_workout.exercises:
                    # Get detailed exercise information from MCP server
                    exercise_info = await self.fitness_mcp.get_exercise_info(exercise.name)
                    
                    if "error" not in exercise_info:
                        # Create enhanced exercise with MCP data
                        enhanced_exercise = Exercise(
                            name=exercise.name,
                            sets=exercise.sets,
                            reps=exercise.reps,
                            duration=exercise.duration,
                            muscle_groups=exercise.muscle_groups,
                            form_description=exercise_info.get("form_description"),
                            safety_notes="; ".join(exercise_info.get("safety_guidelines", [])[:2])  # Top 2 safety tips
                        )
                        
                        # Apply progressive overload recommendations based on user level
                        user_level = self._determine_user_level(workout_plan.plan_type)
                        progression_info = await self.fitness_mcp.suggest_workout_progression(
                            {"exercises": [exercise.name]}, 
                            user_level
                        )
                        
                        # Adjust sets and reps based on MCP recommendations
                        if progression_info.get("volume_adjustments"):
                            volume_adj = progression_info["volume_adjustments"].get(exercise.name, {})
                            if volume_adj:
                                enhanced_exercise.sets = volume_adj.get("sets", exercise.sets)
                                enhanced_exercise.reps = volume_adj.get("reps", exercise.reps)
                        
                        enhanced_exercises.append(enhanced_exercise)
                    else:
                        # Keep original exercise if MCP lookup fails
                        logger.warning(f"MCP lookup failed for exercise: {exercise.name}")
                        enhanced_exercises.append(exercise)
                
                # Create enhanced daily workout
                enhanced_daily_workout = DailyWorkout(
                    day=daily_workout.day,
                    exercises=enhanced_exercises,
                    total_duration=daily_workout.total_duration,
                    notes=daily_workout.notes
                )
                enhanced_daily_workouts.append(enhanced_daily_workout)
            
            # Perform workout balance validation
            workout_validation = await self.fitness_mcp.validate_workout_balance({
                "exercises": [ex.name for daily in enhanced_daily_workouts for ex in daily.exercises]
            })
            
            # Add balance recommendations to workout notes if needed
            if not workout_validation.get("balanced", True):
                balance_notes = f"Balance recommendations: {'; '.join(workout_validation.get('recommendations', [])[:2])}"
                if enhanced_daily_workouts:
                    if enhanced_daily_workouts[0].notes:
                        enhanced_daily_workouts[0].notes += f" | {balance_notes}"
                    else:
                        enhanced_daily_workouts[0].notes = balance_notes
            
            # Create enhanced workout plan
            enhanced_workout_plan = WorkoutPlan(
                user_id=workout_plan.user_id,
                plan_type=workout_plan.plan_type,
                duration_weeks=workout_plan.duration_weeks,
                daily_workouts=enhanced_daily_workouts,
                created_at=workout_plan.created_at
            )
            
            logger.info(f"Enhanced workout plan with MCP data for {len(enhanced_daily_workouts)} days")
            return enhanced_workout_plan
            
        except Exception as e:
            logger.error(f"Error enhancing workout with MCP: {str(e)}")
            # Return original workout plan if enhancement fails
            return workout_plan
    
    def _determine_user_level(self, plan_type: str) -> str:
        """
        Determine user fitness level from plan type for MCP recommendations.
        
        Args:
            plan_type: Type of workout plan
            
        Returns:
            str: User level (beginner, intermediate, advanced)
        """
        plan_type_lower = plan_type.lower()
        
        if any(keyword in plan_type_lower for keyword in ["beginner", "starter", "basic", "introduction"]):
            return "beginner"
        elif any(keyword in plan_type_lower for keyword in ["advanced", "expert", "competitive", "athlete"]):
            return "advanced"
        else:
            return "intermediate"  # Default to intermediate


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generate workout plans using AWS Bedrock.
    
    Expected event format:
    {
        "username": "string",
        "userId": "string", 
        "query": "string"
    }
    """
    try:
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
        
        # Create user profile
        user_profile = UserProfile(
            username=body['username'],
            user_id=body['userId'],
            query=body['query']
        )
        
        # Generate workout plan
        generator = BedrockWorkoutGenerator()
        workout_plan = generator.generate_workout_plan(user_profile)
        
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
                    'workoutPlan': workout_plan.to_dynamodb_item(),
                    'sessionId': user_profile.session_id
                },
                'message': 'Workout plan generated successfully'
            }, default=str)  # Handle Decimal serialization
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