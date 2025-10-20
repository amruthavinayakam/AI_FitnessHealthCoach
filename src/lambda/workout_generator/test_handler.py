"""
Unit tests for Bedrock integration in workout generator.

This module tests the BedrockWorkoutGenerator class including:
- Bedrock API call mocking
- Prompt engineering validation
- Response parsing and validation
- Workout plan structure validation
- Error handling scenarios
"""

import pytest
import json
import boto3
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
import asyncio
import sys
import os

# Add shared modules to path
sys.path.append('../shared')
sys.path.append('../../shared')

# Import shared models with proper path handling
try:
    from models import UserProfile, WorkoutPlan, DailyWorkout, Exercise
except ImportError:
    # Fallback for different path structures
    import importlib.util
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_path = os.path.join(current_dir, "..", "..", "shared", "models.py")
    spec = importlib.util.spec_from_file_location("models", models_path)
    models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models)
    UserProfile = models.UserProfile
    WorkoutPlan = models.WorkoutPlan
    DailyWorkout = models.DailyWorkout
    Exercise = models.Exercise

from handler import BedrockWorkoutGenerator


class TestBedrockWorkoutGenerator:
    """Test suite for BedrockWorkoutGenerator class."""
    
    @pytest.fixture
    def sample_user_profile(self):
        """Create a sample user profile for testing."""
        return UserProfile(
            username="testuser",
            user_id="test123",
            query="I want a strength training workout plan for building muscle"
        )
    
    @pytest.fixture
    def mock_bedrock_response(self):
        """Create a mock Bedrock API response."""
        return {
            'body': Mock(read=Mock(return_value=json.dumps({
                'content': [{
                    'text': '''```json
{
    "plan_type": "Strength Training",
    "duration_weeks": 1,
    "daily_workouts": [
        {
            "day": "Monday",
            "total_duration": 45,
            "notes": "Upper body focus",
            "exercises": [
                {
                    "name": "Push-ups",
                    "sets": 3,
                    "reps": "12-15",
                    "duration": 8,
                    "muscle_groups": ["chest", "triceps", "shoulders"]
                },
                {
                    "name": "Pull-ups",
                    "sets": 3,
                    "reps": "8-10",
                    "duration": 10,
                    "muscle_groups": ["back", "biceps"]
                }
            ]
        },
        {
            "day": "Tuesday",
            "total_duration": 40,
            "notes": "Lower body focus",
            "exercises": [
                {
                    "name": "Squats",
                    "sets": 4,
                    "reps": "15-20",
                    "duration": 12,
                    "muscle_groups": ["legs", "glutes"]
                }
            ]
        }
    ]
}
```'''
                }]
            }).encode()))
        }
    
    @pytest.fixture
    def mock_fitness_mcp_server(self):
        """Create a mock Fitness MCP Server."""
        mock_server = AsyncMock()
        
        # Mock exercise info responses
        mock_server.get_exercise_info.return_value = {
            "form_description": "Keep your back straight and core engaged",
            "safety_guidelines": ["Warm up properly", "Use proper form", "Don't overexert"]
        }
        
        # Mock workout progression responses
        mock_server.suggest_workout_progression.return_value = {
            "volume_adjustments": {
                "Push-ups": {"sets": 3, "reps": "12-15"},
                "Pull-ups": {"sets": 3, "reps": "8-10"}
            }
        }
        
        # Mock workout balance validation
        mock_server.validate_workout_balance.return_value = {
            "balanced": True,
            "recommendations": []
        }
        
        return mock_server
    
    @pytest.fixture
    def generator_with_mocks(self, mock_fitness_mcp_server):
        """Create BedrockWorkoutGenerator with mocked dependencies."""
        with patch('boto3.client') as mock_boto_client:
            generator = BedrockWorkoutGenerator()
            generator.bedrock_client = Mock()
            generator.fitness_mcp = mock_fitness_mcp_server
            return generator
    
    def test_init_bedrock_generator(self):
        """Test BedrockWorkoutGenerator initialization."""
        with patch('boto3.client') as mock_boto_client:
            with patch.dict(os.environ, {
                'BEDROCK_MODEL_ID': 'test-model',
                'BEDROCK_MAX_TOKENS': '1500',
                'BEDROCK_TEMPERATURE': '0.5'
            }):
                generator = BedrockWorkoutGenerator()
                
                assert generator.model_id == 'test-model'
                assert generator.max_tokens == 1500
                assert generator.temperature == 0.5
                mock_boto_client.assert_called_with('bedrock-runtime')
    
    def test_create_workout_prompt(self, generator_with_mocks, sample_user_profile):
        """Test workout prompt creation."""
        prompt = generator_with_mocks._create_workout_prompt(sample_user_profile)
        
        # Verify prompt contains user query
        assert sample_user_profile.query in prompt
        
        # Verify prompt contains required structure elements
        assert "7-day workout plan" in prompt
        assert "JSON" in prompt
        assert "plan_type" in prompt
        assert "daily_workouts" in prompt
        assert "exercises" in prompt
        
        # Verify prompt contains guidance for exercise selection
        assert "push-ups" in prompt.lower()
        assert "squats" in prompt.lower()
        assert "muscle_groups" in prompt
    
    def test_call_bedrock_api_success(self, generator_with_mocks, mock_bedrock_response):
        """Test successful Bedrock API call."""
        generator_with_mocks.bedrock_client.invoke_model.return_value = mock_bedrock_response
        
        prompt = "Test prompt"
        response = generator_with_mocks._call_bedrock_api(prompt)
        
        # Verify API was called with correct parameters
        generator_with_mocks.bedrock_client.invoke_model.assert_called_once()
        call_args = generator_with_mocks.bedrock_client.invoke_model.call_args
        
        assert call_args[1]['modelId'] == generator_with_mocks.model_id
        assert call_args[1]['contentType'] == 'application/json'
        assert call_args[1]['accept'] == 'application/json'
        
        # Verify request body structure
        request_body = json.loads(call_args[1]['body'])
        assert request_body['anthropic_version'] == 'bedrock-2023-05-31'
        assert request_body['max_tokens'] == generator_with_mocks.max_tokens
        assert request_body['temperature'] == generator_with_mocks.temperature
        assert request_body['messages'][0]['content'] == prompt
        
        # Verify response parsing
        assert "```json" in response
        assert "plan_type" in response
    
    def test_call_bedrock_api_failure(self, generator_with_mocks):
        """Test Bedrock API call failure handling."""
        generator_with_mocks.bedrock_client.invoke_model.side_effect = Exception("API Error")
        
        with pytest.raises(Exception) as exc_info:
            generator_with_mocks._call_bedrock_api("Test prompt")
        
        assert "Failed to generate workout plan" in str(exc_info.value)
    
    def test_call_bedrock_api_empty_response(self, generator_with_mocks):
        """Test handling of empty Bedrock response."""
        empty_response = {
            'body': Mock(read=Mock(return_value=json.dumps({
                'content': []
            }).encode()))
        }
        generator_with_mocks.bedrock_client.invoke_model.return_value = empty_response
        
        with pytest.raises(Exception) as exc_info:
            generator_with_mocks._call_bedrock_api("Test prompt")
        
        assert "Empty response from Bedrock" in str(exc_info.value)
    
    def test_parse_workout_response_success(self, generator_with_mocks, sample_user_profile):
        """Test successful workout response parsing."""
        response = '''```json
{
    "plan_type": "Strength Training",
    "duration_weeks": 1,
    "daily_workouts": [
        {
            "day": "Monday",
            "total_duration": 45,
            "notes": "Upper body focus",
            "exercises": [
                {
                    "name": "Push-ups",
                    "sets": 3,
                    "reps": "12-15",
                    "duration": 8,
                    "muscle_groups": ["chest", "triceps"]
                }
            ]
        }
    ]
}
```'''
        
        workout_plan = generator_with_mocks._parse_workout_response(response, sample_user_profile)
        
        # Verify workout plan structure
        assert workout_plan.__class__.__name__ == 'WorkoutPlan'
        assert workout_plan.user_id == sample_user_profile.user_id
        assert workout_plan.plan_type == "Strength Training"
        assert workout_plan.duration_weeks == 1
        assert len(workout_plan.daily_workouts) == 1
        
        # Verify daily workout structure
        daily_workout = workout_plan.daily_workouts[0]
        assert daily_workout.day == "Monday"
        assert daily_workout.total_duration == 45
        assert daily_workout.notes == "Upper body focus"
        assert len(daily_workout.exercises) == 1
        
        # Verify exercise structure
        exercise = daily_workout.exercises[0]
        assert exercise.name == "Push-ups"
        assert exercise.sets == 3
        assert exercise.reps == "12-15"
        assert exercise.duration == 8
        assert exercise.muscle_groups == ["chest", "triceps"]
    
    def test_parse_workout_response_no_json(self, generator_with_mocks, sample_user_profile):
        """Test parsing response without valid JSON."""
        response = "This is not a valid JSON response"
        
        with pytest.raises(Exception) as exc_info:
            generator_with_mocks._parse_workout_response(response, sample_user_profile)
        
        assert "No valid JSON found" in str(exc_info.value)
    
    def test_parse_workout_response_invalid_json(self, generator_with_mocks, sample_user_profile):
        """Test parsing response with invalid JSON."""
        response = '''```json
{
    "plan_type": "Strength Training",
    "invalid_json": 
}
```'''
        
        with pytest.raises(Exception) as exc_info:
            generator_with_mocks._parse_workout_response(response, sample_user_profile)
        
        assert "Invalid JSON in Bedrock response" in str(exc_info.value)
    
    def test_parse_workout_response_missing_fields(self, generator_with_mocks, sample_user_profile):
        """Test parsing response with missing required fields."""
        response = '''```json
{
    "plan_type": "Strength Training"
}
```'''
        
        with pytest.raises(Exception) as exc_info:
            generator_with_mocks._parse_workout_response(response, sample_user_profile)
        
        assert "Missing required field" in str(exc_info.value)
    
    def test_parse_workout_response_invalid_day(self, generator_with_mocks, sample_user_profile):
        """Test parsing response with invalid day name."""
        response = '''```json
{
    "plan_type": "Strength Training",
    "duration_weeks": 1,
    "daily_workouts": [
        {
            "day": "InvalidDay",
            "total_duration": 45,
            "exercises": [
                {
                    "name": "Push-ups",
                    "sets": 3,
                    "reps": "12-15",
                    "duration": 8,
                    "muscle_groups": ["chest"]
                }
            ]
        }
    ]
}
```'''
        
        with pytest.raises(Exception) as exc_info:
            generator_with_mocks._parse_workout_response(response, sample_user_profile)
        
        assert "Invalid day: InvalidDay" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_enhance_workout_with_mcp_success(self, generator_with_mocks, sample_user_profile):
        """Test successful workout enhancement with MCP server."""
        # Create basic workout plan
        exercise = Exercise(
            name="Push-ups",
            sets=3,
            reps="12-15",
            duration=8,
            muscle_groups=["chest", "triceps"]
        )
        daily_workout = DailyWorkout(
            day="Monday",
            exercises=[exercise],
            total_duration=45
        )
        workout_plan = WorkoutPlan(
            user_id=sample_user_profile.user_id,
            plan_type="Strength Training",
            duration_weeks=1,
            daily_workouts=[daily_workout]
        )
        
        # Enhance workout plan
        enhanced_plan = await generator_with_mocks._enhance_workout_with_mcp(workout_plan)
        
        # Verify MCP server was called
        generator_with_mocks.fitness_mcp.get_exercise_info.assert_called_with("Push-ups")
        generator_with_mocks.fitness_mcp.suggest_workout_progression.assert_called()
        generator_with_mocks.fitness_mcp.validate_workout_balance.assert_called()
        
        # Verify enhancement was applied
        enhanced_exercise = enhanced_plan.daily_workouts[0].exercises[0]
        assert enhanced_exercise.form_description == "Keep your back straight and core engaged"
        assert "Warm up properly" in enhanced_exercise.safety_notes
    
    @pytest.mark.asyncio
    async def test_enhance_workout_with_mcp_failure(self, generator_with_mocks, sample_user_profile):
        """Test workout enhancement when MCP server fails."""
        # Create basic workout plan
        exercise = Exercise(
            name="Push-ups",
            sets=3,
            reps="12-15",
            duration=8,
            muscle_groups=["chest", "triceps"]
        )
        daily_workout = DailyWorkout(
            day="Monday",
            exercises=[exercise],
            total_duration=45
        )
        workout_plan = WorkoutPlan(
            user_id=sample_user_profile.user_id,
            plan_type="Strength Training",
            duration_weeks=1,
            daily_workouts=[daily_workout]
        )
        
        # Mock MCP server failure
        generator_with_mocks.fitness_mcp.get_exercise_info.return_value = {"error": "Exercise not found"}
        
        # Enhance workout plan (should not fail, just return original)
        enhanced_plan = await generator_with_mocks._enhance_workout_with_mcp(workout_plan)
        
        # Verify original plan is returned when MCP fails
        assert enhanced_plan.user_id == workout_plan.user_id
        assert len(enhanced_plan.daily_workouts) == 1
        assert enhanced_plan.daily_workouts[0].exercises[0].name == "Push-ups"
    
    def test_determine_user_level(self, generator_with_mocks):
        """Test user level determination from plan type."""
        assert generator_with_mocks._determine_user_level("Beginner Strength Training") == "beginner"
        assert generator_with_mocks._determine_user_level("Advanced Powerlifting") == "advanced"
        assert generator_with_mocks._determine_user_level("Intermediate Bodybuilding") == "intermediate"
        assert generator_with_mocks._determine_user_level("General Fitness") == "intermediate"  # Default
    
    @patch('asyncio.run')
    def test_generate_workout_plan_success(self, mock_asyncio_run, generator_with_mocks, sample_user_profile, mock_bedrock_response):
        """Test complete workout plan generation success."""
        # Mock Bedrock API call
        generator_with_mocks.bedrock_client.invoke_model.return_value = mock_bedrock_response
        
        # Mock MCP enhancement (asyncio.run will call the actual method)
        async def mock_enhance(workout_plan):
            return workout_plan
        mock_asyncio_run.side_effect = lambda coro: asyncio.get_event_loop().run_until_complete(coro)
        
        # Generate workout plan
        workout_plan = generator_with_mocks.generate_workout_plan(sample_user_profile)
        
        # Verify result
        assert workout_plan.__class__.__name__ == 'WorkoutPlan'
        assert workout_plan.user_id == sample_user_profile.user_id
        assert workout_plan.plan_type == "Strength Training"
        assert len(workout_plan.daily_workouts) == 2  # Monday and Tuesday from mock response
    
    def test_generate_workout_plan_bedrock_failure(self, generator_with_mocks, sample_user_profile):
        """Test workout plan generation when Bedrock fails."""
        generator_with_mocks.bedrock_client.invoke_model.side_effect = Exception("Bedrock API Error")
        
        with pytest.raises(Exception) as exc_info:
            generator_with_mocks.generate_workout_plan(sample_user_profile)
        
        assert "Bedrock API Error" in str(exc_info.value)


