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

# -------------------------------------------------------------------
# Paths for shared code (layer and in-repo shared folder)
# -------------------------------------------------------------------
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

# -------------------------------------------------------------------
# Import models/database FIRST (separate from logging utils)
# -------------------------------------------------------------------
try:
    from models import UserProfile, validate_user_input, sanitize_user_input
    from database import get_database_instance, DynamoDBError
except Exception as e:
    logging.error(f"Failed to import shared models/database: {e}")
    # Let this raise during runtime if actually missing in Lambda;
    # but we keep the import error visible here for faster diagnosis.
    raise

# -------------------------------------------------------------------
# Import logging utils with ROBUST FALLBACKS
# -------------------------------------------------------------------
try:
    from logging_utils import (
        get_logger, log_api_request, log_function_call,
        log_external_service_call, log_performance_metric,
        log_business_event, log_security_event
    )
except Exception as e:
    # Fallbacks so the module never fails to import
    import json as _json

    class _SimpleStructuredLogger:
        def __init__(self, name: str):
            self._logger = logging.getLogger(name)
            if not self._logger.handlers:
                h = logging.StreamHandler()
                fmt = logging.Formatter('%(message)s')
                h.setFormatter(fmt)
                self._logger.addHandler(h)
            self._logger.setLevel(logging.INFO)
            self._correlation_id = None

        def set_correlation_id(self, cid: str):
            self._correlation_id = cid

        def _emit(self, level, msg, **fields):
            if self._correlation_id and 'correlation_id' not in fields:
                fields['correlation_id'] = self._correlation_id
            payload = {"level": level.upper(), "message": msg, **fields}
            self._logger.info(_json.dumps(payload, default=str))

        def info(self, msg, **fields):
            self._emit("info", msg, **fields)

        def warning(self, msg, **fields):
            self._emit("warning", msg, **fields)

        def error(self, msg, **fields):
            self._emit("error", msg, **fields)

    def get_logger(name: str):
        return _SimpleStructuredLogger(name)

    # No-op decorators (preserve call signatures)
    def log_api_request(logger_obj):
        def deco(func):
            def wrapper(*a, **kw):
                return func(*a, **kw)
            return wrapper
        return deco

    def log_function_call(logger_obj):
        def deco(func):
            def wrapper(*a, **kw):
                return func(*a, **kw)
            return wrapper
        return deco

    def log_external_service_call(service_name, logger_obj):
        def deco(func):
            def wrapper(*a, **kw):
                return func(*a, **kw)
            return wrapper
        return deco

    # Stubs for optional helpers
    def log_performance_metric(*args, **kwargs): pass
    def log_business_event(*args, **kwargs): pass
    def log_security_event(*args, **kwargs): pass

# -------------------------------------------------------------------
# Initialize structured logger (real or fallback)
# -------------------------------------------------------------------
logger = get_logger('fitness-coach-handler')

