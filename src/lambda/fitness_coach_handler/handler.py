# Main Lambda handler for fitness coach API
import json
import logging
import os
import sys
import uuid
import time
from typing import Dict, Any, Optional
from datetime import datetime
import re
from functools import wraps

# Add shared modules to path
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

try:
    from models import UserProfile, validate_user_input, sanitize_user_input
    from database import get_database_instance, DynamoDBError
    from logging_utils import (
        get_logger, log_api_request, log_function_call, 
        log_external_service_call, log_performance_metric,
        log_business_event, log_security_event
    )
except ImportError as e:
    logging.error(f"Failed to import shared modules: {e}")
    # Fallback for local development
    pass

# Initialize structured logger
logger = get_logger('fitness-coach-handler')

# Retry configuration
RETRY_CONFIG = {
    'bedrock': {
        'max_retries': 3,
        'base_delay': 1.0,
        'max_delay': 8.0,
        'backoff_multiplier': 2.0
    },
    'spoonacular': {
        'max_retries': 2,
        'base_delay': 0.5,
        'max_delay': 2.0,
        'backoff_multiplier': 2.0
    },
    'dynamodb': {
        'max_retries': 3,
        'base_delay': 0.1,
        'max_delay': 1.0,
        'backoff_multiplier': 2.0
    }
}

