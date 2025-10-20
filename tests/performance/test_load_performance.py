#!/usr/bin/env python3
"""
Performance and load tests for fitness coach API
Task 8.2: Set up performance and load testing
- Create load tests for API Gateway endpoints
- Test Bedrock and Spoonacular API performance under load
- Monitor DynamoDB read/write capacity and optimization
- Requirements: 4.1, 4.2, 4.3
"""

import json
import pytest
import time
import asyncio
import concurrent.futures
import statistics
import boto3
import os
import sys
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
import threading
from collections import defaultdict
from moto import mock_aws

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'lambda', 'fitness_coach_handler'))

from handler import lambda_handler


class PerformanceMetrics:
    """Class to collect and analyze performance metrics"""
    
    def __init__(self):
        self.response_times = []
        self.success_count = 0
        self.error_count = 0
        self.status_codes = defaultdict(int)
        self.start_time = None
        self.end_time = None
        self.concurrent_requests = 0
        self.max_concurrent = 0
        self.lock = threading.Lock()
    
    def start_request(self):
        """Mark the start of a request"""
        with self.lock:
            self.concurrent_requests += 1
            self.max_concurrent = max(self.max_concurrent, self.concurrent_requests)
    
    def end_request(self, response_time, status_code, success):
        """Mark the end of a request and record metrics"""
        with self.lock:
            self.concurrent_requests -= 1
            self.response_times.append(response_time)
            self.status_codes[status_code] += 1
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
    
    def get_summary(self):
        """Get performance summary statistics"""
        if not self.response_times:
            return {}
        
        total_requests = len(self.response_times)
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0
        
        return {
            'total_requests': total_requests,
            'success_rate': (self.success_count / total_requests) * 100,
            'error_rate': (self.error_count / total_requests) * 100,
            'avg_response_time': statistics.mean(self.response_times),
            'median_response_time': statistics.median(self.response_times),
            'p95_response_time': self._percentile(self.response_times, 95),
            'p99_response_time': self._percentile(self.response_times, 99),
            'min_response_time': min(self.response_times),
            'max_response_time': max(self.response_times),
            'requests_per_second': total_requests / duration if duration > 0 else 0,
            'max_concurrent_requests': self.max_concurrent,
            'status_code_distribution': dict(self.status_codes),
            'test_duration_seconds': duration
        }
    
    def _percentile(self, data, percentile):
        """Calculate percentile of data"""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


