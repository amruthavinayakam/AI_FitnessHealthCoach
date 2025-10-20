"""Simple test to verify Bedrock integration functionality."""

import sys
import os
sys.path.append('../../shared')

def test_imports():
    """Test that all required modules can be imported."""
    try:
        from models import UserProfile, WorkoutPlan, DailyWorkout, Exercise
        print("✓ Models imported successfully")
        
        from handler import BedrockWorkoutGenerator
        print("✓ Handler imported successfully")
        
        import boto3
        print("✓ Boto3 imported successfully")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_user_profile_creation():
    """Test UserProfile creation and validation."""
    try:
        from models import UserProfile
        
        profile = UserProfile(
            username="testuser",
            user_id="test123",
            query="I want a strength training workout"
        )
        
        assert profile.username == "testuser"
        assert profile.user_id == "test123"
        assert profile.query == "I want a strength training workout"
        assert profile.session_id is not None
        
        print("✓ UserProfile creation test passed")
        return True
    except Exception as e:
        print(f"✗ UserProfile test failed: {e}")
        return False

def test_bedrock_generator_init():
    """Test BedrockWorkoutGenerator initialization."""
    try:
        from unittest.mock import patch
        from handler import BedrockWorkoutGenerator
        
        with patch('boto3.client') as mock_client:
            generator = BedrockWorkoutGenerator()
            assert generator.model_id == 'anthropic.claude-3-haiku-20240307-v1:0'
            assert generator.max_tokens == 2000
            assert generator.temperature == 0.3
            
        print("✓ BedrockWorkoutGenerator initialization test passed")
        return True
    except Exception as e:
        print(f"✗ BedrockWorkoutGenerator test failed: {e}")
        return False

def test_prompt_creation():
    """Test workout prompt creation."""
    try:
        from unittest.mock import patch, AsyncMock
        from handler import BedrockWorkoutGenerator
        from models import UserProfile
        
        with patch('boto3.client'):
            generator = BedrockWorkoutGenerator()
            generator.fitness_mcp = AsyncMock()
            
            profile = UserProfile(
                username="testuser",
                user_id="test123",
                query="I want a strength training workout"
            )
            
            prompt = generator._create_workout_prompt(profile)
            
            assert "strength training workout" in prompt.lower()
            assert "7-day workout plan" in prompt
            assert "JSON" in prompt
            assert "plan_type" in prompt
            
        print("✓ Prompt creation test passed")
        return True
    except Exception as e:
        print(f"✗ Prompt creation test failed: {e}")
        return False

def test_response_parsing():
    """Test Bedrock response parsing."""
    try:
        from unittest.mock import patch, AsyncMock
        from handler import BedrockWorkoutGenerator
        from models import UserProfile
        
        with patch('boto3.client'):
            generator = BedrockWorkoutGenerator()
            generator.fitness_mcp = AsyncMock()
            
            profile = UserProfile(
                username="testuser",
                user_id="test123",
                query="I want a strength training workout"
            )
            
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
            
            workout_plan = generator._parse_workout_response(response, profile)
            
            assert workout_plan.plan_type == "Strength Training"
            assert workout_plan.duration_weeks == 1
            assert len(workout_plan.daily_workouts) == 1
            assert workout_plan.daily_workouts[0].day == "Monday"
            
        print("✓ Response parsing test passed")
        return True
    except Exception as e:
        print(f"✗ Response parsing test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running Bedrock integration tests...")
    print()
    
    tests = [
        test_imports,
        test_user_profile_creation,
        test_bedrock_generator_init,
        test_prompt_creation,
        test_response_parsing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        exit(0)
    else:
        print("❌ Some tests failed")
        exit(1)