def retry_with_exponential_backoff(service_name: str):
    """
    Decorator for implementing exponential backoff retry logic.
    
    Args:
        service_name: Name of the service for retry configuration
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = RETRY_CONFIG.get(service_name, RETRY_CONFIG['bedrock'])
            max_retries = config['max_retries']
            base_delay = config['base_delay']
            max_delay = config['max_delay']
            backoff_multiplier = config['backoff_multiplier']
            
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Don't retry on the last attempt
                    if attempt == max_retries:
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_multiplier ** attempt), max_delay)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {service_name}: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    time.sleep(delay)
            
            # All retries exhausted
            logger.error(f"All {max_retries + 1} attempts failed for {service_name}: {str(last_exception)}")
            raise last_exception
        
        return wrapper
    return decorator

class FitnessCoachAPIHandler:
    """Main API handler for fitness coach requests with comprehensive validation and error handling."""
    
    def __init__(self):
        """Initialize the API handler with database connection."""
        try:
            self.db = get_database_instance()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.db = None
    
    @log_function_call(logger)
    def handle_request(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Handle incoming API Gateway requests with comprehensive validation and error handling.
        
        Args:
            event: API Gateway event
            context: Lambda context
            
        Returns:
            Dict: Formatted API response
        """
        request_id = context.aws_request_id if context else str(uuid.uuid4())
        
        try:
            # Set correlation ID for request tracking
            logger.set_correlation_id(request_id)
            
            # Log incoming request with structured data
            logger.info(
                "Processing fitness coach request",
                request_id=request_id,
                http_method=event.get('httpMethod', 'POST'),
                path=event.get('path', '/fitness-coach'),
                source_ip=event.get('requestContext', {}).get('identity', {}).get('sourceIp')
            )
            
            # Validate HTTP method
            http_method = event.get('httpMethod', 'POST')
            if http_method == 'OPTIONS':
                return self._create_cors_response()
            
            if http_method != 'POST':
                log_security_event(
                    logger, 
                    'invalid_http_method',
                    severity='low',
                    http_method=http_method,
                    request_id=request_id
                )
                return self._create_error_response(
                    405, 'METHOD_NOT_ALLOWED', 
                    'Only POST method is supported',
                    request_id
                )
            
            # Parse and validate request body
            request_data = self._parse_request_body(event)
            if 'error' in request_data:
                return self._create_error_response(
                    400, 'INVALID_REQUEST_BODY',
                    request_data['error'],
                    request_id
                )
            
            # Validate and sanitize user input
            validation_result = self._validate_request_data(request_data['data'])
            if not validation_result['valid']:
                return self._create_error_response(
                    400, 'VALIDATION_ERROR',
                    validation_result['errors'],
                    request_id
                )
            
            # Create user profile
            try:
                user_profile = UserProfile(
                    username=validation_result['data']['username'],
                    user_id=validation_result['data']['userId'],
                    query=validation_result['data']['query']
                )
                
                # Log business event for user profile creation
                log_business_event(
                    logger,
                    'user_profile_created',
                    user_id=user_profile.user_id,
                    username=user_profile.username,
                    session_id=user_profile.session_id,
                    request_id=request_id
                )
                
            except Exception as e:
                logger.error(
                    "Failed to create user profile",
                    request_id=request_id,
                    exception=e,
                    validation_data=validation_result['data']
                )
                return self._create_error_response(
                    400, 'PROFILE_CREATION_ERROR',
                    f"Failed to create user profile: {str(e)}",
                    request_id
                )
            
            # Generate workout and meal plans
            generation_result = self._generate_comprehensive_plan(user_profile, request_id)
            
            if not generation_result['success']:
                # Determine appropriate HTTP status code based on error type
                status_code = self._get_error_status_code(generation_result['error_code'])
                return self._create_error_response(
                    status_code, generation_result['error_code'],
                    generation_result['error_message'],
                    request_id
                )
            
            # Store session in DynamoDB with enhanced error handling
            storage_result = {'success': True}  # Default to success
            
            try:
                storage_result = self._store_session(
                    user_profile, 
                    generation_result.get('workout_plan'),
                    generation_result.get('meal_plan'),
                    request_id
                )
                
                if not storage_result['success']:
                    logger.warning(f"Failed to store session {user_profile.session_id}: {storage_result['error']}")
                    # Continue with response even if storage fails
                    
            except Exception as e:
                logger.error(f"Critical storage error for session {user_profile.session_id}: {str(e)}")
                storage_result = {
                    'success': False,
                    'error': f'Storage service unavailable: {str(e)}'
                }
                # Continue with response even if storage fails
            
            # Return comprehensive response
            return self._create_success_response({
                'message': 'Fitness and nutrition plan generated successfully',
                'userProfile': {
                    'username': user_profile.username,
                    'userId': user_profile.user_id,
                    'sessionId': user_profile.session_id,
                    'query': user_profile.query,
                    'timestamp': user_profile.timestamp.isoformat()
                },
                'workoutPlan': generation_result.get('workout_plan'),
                'mealPlan': generation_result.get('meal_plan'),
                'metadata': {
                    'workoutGenerated': generation_result.get('workout_success', False),
                    'mealPlanGenerated': generation_result.get('meal_success', False),
                    'sessionStored': storage_result['success']
                }
            }, request_id)
            
        except Exception as e:
            logger.error(f"Unexpected error in request {request_id}: {str(e)}")
            return self._create_error_response(
                500, 'INTERNAL_ERROR',
                'An unexpected error occurred',
                request_id
            )
    
    def _parse_request_body(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate the request body from API Gateway event.
        
        Args:
            event: API Gateway event
            
        Returns:
            Dict: Parsed data or error information
        """
        try:
            # Check if body exists
            if 'body' not in event or not event['body']:
                return {'error': 'Request body is required'}
            
            # Parse JSON body
            if isinstance(event['body'], str):
                try:
                    body_data = json.loads(event['body'])
                except json.JSONDecodeError as e:
                    return {'error': f'Invalid JSON in request body: {str(e)}'}
            else:
                body_data = event['body']
            
            # Check if body is empty
            if not body_data:
                return {'error': 'Request body cannot be empty'}
            
            # Check content size (max 1MB)
            body_size = len(json.dumps(body_data))
            if body_size > 1024 * 1024:  # 1MB limit
                return {'error': 'Request body too large (max 1MB)'}
            
            return {'data': body_data}
            
        except Exception as e:
            logger.error(f"Error parsing request body: {str(e)}")
            return {'error': f'Failed to parse request body: {str(e)}'}
    
    def _validate_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize request data using shared validation utilities.
        
        Args:
            data: Request data to validate
            
        Returns:
            Dict: Validation result with sanitized data or errors
        """
        try:
            # Sanitize input data
            sanitized_data = sanitize_user_input(data)
            
            # Validate required fields and formats
            validation_errors = validate_user_input(sanitized_data)
            
            if validation_errors:
                return {
                    'valid': False,
                    'errors': validation_errors
                }
            
            # Additional security validations
            security_errors = self._perform_security_validation(sanitized_data)
            if security_errors:
                return {
                    'valid': False,
                    'errors': security_errors
                }
            
            return {
                'valid': True,
                'data': sanitized_data
            }
            
        except Exception as e:
            logger.error(f"Error validating request data: {str(e)}")
            return {
                'valid': False,
                'errors': {'validation': f'Validation failed: {str(e)}'}
            }
    
    def _perform_security_validation(self, data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Perform additional security validations on sanitized data.
        
        Args:
            data: Sanitized request data
            
        Returns:
            Dict: Security validation errors or None if valid
        """
        errors = {}
        
        # Check for potential SQL injection patterns
        sql_patterns = [
            r"(?i)(union|select|insert|update|delete|drop|create|alter)\s+",
            r"(?i)(or|and)\s+\d+\s*=\s*\d+",
            r"(?i)(\-\-|\#|\/\*|\*\/)"
        ]
        
        for field_name, field_value in data.items():
            if isinstance(field_value, str):
                for pattern in sql_patterns:
                    if re.search(pattern, field_value):
                        errors[field_name] = f"Invalid characters detected in {field_name}"
                        break
        
        # Check for script injection patterns
        script_patterns = [
            r"(?i)<script[^>]*>",
            r"(?i)javascript:",
            r"(?i)on\w+\s*=",
            r"(?i)eval\s*\(",
            r"(?i)expression\s*\("
        ]
        
        for field_name, field_value in data.items():
            if isinstance(field_value, str):
                for pattern in script_patterns:
                    if re.search(pattern, field_value):
                        errors[field_name] = f"Script content not allowed in {field_name}"
                        break
        
        # Check for excessive special characters
        for field_name, field_value in data.items():
            if isinstance(field_value, str):
                special_char_count = len(re.findall(r'[^\w\s\-\.\,\!\?\:\;]', field_value))
                if special_char_count > len(field_value) * 0.3:  # More than 30% special chars
                    errors[field_name] = f"Too many special characters in {field_name}"
        
        return errors if errors else None
    
    def _create_success_response(self, data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Create a standardized success response.
        
        Args:
            data: Response data
            request_id: Request identifier
            
        Returns:
            Dict: Formatted success response
        """
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'X-Request-ID': request_id
            },
            'body': json.dumps({
                'success': True,
                'data': data,
                'requestId': request_id,
                'timestamp': datetime.utcnow().isoformat()
            }, default=str)  # Handle Decimal and datetime serialization
        }
    
    def _create_error_response(self, status_code: int, error_code: str, 
                             message: Any, request_id: str) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            status_code: HTTP status code
            error_code: Application error code
            message: Error message or details
            request_id: Request identifier
            
        Returns:
            Dict: Formatted error response
        """
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'X-Request-ID': request_id
            },
            'body': json.dumps({
                'success': False,
                'error': {
                    'code': error_code,
                    'message': message,
                    'details': message if isinstance(message, dict) else None
                },
                'requestId': request_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    
    def _create_cors_response(self) -> Dict[str, Any]:
        """
        Create a CORS preflight response.
        
        Returns:
            Dict: CORS response
        """
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Max-Age': '86400'
            },
            'body': ''
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the service and its dependencies.
        
        Returns:
            Dict: Health check results
        """
        health_status = {
            'service': 'fitness-coach-api',
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        # Check database connection
        if self.db:
            try:
                db_health = self.db.health_check()
                health_status['checks']['database'] = {
                    'status': 'healthy' if db_health.get('database_connection') else 'unhealthy',
                    'details': db_health
                }
            except Exception as e:
                health_status['checks']['database'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health_status['status'] = 'degraded'
        else:
            health_status['checks']['database'] = {
                'status': 'unavailable',
                'error': 'Database not initialized'
            }
            health_status['status'] = 'degraded'
        
        # Check environment variables
        required_env_vars = ['AWS_DEFAULT_REGION']
        env_check = {'status': 'healthy', 'missing': []}
        
        for var in required_env_vars:
            if not os.getenv(var):
                env_check['missing'].append(var)
                env_check['status'] = 'unhealthy'
        
        health_status['checks']['environment'] = env_check
        if env_check['status'] == 'unhealthy':
            health_status['status'] = 'degraded'
        
        return health_status
    
    def _generate_comprehensive_plan(self, user_profile: UserProfile, request_id: str) -> Dict[str, Any]:
        """
        Orchestrate calls to workout and meal plan generation services.
        
        Args:
            user_profile: User profile with query and preferences
            request_id: Request identifier for logging
            
        Returns:
            Dict: Generation results with workout and meal plans
        """
        result = {
            'success': True,
            'workout_success': False,
            'meal_success': False,
            'workout_plan': None,
            'meal_plan': None,
            'error_code': None,
            'error_message': None
        }
        
        try:
            # Generate workout plan with comprehensive error handling
            logger.info(f"Generating workout plan for request {request_id}")
            try:
                workout_result = self._call_workout_generator(user_profile)
                
                if workout_result['success']:
                    result['workout_plan'] = workout_result['data']
                    result['workout_success'] = True
                    logger.info(f"Workout plan generated successfully for request {request_id}")
                else:
                    logger.error(f"Workout generation failed for request {request_id}: {workout_result['error']}")
                    
            except Exception as e:
                # Handle Bedrock service unavailability
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ['bedrock', 'unavailable', 'timeout']):
                    logger.error(f"Bedrock service unavailable for request {request_id}: {str(e)}")
                else:
                    logger.error(f"Unexpected workout generation error for request {request_id}: {str(e)}")
            
            # Generate meal plan with comprehensive error handling
            logger.info(f"Generating meal plan for request {request_id}")
            try:
                meal_result = self._call_meal_planner(user_profile)
                
                if meal_result['success']:
                    result['meal_plan'] = meal_result['data']
                    result['meal_success'] = True
                    logger.info(f"Meal plan generated successfully for request {request_id}")
                else:
                    logger.error(f"Meal plan generation failed for request {request_id}: {meal_result['error']}")
                    
            except Exception as e:
                # Handle Spoonacular API unavailability
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ['spoonacular', 'unavailable', 'timeout']):
                    logger.error(f"Spoonacular API unavailable for request {request_id}: {str(e)}")
                else:
                    logger.error(f"Unexpected meal planning error for request {request_id}: {str(e)}")
            
            # Determine overall success and appropriate error messaging
            if not result['workout_success'] and not result['meal_success']:
                result['success'] = False
                result['error_code'] = 'ALL_SERVICES_FAILED'
                result['error_message'] = (
                    'Both workout and meal plan generation services are currently unavailable. '
                    'Please try again in a few minutes.'
                )
            elif not result['workout_success']:
                logger.warning(f"Only meal plan generated for request {request_id}")
                # Partial success - continue with meal plan only
            elif not result['meal_success']:
                logger.warning(f"Only workout plan generated for request {request_id}")
                # Partial success - continue with workout plan only
            
            return result
            
        except Exception as e:
            logger.error(f"Critical error in comprehensive plan generation for request {request_id}: {str(e)}")
            result['success'] = False
            result['error_code'] = 'CRITICAL_GENERATION_ERROR'
            result['error_message'] = 'A critical error occurred during plan generation. Please try again.'
            return result
    
    @retry_with_exponential_backoff('bedrock')
    @log_external_service_call('bedrock', logger)
    def _call_workout_generator(self, user_profile: UserProfile) -> Dict[str, Any]:
        """
        Call the workout generator Lambda function with retry logic.
        
        Args:
            user_profile: User profile for workout generation
            
        Returns:
            Dict: Workout generation result
            
        Raises:
            Exception: If all retry attempts fail
        """
        try:
            import boto3
            from botocore.exceptions import ClientError, BotoCoreError
            
            # Initialize Lambda client
            lambda_client = boto3.client('lambda')
            
            # Prepare payload
            payload = {
                'body': json.dumps({
                    'username': user_profile.username,
                    'userId': user_profile.user_id,
                    'query': user_profile.query
                })
            }
            
            # Invoke workout generator function
            function_name = os.getenv('WORKOUT_GENERATOR_FUNCTION_NAME', 'fitness-coach-workout-generator')
            
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            
            # Check for Lambda function errors
            if 'FunctionError' in response:
                error_type = response['FunctionError']
                if error_type == 'Unhandled':
                    raise Exception(f"Workout generator function error: {response_payload}")
                else:
                    raise Exception(f"Workout generator {error_type}: {response_payload}")
            
            if response_payload.get('statusCode') == 200:
                body = json.loads(response_payload['body'])
                if body.get('success'):
                    return {
                        'success': True,
                        'data': body.get('data', {})
                    }
                else:
                    error_msg = body.get('error', 'Unknown workout generation error')
                    # Check if this is a Bedrock service error that should be retried
                    if self._is_retryable_bedrock_error(error_msg):
                        raise Exception(f"Retryable Bedrock error: {error_msg}")
                    else:
                        return {
                            'success': False,
                            'error': error_msg
                        }
            elif response_payload.get('statusCode') in [429, 502, 503, 504]:
                # Retryable HTTP status codes
                raise Exception(f"Retryable error: HTTP {response_payload.get('statusCode')}")
            else:
                return {
                    'success': False,
                    'error': f"Workout generator returned status {response_payload.get('statusCode')}"
                }
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['ThrottlingException', 'ServiceUnavailable', 'InternalFailure']:
                raise Exception(f"Retryable AWS error: {error_code}")
            else:
                return {
                    'success': False,
                    'error': f'AWS error calling workout generator: {error_code}'
                }
        except BotoCoreError as e:
            # Network or connection errors - retryable
            raise Exception(f"Retryable connection error: {str(e)}")
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'Invalid response from workout generator: {str(e)}'
            }
        except Exception as e:
            # Check if this is a retryable error
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['timeout', 'connection', 'network', 'retryable']):
                raise  # Re-raise for retry
            else:
                return {
                    'success': False,
                    'error': f'Workout generator call failed: {str(e)}'
                }
    
    @retry_with_exponential_backoff('spoonacular')
    @log_external_service_call('spoonacular', logger)
    def _call_meal_planner(self, user_profile: UserProfile) -> Dict[str, Any]:
        """
        Call the meal planner Lambda function with retry logic.
        
        Args:
            user_profile: User profile for meal planning
            
        Returns:
            Dict: Meal planning result
            
        Raises:
            Exception: If all retry attempts fail
        """
        try:
            import boto3
            from botocore.exceptions import ClientError, BotoCoreError
            
            # Initialize Lambda client
            lambda_client = boto3.client('lambda')
            
            # Prepare payload
            payload = {
                'body': json.dumps({
                    'username': user_profile.username,
                    'userId': user_profile.user_id,
                    'query': user_profile.query
                })
            }
            
            # Invoke meal planner function
            function_name = os.getenv('MEAL_PLANNER_FUNCTION_NAME', 'fitness-coach-meal-planner')
            
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            
            # Check for Lambda function errors
            if 'FunctionError' in response:
                error_type = response['FunctionError']
                if error_type == 'Unhandled':
                    raise Exception(f"Meal planner function error: {response_payload}")
                else:
                    raise Exception(f"Meal planner {error_type}: {response_payload}")
            
            if response_payload.get('statusCode') == 200:
                body = json.loads(response_payload['body'])
                if body.get('success'):
                    return {
                        'success': True,
                        'data': body.get('data', {})
                    }
                else:
                    error_msg = body.get('error', 'Unknown meal planning error')
                    # Check if this is a Spoonacular API error that should be retried
                    if self._is_retryable_spoonacular_error(error_msg):
                        raise Exception(f"Retryable Spoonacular error: {error_msg}")
                    else:
                        return {
                            'success': False,
                            'error': error_msg
                        }
            elif response_payload.get('statusCode') in [429, 502, 503, 504]:
                # Retryable HTTP status codes
                raise Exception(f"Retryable error: HTTP {response_payload.get('statusCode')}")
            else:
                return {
                    'success': False,
                    'error': f"Meal planner returned status {response_payload.get('statusCode')}"
                }
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['ThrottlingException', 'ServiceUnavailable', 'InternalFailure']:
                raise Exception(f"Retryable AWS error: {error_code}")
            else:
                return {
                    'success': False,
                    'error': f'AWS error calling meal planner: {error_code}'
                }
        except BotoCoreError as e:
            # Network or connection errors - retryable
            raise Exception(f"Retryable connection error: {str(e)}")
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'Invalid response from meal planner: {str(e)}'
            }
        except Exception as e:
            # Check if this is a retryable error
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['timeout', 'connection', 'network', 'retryable']):
                raise  # Re-raise for retry
            else:
                return {
                    'success': False,
                    'error': f'Meal planner call failed: {str(e)}'
                }
    
    def _is_retryable_bedrock_error(self, error_message: str) -> bool:
        """
        Determine if a Bedrock error should be retried.
        
        Args:
            error_message: Error message from Bedrock service
            
        Returns:
            bool: True if error is retryable
        """
        retryable_patterns = [
            'throttling', 'rate limit', 'service unavailable',
            'internal error', 'timeout', 'connection',
            'bedrock.*unavailable', 'model.*unavailable'
        ]
        
        error_lower = error_message.lower()
        return any(re.search(pattern, error_lower) for pattern in retryable_patterns)
    
    def _is_retryable_spoonacular_error(self, error_message: str) -> bool:
        """
        Determine if a Spoonacular API error should be retried.
        
        Args:
            error_message: Error message from Spoonacular API
            
        Returns:
            bool: True if error is retryable
        """
        retryable_patterns = [
            'rate limit', 'quota exceeded', 'service unavailable',
            'internal server error', 'timeout', 'connection',
            'spoonacular.*unavailable', 'api.*unavailable',
            '429', '502', '503', '504'
        ]
        
        error_lower = error_message.lower()
        return any(re.search(pattern, error_lower) for pattern in retryable_patterns)
    
    @retry_with_exponential_backoff('dynamodb')
    def _store_session(self, user_profile: UserProfile, workout_plan: Optional[Dict[str, Any]], 
                      meal_plan: Optional[Dict[str, Any]], request_id: str) -> Dict[str, Any]:
        """
        Store user session with workout and meal plans in DynamoDB with retry logic.
        
        Args:
            user_profile: User profile information
            workout_plan: Generated workout plan data
            meal_plan: Generated meal plan data
            request_id: Request identifier for logging
            
        Returns:
            Dict: Storage result
            
        Raises:
            Exception: If all retry attempts fail for retryable errors
        """
        try:
            if not self.db:
                return {
                    'success': False,
                    'error': 'Database not available'
                }
            
            # Convert plan data to model objects if available
            workout_plan_obj = None
            meal_plan_obj = None
            
            if workout_plan and workout_plan.get('workoutPlan'):
                try:
                    # The workout plan data is already in the correct format from the generator
                    workout_plan_obj = workout_plan['workoutPlan']
                except Exception as e:
                    logger.warning(f"Failed to process workout plan for storage: {str(e)}")
            
            if meal_plan and meal_plan.get('meal_plan'):
                try:
                    # The meal plan data is already in the correct format from the planner
                    meal_plan_obj = meal_plan['meal_plan']
                except Exception as e:
                    logger.warning(f"Failed to process meal plan for storage: {str(e)}")
            
            # Create session with available data
            success = self.db.create_session(
                user_profile=user_profile,
                workout_plan=workout_plan_obj,
                meal_plan=meal_plan_obj
            )
            
            if success:
                logger.info(f"Session stored successfully for request {request_id}")
                
                # Record API usage metrics (with separate error handling)
                self._record_usage_metrics_safe(user_profile, workout_plan_obj, meal_plan_obj)
                
                return {'success': True}
            else:
                # Session creation failed - this might be retryable
                raise Exception("Failed to create session in database")
                
        except DynamoDBError as e:
            error_str = str(e).lower()
            # Check if this is a retryable DynamoDB error
            if any(keyword in error_str for keyword in [
                'throttling', 'provisioned throughput', 'service unavailable',
                'internal server error', 'timeout', 'connection'
            ]):
                raise Exception(f"Retryable DynamoDB error: {str(e)}")
            else:
                return {
                    'success': False,
                    'error': f'Database error: {str(e)}'
                }
        except Exception as e:
            error_str = str(e).lower()
            # Check if this is a retryable error
            if any(keyword in error_str for keyword in [
                'timeout', 'connection', 'network', 'retryable',
                'throttling', 'service unavailable'
            ]):
                raise  # Re-raise for retry
            else:
                return {
                    'success': False,
                    'error': f'Storage failed: {str(e)}'
                }
    
    def _record_usage_metrics_safe(self, user_profile: UserProfile, 
                                  workout_plan_obj: Optional[Any], 
                                  meal_plan_obj: Optional[Any]) -> None:
        """
        Safely record API usage metrics without affecting main flow.
        
        Args:
            user_profile: User profile information
            workout_plan_obj: Workout plan object
            meal_plan_obj: Meal plan object
        """
        try:
            bedrock_tokens = 0
            spoonacular_calls = 0
            
            # Estimate token usage (rough approximation)
            if workout_plan_obj:
                bedrock_tokens = len(user_profile.query) // 4  # Rough token estimate
            
            if meal_plan_obj:
                spoonacular_calls = 1  # One call per meal plan generation
            
            self.db.record_api_usage(
                user_id=user_profile.user_id,
                bedrock_tokens=bedrock_tokens,
                spoonacular_calls=spoonacular_calls
            )
            logger.info(f"Recorded usage metrics: {bedrock_tokens} tokens, {spoonacular_calls} API calls")
            
        except Exception as e:
            logger.warning(f"Failed to record API usage metrics (non-critical): {str(e)}")
    
    def _handle_service_unavailable_error(self, service_name: str, error_details: str) -> Dict[str, Any]:
        """
        Handle service unavailable errors with appropriate user messaging.
        
        Args:
            service_name: Name of the unavailable service
            error_details: Detailed error information
            
        Returns:
            Dict: Formatted error response
        """
        service_messages = {
            'bedrock': {
                'user_message': 'Workout plan generation is temporarily unavailable. Please try again in a few minutes.',
                'error_code': 'BEDROCK_UNAVAILABLE'
            },
            'spoonacular': {
                'user_message': 'Meal plan generation is temporarily unavailable. Please try again in a few minutes.',
                'error_code': 'SPOONACULAR_UNAVAILABLE'
            },
            'dynamodb': {
                'user_message': 'Data storage is temporarily unavailable. Your plans were generated but not saved.',
                'error_code': 'STORAGE_UNAVAILABLE'
            }
        }
        
        service_info = service_messages.get(service_name, {
            'user_message': f'{service_name} service is temporarily unavailable.',
            'error_code': 'SERVICE_UNAVAILABLE'
        })
        
        logger.error(f"{service_name} service unavailable: {error_details}")
        
        return {
            'success': False,
            'error_code': service_info['error_code'],
            'error_message': service_info['user_message'],
            'technical_details': error_details
        }
    
    def _get_error_status_code(self, error_code: str) -> int:
        """
        Determine appropriate HTTP status code based on error type.
        
        Args:
            error_code: Application error code
            
        Returns:
            int: HTTP status code
        """
        status_code_mapping = {
            'VALIDATION_ERROR': 400,
            'INVALID_REQUEST_BODY': 400,
            'PROFILE_CREATION_ERROR': 400,
            'METHOD_NOT_ALLOWED': 405,
            'BEDROCK_UNAVAILABLE': 503,
            'SPOONACULAR_UNAVAILABLE': 503,
            'STORAGE_UNAVAILABLE': 503,
            'ALL_SERVICES_FAILED': 503,
            'SERVICE_UNAVAILABLE': 503,
            'GENERATION_FAILED': 502,
            'GENERATION_ERROR': 500,
            'CRITICAL_GENERATION_ERROR': 500,
            'CRITICAL_ERROR': 500,
            'INTERNAL_ERROR': 500
        }
        
        return status_code_mapping.get(error_code, 500)