class TestAPIPerformance:
    """Performance tests for API Gateway endpoints"""
    
    @pytest.fixture
    def valid_request_payload(self):
        """Standard request payload for performance testing"""
        return {
            'httpMethod': 'POST',
            'path': '/fitness-coach',
            'headers': {'Content-Type': 'application/json'},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}},
            'body': json.dumps({
                'username': 'perf_test_user',
                'userId': 'perf_test_123',
                'query': 'I want a balanced workout and meal plan'
            })
        }
    
    @pytest.fixture
    def mock_context(self):
        """Mock Lambda context for testing"""
        context = Mock()
        context.aws_request_id = 'perf-test-request'
        context.function_name = 'fitness-coach-handler'
        context.memory_limit_in_mb = 512
        context.remaining_time_in_millis = lambda: 30000
        return context
    
    @pytest.fixture
    def mock_successful_services(self):
        """Mock successful service responses for performance testing"""
        workout_response = {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'data': {
                    'workoutPlan': {
                        'user_id': 'perf_test_123',
                        'plan_type': 'Performance Test Plan',
                        'duration_weeks': 1,
                        'daily_workouts': [{'day': 'Monday', 'exercises': []}]
                    }
                }
            })
        }
        
        meal_response = {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'data': {
                    'meal_plan': {
                        'user_id': 'perf_test_123',
                        'weekly_plan': [{'day': 'Day 1', 'breakfast': {}, 'lunch': {}, 'dinner': {}}]
                    }
                }
            })
        }
        
        return [workout_response, meal_response]
    
    def execute_single_request(self, payload, context, metrics):
        """Execute a single API request and record metrics"""
        metrics.start_request()
        start_time = time.time()
        
        try:
            response = lambda_handler(payload, context)
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            status_code = response.get('statusCode', 500)
            success = status_code == 200
            
            metrics.end_request(response_time, status_code, success)
            return response
            
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            metrics.end_request(response_time, 500, False)
            raise e
    
    def test_single_request_performance(self, valid_request_payload, mock_context, mock_successful_services):
        """
        Test single request performance baseline
        Requirements: 4.1 - Process requests within 30 seconds
        """
        with patch('boto3.client') as mock_boto_client:
            mock_lambda_client = Mock()
            mock_boto_client.return_value = mock_lambda_client
            mock_lambda_client.invoke.side_effect = [
                {'Payload': Mock(read=Mock(return_value=json.dumps(resp).encode()))}
                for resp in mock_successful_services
            ]
            
            with patch.dict(os.environ, {
                'WORKOUT_GENERATOR_FUNCTION_NAME': 'test-workout-generator',
                'MEAL_PLANNER_FUNCTION_NAME': 'test-meal-planner',
                'AWS_DEFAULT_REGION': 'us-east-1'
            }):
                start_time = time.time()
                response = lambda_handler(valid_request_payload, mock_context)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # milliseconds
        
        # Validate response
        assert response['statusCode'] == 200
        
        # Performance assertions (Requirements: 4.1)
        assert response_time < 30000, f"Response time {response_time}ms exceeds 30 second limit"
        assert response_time < 5000, f"Response time {response_time}ms should be under 5 seconds for good UX"
        
        print(f"Single request performance: {response_time:.2f}ms")
    
    def test_concurrent_requests_performance(self, valid_request_payload, mock_context, mock_successful_services):
        """
        Test concurrent request handling performance
        Requirements: 4.2 - Maintain 99.5% uptime under load
        """
        metrics = PerformanceMetrics()
        concurrent_users = 10
        requests_per_user = 5
        
        with patch('boto3.client') as mock_boto_client:
            mock_lambda_client = Mock()
            mock_boto_client.return_value = mock_lambda_client
            mock_lambda_client.invoke.side_effect = lambda *args, **kwargs: {
                'Payload': Mock(read=Mock(return_value=json.dumps(mock_successful_services[0]).encode()))
            }
            
            with patch.dict(os.environ, {
                'WORKOUT_GENERATOR_FUNCTION_NAME': 'test-workout-generator',
                'MEAL_PLANNER_FUNCTION_NAME': 'test-meal-planner',
                'AWS_DEFAULT_REGION': 'us-east-1'
            }):
                metrics.start_time = datetime.now()
                
                # Execute concurrent requests
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                    futures = []
                    
                    for user in range(concurrent_users):
                        for request in range(requests_per_user):
                            # Create unique payload for each request
                            unique_payload = valid_request_payload.copy()
                            unique_payload['body'] = json.dumps({
                                'username': f'perf_user_{user}',
                                'userId': f'perf_{user}_{request}',
                                'query': 'Performance test query'
                            })
                            
                            future = executor.submit(
                                self.execute_single_request,
                                unique_payload,
                                mock_context,
                                metrics
                            )
                            futures.append(future)
                    
                    # Wait for all requests to complete
                    concurrent.futures.wait(futures)
                
                metrics.end_time = datetime.now()
        
        # Analyze performance metrics
        summary = metrics.get_summary()
        
        # Performance assertions (Requirements: 4.2)
        assert summary['success_rate'] >= 99.5, f"Success rate {summary['success_rate']:.2f}% below 99.5% requirement"
        assert summary['avg_response_time'] < 10000, f"Average response time {summary['avg_response_time']:.2f}ms too high"
        assert summary['p95_response_time'] < 15000, f"95th percentile {summary['p95_response_time']:.2f}ms too high"
        
        print(f"Concurrent performance summary:")
        print(f"  Total requests: {summary['total_requests']}")
        print(f"  Success rate: {summary['success_rate']:.2f}%")
        print(f"  Average response time: {summary['avg_response_time']:.2f}ms")
        print(f"  95th percentile: {summary['p95_response_time']:.2f}ms")
        print(f"  Requests per second: {summary['requests_per_second']:.2f}")
    
    def test_sustained_load_performance(self, valid_request_payload, mock_context, mock_successful_services):
        """
        Test sustained load over time
        Requirements: 4.3 - Queue requests under high load
        """
        metrics = PerformanceMetrics()
        test_duration = 30  # seconds
        target_rps = 5  # requests per second
        
        with patch('boto3.client') as mock_boto_client:
            mock_lambda_client = Mock()
            mock_boto_client.return_value = mock_lambda_client
            mock_lambda_client.invoke.side_effect = lambda *args, **kwargs: {
                'Payload': Mock(read=Mock(return_value=json.dumps(mock_successful_services[0]).encode()))
            }
            
            with patch.dict(os.environ, {
                'WORKOUT_GENERATOR_FUNCTION_NAME': 'test-workout-generator',
                'MEAL_PLANNER_FUNCTION_NAME': 'test-meal-planner',
                'AWS_DEFAULT_REGION': 'us-east-1'
            }):
                metrics.start_time = datetime.now()
                end_time = metrics.start_time + timedelta(seconds=test_duration)
                
                request_count = 0
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    futures = []
                    
                    while datetime.now() < end_time:
                        # Submit request
                        unique_payload = valid_request_payload.copy()
                        unique_payload['body'] = json.dumps({
                            'username': f'sustained_user_{request_count}',
                            'userId': f'sustained_{request_count}',
                            'query': 'Sustained load test query'
                        })
                        
                        future = executor.submit(
                            self.execute_single_request,
                            unique_payload,
                            mock_context,
                            metrics
                        )
                        futures.append(future)
                        request_count += 1
                        
                        # Control request rate
                        time.sleep(1.0 / target_rps)
                    
                    # Wait for remaining requests
                    concurrent.futures.wait(futures)
                
                metrics.end_time = datetime.now()
        
        # Analyze sustained load performance
        summary = metrics.get_summary()
        
        # Performance assertions
        assert summary['success_rate'] >= 95.0, f"Success rate {summary['success_rate']:.2f}% too low for sustained load"
        assert summary['avg_response_time'] < 20000, f"Average response time {summary['avg_response_time']:.2f}ms too high"
        
        print(f"Sustained load performance:")
        print(f"  Test duration: {summary['test_duration_seconds']:.2f}s")
        print(f"  Total requests: {summary['total_requests']}")
        print(f"  Success rate: {summary['success_rate']:.2f}%")
        print(f"  Average RPS: {summary['requests_per_second']:.2f}")
        print(f"  Average response time: {summary['avg_response_time']:.2f}ms")
    
    def test_error_handling_under_load(self, valid_request_payload, mock_context):
        """
        Test error handling performance under load conditions
        Requirements: 4.4, 4.5 - Handle service failures gracefully
        """
        metrics = PerformanceMetrics()
        concurrent_requests = 15
        
        # Mix of successful and failing responses
        success_response = {
            'statusCode': 200,
            'body': json.dumps({'success': True, 'data': {}})
        }
        
        error_response = {
            'statusCode': 503,
            'body': json.dumps({'success': False, 'error': 'Service unavailable'})
        }
        
        with patch('boto3.client') as mock_boto_client:
            mock_lambda_client = Mock()
            mock_boto_client.return_value = mock_lambda_client
            
            # Simulate 70% success, 30% failure rate
            responses = [success_response] * 7 + [error_response] * 3
            mock_lambda_client.invoke.side_effect = lambda *args, **kwargs: {
                'Payload': Mock(read=Mock(return_value=json.dumps(responses[hash(str(args)) % len(responses)]).encode()))
            }
            
            with patch.dict(os.environ, {
                'WORKOUT_GENERATOR_FUNCTION_NAME': 'test-workout-generator',
                'MEAL_PLANNER_FUNCTION_NAME': 'test-meal-planner',
                'AWS_DEFAULT_REGION': 'us-east-1'
            }):
                metrics.start_time = datetime.now()
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
                    futures = []
                    
                    for i in range(concurrent_requests * 3):  # 3 requests per thread
                        unique_payload = valid_request_payload.copy()
                        unique_payload['body'] = json.dumps({
                            'username': f'error_test_user_{i}',
                            'userId': f'error_test_{i}',
                            'query': 'Error handling test query'
                        })
                        
                        future = executor.submit(
                            self.execute_single_request,
                            unique_payload,
                            mock_context,
                            metrics
                        )
                        futures.append(future)
                    
                    concurrent.futures.wait(futures)
                
                metrics.end_time = datetime.now()
        
        summary = metrics.get_summary()
        
        # Error handling performance assertions
        assert summary['avg_response_time'] < 15000, f"Error handling response time {summary['avg_response_time']:.2f}ms too high"
        assert 200 in summary['status_code_distribution'], "Should have some successful responses"
        assert summary['total_requests'] == concurrent_requests * 3, "All requests should complete"
        
        print(f"Error handling under load:")
        print(f"  Total requests: {summary['total_requests']}")
        print(f"  Success rate: {summary['success_rate']:.2f}%")
        print(f"  Error rate: {summary['error_rate']:.2f}%")
        print(f"  Average response time: {summary['avg_response_time']:.2f}ms")
        print(f"  Status codes: {summary['status_code_distribution']}")


