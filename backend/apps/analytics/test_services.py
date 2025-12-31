"""
Tests for analytics services.
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .services import AnalyticsService
from ..leads.models import Lead, LeadSource
from ..customers.models import Customer
from ..services.models import ServiceRequest, InstallationProject


class AnalyticsServiceTest(TestCase):
    """Test analytics service functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.service = AnalyticsService()
        
        # Create test lead source
        self.source = LeadSource.objects.create(
            name='Website',
            description='Website inquiries'
        )
    
    def test_real_time_metrics(self):
        """Test real-time metrics calculation."""
        metrics = self.service.get_real_time_metrics()
        
        # Should return expected metrics
        expected_keys = [
            'current_leads',
            'open_service_requests',
            'active_projects',
            'total_customers',
            'high_priority_leads',
            'overdue_service_requests',
            'updated_at'
        ]
        
        for key in expected_keys:
            self.assertIn(key, metrics)
        
        # All counts should be non-negative integers
        for key in expected_keys[:-1]:  # Exclude updated_at
            self.assertGreaterEqual(metrics[key], 0)
            self.assertIsInstance(metrics[key], int)
    
    def test_lead_metrics_calculation(self):
        """Test lead metrics calculation."""
        # Create test leads
        leads = []
        for i in range(5):
            lead = Lead.objects.create(
                first_name=f'Test{i}',
                last_name='User',
                email=f'test{i}@example.com',
                phone=f'+9198765432{i}0',
                source=self.source,
                status='new' if i < 3 else 'qualified'
            )
            leads.append(lead)
        
        # Calculate metrics for recent period
        period_start = timezone.now() - timedelta(days=30)
        metrics = self.service._calculate_lead_metrics(period_start)
        
        # Should have correct counts
        self.assertEqual(metrics['total_leads'], 5)
        self.assertEqual(metrics['new_leads'], 3)
        self.assertEqual(metrics['qualified_leads'], 2)
        self.assertGreaterEqual(metrics['avg_lead_score'], 0)
        self.assertGreater(metrics['lead_velocity'], 0)
    
    def test_conversion_metrics_calculation(self):
        """Test conversion metrics calculation."""
        # Create leads with different statuses
        Lead.objects.create(
            first_name='New',
            last_name='Lead',
            email='new@example.com',
            phone='+919876543210',
            source=self.source,
            status='new'
        )
        
        converted_lead = Lead.objects.create(
            first_name='Converted',
            last_name='Lead',
            email='converted@example.com',
            phone='+919876543211',
            source=self.source,
            status='converted',
            converted_at=timezone.now()
        )
        
        period_start = timezone.now() - timedelta(days=30)
        metrics = self.service._calculate_conversion_metrics(period_start)
        
        # Should calculate conversion rate
        self.assertEqual(metrics['total_leads'], 2)
        self.assertEqual(metrics['converted_leads'], 1)
        self.assertEqual(metrics['overall_conversion_rate'], 50.0)
        self.assertGreaterEqual(metrics['avg_conversion_time_days'], 0)
    
    def test_service_metrics_calculation(self):
        """Test service metrics calculation."""
        # Create test customer first
        lead = Lead.objects.create(
            first_name='Test',
            last_name='Customer',
            email='customer@example.com',
            phone='+919876543210',
            source=self.source,
            status='converted'
        )
        
        customer = Customer.objects.create(
            lead=lead,
            address='Test Address',
            city='Test City',
            state='Test State',
            pincode='123456'
        )
        
        # Create service requests
        ServiceRequest.objects.create(
            ticket_number='SR001',
            customer=customer,
            request_type='maintenance',
            priority='medium',
            subject='Test Request',
            description='Test Description',
            status='open'
        )
        
        ServiceRequest.objects.create(
            ticket_number='SR002',
            customer=customer,
            request_type='repair',
            priority='high',
            subject='Test Request 2',
            description='Test Description 2',
            status='resolved',
            resolved_at=timezone.now()
        )
        
        period_start = timezone.now() - timedelta(days=30)
        metrics = self.service._calculate_service_metrics(period_start)
        
        # Should have correct counts
        self.assertEqual(metrics['total_requests'], 2)
        self.assertEqual(metrics['open_requests'], 1)
        self.assertEqual(metrics['closed_requests'], 1)
        self.assertEqual(metrics['resolution_rate'], 50.0)
    
    def test_dashboard_metrics_calculation(self):
        """Test full dashboard metrics calculation."""
        # Create some test data
        Lead.objects.create(
            first_name='Test',
            last_name='Lead',
            email='test@example.com',
            phone='+919876543210',
            source=self.source
        )
        
        # Calculate dashboard metrics
        metrics = self.service.calculate_dashboard_metrics(30)
        
        # Should have all expected sections
        expected_sections = [
            'lead_metrics',
            'conversion_metrics',
            'revenue_metrics',
            'service_metrics',
            'performance_indicators',
            'trending_data',
            'calculated_at',
            'period_days'
        ]
        
        for section in expected_sections:
            self.assertIn(section, metrics)
        
        # Should have valid period info
        self.assertEqual(metrics['period_days'], 30)
        self.assertIsInstance(metrics['calculated_at'], timezone.datetime)
    
    def test_comparative_analysis(self):
        """Test comparative analysis calculation."""
        # Create leads in different periods
        now = timezone.now()
        
        # Current period lead
        Lead.objects.create(
            first_name='Current',
            last_name='Lead',
            email='current@example.com',
            phone='+919876543210',
            source=self.source,
            created_at=now - timedelta(days=15)
        )
        
        # Previous period lead
        Lead.objects.create(
            first_name='Previous',
            last_name='Lead',
            email='previous@example.com',
            phone='+919876543211',
            source=self.source,
            created_at=now - timedelta(days=45)
        )
        
        # Generate comparative analysis
        analysis = self.service.generate_comparative_analysis(30, 30)
        
        # Should have comparison data
        self.assertIn('current_period', analysis)
        self.assertIn('previous_period', analysis)
        self.assertIn('changes', analysis)
        self.assertIn('period_info', analysis)
        
        # Should have lead counts
        self.assertEqual(analysis['current_period']['leads'], 1)
        self.assertEqual(analysis['previous_period']['leads'], 1)
    
    def test_fallback_metrics(self):
        """Test fallback metrics when calculation fails."""
        fallback = self.service._get_fallback_metrics()
        
        # Should have all required sections with zero values
        self.assertIn('lead_metrics', fallback)
        self.assertIn('conversion_metrics', fallback)
        self.assertIn('revenue_metrics', fallback)
        self.assertIn('service_metrics', fallback)
        self.assertIn('error', fallback)
        
        # All metrics should be zero or empty
        self.assertEqual(fallback['lead_metrics']['total_leads'], 0)
        self.assertEqual(fallback['conversion_metrics']['overall_conversion_rate'], 0)
        self.assertEqual(fallback['revenue_metrics']['actual_revenue'], 0)