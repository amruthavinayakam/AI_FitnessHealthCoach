"""
Structured logging utilities for Fitness Health Coach system
Implements requirements 6.6, 4.1, 4.2 for comprehensive monitoring and logging
"""
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import traceback

class StructuredLogger:
    """
    Structured logger with correlation IDs and standardized formatting
    """
    
    def __init__(self, service_name: str, logger_name: str = None):
        """
        Initialize structured logger
        
        Args:
            service_name: Name of the service (e.g., 'fitness-coach-handler')
            logger_name: Optional logger name, defaults to service_name
        """
        self.service_name = service_name
        self.logger = logging.getLogger(logger_name or service_name)
        
        # Configure logger if not already configured
        if not self.logger.handlers:
            self._configure_logger()
        
        # Get correlation ID from environment or generate new one
        self.correlation_id = os.getenv('CORRELATION_ID', str(uuid.uuid4()))
    
    def _configure_logger(self):
        """Configure logger with structured formatting"""
        # Set log level from environment
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Create structured formatter
        formatter = StructuredFormatter(self.service_name)
        
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
        self.logger.propagate = False
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracking"""
        self.correlation_id = correlation_id
        os.environ['CORRELATION_ID'] = correlation_id
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        self._log(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with structured data"""
        extra_data = {
            'correlation_id': self.correlation_id,
            'service': self.service_name,
            'timestamp': datetime.utcnow().isoformat(),
            **kwargs
        }
        
        # Add exception info if available
        if 'exception' in kwargs:
            extra_data['exception_type'] = type(kwargs['exception']).__name__
            extra_data['exception_message'] = str(kwargs['exception'])
            extra_data['stack_trace'] = traceback.format_exc()
        
        self.logger.log(level, message, extra=extra_data)

class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logging
    """
    
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'service': self.service_name,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields from the record
        if hasattr(record, 'correlation_id'):
            log_entry['correlation_id'] = record.correlation_id
        
        # Add any additional structured data
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)

def log_function_call(logger: StructuredLogger):
    """
    Decorator to log function entry and exit with performance metrics
    
    Args:
        logger: StructuredLogger instance
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            function_name = func.__name__
            
            # Log function entry
            logger.debug(
                f"Entering function: {function_name}",
                function=function_name,
                event_type="function_entry",
                args_count=len(args),
                kwargs_keys=list(kwargs.keys())
            )
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Calculate execution time
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds()
                
                # Log successful exit
                logger.debug(
                    f"Exiting function: {function_name}",
                    function=function_name,
                    event_type="function_exit",
                    execution_time_seconds=execution_time,
                    success=True
                )
                
                return result
                
            except Exception as e:
                # Calculate execution time for failed calls
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds()
                
                # Log error exit
                logger.error(
                    f"Function {function_name} failed",
                    function=function_name,
                    event_type="function_error",
                    execution_time_seconds=execution_time,
                    success=False,
                    exception=e
                )
                
                raise
        
        return wrapper
    return decorator

