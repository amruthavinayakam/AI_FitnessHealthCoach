"""
Pytest configuration for fitness coach testing suite
Shared fixtures and configuration for integration and performance tests
"""

import pytest
import os
import sys
import boto3
from moto import mock_aws
from unittest.mock import patch, Mock

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'lambda', 'fitness_coach_handler'))


@pytest.fixture(scope="session")
def aws_credentials():
    """Mock AWS Credentials for moto"""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def aws_mock(aws_credentials):
    """Mock AWS services"""
    with mock_aws():
        yield {
            'dynamodb': boto3.resource('dynamodb', region_name='us-east-1'),
            'lambda': boto3.client('lambda', region_name='us-east-1'),
            'bedrock': boto3.client('bedrock-runtime', region_name='us-east-1')
        }


@pytest.fixture
def test_environment():
    """Set up test environment variables"""
    test_env = {
        'DYNAMODB_TABLE_NAME': 'test-fitness-coach-sessions',
        'WORKOUT_GENERATOR_FUNCTION_NAME': 'test-workout-generator',
        'MEAL_PLANNER_FUNCTION_NAME': 'test-meal-planner',
        'BEDROCK_MODEL_ID': 'anthropic.claude-3-haiku-20240307-v1:0',
        'BEDROCK_MAX_TOKENS': '2000',
        'BEDROCK_TEMPERATURE': '0.3',
        'AWS_DEFAULT_REGION': 'us-east-1'
    }
    
    with patch.dict(os.environ, test_env):
        yield test_env


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        'username': 'test_user',
        'userId': 'test_123',
        'query': 'I want a balanced workout and meal plan for muscle building'
    }


@pytest.fixture
def mock_successful_workout_response():
    """Mock successful workout generator response"""
    return {
        'statusCode': 200,
        'body': {
            'success': True,
            'data': {
                'workoutPlan': {
                    'user_id': 'test_123',
                    'plan_type': 'Strength Training',
                    'duration_weeks': 1,
                    'daily_workouts': [
                        {
                            'day': 'Monday',
                            'total_duration': 45,
                            'exercises': [
                                {
                                    'name': 'Push-ups',
                                    'sets': 3,
                                    'reps': '12-15',
                                    'duration': 8,
                                    'muscle_groups': ['chest', 'triceps']
                                }
                            ]
                        }
                    ]
                },
                'sessionId': 'test-session-123'
            }
        }
    }


@pytest.fixture
def mock_successful_meal_response():
    """Mock successful meal planner response"""
    return {
        'statusCode': 200,
        'body': {
            'success': True,
            'data': {
                'meal_plan': {
                    'user_id': 'test_123',
                    'weekly_plan': [
                        {
                            'day': 'Day 1',
                            'breakfast': {
                                'title': 'Protein Pancakes',
                                'calories_per_serving': 350,
                                'protein_g': 25,
                                'carbs_g': 40,
                                'fat_g': 8
                            },
                            'lunch': {
                                'title': 'Chicken Salad',
                                'calories_per_serving': 450,
                                'protein_g': 35,
                                'carbs_g': 20,
                                'fat_g': 15
                            },
                            'dinner': {
                                'title': 'Salmon with Rice',
                                'calories_per_serving': 550,
                                'protein_g': 40,
                                'carbs_g': 45,
                                'fat_g': 18
                            },
                            'total_calories': 1350,
                            'total_protein': 100,
                            'total_carbs': 105,
                            'total_fat': 41
                        }
                    ]
                },
                'nutrition_analysis': {
                    'analysis_summary': {
                        'avg_daily_calories': 1350,
                        'avg_daily_protein': 100,
                        'avg_daily_carbs': 105,
                        'avg_daily_fat': 41
                    },
                    'balance_score': 85.0
                }
            }
        }
    }


@pytest.fixture
def mock_service_error_response():
    """Mock service error response"""
    return {
        'statusCode': 503,
        'body': {
            'success': False,
            'error': 'Service temporarily unavailable'
        }
    }


# Performance test configuration
@pytest.fixture
def performance_config():
    """Configuration for performance tests"""
    return {
        'max_response_time_ms': 30000,  # 30 seconds (requirement 4.1)
        'target_success_rate': 99.5,   # 99.5% uptime (requirement 4.2)
        'concurrent_users': 10,
        'requests_per_user': 5,
        'sustained_test_duration': 30,  # seconds
        'target_rps': 5                 # requests per second
    }


# Test markers for different test categories
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# Custom test collection
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add integration marker to integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add performance marker to performance tests
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        
        # Add unit marker to unit tests
        if "test_" in item.name and "integration" not in str(item.fspath) and "performance" not in str(item.fspath):
            item.add_marker(pytest.mark.unit)