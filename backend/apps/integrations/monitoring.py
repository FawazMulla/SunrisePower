"""
System monitoring and health check system for Solar CRM Platform.
Provides real-time monitoring, performance tracking, and automated alerting.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail

from .error_handler import error_handler, ErrorCategory, ErrorSeverity
from .models import ErrorLog, EmailLog, BackgroundTask

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health status constants."""
    HEALTHY = 'healthy'
    WARNING = 'warning'
    CRITICAL = 'critical'
    UNKNOWN = 'unknown'


class SystemMonitor:
    """
    Comprehensive system monitoring with health checks and performance tracking.
    """
    
    def __init__(self):
        self.health_thresholds = {
            'api_response_time': {
                'warning': 2.0,    # 2 seconds
                'critical': 5.0    # 5 seconds
            },
            'database_response_time': {
                'warning': 1.0,    # 1 second
                'critical': 3.0    # 3 seconds
            },
            'error_rate': {
                'warning': 0.05,   # 5% error rate
                'critical': 0.15   # 15% error rate
            },
            'queue_size': {
                'warning': 100,    # 100 pending tasks
                'critical': 500    # 500 pending tasks
            }
        }
        
        self.alert_cooldown = 300  # 5 minutes between alerts
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.
        
        Returns:
            Dict containing health status for all system components
        """
        try:
            health_data = {
                'timestamp': timezone.now(),
                'overall_status': HealthStatus.HEALTHY,
                'components': {}
            }
            
            # Check database health
            db_health = self._check_database_health()
            health_data['components']['database'] = db_health
            
            # Check API health
            api_health = self._check_api_health()
            health_data['components']['api'] = api_health
            
            # Check background task queue health
            queue_health = self._check_queue_health()
            health_data['components']['task_queue'] = queue_health
            
            # Check email processing health
            email_health = self._check_email_processing_health()
            health_data['components']['email_processing'] = email_health
            
            # Check error rates
            error_health = self._check_error_rates()
            health_data['components']['error_rates'] = error_health
            
            # Check external integrations
            integration_health = self._check_integration_health()
            health_data['components']['integrations'] = integration_health
            
            # Determine overall status
            component_statuses = [comp['status'] for comp in health_data['components'].values()]
            
            if HealthStatus.CRITICAL in component_statuses:
                health_data['overall_status'] = HealthStatus.CRITICAL
            elif HealthStatus.WARNING in component_statuses:
                health_data['overall_status'] = HealthStatus.WARNING
            else:
                health_data['overall_status'] = HealthStatus.HEALTHY
            
            # Cache health data
            cache.set('system_health', health_data, 60)  # Cache for 1 minute
            
            return health_data
            
        except Exception as e:
            error_handler.handle_error(
                error=e,
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                context={'function': 'get_system_health'}
            )
            
            return {
                'timestamp': timezone.now(),
                'overall_status': HealthStatus.UNKNOWN,
                'error': str(e),
                'components': {}
            }
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            
            # Test database connection with a simple query
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            response_time = time.time() - start_time
            
            # Check database performance metrics
            db_metrics = self._get_database_metrics()
            
            # Determine status based on response time
            if response_time > self.health_thresholds['database_response_time']['critical']:
                status = HealthStatus.CRITICAL
            elif response_time > self.health_thresholds['database_response_time']['warning']:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'response_time': response_time,
                'metrics': db_metrics,
                'message': f'Database responding in {response_time:.3f}s'
            }
            
        except Exception as e:
            return {
                'status': HealthStatus.CRITICAL,
                'error': str(e),
                'message': 'Database connection failed'
            }
    
    def _check_api_health(self) -> Dict[str, Any]:
        """Check API performance and availability."""
        try:
            # Get API performance metrics from cache
            api_metrics = self._get_api_metrics()
            
            avg_response_time = api_metrics.get('avg_response_time', 0)
            error_rate = api_metrics.get('error_rate', 0)
            
            # Determine status
            if (avg_response_time > self.health_thresholds['api_response_time']['critical'] or
                error_rate > self.health_thresholds['error_rate']['critical']):
                status = HealthStatus.CRITICAL
            elif (avg_response_time > self.health_thresholds['api_response_time']['warning'] or
                  error_rate > self.health_thresholds['error_rate']['warning']):
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'metrics': api_metrics,
                'message': f'API avg response time: {avg_response_time:.3f}s, error rate: {error_rate:.2%}'
            }
            
        except Exception as e:
            return {
                'status': HealthStatus.UNKNOWN,
                'error': str(e),
                'message': 'Unable to check API health'
            }
    
    def _check_queue_health(self) -> Dict[str, Any]:
        """Check background task queue health."""
        try:
            # Get queue metrics
            queue_metrics = self._get_queue_metrics()
            
            pending_tasks = queue_metrics.get('pending_tasks', 0)
            failed_tasks = queue_metrics.get('failed_tasks_last_hour', 0)
            
            # Determine status
            if pending_tasks > self.health_thresholds['queue_size']['critical']:
                status = HealthStatus.CRITICAL
            elif pending_tasks > self.health_thresholds['queue_size']['warning']:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'metrics': queue_metrics,
                'message': f'{pending_tasks} pending tasks, {failed_tasks} failed in last hour'
            }
            
        except Exception as e:
            return {
                'status': HealthStatus.UNKNOWN,
                'error': str(e),
                'message': 'Unable to check queue health'
            }
    
    def _check_email_processing_health(self) -> Dict[str, Any]:
        """Check email processing system health."""
        try:
            # Get email processing metrics
            email_metrics = self._get_email_processing_metrics()
            
            processing_rate = email_metrics.get('processing_rate', 1.0)
            failed_rate = email_metrics.get('failed_rate', 0.0)
            
            # Determine status
            if failed_rate > 0.2:  # More than 20% failure rate
                status = HealthStatus.CRITICAL
            elif failed_rate > 0.1:  # More than 10% failure rate
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'metrics': email_metrics,
                'message': f'Processing rate: {processing_rate:.1%}, failure rate: {failed_rate:.1%}'
            }
            
        except Exception as e:
            return {
                'status': HealthStatus.UNKNOWN,
                'error': str(e),
                'message': 'Unable to check email processing health'
            }
    
    def _check_error_rates(self) -> Dict[str, Any]:
        """Check system-wide error rates."""
        try:
            # Get error metrics from last hour
            error_metrics = self._get_error_metrics()
            
            total_errors = error_metrics.get('total_errors', 0)
            critical_errors = error_metrics.get('critical_errors', 0)
            
            # Determine status
            if critical_errors > 5:  # More than 5 critical errors in last hour
                status = HealthStatus.CRITICAL
            elif total_errors > 20:  # More than 20 total errors in last hour
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'metrics': error_metrics,
                'message': f'{total_errors} total errors, {critical_errors} critical in last hour'
            }
            
        except Exception as e:
            return {
                'status': HealthStatus.UNKNOWN,
                'error': str(e),
                'message': 'Unable to check error rates'
            }
    
    def _check_integration_health(self) -> Dict[str, Any]:
        """Check external integration health."""
        try:
            # Check EmailJS integration
            emailjs_status = self._check_emailjs_integration()
            
            # Check other integrations as needed
            integrations = {
                'emailjs': emailjs_status
            }
            
            # Determine overall integration status
            statuses = [integration['status'] for integration in integrations.values()]
            
            if HealthStatus.CRITICAL in statuses:
                status = HealthStatus.CRITICAL
            elif HealthStatus.WARNING in statuses:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'integrations': integrations,
                'message': 'Integration health checked'
            }
            
        except Exception as e:
            return {
                'status': HealthStatus.UNKNOWN,
                'error': str(e),
                'message': 'Unable to check integration health'
            }
    
    def _get_database_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        try:
            with connection.cursor() as cursor:
                # Get table sizes and counts
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_leads
                    FROM leads_lead
                """)
                lead_count = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_customers
                    FROM customers_customer
                """)
                customer_count = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_service_requests
                    FROM services_servicerequest
                """)
                service_request_count = cursor.fetchone()[0]
            
            return {
                'lead_count': lead_count,
                'customer_count': customer_count,
                'service_request_count': service_request_count,
                'connection_status': 'active'
            }
            
        except Exception as e:
            logger.warning(f"Error getting database metrics: {e}")
            return {'error': str(e)}
    
    def _get_api_metrics(self) -> Dict[str, Any]:
        """Get API performance metrics from cache."""
        # These would be populated by middleware or API monitoring
        return cache.get('api_metrics', {
            'avg_response_time': 0.5,
            'error_rate': 0.02,
            'requests_per_minute': 10,
            'active_sessions': 5
        })
    
    def _get_queue_metrics(self) -> Dict[str, Any]:
        """Get background task queue metrics."""
        try:
            from django.db.models import Count
            
            # Get task counts by status
            task_counts = BackgroundTask.objects.values('status').annotate(
                count=Count('id')
            )
            
            metrics = {status['status']: status['count'] for status in task_counts}
            
            # Get failed tasks in last hour
            one_hour_ago = timezone.now() - timedelta(hours=1)
            failed_last_hour = BackgroundTask.objects.filter(
                status='failed',
                updated_at__gte=one_hour_ago
            ).count()
            
            metrics.update({
                'pending_tasks': metrics.get('pending', 0),
                'failed_tasks_last_hour': failed_last_hour,
                'total_tasks': sum(metrics.values())
            })
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Error getting queue metrics: {e}")
            return {'error': str(e)}
    
    def _get_email_processing_metrics(self) -> Dict[str, Any]:
        """Get email processing metrics."""
        try:
            one_hour_ago = timezone.now() - timedelta(hours=1)
            
            # Get email processing stats from last hour
            total_emails = EmailLog.objects.filter(
                received_at__gte=one_hour_ago
            ).count()
            
            processed_emails = EmailLog.objects.filter(
                received_at__gte=one_hour_ago,
                processing_status='processed'
            ).count()
            
            failed_emails = EmailLog.objects.filter(
                received_at__gte=one_hour_ago,
                processing_status='failed'
            ).count()
            
            processing_rate = processed_emails / total_emails if total_emails > 0 else 1.0
            failed_rate = failed_emails / total_emails if total_emails > 0 else 0.0
            
            return {
                'total_emails': total_emails,
                'processed_emails': processed_emails,
                'failed_emails': failed_emails,
                'processing_rate': processing_rate,
                'failed_rate': failed_rate
            }
            
        except Exception as e:
            logger.warning(f"Error getting email processing metrics: {e}")
            return {'error': str(e)}
    
    def _get_error_metrics(self) -> Dict[str, Any]:
        """Get system error metrics."""
        try:
            one_hour_ago = timezone.now() - timedelta(hours=1)
            
            # Get error counts by severity
            total_errors = ErrorLog.objects.filter(
                timestamp__gte=one_hour_ago
            ).count()
            
            critical_errors = ErrorLog.objects.filter(
                timestamp__gte=one_hour_ago,
                severity='critical'
            ).count()
            
            high_errors = ErrorLog.objects.filter(
                timestamp__gte=one_hour_ago,
                severity='high'
            ).count()
            
            return {
                'total_errors': total_errors,
                'critical_errors': critical_errors,
                'high_errors': high_errors,
                'resolved_errors': ErrorLog.objects.filter(
                    timestamp__gte=one_hour_ago,
                    resolved=True
                ).count()
            }
            
        except Exception as e:
            logger.warning(f"Error getting error metrics: {e}")
            return {'error': str(e)}
    
    def _check_emailjs_integration(self) -> Dict[str, Any]:
        """Check EmailJS integration health."""
        try:
            # Check recent email processing success rate
            one_hour_ago = timezone.now() - timedelta(hours=1)
            
            recent_emails = EmailLog.objects.filter(
                received_at__gte=one_hour_ago
            ).count()
            
            if recent_emails == 0:
                return {
                    'status': HealthStatus.HEALTHY,
                    'message': 'No recent emails to process'
                }
            
            failed_emails = EmailLog.objects.filter(
                received_at__gte=one_hour_ago,
                processing_status='failed'
            ).count()
            
            failure_rate = failed_emails / recent_emails
            
            if failure_rate > 0.5:  # More than 50% failure rate
                status = HealthStatus.CRITICAL
            elif failure_rate > 0.2:  # More than 20% failure rate
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'recent_emails': recent_emails,
                'failed_emails': failed_emails,
                'failure_rate': failure_rate,
                'message': f'{recent_emails} emails, {failure_rate:.1%} failure rate'
            }
            
        except Exception as e:
            return {
                'status': HealthStatus.UNKNOWN,
                'error': str(e),
                'message': 'Unable to check EmailJS integration'
            }
    
    def check_and_alert(self) -> Dict[str, Any]:
        """
        Check system health and send alerts if necessary.
        
        Returns:
            Dict containing alert information
        """
        try:
            health_data = self.get_system_health()
            alerts_sent = []
            
            # Check if we need to send alerts
            if health_data['overall_status'] in [HealthStatus.CRITICAL, HealthStatus.WARNING]:
                alert_key = f"health_alert_{health_data['overall_status']}"
                
                # Check cooldown period
                last_alert = cache.get(alert_key)
                if not last_alert or (timezone.now() - last_alert).seconds > self.alert_cooldown:
                    
                    # Send alert
                    alert_sent = self._send_health_alert(health_data)
                    if alert_sent:
                        alerts_sent.append(alert_sent)
                        cache.set(alert_key, timezone.now(), self.alert_cooldown)
            
            return {
                'health_data': health_data,
                'alerts_sent': alerts_sent,
                'timestamp': timezone.now()
            }
            
        except Exception as e:
            error_handler.handle_error(
                error=e,
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                context={'function': 'check_and_alert'}
            )
            
            return {
                'error': str(e),
                'timestamp': timezone.now()
            }
    
    def _send_health_alert(self, health_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send health alert notification."""
        try:
            status = health_data['overall_status']
            timestamp = health_data['timestamp']
            
            # Prepare alert message
            subject = f"[Solar CRM Alert] System Health {status.upper()}"
            
            message_parts = [
                f"System health status: {status.upper()}",
                f"Timestamp: {timestamp}",
                "",
                "Component Status:"
            ]
            
            for component, data in health_data['components'].items():
                component_status = data.get('status', 'unknown')
                component_message = data.get('message', 'No details')
                message_parts.append(f"- {component}: {component_status} - {component_message}")
            
            message = "\n".join(message_parts)
            
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
            
            logger.critical(f"Health alert sent: {subject}")
            
            return {
                'type': 'health_alert',
                'status': status,
                'subject': subject,
                'recipients': admin_emails,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Failed to send health alert: {e}")
            return None


# Global system monitor instance
system_monitor = SystemMonitor()


class PerformanceTracker:
    """
    Track API performance metrics for monitoring.
    """
    
    def __init__(self):
        self.metrics_cache_timeout = 300  # 5 minutes
    
    def record_api_request(self, 
                          endpoint: str, 
                          method: str, 
                          response_time: float, 
                          status_code: int,
                          user_id: Optional[int] = None) -> None:
        """
        Record API request metrics.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            response_time: Response time in seconds
            status_code: HTTP status code
            user_id: ID of authenticated user
        """
        try:
            timestamp = timezone.now()
            
            # Store individual request data
            request_data = {
                'endpoint': endpoint,
                'method': method,
                'response_time': response_time,
                'status_code': status_code,
                'user_id': user_id,
                'timestamp': timestamp.isoformat()
            }
            
            # Add to recent requests list (keep last 100)
            recent_requests = cache.get('recent_api_requests', [])
            recent_requests.append(request_data)
            recent_requests = recent_requests[-100:]  # Keep only last 100
            cache.set('recent_api_requests', recent_requests, self.metrics_cache_timeout)
            
            # Update aggregated metrics
            self._update_aggregated_metrics(endpoint, method, response_time, status_code)
            
        except Exception as e:
            logger.warning(f"Error recording API request metrics: {e}")
    
    def _update_aggregated_metrics(self, 
                                  endpoint: str, 
                                  method: str, 
                                  response_time: float, 
                                  status_code: int) -> None:
        """Update aggregated API metrics."""
        try:
            # Get current metrics
            metrics = cache.get('api_metrics', {
                'total_requests': 0,
                'total_response_time': 0.0,
                'error_count': 0,
                'avg_response_time': 0.0,
                'error_rate': 0.0,
                'requests_per_minute': 0,
                'last_updated': timezone.now().isoformat()
            })
            
            # Update metrics
            metrics['total_requests'] += 1
            metrics['total_response_time'] += response_time
            metrics['avg_response_time'] = metrics['total_response_time'] / metrics['total_requests']
            
            if status_code >= 400:
                metrics['error_count'] += 1
            
            metrics['error_rate'] = metrics['error_count'] / metrics['total_requests']
            metrics['last_updated'] = timezone.now().isoformat()
            
            # Calculate requests per minute (approximate)
            metrics['requests_per_minute'] = min(metrics['total_requests'], 60)
            
            # Store updated metrics
            cache.set('api_metrics', metrics, self.metrics_cache_timeout)
            
        except Exception as e:
            logger.warning(f"Error updating aggregated metrics: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for dashboard."""
        try:
            metrics = cache.get('api_metrics', {})
            recent_requests = cache.get('recent_api_requests', [])
            
            # Calculate additional metrics from recent requests
            if recent_requests:
                recent_response_times = [req['response_time'] for req in recent_requests[-20:]]
                recent_avg = sum(recent_response_times) / len(recent_response_times)
                
                # Get slowest endpoints
                endpoint_times = {}
                for req in recent_requests[-50:]:
                    endpoint = req['endpoint']
                    if endpoint not in endpoint_times:
                        endpoint_times[endpoint] = []
                    endpoint_times[endpoint].append(req['response_time'])
                
                slowest_endpoints = []
                for endpoint, times in endpoint_times.items():
                    avg_time = sum(times) / len(times)
                    slowest_endpoints.append({
                        'endpoint': endpoint,
                        'avg_response_time': avg_time,
                        'request_count': len(times)
                    })
                
                slowest_endpoints.sort(key=lambda x: x['avg_response_time'], reverse=True)
                
                metrics.update({
                    'recent_avg_response_time': recent_avg,
                    'slowest_endpoints': slowest_endpoints[:5],
                    'recent_request_count': len(recent_requests)
                })
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Error getting performance summary: {e}")
            return {'error': str(e)}


# Global performance tracker instance
performance_tracker = PerformanceTracker()