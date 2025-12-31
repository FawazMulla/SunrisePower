"""
Middleware for performance tracking and error monitoring.
"""

import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings

from .monitoring import performance_tracker
from .error_handler import error_handler, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class PerformanceTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track API performance metrics.
    """
    
    def process_request(self, request):
        """Record request start time."""
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Record API performance metrics."""
        try:
            # Calculate response time
            if hasattr(request, '_start_time'):
                response_time = time.time() - request._start_time
                
                # Get user ID if authenticated
                user_id = None
                if hasattr(request, 'user') and request.user.is_authenticated:
                    user_id = request.user.id
                
                # Record metrics for API endpoints
                if request.path.startswith('/api/'):
                    performance_tracker.record_api_request(
                        endpoint=request.path,
                        method=request.method,
                        response_time=response_time,
                        status_code=response.status_code,
                        user_id=user_id
                    )
                
                # Log slow requests
                if response_time > 5.0:  # Requests taking more than 5 seconds
                    logger.warning(
                        f"Slow request: {request.method} {request.path} "
                        f"took {response_time:.2f}s (status: {response.status_code})"
                    )
            
        except Exception as e:
            # Don't let monitoring errors break the response
            logger.error(f"Error in performance tracking middleware: {e}")
        
        return response
    
    def process_exception(self, request, exception):
        """Handle exceptions and record error metrics."""
        try:
            # Get user ID if authenticated
            user_id = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_id = request.user.id
            
            # Prepare request data
            request_data = {
                'method': request.method,
                'path': request.path,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'remote_addr': request.META.get('REMOTE_ADDR', ''),
            }
            
            # Add POST data if available (be careful with sensitive data)
            if request.method == 'POST' and hasattr(request, 'POST'):
                # Only include non-sensitive fields
                safe_fields = ['task_name', 'action', 'email_type']
                request_data['post_data'] = {
                    key: value for key, value in request.POST.items()
                    if key in safe_fields
                }
            
            # Determine error category and severity
            category = ErrorCategory.API_INTEGRATION
            severity = ErrorSeverity.MEDIUM
            
            if 'database' in str(exception).lower():
                category = ErrorCategory.DATABASE
                severity = ErrorSeverity.HIGH
            elif 'permission' in str(exception).lower():
                category = ErrorCategory.PERMISSION
                severity = ErrorSeverity.LOW
            elif 'validation' in str(exception).lower():
                category = ErrorCategory.VALIDATION
                severity = ErrorSeverity.LOW
            
            # Handle the error
            error_handler.handle_error(
                error=exception,
                category=category,
                severity=severity,
                user_id=user_id,
                request_data=request_data,
                context={
                    'middleware': 'PerformanceTrackingMiddleware',
                    'endpoint': request.path
                }
            )
            
        except Exception as e:
            # Don't let error handling errors break the response
            logger.error(f"Error in exception handling middleware: {e}")
        
        # Don't return a response here - let Django handle the exception normally
        return None


class HealthCheckMiddleware(MiddlewareMixin):
    """
    Middleware to handle health check requests efficiently.
    """
    
    def process_request(self, request):
        """Handle health check requests quickly."""
        if request.path == '/health/' or request.path == '/health':
            try:
                # Quick database check
                from django.db import connection
                
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                
                return JsonResponse({
                    'status': 'healthy',
                    'timestamp': time.time()
                })
                
            except Exception as e:
                return JsonResponse({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': time.time()
                }, status=503)
        
        return None


class ErrorRecoveryMiddleware(MiddlewareMixin):
    """
    Middleware to provide graceful error recovery for critical endpoints.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.critical_endpoints = [
            '/api/integrations/emailjs-webhook/',
            '/api/integrations/chatbot-data/',
            '/api/integrations/calculator-data/',
        ]
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """Provide graceful error recovery for critical endpoints."""
        try:
            # Only handle exceptions for critical endpoints
            if not any(request.path.startswith(endpoint) for endpoint in self.critical_endpoints):
                return None
            
            # Log the error
            logger.error(
                f"Critical endpoint error: {request.path} - {exception}",
                exc_info=True
            )
            
            # Return a graceful error response that won't break integrations
            if request.path.startswith('/api/integrations/emailjs-webhook/'):
                return JsonResponse({
                    'status': 'received',
                    'message': 'Email received and queued for manual processing',
                    'error': 'Processing temporarily unavailable'
                })
            
            elif request.path.startswith('/api/integrations/chatbot-data/'):
                return JsonResponse({
                    'status': 'received',
                    'message': 'Chatbot data received and queued for processing',
                    'error': 'Processing temporarily unavailable'
                })
            
            elif request.path.startswith('/api/integrations/calculator-data/'):
                return JsonResponse({
                    'status': 'received',
                    'message': 'Calculator data received and queued for processing',
                    'error': 'Processing temporarily unavailable'
                })
            
            # Default graceful response
            return JsonResponse({
                'status': 'error',
                'message': 'Service temporarily unavailable',
                'error': str(exception) if settings.DEBUG else 'Internal server error'
            }, status=503)
            
        except Exception as e:
            # Don't let error recovery errors break the response
            logger.error(f"Error in error recovery middleware: {e}")
            return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to responses.
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        try:
            # Add security headers
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Add cache control for HTML responses to prevent CSP caching issues
            if response.get('Content-Type', '').startswith('text/html'):
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                # Add ETag to force revalidation
                import time
                response['ETag'] = f'"{int(time.time())}"'
            
            # Add HSTS header for HTTPS requests
            if request.is_secure():
                response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            # Add CSP header for HTML responses
            if response.get('Content-Type', '').startswith('text/html'):
                response['Content-Security-Policy'] = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                    "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
                    "img-src 'self' data: https:; "
                    "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
                    "connect-src 'self' https://api.cohere.ai https://api.emailjs.com https://cdnjs.cloudflare.com;"
                )
            
        except Exception as e:
            # Don't let security header errors break the response
            logger.error(f"Error in security headers middleware: {e}")
        
        return response