def log_api_request(logger: StructuredLogger):
    """
    Decorator to log API request details and performance
    
    Args:
        logger: StructuredLogger instance
    """
    def decorator(func):
        @wraps(func)
        def wrapper(event, context, *args, **kwargs):
            start_time = datetime.utcnow()
            request_id = context.aws_request_id if context else str(uuid.uuid4())
            
            # Set correlation ID
            logger.set_correlation_id(request_id)
            
            # Extract request details
            http_method = event.get('httpMethod', 'UNKNOWN')
            path = event.get('path', 'UNKNOWN')
            source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'UNKNOWN')
            user_agent = event.get('headers', {}).get('User-Agent', 'UNKNOWN')
            
            # Log request start
            logger.info(
                f"API request started: {http_method} {path}",
                event_type="api_request_start",
                request_id=request_id,
                http_method=http_method,
                path=path,
                source_ip=source_ip,
                user_agent=user_agent,
                lambda_request_id=context.aws_request_id if context else None
            )
            
            try:
                # Execute function
                result = func(event, context, *args, **kwargs)
                
                # Calculate execution time
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds()
                
                # Extract response details
                status_code = result.get('statusCode', 'UNKNOWN')
                success = status_code < 400 if isinstance(status_code, int) else False
                
                # Log request completion
                logger.info(
                    f"API request completed: {http_method} {path}",
                    event_type="api_request_complete",
                    request_id=request_id,
                    status_code=status_code,
                    execution_time_seconds=execution_time,
                    success=success
                )
                
                return result
                
            except Exception as e:
                # Calculate execution time for failed requests
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds()
                
                # Log request error
                logger.error(
                    f"API request failed: {http_method} {path}",
                    event_type="api_request_error",
                    request_id=request_id,
                    execution_time_seconds=execution_time,
                    success=False,
                    exception=e
                )
                
                raise
        
        return wrapper
    return decorator

def log_external_service_call(service_name: str, logger: StructuredLogger):
    """
    Decorator to log external service calls (Bedrock, Spoonacular, etc.)
    
    Args:
        service_name: Name of the external service
        logger: StructuredLogger instance
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            call_id = str(uuid.uuid4())
            
            # Log service call start
            logger.info(
                f"External service call started: {service_name}",
                event_type="external_service_call_start",
                service_name=service_name,
                call_id=call_id,
                function=func.__name__
            )
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Calculate execution time
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds()
                
                # Determine success based on result
                success = True
                if isinstance(result, dict):
                    success = result.get('success', True)
                
                # Log service call completion
                logger.info(
                    f"External service call completed: {service_name}",
                    event_type="external_service_call_complete",
                    service_name=service_name,
                    call_id=call_id,
                    execution_time_seconds=execution_time,
                    success=success
                )
                
                return result
                
            except Exception as e:
                # Calculate execution time for failed calls
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds()
                
                # Log service call error
                logger.error(
                    f"External service call failed: {service_name}",
                    event_type="external_service_call_error",
                    service_name=service_name,
                    call_id=call_id,
                    execution_time_seconds=execution_time,
                    success=False,
                    exception=e
                )
                
                raise
        
        return wrapper
    return decorator

# Global logger instances for different services
def get_logger(service_name: str) -> StructuredLogger:
    """
    Get or create a structured logger for a service
    
    Args:
        service_name: Name of the service
        
    Returns:
        StructuredLogger: Configured logger instance
    """
    return StructuredLogger(service_name)

# Convenience functions for common logging patterns
def log_performance_metric(logger: StructuredLogger, metric_name: str, 
                          value: float, unit: str = 'seconds', **kwargs):
    """
    Log a performance metric
    
    Args:
        logger: StructuredLogger instance
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        **kwargs: Additional metadata
    """
    logger.info(
        f"Performance metric: {metric_name}",
        event_type="performance_metric",
        metric_name=metric_name,
        metric_value=value,
        metric_unit=unit,
        **kwargs
    )

def log_business_event(logger: StructuredLogger, event_name: str, 
                      user_id: str = None, **kwargs):
    """
    Log a business event
    
    Args:
        logger: StructuredLogger instance
        event_name: Name of the business event
        user_id: Optional user identifier
        **kwargs: Additional event data
    """
    logger.info(
        f"Business event: {event_name}",
        event_type="business_event",
        business_event=event_name,
        user_id=user_id,
        **kwargs
    )

def log_security_event(logger: StructuredLogger, event_type: str, 
                      severity: str = 'medium', **kwargs):
    """
    Log a security-related event
    
    Args:
        logger: StructuredLogger instance
        event_type: Type of security event
        severity: Severity level (low, medium, high, critical)
        **kwargs: Additional security context
    """
    logger.warning(
        f"Security event: {event_type}",
        event_type="security_event",
        security_event_type=event_type,
        severity=severity,
        **kwargs
    )