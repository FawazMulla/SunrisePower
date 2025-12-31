"""
Comprehensive error handling system for the Solar CRM Platform.
Provides centralized error handling, logging, and recovery mechanisms.
"""

import logging
import traceback
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from functools import wraps
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class ErrorSeverity:
    """Error severity levels for classification and handling."""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class ErrorCategory:
    """Error categories for better organization and handling."""
    EMAIL_PROCESSING = 'email_processing'
    API_INTEGRATION = 'api_integration'
    DATABASE = 'database'
    EXTERNAL_SERVICE = 'external_service'
    VALIDATION = 'validation'
    AUTHENTICATION = 'authentication'
    PERMISSION = 'permission'
    SYSTEM = 'system'


class ErrorHandler:
    """
    Centralized error handling system with logging, alerting, and recovery.
    """
    
    def __init__(self):
        self.error_counts = {}
        self.alert_thresholds = {
            ErrorSeverity.LOW: 50,      # 50 errors in 1 hour
            ErrorSeverity.MEDIUM: 20,   # 20 errors in 1 hour
            ErrorSeverity.HIGH: 10,     # 10 errors in 1 hour
            ErrorSeverity.CRITICAL: 3,  # 3 errors in 1 hour
        }
    
    def handle_error(self, 
                    error: Exception, 
                    category: str = ErrorCategory.SYSTEM,
                    severity: str = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None,
                    user_id: Optional[int] = None,
                    request_data: Optional[Dict[str, Any]] = None,
                    recovery_action: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Handle an error with comprehensive logging and alerting.
        
        Args:
            error: The exception that occurred
            category: Error category for classification
            severity: Error severity level
            context: Additional context information
            user_id: ID of the user associated with the error
            request_data: Request data that caused the error
            recovery_action: Optional recovery function to execute
            
        Returns:
            Dict containing error information and recovery status
        """
        error_id = self._generate_error_id()
        timestamp = datetime.now()
        
        # Prepare error information
        error_info = {
            'error_id': error_id,
            'timestamp': timestamp,
            'category': category,
            'severity': severity,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'user_id': user_id,
            'request_data': request_data or {},
            'recovery_attempted': False,
            'recovery_successful': False
        }
        
        # Log the error
        self._log_error(error_info)
        
        # Store error in database
        self._store_error(error_info)
        
        # Check if alerting is needed
        self._check_alert_thresholds(category, severity)
        
        # Attempt recovery if provided
        if recovery_action:
            try:
                recovery_result = recovery_action()
                error_info['recovery_attempted'] = True
                error_info['recovery_successful'] = True
                error_info['recovery_result'] = recovery_result
                logger.info(f"Recovery successful for error {error_id}")
            except Exception as recovery_error:
                error_info['recovery_attempted'] = True
                error_info['recovery_successful'] = False
                error_info['recovery_error'] = str(recovery_error)
                logger.error(f"Recovery failed for error {error_id}: {recovery_error}")
        
        return error_info
    
    def _generate_error_id(self) -> str:
        """Generate a unique error ID."""
        import uuid
        return f"ERR_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    
    def _log_error(self, error_info: Dict[str, Any]) -> None:
        """Log error information with appropriate level."""
        severity = error_info['severity']
        error_id = error_info['error_id']
        message = f"[{error_id}] {error_info['error_type']}: {error_info['error_message']}"
        
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(message, extra=error_info)
        elif severity == ErrorSeverity.HIGH:
            logger.error(message, extra=error_info)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(message, extra=error_info)
        else:
            logger.info(message, extra=error_info)
    
    def _store_error(self, error_info: Dict[str, Any]) -> None:
        """Store error information in database."""
        try:
            from .models import ErrorLog
            from django.utils import timezone
            
            ErrorLog.objects.create(
                error_id=error_info['error_id'],
                category=error_info['category'],
                severity=error_info['severity'],
                error_type=error_info['error_type'],
                error_message=error_info['error_message'],
                traceback=error_info['traceback'],
                context=error_info['context'],
                user_id=error_info['user_id'],
                request_data=error_info.get('request_data', {}),
                recovery_attempted=error_info['recovery_attempted'],
                recovery_successful=error_info['recovery_successful'],
                timestamp=timezone.make_aware(error_info['timestamp']) if timezone.is_naive(error_info['timestamp']) else error_info['timestamp']
            )
        except Exception as e:
            # If we can't store the error, at least log it
            logger.error(f"Failed to store error in database: {e}")
    
    def _check_alert_thresholds(self, category: str, severity: str) -> None:
        """Check if error count exceeds alert thresholds."""
        cache_key = f"error_count_{category}_{severity}"
        current_count = cache.get(cache_key, 0) + 1
        
        # Store count with 1-hour expiry
        cache.set(cache_key, current_count, 3600)
        
        threshold = self.alert_thresholds.get(severity, 10)
        
        if current_count >= threshold:
            self._send_alert(category, severity, current_count, threshold)
    
    def _send_alert(self, category: str, severity: str, count: int, threshold: int) -> None:
        """Send alert notification for high error rates."""
        try:
            subject = f"[Solar CRM Alert] High Error Rate - {severity.upper()} - {category}"
            message = f"""
            High error rate detected in Solar CRM Platform:
            
            Category: {category}
            Severity: {severity}
            Error Count: {count} (Threshold: {threshold})
            Time Window: Last 1 hour
            Timestamp: {datetime.now()}
            
            Please investigate immediately.
            """
            
            # Send email alert (if configured)
            admin_emails = getattr(settings, 'ADMIN_EMAILS', [])
            if admin_emails:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=True
                )
            
            logger.critical(f"Alert sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")


class RetryHandler:
    """
    Handles retry logic with exponential backoff and circuit breaker pattern.
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.circuit_breaker_threshold = 5  # Failures before opening circuit
        self.circuit_breaker_timeout = 300  # 5 minutes
    
    def retry_with_backoff(self, 
                          func: Callable, 
                          *args, 
                          retry_on: tuple = (Exception,),
                          **kwargs) -> Any:
        """
        Execute function with exponential backoff retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            retry_on: Tuple of exceptions to retry on
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except retry_on as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    # Final attempt failed
                    break
                
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                
                logger.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay} seconds..."
                )
                
                time.sleep(delay)
        
        # All retries failed
        raise last_exception
    
    def circuit_breaker(self, service_name: str):
        """
        Circuit breaker decorator to prevent cascading failures.
        
        Args:
            service_name: Name of the service for circuit breaker tracking
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key_failures = f"circuit_breaker_failures_{service_name}"
                cache_key_last_failure = f"circuit_breaker_last_failure_{service_name}"
                
                # Check if circuit is open
                failures = cache.get(cache_key_failures, 0)
                last_failure = cache.get(cache_key_last_failure)
                
                if failures >= self.circuit_breaker_threshold:
                    if last_failure and (datetime.now() - last_failure).seconds < self.circuit_breaker_timeout:
                        raise Exception(f"Circuit breaker open for {service_name}")
                    else:
                        # Reset circuit breaker after timeout
                        cache.delete(cache_key_failures)
                        cache.delete(cache_key_last_failure)
                
                try:
                    result = func(*args, **kwargs)
                    # Success - reset failure count
                    cache.delete(cache_key_failures)
                    cache.delete(cache_key_last_failure)
                    return result
                except Exception as e:
                    # Failure - increment counter
                    cache.set(cache_key_failures, failures + 1, 3600)
                    cache.set(cache_key_last_failure, datetime.now(), 3600)
                    raise e
            
            return wrapper
        return decorator


# Global error handler instance
error_handler = ErrorHandler()
retry_handler = RetryHandler()


def handle_api_error(func):
    """
    Decorator for API views to handle errors gracefully.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Extract request information if available
            request = None
            user_id = None
            request_data = None
            
            if args and hasattr(args[0], 'user'):
                request = args[0]
                user_id = request.user.id if request.user.is_authenticated else None
                request_data = {
                    'method': request.method,
                    'path': request.path,
                    'data': getattr(request, 'data', {}),
                    'params': dict(request.GET)
                }
            
            # Determine error category and severity
            category = ErrorCategory.API_INTEGRATION
            severity = ErrorSeverity.MEDIUM
            
            if isinstance(e, (PermissionError, PermissionDenied)):
                category = ErrorCategory.PERMISSION
                severity = ErrorSeverity.LOW
            elif 'database' in str(e).lower() or 'connection' in str(e).lower():
                category = ErrorCategory.DATABASE
                severity = ErrorSeverity.HIGH
            elif 'validation' in str(e).lower():
                category = ErrorCategory.VALIDATION
                severity = ErrorSeverity.LOW
            
            # Handle the error
            error_info = error_handler.handle_error(
                error=e,
                category=category,
                severity=severity,
                user_id=user_id,
                request_data=request_data,
                context={'function': func.__name__}
            )
            
            # Return appropriate API response
            return Response(
                {
                    'error': 'An error occurred while processing your request',
                    'error_id': error_info['error_id'],
                    'message': str(e) if settings.DEBUG else 'Internal server error'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return wrapper


def handle_email_processing_error(func):
    """
    Decorator specifically for email processing functions.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Handle email processing errors with specific recovery
            def recovery_action():
                # Store raw email for manual processing
                email_data = kwargs.get('email_data') or (args[0] if args else {})
                from .models import EmailLog
                
                EmailLog.objects.create(
                    email_id=email_data.get('email_id', 'unknown'),
                    sender_email=email_data.get('sender_email', ''),
                    subject=email_data.get('subject', ''),
                    raw_content=str(email_data),
                    processing_status='manual_review',
                    processing_notes=f'Auto-processing failed: {str(e)}',
                    confidence_score=0.0
                )
                return 'Email stored for manual review'
            
            error_info = error_handler.handle_error(
                error=e,
                category=ErrorCategory.EMAIL_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                context={'function': func.__name__, 'email_data': kwargs.get('email_data')},
                recovery_action=recovery_action
            )
            
            # Return processing result with error information
            return {
                'processed': False,
                'error': str(e),
                'error_id': error_info['error_id'],
                'recovery_attempted': error_info['recovery_attempted'],
                'recovery_successful': error_info['recovery_successful']
            }
    
    return wrapper


def graceful_degradation(fallback_func: Callable = None):
    """
    Decorator to provide graceful degradation when services fail.
    
    Args:
        fallback_func: Function to call if main function fails
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Service {func.__name__} failed, attempting graceful degradation: {e}")
                
                if fallback_func:
                    try:
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback function also failed: {fallback_error}")
                
                # Return a safe default response
                return {
                    'status': 'degraded',
                    'message': 'Service temporarily unavailable',
                    'error': str(e) if settings.DEBUG else None
                }
        
        return wrapper
    return decorator


# Utility functions for common error scenarios

def safe_database_operation(operation: Callable, *args, **kwargs) -> Dict[str, Any]:
    """
    Safely execute database operations with error handling and retry logic.
    """
    try:
        with transaction.atomic():
            result = retry_handler.retry_with_backoff(
                operation,
                *args,
                retry_on=(Exception,),
                **kwargs
            )
            return {'success': True, 'result': result}
    except Exception as e:
        error_info = error_handler.handle_error(
            error=e,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            context={'operation': operation.__name__ if hasattr(operation, '__name__') else str(operation)}
        )
        return {
            'success': False,
            'error': str(e),
            'error_id': error_info['error_id']
        }


def safe_external_api_call(api_func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """
    Safely call external APIs with circuit breaker and retry logic.
    """
    service_name = kwargs.pop('service_name', 'external_api')
    
    @retry_handler.circuit_breaker(service_name)
    def protected_api_call():
        return retry_handler.retry_with_backoff(
            api_func,
            *args,
            retry_on=(ConnectionError, TimeoutError, Exception),
            **kwargs
        )
    
    try:
        result = protected_api_call()
        return {'success': True, 'result': result}
    except Exception as e:
        error_info = error_handler.handle_error(
            error=e,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            context={'service': service_name, 'function': api_func.__name__ if hasattr(api_func, '__name__') else str(api_func)}
        )
        return {
            'success': False,
            'error': str(e),
            'error_id': error_info['error_id']
        }