# -------------------------------------------------------------------
# Retry configuration
# -------------------------------------------------------------------
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

                    if attempt == max_retries:
                        break

                    delay = min(base_delay * (backoff_multiplier ** attempt), max_delay)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {service_name}: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    time.sleep(delay)

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
        """
        request_id = context.aws_request_id if context else str(uuid.uuid4())

        try:
            # Correlation ID
            logger.set_correlation_id(request_id)

            # Log inbound
            logger.info(
                "Processing fitness coach request",
                request_id=request_id,
                http_method=event.get('httpMethod', 'POST'),
                path=event.get('path', '/fitness-coach'),
                source_ip=event.get('requestContext', {}).get('identity', {}).get('sourceIp')
            )

            # Method/CORS
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

            # Parse body
            request_data = self._parse_request_body(event)
            if 'error' in request_data:
                return self._create_error_response(
                    400, 'INVALID_REQUEST_BODY',
                    request_data['error'],
                    request_id
                )

            # Validate & sanitize
            validation_result = self._validate_request_data(request_data['data'])
            if not validation_result['valid']:
                return self._create_error_response(
                    400, 'VALIDATION_ERROR',
                    validation_result['errors'],
                    request_id
                )

            # Create profile
            try:
                user_profile = UserProfile(
                    username=validation_result['data']['username'],
                    user_id=validation_result['data']['userId'],
                    query=validation_result['data']['query']
                )

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

            # Generate plans
            generation_result = self._generate_comprehensive_plan(user_profile, request_id)

            if not generation_result['success']:
                status_code = self._get_error_status_code(generation_result['error_code'])
                return self._create_error_response(
                    status_code, generation_result['error_code'],
                    generation_result['error_message'],
                    request_id
                )

            # Store session (non-blocking for errors)
            storage_result = {'success': True}
            try:
                storage_result = self._store_session(
                    user_profile,
                    generation_result.get('workout_plan'),
                    generation_result.get('meal_plan'),
                    request_id
                )
                if not storage_result['success']:
                    logger.warning(f"Failed to store session {user_profile.session_id}: {storage_result['error']}")
            except Exception as e:
                logger.error(f"Critical storage error for session {user_profile.session_id}: {str(e)}")
                storage_result = {'success': False, 'error': f'Storage service unavailable: {str(e)}'}

            # Success response
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
        """Parse and validate the request body from API Gateway event."""
        try:
            if 'body' not in event or not event['body']:
                return {'error': 'Request body is required'}

            if isinstance(event['body'], str):
                try:
                    body_data = json.loads(event['body'])
                except json.JSONDecodeError as e:
                    return {'error': f'Invalid JSON in request body: {str(e)}'}
            else:
                body_data = event['body']

            if not body_data:
                return {'error': 'Request body cannot be empty'}

            body_size = len(json.dumps(body_data))
            if body_size > 1024 * 1024:
                return {'error': 'Request body too large (max 1MB)'}

            return {'data': body_data}

        except Exception as e:
            logger.error(f"Error parsing request body: {str(e)}")
            return {'error': f'Failed to parse request body: {str(e)}'}

    def _validate_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize request data using shared validation utilities."""
        try:
            sanitized_data = sanitize_user_input(data)
            validation_errors = validate_user_input(sanitized_data)

            if validation_errors:
                return {'valid': False, 'errors': validation_errors}

            security_errors = self._perform_security_validation(sanitized_data)
            if security_errors:
                return {'valid': False, 'errors': security_errors}

            return {'valid': True, 'data': sanitized_data}

        except Exception as e:
            logger.error(f"Error validating request data: {str(e)}")
            return {'valid': False, 'errors': {'validation': f'Validation failed: {str(e)}'}}

    def _perform_security_validation(self, data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Additional security validations on sanitized data."""
        errors = {}

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

        for field_name, field_value in data.items():
            if isinstance(field_value, str):
                special_char_count = len(re.findall(r'[^\w\s\-\.\,\!\?\:\;]', field_value))
                if special_char_count > len(field_value) * 0.3:
                    errors[field_name] = f"Too many special characters in {field_name}"

        return errors if errors else None

    def _create_success_response(self, data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Standard success response."""
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
            }, default=str)
        }

    def _create_error_response(self, status_code: int, error_code: str,
                               message: Any, request_id: str) -> Dict[str, Any]:
        """Standard error response."""
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
        """CORS preflight response."""
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
        """Health check of the service and its dependencies."""
        health_status = {
            'service': 'fitness-coach-api',
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }

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
        """Orchestrate calls to workout and meal plan generation services."""
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
            # Workout
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
                error_str = str(e).lower()
                if any(k in error_str for k in ['bedrock', 'unavailable', 'timeout']):
                    logger.error(f"Bedrock service unavailable for request {request_id}: {str(e)}")
                else:
                    logger.error(f"Unexpected workout generation error for request {request_id}: {str(e)}")

            # Meal
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
                error_str = str(e).lower()
                if any(k in error_str for k in ['spoonacular', 'unavailable', 'timeout']):
                    logger.error(f"Spoonacular API unavailable for request {request_id}: {str(e)}")
                else:
                    logger.error(f"Unexpected meal planning error for request {request_id}: {str(e)}")

            if not result['workout_success'] and not result['meal_success']:
                result['success'] = False
                result['error_code'] = 'ALL_SERVICES_FAILED'
                result['error_message'] = (
                    'Both workout and meal plan generation services are currently unavailable. '
                    'Please try again in a few minutes.'
                )
            elif not result['workout_success']:
                logger.warning(f"Only meal plan generated for request {request_id}")
            elif not result['meal_success']:
                logger.warning(f"Only workout plan generated for request {request_id}")

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
        """Call the workout generator Lambda function with retry logic."""
        try:
            import boto3
            from botocore.exceptions import ClientError, BotoCoreError

            lambda_client = boto3.client('lambda')

            payload = {
                'body': json.dumps({
                    'username': user_profile.username,
                    'userId': user_profile.user_id,
                    'query': user_profile.query
                })
            }

            function_name = os.getenv('WORKOUT_GENERATOR_FUNCTION_NAME', 'workout-generator')
            logger.info("Invoking downstream lambda", target=function_name, payload_preview=payload)

            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            response_payload = json.loads(response['Payload'].read())

            if 'FunctionError' in response:
                error_type = response['FunctionError']
                if error_type == 'Unhandled':
                    raise Exception(f"Workout generator function error: {response_payload}")
                else:
                    raise Exception(f"Workout generator {error_type}: {response_payload}")

            if response_payload.get('statusCode') == 200:
                body = json.loads(response_payload['body'])
                if body.get('success'):
                    return {'success': True, 'data': body.get('data', {})}
                else:
                    error_msg = body.get('error', 'Unknown workout generation error')
                    if self._is_retryable_bedrock_error(error_msg):
                        raise Exception(f"Retryable Bedrock error: {error_msg}")
                    else:
                        return {'success': False, 'error': error_msg}
            elif response_payload.get('statusCode') in [429, 502, 503, 504]:
                raise Exception(f"Retryable error: HTTP {response_payload.get('statusCode')}")
            else:
                return {'success': False, 'error': f"Workout generator returned status {response_payload.get('statusCode')}"}

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['ThrottlingException', 'ServiceUnavailable', 'InternalFailure']:
                raise Exception(f"Retryable AWS error: {error_code}")
            else:
                return {'success': False, 'error': f'AWS error calling workout generator: {error_code}'}
        except BotoCoreError as e:
            raise Exception(f"Retryable connection error: {str(e)}")
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'Invalid response from workout generator: {str(e)}'}
        except Exception as e:
            error_str = str(e).lower()
            if any(k in error_str for k in ['timeout', 'connection', 'network', 'retryable']):
                raise
            else:
                return {'success': False, 'error': f'Workout generator call failed: {str(e)}'}

    @retry_with_exponential_backoff('spoonacular')
    @log_external_service_call('spoonacular', logger)
    def _call_meal_planner(self, user_profile: UserProfile) -> Dict[str, Any]:
        """Call the meal planner Lambda function with retry logic."""
        try:
            import boto3
            from botocore.exceptions import ClientError, BotoCoreError

            lambda_client = boto3.client('lambda')

            payload = {
                'body': json.dumps({
                    'username': user_profile.username,
                    'userId': user_profile.user_id,
                    'query': user_profile.query
                })
            }

            function_name = os.getenv('MEAL_PLANNER_FUNCTION_NAME', 'meal-planner')
            logger.info("Invoking downstream lambda", target=function_name, payload_preview=payload)

            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            response_payload = json.loads(response['Payload'].read())

            if 'FunctionError' in response:
                error_type = response['FunctionError']
                if error_type == 'Unhandled':
                    raise Exception(f"Meal planner function error: {response_payload}")
                else:
                    raise Exception(f"Meal planner {error_type}: {response_payload}")

            if response_payload.get('statusCode') == 200:
                body = json.loads(response_payload['body'])
                if body.get('success'):
                    return {'success': True, 'data': body.get('data', {})}
                else:
                    error_msg = body.get('error', 'Unknown meal planning error')
                    if self._is_retryable_spoonacular_error(error_msg):
                        raise Exception(f"Retryable Spoonacular error: {error_msg}")
                    else:
                        return {'success': False, 'error': error_msg}
            elif response_payload.get('statusCode') in [429, 502, 503, 504]:
                raise Exception(f"Retryable error: HTTP {response_payload.get('statusCode')}")
            else:
                return {'success': False, 'error': f"Meal planner returned status {response_payload.get('statusCode')}"}

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['ThrottlingException', 'ServiceUnavailable', 'InternalFailure']:
                raise Exception(f"Retryable AWS error: {error_code}")
            else:
                return {'success': False, 'error': f'AWS error calling meal planner: {error_code}'}
        except BotoCoreError as e:
            raise Exception(f"Retryable connection error: {str(e)}")
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'Invalid response from meal planner: {str(e)}'}
        except Exception as e:
            error_str = str(e).lower()
            if any(k in error_str for k in ['timeout', 'connection', 'network', 'retryable']):
                raise
            else:
                return {'success': False, 'error': f'Meal planner call failed: {str(e)}'}

    def _is_retryable_bedrock_error(self, error_message: str) -> bool:
        """Determine if a Bedrock error should be retried."""
        retryable_patterns = [
            'throttling', 'rate limit', 'service unavailable',
            'internal error', 'timeout', 'connection',
            'bedrock.*unavailable', 'model.*unavailable'
        ]
        error_lower = error_message.lower()
        return any(re.search(pattern, error_lower) for pattern in retryable_patterns)

    def _is_retryable_spoonacular_error(self, error_message: str) -> bool:
        """Determine if a Spoonacular API error should be retried."""
        retryable_patterns = [
            'rate limit', 'quota exceeded', 'service unavailable',
            'internal server error', 'timeout', 'connection',
            'spoonacular.*unavailable', 'api.*unavailable',
            '429', '502', '503', '504'
        ]
        error_lower = error_message.lower()
        return any(re.search(pattern, error_lower) for pattern in retryable_patterns)

    @retry_with_exponential_backoff('dynamodb')
    def _store_session(self, user_profile: UserProfile,
                       workout_plan: Optional[Dict[str, Any]],
                       meal_plan: Optional[Dict[str, Any]],
                       request_id: str) -> Dict[str, Any]:
        """Store user session with workout and meal plans in DynamoDB with retry logic."""
        try:
            if not self.db:
                return {'success': False, 'error': 'Database not available'}

            workout_plan_obj = None
            meal_plan_obj = None

            if workout_plan and workout_plan.get('workoutPlan'):
                try:
                    workout_plan_obj = workout_plan['workoutPlan']
                except Exception as e:
                    logger.warning(f"Failed to process workout plan for storage: {str(e)}")

            if meal_plan and meal_plan.get('meal_plan'):
                try:
                    meal_plan_obj = meal_plan['meal_plan']
                except Exception as e:
                    logger.warning(f"Failed to process meal plan for storage: {str(e)}")

            success = self.db.create_session(
                user_profile=user_profile,
                workout_plan=workout_plan_obj,
                meal_plan=meal_plan_obj
            )

            if success:
                logger.info(f"Session stored successfully for request {request_id}")
                self._record_usage_metrics_safe(user_profile, workout_plan_obj, meal_plan_obj)
                return {'success': True}
            else:
                raise Exception("Failed to create session in database")

        except DynamoDBError as e:
            error_str = str(e).lower()
            if any(k in error_str for k in [
                'throttling', 'provisioned throughput', 'service unavailable',
                'internal server error', 'timeout', 'connection'
            ]):
                raise Exception(f"Retryable DynamoDB error: {str(e)}")
            else:
                return {'success': False, 'error': f'Database error: {str(e)}'}
        except Exception as e:
            error_str = str(e).lower()
            if any(k in error_str for k in [
                'timeout', 'connection', 'network', 'retryable',
                'throttling', 'service unavailable'
            ]):
                raise
            else:
                return {'success': False, 'error': f'Storage failed: {str(e)}'}

    def _record_usage_metrics_safe(self, user_profile: UserProfile,
                                   workout_plan_obj: Optional[Any],
                                   meal_plan_obj: Optional[Any]) -> None:
        """Safely record API usage metrics without affecting main flow."""
        try:
            bedrock_tokens = 0
            spoonacular_calls = 0

            if workout_plan_obj:
                bedrock_tokens = len(user_profile.query) // 4

            if meal_plan_obj:
                spoonacular_calls = 1

            self.db.record_api_usage(
                user_id=user_profile.user_id,
                bedrock_tokens=bedrock_tokens,
                spoonacular_calls=spoonacular_calls
            )
            logger.info(f"Recorded usage metrics: {bedrock_tokens} tokens, {spoonacular_calls} API calls")

        except Exception as e:
            logger.warning(f"Failed to record API usage metrics (non-critical): {str(e)}")

    def _handle_service_unavailable_error(self, service_name: str, error_details: str) -> Dict[str, Any]:
        """Handle service unavailable errors with appropriate user messaging."""
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
        """Map application error codes to HTTP status codes."""
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
    """
    try:
        api_handler = FitnessCoachAPIHandler()

        # Health check
        if event.get('path') == '/health' or event.get('rawPath') == '/health':
            health_result = api_handler.health_check()
            status_code = 200 if health_result['status'] == 'healthy' else 503

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

        # Normal requests
        return api_handler.handle_request(event, context)

    except Exception as e:
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