@log_api_request(logger)
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main entry point for fitness coach API requests.
    
    This handler implements comprehensive request validation, input sanitization,
    and error handling as specified in requirements 1.1, 1.2, 5.2, and 6.2.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        Dict: Formatted API response
    """
    try:
        # Initialize API handler
        api_handler = FitnessCoachAPIHandler()
        
        # Check for health check requests
        if event.get('path') == '/health' or event.get('rawPath') == '/health':
            health_result = api_handler.health_check()
            status_code = 200 if health_result['status'] == 'healthy' else 503
            
            # Log health check event
            logger.info(
                "Health check performed",
                event_type="health_check",
                health_status=health_result['status'],
                status_code=status_code
            )
            
            return {
                'statusCode': status_code,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(health_result, default=str)
            }
        
        # Handle main API requests
        return api_handler.handle_request(event, context)
        
    except Exception as e:
        # Fallback error handling if API handler fails to initialize
        request_id = context.aws_request_id if context else str(uuid.uuid4())
        
        logger.error(
            "Critical error in lambda_handler",
            request_id=request_id,
            exception=e,
            event_type="critical_error"
        )
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'X-Request-ID': request_id
            },
            'body': json.dumps({
                'success': False,
                'error': {
                    'code': 'CRITICAL_ERROR',
                    'message': 'Service temporarily unavailable'
                },
                'requestId': request_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        }