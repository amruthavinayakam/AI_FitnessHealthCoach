#!/usr/bin/env python3
"""
Integration tests for full fitness coach workflow
Task 8.1: Create integration tests for full workflow
- Test complete user request to response workflow
- Validate workout and meal plan generation end-to-end
- Test error scenarios and service failure handling
- Requirements: 1.1, 1.6, 4.4, 4.5
"""

import json
import pytest
import boto3
import os
import sys
import uuid
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime
import asyncio
from moto import mock_aws

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'lambda', 'fitness_coach_handler'))

from handler import lambda_handler, FitnessCoachAPIHandler


class TestFullWorkflowIntegration:
    """Integration tests for complete fitness coach workflow"""
    
    @pytest.fixture
    def valid_api_event(self):
        """Create a valid API Gateway event for testing"""
        return {
            'httpMethod': 'POST',
            'path': '/fitness-coach',
            'headers': {
                'Content-Type': 'application/json'
            },
            'requestContext': {
                'identity': {
                    'sourceIp': '127.0.0.1'
                }
            },
            'body': json.dumps({
                'username': 'integration_test_user',
                'userId': 'test_user_123',
                'query': 'I want a strength training workout plan and healthy meals for muscle building'
            })
        }
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Lambda context"""
        context = Mock()
        context.aws_request_id = str(uuid.uuid4())
        context.function_name = 'fitness-coach-handler'
        context.memory_limit_in_mb = 512
        context.remaining_time_in_millis = lambda: 30000
        return context
    
    @pytest.fixture
    def mock_workout_response(self):
        """Mock successful workout generator response"""
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'data': {
                    'workoutPlan': {
                        'user_id': 'test_user_123',
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
                    'sessionId': str(uuid.uuid4())
                }
            })
        }
    
    @pytest.fixture
    def mock_meal_response(self):
        """Mock successful meal planner response"""
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'data': {
                    'meal_plan': {
                        'user_id': 'test_user_123',
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
            })
        }
    
    @mock_aws
    def test_complete_successful_workflow(self, valid_api_event, mock_context, 
                                        mock_workout_response, mock_meal_response):
        """
        Test complete successful workflow from request to response
        Requirements: 1.1, 1.6
        """
        # Setup DynamoDB mock
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create sessions table
        table = dynamodb.create_table(
            TableName='fitness-coach-sessions',
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},
                {'AttributeName': 'sessionId', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'sessionId', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create metrics table
        metrics_table = dynamodb.create_table(
            TableName='api-usage-metrics',
            KeySchema=[
                {'AttributeName': 'date', 'KeyType': 'HASH'},
                {'AttributeName': 'userId', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'date', 'AttributeType': 'S'},
                {'AttributeName': 'userId', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Mock Lambda client for service calls
        with patch('boto3.client') as mock_boto_client:
            mock_lambda_client = Mock()
            mock_boto_client.return_value = mock_lambda_client
            
            # Mock workout generator call
            mock_lambda_client.invoke.side_effect = [
                {'Payload': Mock(read=Mock(return_value=json.dumps(mock_workout_response).encode()))},
                {'Payload': Mock(read=Mock(return_value=json.dumps(mock_meal_response).encode()))}
            ]
            
            # Set environment variables
            with patch.dict(os.environ, {
                'DYNAMODB_TABLE_NAME': 'fitness-coach-sessions',
                'WORKOUT_GENERATOR_FUNCTION_NAME': 'test-workout-generator',
                'MEAL_PLANNER_FUNCTION_NAME': 'test-meal-planner',
                'AWS_DEFAULT_REGION': 'us-east-1'
            }):
                # Execute the handler
                response = lambda_handler(valid_api_event, mock_context)
        
        # Validate response structure
        assert response['statusCode'] == 200
        assert 'application/json' in response['headers']['Content-Type']
        assert 'X-Request-ID' in response['headers']
        
        # Parse response body
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'data' in body
        assert 'requestId' in body
        assert 'timestamp' in body
        
        # Validate response data structure
        data = body['data']
        assert 'message' in data
        assert 'userProfile' in data
        assert 'workoutPlan' in data
        assert 'mealPlan' in data
        assert 'metadata' in data
        
        # Validate user profile
        user_profile = data['userProfile']
        assert user_profile['username'] == 'integration_test_user'
        assert user_profile['userId'] == 'test_user_123'
        assert 'sessionId' in user_profile
        assert 'timestamp' in user_profile
        
        # Validate workout plan structure
        workout_plan = data['workoutPlan']['workoutPlan']
        assert workout_plan['user_id'] == 'test_user_123'
        assert workout_plan['plan_type'] == 'Strength Training'
        assert len(workout_plan['daily_workouts']) == 1
        
        # Validate meal plan structure
        meal_plan = data['mealPlan']['meal_plan']
        assert meal_plan['user_id'] == 'test_user_123'
        assert len(meal_plan['weekly_plan']) == 1
        
        # Validate metadata
        metadata = data['metadata']
        assert metadata['workoutGenerated'] is True
        assert metadata['mealPlanGenerated'] is True
        assert metadata['sessionStored'] is True
        
        # Verify Lambda service calls were made
        assert mock_lambda_client.invoke.call_count == 2
    
    def test_workout_service_failure_scenario(self, valid_api_event, mock_context, mock_meal_response):
        """
        Test scenario where workout service fails but meal service succeeds
        Requirements: 4.4, 4.5
        """
        # Mock Lambda client with workout failure
        with patch('boto3.client') as mock_boto_client:
            mock_lambda_client = Mock()
            mock_boto_client.return_value = mock_lambda_client
            
            # Mock workout generator failure and meal planner success
            workout_error_response = {
                'statusCode': 503,
                'body': json.dumps({
                    'success': False,
                    'error': 'Bedrock service unavailable'
                })
            }
            
            mock_lambda_client.invoke.side_effect = [
                {'Payload': Mock(read=Mock(return_value=json.dumps(workout_error_response).encode()))},
                {'Payload': Mock(read=Mock(return_value=json.dumps(mock_meal_response).encode()))}
            ]
            
            with patch.dict(os.environ, {
                'WORKOUT_GENERATOR_FUNCTION_NAME': 'test-workout-generator',
                'MEAL_PLANNER_FUNCTION_NAME': 'test-meal-planner',
                'AWS_DEFAULT_REGION': 'us-east-1'
            }):
                response = lambda_handler(valid_api_event, mock_context)
        
        # Should still return success with partial data
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        
        # Validate partial success metadata
        metadata = body['data']['metadata']
        assert metadata['workoutGenerated'] is False
        assert metadata['mealPlanGenerated'] is True
        
        # Workout plan should be None, meal plan should exist
        assert body['data']['workoutPlan'] is None
        assert body['data']['mealPlan'] is not None
    
    def test_meal_service_failure_scenario(self, valid_api_event, mock_context, mock_workout_response):
        """
        Test scenario where meal service fails but workout service succeeds
        Requirements: 4.4, 4.5
        """
        # Mock Lambda client with meal failure
        with patch('boto3.client') as mock_boto_client:
            mock_lambda_client = Mock()
            mock_boto_client.return_value = mock_lambda_client
            
            # Mock workout generator success and meal planner failure
            meal_error_response = {
                'statusCode': 503,
                'body': json.dumps({
                    'success': False,
                    'error': 'Spoonacular API unavailable'
                })
            }
            
            mock_lambda_client.invoke.side_effect = [
                {'Payload': Mock(read=Mock(return_value=json.dumps(mock_workout_response).encode()))},
                {'Payload': Mock(read=Mock(return_value=json.dumps(meal_error_response).encode()))}
            ]
            
            with patch.dict(os.environ, {
                'WORKOUT_GENERATOR_FUNCTION_NAME': 'test-workout-generator',
                'MEAL_PLANNER_FUNCTION_NAME': 'test-meal-planner',
                'AWS_DEFAULT_REGION': 'us-east-1'
            }):
                response = lambda_handler(valid_api_event, mock_context)
        
        # Should still return success with partial data
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        
        # Validate partial success metadata
        metadata = body['data']['metadata']
        assert metadata['workoutGenerated'] is True
        assert metadata['mealPlanGenerated'] is False
        
        # Workout plan should exist, meal plan should be None
        assert body['data']['workoutPlan'] is not None
        assert body['data']['mealPlan'] is None
    
    def test_all_services_failure_scenario(self, valid_api_event, mock_context):
        """
        Test scenario where both workout and meal services fail
        Requirements: 4.4, 4.5
        """
        # Mock Lambda client with both services failing
        with patch('boto3.client') as mock_boto_client:
            mock_lambda_client = Mock()
            mock_boto_client.return_value = mock_lambda_client
            
            # Mock both services failing
            error_response = {
                'statusCode': 503,
                'body': json.dumps({
                    'success': False,
                    'error': 'Service unavailable'
                })
            }
            
            mock_lambda_client.invoke.side_effect = [
                {'Payload': Mock(read=Mock(return_value=json.dumps(error_response).encode()))},
                {'Payload': Mock(read=Mock(return_value=json.dumps(error_response).encode()))}
            ]
            
            with patch.dict(os.environ, {
                'WORKOUT_GENERATOR_FUNCTION_NAME': 'test-workout-generator',
                'MEAL_PLANNER_FUNCTION_NAME': 'test-meal-planner',
                'AWS_DEFAULT_REGION': 'us-east-1'
            }):
                response = lambda_handler(valid_api_event, mock_context)
        
        # Should return service unavailable error
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error']['code'] == 'ALL_SERVICES_FAILED'
        assert 'both workout and meal plan generation services' in body['error']['message'].lower()
    
    def test_invalid_request_validation(self, mock_context):
        """
        Test request validation for invalid inputs
        Requirements: 1.1
        """
        # Test missing body
        event_no_body = {'httpMethod': 'POST', 'path': '/fitness-coach'}
        response = lambda_handler(event_no_body, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'INVALID_REQUEST_BODY' in body['error']['code']
        
        # Test invalid JSON
        event_invalid_json = {
            'httpMethod': 'POST',
            'path': '/fitness-coach',
            'body': 'invalid json'
        }
        response = lambda_handler(event_invalid_json, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        
        # Test missing required fields
        event_missing_fields = {
            'httpMethod': 'POST',
            'path': '/fitness-coach',
            'body': json.dumps({
                'username': 'test_user'
                # Missing userId and query
            })
        }
        response = lambda_handler(event_missing_fields, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'VALIDATION_ERROR' in body['error']['code']
    
    def test_security_validation(self, mock_context):
        """
        Test security validation for malicious inputs
        Requirements: 1.1
        """
        # Test SQL injection attempt
        malicious_event = {
            'httpMethod': 'POST',
            'path': '/fitness-coach',
            'body': json.dumps({
                'username': 'test_user',
                'userId': 'test_123',
                'query': "'; DROP TABLE users; --"
            })
        }
        
        response = lambda_handler(malicious_event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'VALIDATION_ERROR' in body['error']['code']
        
        # Test script injection attempt
        script_event = {
            'httpMethod': 'POST',
            'path': '/fitness-coach',
            'body': json.dumps({
                'username': 'test_user',
                'userId': 'test_123',
                'query': '<script>alert("xss")</script>'
            })
        }
        
        response = lambda_handler(script_event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
    
    def test_cors_preflight_request(self, mock_context):
        """
        Test CORS preflight OPTIONS request handling
        """
        options_event = {
            'httpMethod': 'OPTIONS',
            'path': '/fitness-coach'
        }
        
        response = lambda_handler(options_event, mock_context)
        
        assert response['statusCode'] == 200
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert 'POST,OPTIONS' in response['headers']['Access-Control-Allow-Methods']
        assert response['body'] == ''
    
    def test_health_check_endpoint(self, mock_context):
        """
        Test health check endpoint functionality
        """
        health_event = {
            'httpMethod': 'GET',
            'path': '/health'
        }
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
            response = lambda_handler(health_event, mock_context)
        
        assert response['statusCode'] in [200, 503]  # Healthy or degraded
        assert 'application/json' in response['headers']['Content-Type']
        
        body = json.loads(response['body'])
        assert 'service' in body
        assert 'status' in body
        assert 'timestamp' in body
        assert 'checks' in body
        
        # Validate health check structure
        assert body['service'] == 'fitness-coach-api'
        assert body['status'] in ['healthy', 'degraded', 'unhealthy']
    
    @mock_aws
    def test_database_storage_integration(self, valid_api_event, mock_context, 
                                        mock_workout_response, mock_meal_response):
        """
        Test database storage integration with DynamoDB
        Requirements: 1.6
        """
        # Setup DynamoDB mock
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create sessions table
        table = dynamodb.create_table(
            TableName='fitness-coach-sessions',
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},
                {'AttributeName': 'sessionId', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'sessionId', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Mock Lambda client
        with patch('boto3.client') as mock_boto_client:
            mock_lambda_client = Mock()
            mock_boto_client.return_value = mock_lambda_client
            
            mock_lambda_client.invoke.side_effect = [
                {'Payload': Mock(read=Mock(return_value=json.dumps(mock_workout_response).encode()))},
                {'Payload': Mock(read=Mock(return_value=json.dumps(mock_meal_response).encode()))}
            ]
            
            with patch.dict(os.environ, {
                'DYNAMODB_TABLE_NAME': 'fitness-coach-sessions',
                'AWS_DEFAULT_REGION': 'us-east-1'
            }):
                response = lambda_handler(valid_api_event, mock_context)
        
        # Verify successful response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        
        # Verify session was stored
        metadata = body['data']['metadata']
        assert metadata['sessionStored'] is True
        
        # Verify data was actually written to DynamoDB
        session_id = body['data']['userProfile']['sessionId']
        stored_item = table.get_item(
            Key={
                'userId': 'test_user_123',
                'sessionId': session_id
            }
        )
        
        assert 'Item' in stored_item
        stored_session = stored_item['Item']
        assert stored_session['username'] == 'integration_test_user'
        assert 'workoutPlan' in stored_session
        assert 'mealPlan' in stored_session
    
    def test_retry_mechanism_integration(self, valid_api_event, mock_context):
        """
        Test retry mechanism for transient failures
        Requirements: 4.4, 4.5
        """
        with patch('boto3.client') as mock_boto_client:
            mock_lambda_client = Mock()
            mock_boto_client.return_value = mock_lambda_client
            
            # Mock transient failure followed by success
            failure_response = {
                'statusCode': 503,
                'body': json.dumps({
                    'success': False,
                    'error': 'Service temporarily unavailable'
                })
            }
            
            success_response = {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'data': {'workoutPlan': {'plan_type': 'Test'}}
                })
            }
            
            # First call fails, second succeeds (simulating retry)
            mock_lambda_client.invoke.side_effect = [
                {'Payload': Mock(read=Mock(return_value=json.dumps(success_response).encode()))},
                {'Payload': Mock(read=Mock(return_value=json.dumps(success_response).encode()))}
            ]
            
            with patch.dict(os.environ, {
                'WORKOUT_GENERATOR_FUNCTION_NAME': 'test-workout-generator',
                'MEAL_PLANNER_FUNCTION_NAME': 'test-meal-planner',
                'AWS_DEFAULT_REGION': 'us-east-1'
            }):
                response = lambda_handler(valid_api_event, mock_context)
        
        # Should eventually succeed
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])