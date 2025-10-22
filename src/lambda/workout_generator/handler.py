# Lambda function for workout plan generation using AWS Bedrock
import json
import logging
import os
import boto3
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re
import sys

# Import shared models
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
    current_dir = os.path.dirname(os.path.abspath(__file__))

    models_path = os.path.join(current_dir, "..", "..", "shared", "models.py")
    spec = importlib.util.spec_from_file_location("models", models_path)
    models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models)
    WorkoutPlan = models.WorkoutPlan
    DailyWorkout = models.DailyWorkout
    Exercise = models.Exercise
    UserProfile = models.UserProfile

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
    from fitness_knowledge.server import FitnessKnowledgeMCPServer
except ImportError:
    raise

# Initialize structured logger
logger = get_logger('workout-generator')


# ===============================================================
# Utility for resilient JSON parsing (handles Bedrock quirks)
# ===============================================================
def safe_json_loads(text: str):
    """Attempt to parse JSON text even if Bedrock adds minor formatting errors."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to clean up common issues
        cleaned = text.replace("\u201c", '"').replace("\u201d", '"').replace("“", '"').replace("”", '"')
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)  # Remove trailing commas
        try:
            return json.loads(cleaned)
        except Exception:
            # Try extracting JSON block manually
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                candidate = match.group(0)
                try:
                    return json.loads(candidate)
                except Exception:
                    pass
            raise Exception("Invalid JSON in Bedrock response after cleanup")


# ===============================================================
# Bedrock Workout Generator
# ===============================================================
class BedrockWorkoutGenerator:
    """AWS Bedrock client for generating structured workout plans enhanced with Fitness MCP Server."""

    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime')
        self.model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        self.max_tokens = int(os.environ.get('BEDROCK_MAX_TOKENS', '2000'))
        self.temperature = float(os.environ.get('BEDROCK_TEMPERATURE', '0.3'))
        self.fitness_mcp = FitnessKnowledgeMCPServer()

    def generate_workout_plan(self, user_profile: UserProfile) -> WorkoutPlan:
        """Generate a structured workout plan using AWS Bedrock enhanced with Fitness MCP Server."""
        try:
            prompt = self._create_workout_prompt(user_profile)
            response = self._call_bedrock_api(prompt)
            logger.info(f"\n----- RAW BEDROCK RESPONSE START -----\n{response[:2000]}\n----- RAW BEDROCK RESPONSE END -----")

            workout_plan = self._parse_workout_response(response, user_profile)
            enhanced_workout_plan = asyncio.run(self._enhance_workout_with_mcp(workout_plan))

            logger.info(f"Successfully generated enhanced workout plan for user {user_profile.user_id}")
            return enhanced_workout_plan

        except Exception as e:
            logger.error(f"Error generating workout plan: {str(e)}")
            raise

    # ===============================================================
    # Prompt builder
    # ===============================================================
    def _create_workout_prompt(self, user_profile: UserProfile) -> str:
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
- Duration in minutes
- lowercase muscle groups
- 7 days total, 4–8 exercises per day
- JSON only, no explanations or markdown formatting

Generate a complete 7-day workout plan following this exact JSON format:
"""
        return prompt

    # ===============================================================
    # Bedrock API call
    # ===============================================================
    def _call_bedrock_api(self, prompt: str) -> str:
        """Call AWS Bedrock API with structured prompt, handle bad JSON gracefully."""
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": 0.9,
                "messages": [{"role": "user", "content": prompt}]
            }

            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )

            # Read and parse response body
            raw_bytes = response['body'].read()
            try:
                response_body = json.loads(raw_bytes)
            except Exception as e:
                raise Exception(f"Failed to parse Bedrock envelope: {str(e)}")

            if 'content' not in response_body or not response_body['content']:
                raise Exception("Empty response from Bedrock")

            content = response_body['content'][0].get('text', '').strip()
            if not content:
                raise Exception("Bedrock returned empty text content")

            logger.info(f"Bedrock API call successful, response length: {len(content)}")
            return content

        except Exception as e:
            logger.error(f"Bedrock API call failed: {str(e)}")
            raise Exception(f"Failed to generate workout plan: {str(e)}")

    # ===============================================================
    # Response parsing
    # ===============================================================
    def _extract_json_text(self, response: str) -> str:
        """Extract JSON block from model output."""
        m = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'\{.*\}', response, re.DOTALL)
        if not m:
            raise Exception("No JSON object found in Bedrock response")
        return m.group(0)

    def _parse_workout_response(self, response: str, user_profile: UserProfile) -> WorkoutPlan:
        """Parse Bedrock JSON safely into structured WorkoutPlan."""
        try:
            json_str = self._extract_json_text(response)
            workout_data = safe_json_loads(json_str)

            required_fields = ['plan_type', 'duration_weeks', 'daily_workouts']
            for field in required_fields:
                if field not in workout_data:
                    raise Exception(f"Missing required field: {field}")

            daily_workouts: List[DailyWorkout] = []
            expected_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

            for workout_item in workout_data['daily_workouts']:
                if workout_item['day'] not in expected_days:
                    raise Exception(f"Invalid day: {workout_item['day']}")

                exercises = []
                for ex in workout_item['exercises']:
                    exercises.append(Exercise(
                        name=ex['name'],
                        sets=int(ex['sets']),
                        reps=str(ex['reps']),
                        duration=int(ex['duration']),
                        muscle_groups=ex['muscle_groups']
                    ))

                daily_workouts.append(DailyWorkout(
                    day=workout_item['day'],
                    exercises=exercises,
                    total_duration=int(workout_item['total_duration']),
                    notes=workout_item.get('notes')
                ))

            plan = WorkoutPlan(
                user_id=user_profile.user_id,
                plan_type=workout_data['plan_type'],
                duration_weeks=int(workout_data['duration_weeks']),
                daily_workouts=daily_workouts
            )

            logger.info(f"Successfully parsed workout plan with {len(daily_workouts)} days")
            return plan

        except Exception as e:
            logger.error(f"Error parsing Bedrock JSON: {str(e)}")
            raise Exception(f"Invalid JSON in Bedrock response: {str(e)}")

    # ===============================================================
    # Enhancement via Fitness MCP
    # ===============================================================
    async def _enhance_workout_with_mcp(self, workout_plan: WorkoutPlan) -> WorkoutPlan:
        try:
            enhanced_days: List[DailyWorkout] = []

            for day in workout_plan.daily_workouts:
                enhanced_exs = []
                for ex in day.exercises:
                    info = await self.fitness_mcp.get_exercise_info(ex.name)
                    if "error" not in info:
                        ex.form_description = info.get("form_description")
                        ex.safety_notes = "; ".join(info.get("safety_guidelines", [])[:2])
                    enhanced_exs.append(ex)
                enhanced_days.append(DailyWorkout(
                    day=day.day,
                    exercises=enhanced_exs,
                    total_duration=day.total_duration,
                    notes=day.notes
                ))

            validation = await self.fitness_mcp.validate_workout_balance({
                "exercises": [ex.name for d in enhanced_days for ex in d.exercises]
            })

            if not validation.get("balanced", True):
                note = f"Balance recommendations: {'; '.join(validation.get('recommendations', [])[:2])}"
                if enhanced_days:
                    enhanced_days[0].notes = (enhanced_days[0].notes or '') + " | " + note

            return WorkoutPlan(
                user_id=workout_plan.user_id,
                plan_type=workout_plan.plan_type,
                duration_weeks=workout_plan.duration_weeks,
                daily_workouts=enhanced_days,
                created_at=workout_plan.created_at
            )

        except Exception as e:
            logger.warning(f"Enhancement failed: {str(e)}")
            return workout_plan


# ===============================================================
# Lambda Handler
# ===============================================================
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry for generating workout plans via AWS Bedrock."""
    try:
        if not event or 'body' not in event:
            raise Exception("Missing request body")

        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        for f in ['username', 'userId', 'query']:
            if f not in body:
                raise Exception(f"Missing required field: {f}")

        user_profile = UserProfile(
            username=body['username'],
            user_id=body['userId'],
            query=body['query']
        )

        generator = BedrockWorkoutGenerator()
        workout_plan = generator.generate_workout_plan(user_profile)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'data': {
                    'workoutPlan': workout_plan.to_dynamodb_item(),
                    'sessionId': user_profile.session_id
                },
                'message': 'Workout plan generated successfully'
            }, default=str)
        }

    except Exception as e:
        logger.error(f"Error in workout generator: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'message': 'Failed to generate workout plan'
            })
        }
