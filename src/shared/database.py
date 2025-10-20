"""
DynamoDB utilities and table schemas for the Fitness Health Coach system.

This module provides database connection, CRUD operations, and table management
for DynamoDB integration with proper error handling and TTL configuration.
"""

import boto3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from botocore.exceptions import ClientError, BotoCoreError
import os
import json

from .models import UserProfile, WorkoutPlan, MealPlan

logger = logging.getLogger(__name__)


class DynamoDBError(Exception):
    """Custom exception for DynamoDB operations."""
    pass


class FitnessCoachDatabase:
    """Database manager for Fitness Coach DynamoDB operations."""
    
    def __init__(self, region_name: str = None):
        """
        Initialize DynamoDB client and table references.
        
        Args:
            region_name: AWS region name (defaults to environment variable)
        """
        self.region_name = region_name or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
            self.client = boto3.client('dynamodb', region_name=self.region_name)
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB client: {str(e)}")
            raise DynamoDBError(f"Database initialization failed: {str(e)}")
        
        # Table names from environment variables
        self.sessions_table_name = os.getenv('SESSIONS_TABLE_NAME', 'fitness-coach-sessions')
        self.metrics_table_name = os.getenv('METRICS_TABLE_NAME', 'api-usage-metrics')
        
        # Table references (lazy loaded)
        self._sessions_table = None
        self._metrics_table = None
    
    @property
    def sessions_table(self):
        """Get sessions table reference (lazy loaded)."""
        if self._sessions_table is None:
            self._sessions_table = self.dynamodb.Table(self.sessions_table_name)
        return self._sessions_table
    
    @property
    def metrics_table(self):
        """Get metrics table reference (lazy loaded)."""
        if self._metrics_table is None:
            self._metrics_table = self.dynamodb.Table(self.metrics_table_name)
        return self._metrics_table
    
    # Session Management Operations
    
    def create_session(self, user_profile: UserProfile, 
                      workout_plan: Optional[WorkoutPlan] = None,
                      meal_plan: Optional[MealPlan] = None) -> bool:
        """
        Create a new user session with optional workout and meal plans.
        
        Args:
            user_profile: User profile information
            workout_plan: Optional workout plan
            meal_plan: Optional meal plan
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            DynamoDBError: If database operation fails
        """
        try:
            # Prepare session item
            session_item = user_profile.to_dynamodb_item()
            
            # Add workout plan if provided
            if workout_plan:
                session_item['workoutPlan'] = workout_plan.to_dynamodb_item()
            
            # Add meal plan if provided
            if meal_plan:
                session_item['mealPlan'] = meal_plan.to_dynamodb_item()
            
            # Add metadata
            session_item['createdAt'] = Decimal(str(datetime.utcnow().timestamp()))
            session_item['updatedAt'] = Decimal(str(datetime.utcnow().timestamp()))
            
            # Put item with condition to prevent overwrites
            response = self.sessions_table.put_item(
                Item=session_item,
                ConditionExpression='attribute_not_exists(userId) AND attribute_not_exists(sessionId)'
            )
            
            logger.info(f"Created session for user {user_profile.user_id}, session {user_profile.session_id}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                logger.warning(f"Session already exists for user {user_profile.user_id}")
                return False
            else:
                logger.error(f"Failed to create session: {str(e)}")
                raise DynamoDBError(f"Failed to create session: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating session: {str(e)}")
            raise DynamoDBError(f"Unexpected error creating session: {str(e)}")
    
    def get_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user session by user ID and session ID.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Session data dictionary or None if not found
            
        Raises:
            DynamoDBError: If database operation fails
        """
        try:
            response = self.sessions_table.get_item(
                Key={
                    'userId': user_id,
                    'sessionId': session_id
                }
            )
            
            if 'Item' in response:
                logger.info(f"Retrieved session for user {user_id}, session {session_id}")
                return response['Item']
            else:
                logger.info(f"Session not found for user {user_id}, session {session_id}")
                return None
                
        except ClientError as e:
            logger.error(f"Failed to get session: {str(e)}")
            raise DynamoDBError(f"Failed to get session: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting session: {str(e)}")
            raise DynamoDBError(f"Unexpected error getting session: {str(e)}")
    
    def update_session(self, user_id: str, session_id: str, 
                      workout_plan: Optional[WorkoutPlan] = None,
                      meal_plan: Optional[MealPlan] = None) -> bool:
        """
        Update an existing session with workout and/or meal plans.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            workout_plan: Optional workout plan to add/update
            meal_plan: Optional meal plan to add/update
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            DynamoDBError: If database operation fails
        """
        try:
            update_expression = "SET updatedAt = :updated_at"
            expression_values = {
                ':updated_at': Decimal(str(datetime.utcnow().timestamp()))
            }
            
            if workout_plan:
                update_expression += ", workoutPlan = :workout_plan"
                expression_values[':workout_plan'] = workout_plan.to_dynamodb_item()
            
            if meal_plan:
                update_expression += ", mealPlan = :meal_plan"
                expression_values[':meal_plan'] = meal_plan.to_dynamodb_item()
            
            response = self.sessions_table.update_item(
                Key={
                    'userId': user_id,
                    'sessionId': session_id
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ConditionExpression='attribute_exists(userId) AND attribute_exists(sessionId)',
                ReturnValues='UPDATED_NEW'
            )
            
            logger.info(f"Updated session for user {user_id}, session {session_id}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                logger.warning(f"Session not found for update: user {user_id}, session {session_id}")
                return False
            else:
                logger.error(f"Failed to update session: {str(e)}")
                raise DynamoDBError(f"Failed to update session: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating session: {str(e)}")
            raise DynamoDBError(f"Unexpected error updating session: {str(e)}")
    
    def delete_session(self, user_id: str, session_id: str) -> bool:
        """
        Delete a user session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            True if successful, False if session not found
            
        Raises:
            DynamoDBError: If database operation fails
        """
        try:
            response = self.sessions_table.delete_item(
                Key={
                    'userId': user_id,
                    'sessionId': session_id
                },
                ConditionExpression='attribute_exists(userId) AND attribute_exists(sessionId)',
                ReturnValues='ALL_OLD'
            )
            
            logger.info(f"Deleted session for user {user_id}, session {session_id}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                logger.warning(f"Session not found for deletion: user {user_id}, session {session_id}")
                return False
            else:
                logger.error(f"Failed to delete session: {str(e)}")
                raise DynamoDBError(f"Failed to delete session: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error deleting session: {str(e)}")
            raise DynamoDBError(f"Unexpected error deleting session: {str(e)}")
    
    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent sessions for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return
            
        Returns:
            List of session data dictionaries
            
        Raises:
            DynamoDBError: If database operation fails
        """
        try:
            response = self.sessions_table.query(
                KeyConditionExpression='userId = :user_id',
                ExpressionAttributeValues={':user_id': user_id},
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )
            
            sessions = response.get('Items', [])
            logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
            return sessions
            
        except ClientError as e:
            logger.error(f"Failed to get user sessions: {str(e)}")
            raise DynamoDBError(f"Failed to get user sessions: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting user sessions: {str(e)}")
            raise DynamoDBError(f"Unexpected error getting user sessions: {str(e)}")
    
    # Metrics Operations
    
    def record_api_usage(self, user_id: str, bedrock_tokens: int = 0, 
                        spoonacular_calls: int = 0) -> bool:
        """
        Record API usage metrics for a user.
        
        Args:
            user_id: User identifier
            bedrock_tokens: Number of Bedrock tokens used
            spoonacular_calls: Number of Spoonacular API calls made
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            DynamoDBError: If database operation fails
        """
        try:
            today = datetime.utcnow().strftime('%Y-%m-%d')
            
            response = self.metrics_table.update_item(
                Key={
                    'date': today,
                    'userId': user_id
                },
                UpdateExpression='''
                    ADD requestCount :inc, bedrockTokens :bedrock_tokens, spoonacularCalls :spoon_calls
                    SET updatedAt = :updated_at
                ''',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':bedrock_tokens': bedrock_tokens,
                    ':spoon_calls': spoonacular_calls,
                    ':updated_at': Decimal(str(datetime.utcnow().timestamp()))
                },
                ReturnValues='UPDATED_NEW'
            )
            
            logger.info(f"Recorded API usage for user {user_id} on {today}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to record API usage: {str(e)}")
            raise DynamoDBError(f"Failed to record API usage: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error recording API usage: {str(e)}")
            raise DynamoDBError(f"Unexpected error recording API usage: {str(e)}")
    
    def get_usage_metrics(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get usage metrics for a user over the specified number of days.
        
        Args:
            user_id: User identifier
            days: Number of days to retrieve (default 7)
            
        Returns:
            List of usage metric dictionaries
            
        Raises:
            DynamoDBError: If database operation fails
        """
        try:
            # Generate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            date_range = []
            current_date = start_date
            while current_date <= end_date:
                date_range.append(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)
            
            metrics = []
            for date_str in date_range:
                try:
                    response = self.metrics_table.get_item(
                        Key={
                            'date': date_str,
                            'userId': user_id
                        }
                    )
                    
                    if 'Item' in response:
                        metrics.append(response['Item'])
                    else:
                        # Create empty metric for missing days
                        metrics.append({
                            'date': date_str,
                            'userId': user_id,
                            'requestCount': 0,
                            'bedrockTokens': 0,
                            'spoonacularCalls': 0
                        })
                except ClientError:
                    # Skip individual date errors
                    continue
            
            logger.info(f"Retrieved {len(metrics)} usage metrics for user {user_id}")
            return metrics
            
        except Exception as e:
            logger.error(f"Unexpected error getting usage metrics: {str(e)}")
            raise DynamoDBError(f"Unexpected error getting usage metrics: {str(e)}")
    
    # Table Management Operations
    
    def create_tables(self) -> bool:
        """
        Create DynamoDB tables if they don't exist.
        
        Returns:
            True if successful, False otherwise
            
        Raises:
            DynamoDBError: If table creation fails
        """
        try:
            # Create sessions table
            sessions_created = self._create_sessions_table()
            
            # Create metrics table
            metrics_created = self._create_metrics_table()
            
            return sessions_created and metrics_created
            
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise DynamoDBError(f"Failed to create tables: {str(e)}")
    
    def _create_sessions_table(self) -> bool:
        """Create the sessions table with TTL configuration."""
        try:
            # Check if table exists
            try:
                self.sessions_table.load()
                logger.info(f"Sessions table {self.sessions_table_name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
            
            # Create table
            table = self.dynamodb.create_table(
                TableName=self.sessions_table_name,
                KeySchema=[
                    {
                        'AttributeName': 'userId',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'sessionId',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'userId',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'sessionId',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Wait for table to be created
            table.wait_until_exists()
            
            # Configure TTL
            self.client.update_time_to_live(
                TableName=self.sessions_table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': 'ttl'
                }
            )
            
            logger.info(f"Created sessions table {self.sessions_table_name} with TTL")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create sessions table: {str(e)}")
            raise DynamoDBError(f"Failed to create sessions table: {str(e)}")
    
    def _create_metrics_table(self) -> bool:
        """Create the metrics table."""
        try:
            # Check if table exists
            try:
                self.metrics_table.load()
                logger.info(f"Metrics table {self.metrics_table_name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
            
            # Create table
            table = self.dynamodb.create_table(
                TableName=self.metrics_table_name,
                KeySchema=[
                    {
                        'AttributeName': 'date',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'userId',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'date',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'userId',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Wait for table to be created
            table.wait_until_exists()
            
            logger.info(f"Created metrics table {self.metrics_table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create metrics table: {str(e)}")
            raise DynamoDBError(f"Failed to create metrics table: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on database connections and tables.
        
        Returns:
            Dictionary with health check results
        """
        health_status = {
            'database_connection': False,
            'sessions_table': False,
            'metrics_table': False,
            'errors': []
        }
        
        try:
            # Test database connection
            self.client.describe_limits()
            health_status['database_connection'] = True
            
            # Test sessions table
            try:
                self.sessions_table.load()
                health_status['sessions_table'] = True
            except Exception as e:
                health_status['errors'].append(f"Sessions table error: {str(e)}")
            
            # Test metrics table
            try:
                self.metrics_table.load()
                health_status['metrics_table'] = True
            except Exception as e:
                health_status['errors'].append(f"Metrics table error: {str(e)}")
                
        except Exception as e:
            health_status['errors'].append(f"Database connection error: {str(e)}")
        
        return health_status


# Utility functions for database operations

def get_database_instance() -> FitnessCoachDatabase:
    """
    Get a singleton instance of the database manager.
    
    Returns:
        FitnessCoachDatabase instance
    """
    if not hasattr(get_database_instance, '_instance'):
        get_database_instance._instance = FitnessCoachDatabase()
    return get_database_instance._instance


def convert_decimal_to_float(obj: Any) -> Any:
    """
    Recursively convert Decimal objects to float for JSON serialization.
    
    Args:
        obj: Object that may contain Decimal values
        
    Returns:
        Object with Decimals converted to floats
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimal_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    else:
        return obj


def convert_float_to_decimal(obj: Any) -> Any:
    """
    Recursively convert float objects to Decimal for DynamoDB storage.
    
    Args:
        obj: Object that may contain float values
        
    Returns:
        Object with floats converted to Decimals
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {key: convert_float_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_float_to_decimal(item) for item in obj]
    else:
        return obj