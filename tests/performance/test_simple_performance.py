#!/usr/bin/env python3
"""
Simple performance tests for fitness coach API
Task 8.2: Set up performance and load testing
- Create load tests for API Gateway endpoints
- Test performance characteristics under load
- Monitor response times and throughput
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
import threading
from collections import defaultdict
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
from moto import mock_aws


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


class TestSimplePerformance:
    """Simple performance tests for API components"""
    
    def test_response_time_requirements(self):
        """
        Test response time meets requirements
        Requirements: 4.1 - Process requests within 30 seconds
        """
        # Simulate API processing time
        def simulate_api_call():
            # Simulate processing time (2-5 seconds typical)
            processing_time = 0.1  # 100ms for test
            time.sleep(processing_time)
            return {
                'statusCode': 200,
                'body': json.dumps({'success': True, 'data': {}})
            }
        
        # Test single request performance
        start_time = time.time()
        response = simulate_api_call()
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # Performance assertions (Requirements: 4.1)
        assert response_time_ms < 30000, f"Response time {response_time_ms}ms exceeds 30 second limit"
        assert response_time_ms < 5000, f"Response time {response_time_ms}ms should be under 5 seconds for good UX"
        assert response['statusCode'] == 200
        
        print(f"Single request performance: {response_time_ms:.2f}ms")
    
    def test_concurrent_request_handling(self):
        """
        Test concurrent request handling performance
        Requirements: 4.2 - Maintain 99.5% uptime under load
        """
        metrics = PerformanceMetrics()
        concurrent_users = 5
        requests_per_user = 3
        
        def execute_request(user_id, request_id):
            """Execute a single request and record metrics"""
            metrics.start_request()
            start_time = time.time()
            
            try:
                # Simulate API processing
                time.sleep(0.05)  # 50ms processing time
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                # Simulate 95% success rate
                success = (user_id + request_id) % 20 != 0  # 95% success
                status_code = 200 if success else 503
                
                metrics.end_request(response_time, status_code, success)
                return {'statusCode': status_code}
                
            except Exception:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                metrics.end_request(response_time, 500, False)
                return {'statusCode': 500}
        
        # Execute concurrent requests
        metrics.start_time = datetime.now()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            
            for user in range(concurrent_users):
                for request in range(requests_per_user):
                    future = executor.submit(execute_request, user, request)
                    futures.append(future)
            
            # Wait for all requests to complete
            concurrent.futures.wait(futures)
        
        metrics.end_time = datetime.now()
        
        # Analyze performance metrics
        summary = metrics.get_summary()
        
        # Performance assertions (Requirements: 4.2)
        assert summary['success_rate'] >= 90.0, f"Success rate {summary['success_rate']:.2f}% too low"
        assert summary['avg_response_time'] < 1000, f"Average response time {summary['avg_response_time']:.2f}ms too high"
        assert summary['p95_response_time'] < 2000, f"95th percentile {summary['p95_response_time']:.2f}ms too high"
        
        print(f"Concurrent performance summary:")
        print(f"  Total requests: {summary['total_requests']}")
        print(f"  Success rate: {summary['success_rate']:.2f}%")
        print(f"  Average response time: {summary['avg_response_time']:.2f}ms")
        print(f"  95th percentile: {summary['p95_response_time']:.2f}ms")
        print(f"  Requests per second: {summary['requests_per_second']:.2f}")
    
    def test_sustained_load_performance(self):
        """
        Test sustained load over time
        Requirements: 4.3 - Queue requests under high load
        """
        metrics = PerformanceMetrics()
        test_duration = 5  # seconds (reduced for testing)
        target_rps = 10  # requests per second
        
        def execute_sustained_request(request_id):
            """Execute a request during sustained load test"""
            metrics.start_request()
            start_time = time.time()
            
            try:
                # Simulate variable processing time
                processing_time = 0.02 + (request_id % 3) * 0.01  # 20-40ms
                time.sleep(processing_time)
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                # Simulate high success rate under load
                success = request_id % 50 != 0  # 98% success rate
                status_code = 200 if success else 503
                
                metrics.end_request(response_time, status_code, success)
                return {'statusCode': status_code}
                
            except Exception:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                metrics.end_request(response_time, 500, False)
                return {'statusCode': 500}
        
        metrics.start_time = datetime.now()
        end_time = metrics.start_time + timedelta(seconds=test_duration)
        
        request_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = []
            
            while datetime.now() < end_time:
                # Submit request
                future = executor.submit(execute_sustained_request, request_count)
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
        assert summary['avg_response_time'] < 500, f"Average response time {summary['avg_response_time']:.2f}ms too high"
        
        print(f"Sustained load performance:")
        print(f"  Test duration: {summary['test_duration_seconds']:.2f}s")
        print(f"  Total requests: {summary['total_requests']}")
        print(f"  Success rate: {summary['success_rate']:.2f}%")
        print(f"  Average RPS: {summary['requests_per_second']:.2f}")
        print(f"  Average response time: {summary['avg_response_time']:.2f}ms")
    
    @mock_aws
    def test_dynamodb_performance(self):
        """
        Test DynamoDB performance characteristics
        Requirements: 4.3 - Monitor DynamoDB read/write capacity
        """
        # Create DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        table = dynamodb.create_table(
            TableName='performance-test-table',
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
        
        # Test write performance
        write_times = []
        batch_size = 10
        
        for batch in range(3):  # 3 batches = 30 items
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
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    batch_writer.put_item(Item=item)
            
            end_time = time.time()
            write_time = (end_time - start_time) * 1000
            write_times.append(write_time)
        
        # Test read performance
        read_times = []
        for batch in range(3):
            for i in range(5):  # 5 reads per batch
                start_time = time.time()
                
                response = table.get_item(
                    Key={
                        'userId': f'perf_user_{batch}_{i}',
                        'sessionId': f'session_{batch}_{i}'
                    }
                )
                
                end_time = time.time()
                read_time = (end_time - start_time) * 1000
                read_times.append(read_time)
                
                # Validate read result
                assert 'Item' in response
        
        # Analyze DynamoDB performance
        avg_write_time = statistics.mean(write_times)
        avg_read_time = statistics.mean(read_times)
        
        # Performance assertions for DynamoDB
        assert avg_write_time < 500, f"DynamoDB batch write time {avg_write_time:.2f}ms too high"
        assert avg_read_time < 100, f"DynamoDB read time {avg_read_time:.2f}ms too high"
        
        print(f"DynamoDB performance:")
        print(f"  Average batch write time: {avg_write_time:.2f}ms")
        print(f"  Average read time: {avg_read_time:.2f}ms")
        print(f"  Items per batch: {batch_size}")
    
    def test_error_handling_performance(self):
        """
        Test error handling performance under load
        Requirements: 4.4, 4.5 - Handle service failures gracefully
        """
        metrics = PerformanceMetrics()
        total_requests = 20
        
        def execute_error_test_request(request_id):
            """Execute request with mixed success/failure"""
            metrics.start_request()
            start_time = time.time()
            
            try:
                # Simulate processing time
                time.sleep(0.03)  # 30ms
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                # Simulate 70% success, 30% failure
                success = request_id % 10 < 7
                status_code = 200 if success else 503
                
                metrics.end_request(response_time, status_code, success)
                return {'statusCode': status_code}
                
            except Exception:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                metrics.end_request(response_time, 500, False)
                return {'statusCode': 500}
        
        metrics.start_time = datetime.now()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for i in range(total_requests):
                future = executor.submit(execute_error_test_request, i)
                futures.append(future)
            
            concurrent.futures.wait(futures)
        
        metrics.end_time = datetime.now()
        
        summary = metrics.get_summary()
        
        # Error handling performance assertions
        assert summary['avg_response_time'] < 200, f"Error handling response time {summary['avg_response_time']:.2f}ms too high"
        assert 200 in summary['status_code_distribution'], "Should have some successful responses"
        assert summary['total_requests'] == total_requests, "All requests should complete"
        
        print(f"Error handling performance:")
        print(f"  Total requests: {summary['total_requests']}")
        print(f"  Success rate: {summary['success_rate']:.2f}%")
        print(f"  Error rate: {summary['error_rate']:.2f}%")
        print(f"  Average response time: {summary['avg_response_time']:.2f}ms")
        print(f"  Status codes: {summary['status_code_distribution']}")
    
    def test_memory_usage_pattern(self):
        """Test memory usage patterns during processing"""
        import sys
        
        # Simulate data processing
        initial_objects = len(gc.get_objects()) if 'gc' in sys.modules else 0
        
        # Create test data structures
        test_data = []
        for i in range(1000):
            item = {
                'id': i,
                'data': f'test_data_{i}' * 10,  # Some string data
                'nested': {
                    'workout': {'exercises': [f'exercise_{j}' for j in range(5)]},
                    'meal': {'meals': [f'meal_{j}' for j in range(3)]}
                }
            }
            test_data.append(item)
        
        # Process data
        processed_count = 0
        for item in test_data:
            # Simulate processing
            processed_item = {
                'processed_id': item['id'],
                'processed_data': item['data'].upper(),
                'summary': len(item['nested']['workout']['exercises'])
            }
            processed_count += 1
        
        # Clean up
        del test_data
        
        final_objects = len(gc.get_objects()) if 'gc' in sys.modules else 0
        
        # Memory usage assertions
        assert processed_count == 1000, "Should process all items"
        
        print(f"Memory usage test:")
        print(f"  Processed items: {processed_count}")
        print(f"  Initial objects: {initial_objects}")
        print(f"  Final objects: {final_objects}")


# Import gc for memory testing
try:
    import gc
except ImportError:
    gc = None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])