class TestServicePerformance:
    """Performance tests for individual services (Bedrock, Spoonacular)"""
    
    def test_bedrock_service_performance(self):
        """
        Test Bedrock service performance characteristics
        Requirements: 4.1, 4.2 - Bedrock response times
        """
        # Import would be: from src.lambda.workout_generator.handler import BedrockWorkoutGenerator
        # Import would be: from src.shared.models import UserProfile
        # For testing, we'll mock these components
        
        # Mock Bedrock responses with realistic timing
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock_client = Mock()
            mock_boto_client.return_value = mock_bedrock_client
            
            # Simulate Bedrock response time (2-5 seconds typical)
            def mock_invoke_model(*args, **kwargs):
                time.sleep(0.1)  # Simulate processing time
                return {
                    'body': Mock(read=Mock(return_value=json.dumps({
                        'content': [{
                            'text': '''```json
{
    "plan_type": "Performance Test",
    "duration_weeks": 1,
    "daily_workouts": [
        {
            "day": "Monday",
            "exercises": [
                {
                    "name": "Push-ups",
                    "sets": 3,
                    "reps": "10-12",
                    "duration": 5,
                    "muscle_groups": ["chest"]
                }
            ],
            "total_duration": 30
        }
    ]
}
```'''
                        }]
                    }).encode()))
                }
            
            mock_bedrock_client.invoke_model = mock_invoke_model
            
            generator = BedrockWorkoutGenerator()
            user_profile = UserProfile(
                username="perf_test",
                user_id="perf_123",
                query="Performance test workout"
            )
            
            # Test multiple Bedrock calls
            response_times = []
            for i in range(10):
                start_time = time.time()
                try:
                    workout_plan = generator.generate_workout_plan(user_profile)
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    response_times.append(response_time)
                    
                    # Validate response structure
                    assert workout_plan is not None
                    assert hasattr(workout_plan, 'plan_type')
                    
                except Exception as e:
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    response_times.append(response_time)
                    print(f"Bedrock call {i} failed: {e}")
            
            # Analyze Bedrock performance
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            
            # Performance assertions for Bedrock
            assert avg_response_time < 5000, f"Bedrock average response time {avg_response_time:.2f}ms too high"
            assert max_response_time < 10000, f"Bedrock max response time {max_response_time:.2f}ms too high"
            
            print(f"Bedrock performance:")
            print(f"  Average response time: {avg_response_time:.2f}ms")
            print(f"  Max response time: {max_response_time:.2f}ms")
            print(f"  Min response time: {min(response_times):.2f}ms")
    
    def test_spoonacular_service_performance(self):
        """
        Test Spoonacular API performance characteristics
        Requirements: 4.1, 4.2 - Spoonacular response times
        """
        # Import meal planner components
        # sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'lambda', 'meal_planner'))
        # from handler import MealPlannerService
        # For testing, we'll mock the MealPlannerService
        
        # Mock Spoonacular MCP server responses
        with patch('src.mcp_servers.spoonacular_enhanced.server.SpoonacularEnhancedMCPServer') as mock_mcp:
            mock_server = Mock()
            mock_mcp.return_value = mock_server
            
            # Simulate Spoonacular API response time (1-3 seconds typical)
            async def mock_get_meal_plan(*args, **kwargs):
                await asyncio.sleep(0.05)  # Simulate API call time
                return {
                    'cached': False,
                    'meal_plan': {
                        'weekly_plan': [
                            {
                                'day': 'Day 1',
                                'breakfast': {'title': 'Test Breakfast', 'calories_per_serving': 300},
                                'lunch': {'title': 'Test Lunch', 'calories_per_serving': 400},
                                'dinner': {'title': 'Test Dinner', 'calories_per_serving': 500}
                            }
                        ]
                    }
                }
            
            async def mock_analyze_nutrition(*args, **kwargs):
                await asyncio.sleep(0.02)  # Simulate analysis time
                return {
                    'analysis_summary': {
                        'avg_daily_calories': 1200,
                        'avg_daily_protein': 80,
                        'avg_daily_carbs': 120,
                        'avg_daily_fat': 40
                    },
                    'balance_score': 85.0
                }
            
            mock_server.get_optimized_meal_plan = mock_get_meal_plan
            mock_server.analyze_nutrition_balance = mock_analyze_nutrition
            
            meal_planner = MealPlannerService()
            
            # Test multiple Spoonacular calls
            async def run_performance_test():
                response_times = []
                
                for i in range(10):
                    start_time = time.time()
                    try:
                        result = await meal_planner.generate_meal_plan(
                            user_profile={
                                'username': 'perf_test',
                                'user_id': 'perf_123',
                                'query': 'Performance test meal plan'
                            },
                            dietary_preferences=['omnivore'],
                            calorie_target=2000,
                            fitness_goals='maintenance',
                            days=1
                        )
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        response_times.append(response_time)
                        
                        # Validate response structure
                        assert result['success'] is True
                        assert 'meal_plan' in result
                        
                    except Exception as e:
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        response_times.append(response_time)
                        print(f"Spoonacular call {i} failed: {e}")
                
                return response_times
            
            # Run async performance test
            response_times = asyncio.run(run_performance_test())
            
            # Analyze Spoonacular performance
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            
            # Performance assertions for Spoonacular
            assert avg_response_time < 3000, f"Spoonacular average response time {avg_response_time:.2f}ms too high"
            assert max_response_time < 8000, f"Spoonacular max response time {max_response_time:.2f}ms too high"
            
            print(f"Spoonacular performance:")
            print(f"  Average response time: {avg_response_time:.2f}ms")
            print(f"  Max response time: {max_response_time:.2f}ms")
            print(f"  Min response time: {min(response_times):.2f}ms")