class TestLambdaHandler:
    """Test suite for Lambda handler function."""
    
    @pytest.fixture
    def valid_event(self):
        """Create a valid Lambda event."""
        return {
            'body': json.dumps({
                'username': 'testuser',
                'userId': 'test123',
                'query': 'I want a strength training workout'
            })
        }
    
    @pytest.fixture
    def mock_workout_plan(self):
        """Create a mock workout plan for testing."""
        exercise = Exercise(
            name="Push-ups",
            sets=3,
            reps="12-15",
            duration=8,
            muscle_groups=["chest", "triceps"]
        )
        daily_workout = DailyWorkout(
            day="Monday",
            exercises=[exercise],
            total_duration=45
        )
        return WorkoutPlan(
            user_id="test123",
            plan_type="Strength Training",
            duration_weeks=1,
            daily_workouts=[daily_workout]
        )
    
    @patch('handler.BedrockWorkoutGenerator')
    def test_lambda_handler_success(self, mock_generator_class, valid_event, mock_workout_plan):
        """Test successful Lambda handler execution."""
        from handler import lambda_handler
        
        # Mock generator
        mock_generator = Mock()
        mock_generator.generate_workout_plan.return_value = mock_workout_plan
        mock_generator_class.return_value = mock_generator
        
        # Call handler
        response = lambda_handler(valid_event, {})
        
        # Verify response
        assert response['statusCode'] == 200
        assert 'application/json' in response['headers']['Content-Type']
        
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'workoutPlan' in body['data']
        assert 'sessionId' in body['data']
        assert body['message'] == 'Workout plan generated successfully'
    
    def test_lambda_handler_missing_body(self):
        """Test Lambda handler with missing body."""
        from handler import lambda_handler
        
        event = {}
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Missing request body' in body['error']
    
    def test_lambda_handler_invalid_json(self):
        """Test Lambda handler with invalid JSON body."""
        from handler import lambda_handler
        
        event = {'body': 'invalid json'}
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['success'] is False
    
    def test_lambda_handler_missing_fields(self):
        """Test Lambda handler with missing required fields."""
        from handler import lambda_handler
        
        event = {
            'body': json.dumps({
                'username': 'testuser'
                # Missing userId and query
            })
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Missing required field' in body['error']
    
    @patch('handler.BedrockWorkoutGenerator')
    def test_lambda_handler_generator_failure(self, mock_generator_class, valid_event):
        """Test Lambda handler when workout generator fails."""
        from handler import lambda_handler
        
        # Mock generator failure
        mock_generator = Mock()
        mock_generator.generate_workout_plan.side_effect = Exception("Generation failed")
        mock_generator_class.return_value = mock_generator
        
        # Call handler
        response = lambda_handler(valid_event, {})
        
        # Verify error response
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Generation failed' in body['error']


if __name__ == '__main__':
    pytest.main([__file__])