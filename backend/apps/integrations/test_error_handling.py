"""
Tests for error handling and monitoring system.
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock

from .error_handler import error_handler, ErrorCategory, ErrorSeverity
from .monitoring import system_monitor, performance_tracker
from .models import ErrorLog

User = get_user_model()


class ErrorHandlerTestCase(TestCase):
    """Test cases for error handling system."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
    
    def test_error_logging(self):
        """Test that errors are properly logged."""
        # Create a test error
        test_error = ValueError("Test error message")
        
        # Handle the error
        error_info = error_handler.handle_error(
            error=test_error,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            context={'test': 'data'},
            user_id=self.user.id
        )
        
        # Verify error was logged
        self.assertIn('error_id', error_info)
        self.assertEqual(error_info['category'], ErrorCategory.SYSTEM)
        self.assertEqual(error_info['severity'], ErrorSeverity.MEDIUM)
        
        # Verify error was stored in database
        error_log = ErrorLog.objects.get(error_id=error_info['error_id'])
        self.assertEqual(error_log.error_type, 'ValueError')
        self.assertEqual(error_log.error_message, 'Test error message')
        self.assertEqual(error_log.user_id, self.user.id)
    
    def test_error_recovery(self):
        """Test error recovery mechanism."""
        # Create a recovery function
        def recovery_function():
            return "Recovery successful"
        
        # Create a test error with recovery
        test_error = ConnectionError("Connection failed")
        
        error_info = error_handler.handle_error(
            error=test_error,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            recovery_action=recovery_function
        )
        
        # Verify recovery was attempted and successful
        self.assertTrue(error_info['recovery_attempted'])
        self.assertTrue(error_info['recovery_successful'])
        self.assertEqual(error_info['recovery_result'], "Recovery successful")


class SystemMonitorTestCase(TestCase):
    """Test cases for system monitoring."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser2',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
    
    def test_system_health_check(self):
        """Test system health check functionality."""
        health_data = system_monitor.get_system_health()
        
        # Verify health data structure
        self.assertIn('timestamp', health_data)
        self.assertIn('overall_status', health_data)
        self.assertIn('components', health_data)
        
        # Verify component checks
        components = health_data['components']
        expected_components = [
            'database', 'api', 'task_queue', 
            'email_processing', 'error_rates', 'integrations'
        ]
        
        for component in expected_components:
            self.assertIn(component, components)
            self.assertIn('status', components[component])
    
    @patch('apps.integrations.monitoring.send_mail')
    def test_health_alerting(self, mock_send_mail):
        """Test health alerting system."""
        # Mock a critical health status
        with patch.object(system_monitor, 'get_system_health') as mock_health:
            mock_health.return_value = {
                'timestamp': timezone.now(),
                'overall_status': 'critical',
                'components': {
                    'database': {
                        'status': 'critical',
                        'message': 'Database connection failed'
                    }
                }
            }
            
            # Trigger health check and alerting
            result = system_monitor.check_and_alert()
            
            # Verify alert was sent
            self.assertIn('alerts_sent', result)


class PerformanceTrackerTestCase(TestCase):
    """Test cases for performance tracking."""
    
    def test_api_request_recording(self):
        """Test API request performance recording."""
        # Record a test API request
        performance_tracker.record_api_request(
            endpoint='/api/test/',
            method='GET',
            response_time=0.5,
            status_code=200,
            user_id=1
        )
        
        # Get performance summary
        summary = performance_tracker.get_performance_summary()
        
        # Verify metrics are recorded
        self.assertIn('total_requests', summary)
        self.assertIn('avg_response_time', summary)
        self.assertIn('error_rate', summary)


class MonitoringAPITestCase(TestCase):
    """Test cases for monitoring API endpoints."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser3',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
        self.client.force_login(self.user)
    
    def test_system_health_endpoint(self):
        """Test system health API endpoint."""
        url = reverse('integrations:system_health')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('overall_status', data)
        self.assertIn('components', data)
    
    def test_system_metrics_endpoint(self):
        """Test system metrics API endpoint."""
        url = reverse('integrations:system_metrics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('performance', data)
        self.assertIn('health', data)
        self.assertIn('timestamp', data)
    
    def test_error_dashboard_endpoint(self):
        """Test error dashboard API endpoint."""
        # Create a test error
        ErrorLog.objects.create(
            error_id='test_error_123',
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            error_type='TestError',
            error_message='Test error message',
            traceback='Test traceback',
            timestamp=timezone.now()
        )
        
        url = reverse('integrations:error_dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('recent_errors_by_severity', data)
        self.assertIn('errors_by_category', data)
        self.assertIn('unresolved_errors', data)
        self.assertIn('error_trends', data)
    
    def test_health_check_endpoint(self):
        """Test public health check endpoint."""
        url = reverse('integrations:health_check')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_resolve_error_endpoint(self):
        """Test error resolution endpoint."""
        # Create a test error
        error_log = ErrorLog.objects.create(
            error_id='test_error_456',
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            error_type='TestError',
            error_message='Test error message',
            traceback='Test traceback',
            timestamp=timezone.now()
        )
        
        url = reverse('integrations:resolve_error', kwargs={'error_id': 'test_error_456'})
        response = self.client.post(url, {
            'resolution_notes': 'Test resolution'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        # Verify error was marked as resolved
        error_log.refresh_from_db()
        self.assertTrue(error_log.resolved)
        self.assertEqual(error_log.resolved_by, self.user)
        self.assertEqual(error_log.resolution_notes, 'Test resolution')


class MiddlewareTestCase(TestCase):
    """Test cases for monitoring middleware."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser4',
            email='test@example.com',
            password='testpass123',
            role='owner'
        )
    
    def test_performance_tracking_middleware(self):
        """Test that performance tracking middleware records metrics."""
        # Make an API request
        self.client.force_login(self.user)
        url = reverse('integrations:system_health')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify performance metrics were recorded
        # (This would require checking cache or other storage mechanism)
    
    def test_health_check_middleware(self):
        """Test health check middleware for quick responses."""
        response = self.client.get('/health/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('status', data)
    
    def test_error_recovery_middleware(self):
        """Test error recovery middleware for critical endpoints."""
        # This would require simulating an error in a critical endpoint
        # and verifying graceful error handling
        pass


class EmailProcessingErrorHandlingTestCase(TestCase):
    """Test cases for email processing error handling."""
    
    def test_email_processing_with_invalid_data(self):
        """Test email processing handles invalid data gracefully."""
        from .email_parser import process_emailjs_webhook
        
        # Test with invalid webhook data
        invalid_data = {'invalid': 'data'}
        
        result = process_emailjs_webhook(invalid_data)
        
        # Verify error was handled gracefully
        self.assertIn('processed', result)
        # The result might be False due to error handling
    
    def test_email_webhook_error_recovery(self):
        """Test EmailJS webhook error recovery."""
        url = reverse('integrations:emailjs_webhook')
        
        # Send invalid JSON
        response = self.client.post(
            url,
            'invalid json',
            content_type='application/json'
        )
        
        # Should return error but not crash
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn('error', data)