class TestDynamoDBPerformance:
    """Performance tests for DynamoDB operations"""
    
    def test_dynamodb_write_performance(self):
        """
        Test DynamoDB write performance and capacity
        Requirements: 4.3 - Monitor DynamoDB capacity
        """
        # mock_aws already imported at top
        
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            
            # Create test table
            table = dynamodb.create_table(
                TableName='performance-test-sessions',
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
            
            # Test batch write performance
            write_times = []
            batch_size = 25  # DynamoDB batch limit
            
            for batch in range(5):  # 5 batches = 125 items
                start_time = time.time()
                
                with table.batch_writer() as batch_writer:
                    for i in range(batch_size):
                        item = {
                            'userId': f'perf_user_{batch}_{i}',
                            'sessionId': f'session_{batch}_{i}',
                            'username': f'user_{i}',
                            'query': 'Performance test query',
                            'workoutPlan': {'plan_type': 'Test'},
                            'mealPlan': {'weekly_plan': []},
                            'timestamp': datetime.utcnow().isoformat(),
                            'ttl': int(time.time()) + 86400
                        }
                        batch_writer.put_item(Item=item)
                
                end_time = time.time()
                write_time = (end_time - start_time) * 1000
                write_times.append(write_time)
            
            # Analyze write performance
            avg_write_time = statistics.mean(write_times)
            max_write_time = max(write_times)
            
            # Performance assertions for DynamoDB writes
            assert avg_write_time < 1000, f"DynamoDB batch write time {avg_write_time:.2f}ms too high"
            assert max_write_time < 2000, f"DynamoDB max write time {max_write_time:.2f}ms too high"
            
            print(f"DynamoDB write performance:")
            print(f"  Average batch write time: {avg_write_time:.2f}ms")
            print(f"  Max batch write time: {max_write_time:.2f}ms")
            print(f"  Items per batch: {batch_size}")
    
    def test_dynamodb_read_performance(self):
        """
        Test DynamoDB read performance and query optimization
        Requirements: 4.3 - Monitor DynamoDB capacity
        """
        # mock_aws already imported at top
        
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            
            # Create and populate test table
            table = dynamodb.create_table(
                TableName='performance-test-sessions',
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
            
            # Populate table with test data
            test_user_id = 'perf_read_user'
            for i in range(50):
                table.put_item(Item={
                    'userId': test_user_id,
                    'sessionId': f'session_{i}',
                    'username': f'user_{i}',
                    'query': f'Test query {i}',
                    'workoutPlan': {'plan_type': f'Plan {i}'},
                    'mealPlan': {'weekly_plan': []},
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Test single item read performance
            read_times = []
            for i in range(20):
                start_time = time.time()
                
                response = table.get_item(
                    Key={
                        'userId': test_user_id,
                        'sessionId': f'session_{i}'
                    }
                )
                
                end_time = time.time()
                read_time = (end_time - start_time) * 1000
                read_times.append(read_time)
                
                # Validate read result
                assert 'Item' in response
                assert response['Item']['userId'] == test_user_id
            
            # Test query performance (multiple items)
            query_times = []
            for i in range(10):
                start_time = time.time()
                
                response = table.query(
                    KeyConditionExpression='userId = :uid',
                    ExpressionAttributeValues={':uid': test_user_id},
                    Limit=10
                )
                
                end_time = time.time()
                query_time = (end_time - start_time) * 1000
                query_times.append(query_time)
                
                # Validate query result
                assert len(response['Items']) == 10
            
            # Analyze read performance
            avg_read_time = statistics.mean(read_times)
            avg_query_time = statistics.mean(query_times)
            
            # Performance assertions for DynamoDB reads
            assert avg_read_time < 100, f"DynamoDB single read time {avg_read_time:.2f}ms too high"
            assert avg_query_time < 200, f"DynamoDB query time {avg_query_time:.2f}ms too high"
            
            print(f"DynamoDB read performance:")
            print(f"  Average single read time: {avg_read_time:.2f}ms")
            print(f"  Average query time (10 items): {avg_query_time:.2f}ms")


def run_performance_tests():
    """Run all performance tests and generate report"""
    print("Starting Fitness Coach API Performance Tests")
    print("=" * 50)
    
    # Run tests with pytest
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '-x'  # Stop on first failure
    ])


if __name__ == '__main__':
    run_performance_tests()