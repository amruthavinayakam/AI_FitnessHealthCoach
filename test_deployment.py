#!/usr/bin/env python3
"""
Comprehensive testing script for Fitness Health Coach deployment
"""
import json
import sys
import time
import boto3
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    print("❌ requests library required. Install with: pip install requests")
    sys.exit(1)

class FitnessCoachTester:
    """Test suite for Fitness Health Coach API"""
    
    def __init__(self):
        self.config = self._load_config()
        self.api_url = self.config.get('api_gateway_url')
        self.api_key = self.config.get('api_key_value')
        self.test_results = []
    
    def _load_config(self) -> Dict[str, Any]:
        """Load deployment configuration"""
        try:
            with open('deployment_config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("❌ deployment_config.json not found. Run deploy.py first.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            sys.exit(1)
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     headers: Optional[Dict] = None) -> requests.Response:
        """Make HTTP request to API"""
        url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        default_headers = {
            'Content-Type': 'application/json'
        }
        
        if self.api_key:
            default_headers['X-API-Key'] = self.api_key
        
        if headers:
            default_headers.update(headers)
        
        if method.upper() == 'GET':
            return requests.get(url, headers=default_headers, timeout=30)
        elif method.upper() == 'POST':
            return requests.post(url, json=data, headers=default_headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
    
    def _log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        try:
            response = self._make_request('GET', '/health')
            
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get('status', 'unknown')
                
                if status == 'healthy':
                    self._log_test_result(
                        "Health Check", True, 
                        f"Service healthy, response time: {response.elapsed.total_seconds():.2f}s"
                    )
                else:
                    self._log_test_result(
                        "Health Check", False, 
                        f"Service status: {status}"
                    )
            else:
                self._log_test_result(
                    "Health Check", False, 
                    f"HTTP {response.status_code}: {response.text[:100]}"
                )
                
        except Exception as e:
            self._log_test_result("Health Check", False, f"Exception: {str(e)}")
    
    def test_cors_preflight(self):
        """Test CORS preflight request"""
        try:
            headers = {
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type,X-API-Key',
                'Origin': 'https://example.com'
            }
            
            response = requests.options(
                f"{self.api_url}/fitness-coach", 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                cors_headers = response.headers
                if 'Access-Control-Allow-Origin' in cors_headers:
                    self._log_test_result(
                        "CORS Preflight", True, 
                        f"CORS headers present"
                    )
                else:
                    self._log_test_result(
                        "CORS Preflight", False, 
                        "Missing CORS headers"
                    )
            else:
                self._log_test_result(
                    "CORS Preflight", False, 
                    f"HTTP {response.status_code}"
                )
                
        except Exception as e:
            self._log_test_result("CORS Preflight", False, f"Exception: {str(e)}")
    
    def test_invalid_method(self):
        """Test invalid HTTP method handling"""
        try:
            response = requests.get(f"{self.api_url}/fitness-coach", timeout=10)
            
            if response.status_code == 405:
                self._log_test_result(
                    "Invalid Method Handling", True, 
                    "Correctly rejected GET request"
                )
            else:
                self._log_test_result(
                    "Invalid Method Handling", False, 
                    f"Expected 405, got {response.status_code}"
                )
                
        except Exception as e:
            self._log_test_result("Invalid Method Handling", False, f"Exception: {str(e)}")
    
    def test_request_validation(self):
        """Test request validation"""
        test_cases = [
            {
                'name': 'Empty Body',
                'data': {},
                'expected_status': 400
            },
            {
                'name': 'Missing Required Fields',
                'data': {'username': 'test'},
                'expected_status': 400
            },
            {
                'name': 'Invalid Data Types',
                'data': {'username': 123, 'userId': 'test', 'query': 'test'},
                'expected_status': 400
            }
        ]
        
        for case in test_cases:
            try:
                response = self._make_request('POST', '/fitness-coach', case['data'])
                
                if response.status_code == case['expected_status']:
                    self._log_test_result(
                        f"Request Validation - {case['name']}", True,
                        f"Correctly returned {response.status_code}"
                    )
                else:
                    self._log_test_result(
                        f"Request Validation - {case['name']}", False,
                        f"Expected {case['expected_status']}, got {response.status_code}"
                    )
                    
            except Exception as e:
                self._log_test_result(
                    f"Request Validation - {case['name']}", False, 
                    f"Exception: {str(e)}"
                )
    
    def test_valid_request(self):
        """Test valid fitness coach request"""
        try:
            test_data = {
                'username': 'test_user',
                'userId': 'test_123',
                'query': 'I want to build muscle and lose weight. I can work out 4 days a week and prefer high protein meals.'
            }
            
            print("🧪 Testing valid request (this may take 30+ seconds)...")
            start_time = time.time()
            
            response = self._make_request('POST', '/fitness-coach', test_data)
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                response_data = response.json()
                
                if response_data.get('success'):
                    data = response_data.get('data', {})
                    workout_plan = data.get('workoutPlan')
                    meal_plan = data.get('mealPlan')
                    
                    details = f"Response time: {response_time:.2f}s"
                    if workout_plan:
                        details += ", Workout plan generated"
                    if meal_plan:
                        details += ", Meal plan generated"
                    
                    self._log_test_result("Valid Request", True, details)
                else:
                    error = response_data.get('error', {})
                    self._log_test_result(
                        "Valid Request", False,
                        f"API returned error: {error.get('message', 'Unknown error')}"
                    )
            else:
                self._log_test_result(
                    "Valid Request", False,
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                
        except Exception as e:
            self._log_test_result("Valid Request", False, f"Exception: {str(e)}")
    
    def test_rate_limiting(self):
        """Test API rate limiting"""
        print("🧪 Testing rate limiting (making multiple requests)...")
        
        test_data = {
            'username': 'rate_test_user',
            'userId': 'rate_test_123',
            'query': 'Quick workout plan test'
        }
        
        rate_limited = False
        successful_requests = 0
        
        # Make multiple requests quickly
        for i in range(10):
            try:
                response = self._make_request('POST', '/fitness-coach', test_data)
                
                if response.status_code == 429:
                    rate_limited = True
                    break
                elif response.status_code == 200:
                    successful_requests += 1
                
                time.sleep(0.1)  # Small delay between requests
                
            except Exception as e:
                break
        
        if rate_limited:
            self._log_test_result(
                "Rate Limiting", True,
                f"Rate limiting triggered after {successful_requests} requests"
            )
        else:
            self._log_test_result(
                "Rate Limiting", False,
                f"No rate limiting detected after {successful_requests} requests"
            )
    
    def test_aws_services(self):
        """Test AWS services connectivity"""
        try:
            # Test Lambda functions exist
            lambda_client = boto3.client('lambda')
            functions = ['fitness-coach-handler', 'workout-generator', 'meal-planner']
            
            for func_name in functions:
                try:
                    lambda_client.get_function(FunctionName=func_name)
                    self._log_test_result(f"Lambda Function - {func_name}", True, "Function exists")
                except lambda_client.exceptions.ResourceNotFoundException:
                    self._log_test_result(f"Lambda Function - {func_name}", False, "Function not found")
                except Exception as e:
                    self._log_test_result(f"Lambda Function - {func_name}", False, f"Error: {str(e)}")
            
            # Test DynamoDB tables
            dynamodb = boto3.client('dynamodb')
            tables = ['fitness-coach-sessions', 'api-usage-metrics']
            
            for table_name in tables:
                try:
                    response = dynamodb.describe_table(TableName=table_name)
                    status = response['Table']['TableStatus']
                    self._log_test_result(f"DynamoDB Table - {table_name}", True, f"Status: {status}")
                except dynamodb.exceptions.ResourceNotFoundException:
                    self._log_test_result(f"DynamoDB Table - {table_name}", False, "Table not found")
                except Exception as e:
                    self._log_test_result(f"DynamoDB Table - {table_name}", False, f"Error: {str(e)}")
            
            # Test Secrets Manager
            secrets_client = boto3.client('secretsmanager')
            try:
                secrets_client.describe_secret(SecretId='fitness-coach/spoonacular-api-key')
                self._log_test_result("Secrets Manager", True, "Spoonacular secret exists")
            except secrets_client.exceptions.ResourceNotFoundException:
                self._log_test_result("Secrets Manager", False, "Spoonacular secret not found")
            except Exception as e:
                self._log_test_result("Secrets Manager", False, f"Error: {str(e)}")
                
        except Exception as e:
            self._log_test_result("AWS Services", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Fitness Health Coach API Tests\n")
        print(f"API URL: {self.api_url}")
        print(f"API Key: {'Configured' if self.api_key else 'Not configured'}")
        print()
        
        # Run tests
        self.test_health_endpoint()
        self.test_cors_preflight()
        self.test_invalid_method()
        self.test_request_validation()
        self.test_valid_request()
        self.test_rate_limiting()
        self.test_aws_services()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Save results
        with open('test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100
                },
                'tests': self.test_results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to test_results.json")
        
        return failed_tests == 0

def main():
    """Main function"""
    tester = FitnessCoachTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the results above.")
        sys.exit(1)

if __name__ == "__main__":
    main()