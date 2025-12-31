"""
Management command to calculate and update analytics metrics.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
import logging

from ...services import AnalyticsService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Calculate and update analytics metrics for dashboard display'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--period-days',
            type=int,
            default=30,
            help='Number of days to calculate metrics for (default: 30)',
        )
        parser.add_argument(
            '--real-time-only',
            action='store_true',
            help='Only calculate real-time metrics (faster)',
        )
        parser.add_argument(
            '--comparative',
            action='store_true',
            help='Include comparative analysis with previous period',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output of calculated metrics',
        )
    
    def handle(self, *args, **options):
        try:
            start_time = timezone.now()
            service = AnalyticsService()
            
            self.stdout.write("Starting analytics calculation...")
            
            if options['real_time_only']:
                # Calculate only real-time metrics
                self.stdout.write("Calculating real-time metrics...")
                metrics = service.get_real_time_metrics()
                
                if options['verbose']:
                    self.stdout.write("Real-time metrics:")
                    for key, value in metrics.items():
                        self.stdout.write(f"  {key}: {value}")
                
            else:
                # Calculate full dashboard metrics
                period_days = options['period_days']
                self.stdout.write(f"Calculating dashboard metrics for {period_days} days...")
                
                with transaction.atomic():
                    metrics = service.calculate_dashboard_metrics(period_days)
                
                if options['verbose']:
                    self._display_detailed_metrics(metrics)
                
                # Calculate comparative analysis if requested
                if options['comparative']:
                    self.stdout.write("Calculating comparative analysis...")
                    comparative = service.generate_comparative_analysis(period_days, period_days)
                    
                    if options['verbose']:
                        self._display_comparative_analysis(comparative)
            
            # Summary
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nAnalytics calculation completed successfully in {duration:.2f} seconds"
                )
            )
            
        except Exception as e:
            logger.error(f"Error in calculate_analytics command: {e}")
            raise CommandError(f"Analytics calculation failed: {e}")
    
    def _display_detailed_metrics(self, metrics):
        """Display detailed metrics output."""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("DETAILED ANALYTICS METRICS")
        self.stdout.write("="*50)
        
        # Lead metrics
        if 'lead_metrics' in metrics:
            lead_metrics = metrics['lead_metrics']
            self.stdout.write("\nLEAD METRICS:")
            self.stdout.write(f"  Total Leads: {lead_metrics.get('total_leads', 0)}")
            self.stdout.write(f"  New Leads: {lead_metrics.get('new_leads', 0)}")
            self.stdout.write(f"  Qualified Leads: {lead_metrics.get('qualified_leads', 0)}")
            self.stdout.write(f"  Converted Leads: {lead_metrics.get('converted_leads', 0)}")
            self.stdout.write(f"  Average Score: {lead_metrics.get('avg_lead_score', 0):.2f}")
            self.stdout.write(f"  Lead Velocity: {lead_metrics.get('lead_velocity', 0):.2f} leads/day")
        
        # Conversion metrics
        if 'conversion_metrics' in metrics:
            conv_metrics = metrics['conversion_metrics']
            self.stdout.write("\nCONVERSION METRICS:")
            self.stdout.write(f"  Overall Conversion Rate: {conv_metrics.get('overall_conversion_rate', 0):.2f}%")
            self.stdout.write(f"  Average Conversion Time: {conv_metrics.get('avg_conversion_time_days', 0):.1f} days")
            
            # Conversion by source
            if 'conversion_by_source' in conv_metrics:
                self.stdout.write("  Conversion by Source:")
                for source in conv_metrics['conversion_by_source']:
                    self.stdout.write(f"    {source['source']}: {source['rate']:.2f}% ({source['conversions']}/{source['leads']})")
        
        # Revenue metrics
        if 'revenue_metrics' in metrics:
            rev_metrics = metrics['revenue_metrics']
            self.stdout.write("\nREVENUE METRICS:")
            self.stdout.write(f"  Actual Revenue: ₹{rev_metrics.get('actual_revenue', 0):,.2f}")
            self.stdout.write(f"  Pipeline Revenue: ₹{rev_metrics.get('pipeline_revenue', 0):,.2f}")
            self.stdout.write(f"  Average Deal Size: ₹{rev_metrics.get('avg_deal_size', 0):,.2f}")
            self.stdout.write(f"  Monthly Recurring Revenue: ₹{rev_metrics.get('monthly_recurring_revenue', 0):,.2f}")
        
        # Service metrics
        if 'service_metrics' in metrics:
            service_metrics = metrics['service_metrics']
            self.stdout.write("\nSERVICE METRICS:")
            self.stdout.write(f"  Total Requests: {service_metrics.get('total_requests', 0)}")
            self.stdout.write(f"  Open Requests: {service_metrics.get('open_requests', 0)}")
            self.stdout.write(f"  Closed Requests: {service_metrics.get('closed_requests', 0)}")
            self.stdout.write(f"  Overdue Requests: {service_metrics.get('overdue_requests', 0)}")
            self.stdout.write(f"  Resolution Rate: {service_metrics.get('resolution_rate', 0):.2f}%")
            self.stdout.write(f"  Avg Resolution Time: {service_metrics.get('avg_resolution_time_hours', 0):.2f} hours")
        
        # Performance indicators
        if 'performance_indicators' in metrics:
            perf_metrics = metrics['performance_indicators']
            self.stdout.write("\nPERFORMANCE INDICATORS:")
            self.stdout.write(f"  Lead to Customer Ratio: {perf_metrics.get('lead_to_customer_ratio', 0):.2f}%")
            self.stdout.write(f"  Lead Quality Score: {perf_metrics.get('lead_quality_score', 0):.2f}")
            
            if 'engagement_metrics' in perf_metrics:
                eng_metrics = perf_metrics['engagement_metrics']
                self.stdout.write("  Engagement Metrics:")
                self.stdout.write(f"    Calculator Usage: {eng_metrics.get('calculator_usage', 0)}")
                self.stdout.write(f"    Chatbot Interactions: {eng_metrics.get('chatbot_interactions', 0)}")
                self.stdout.write(f"    Email Inquiries: {eng_metrics.get('email_inquiries', 0)}")
                self.stdout.write(f"    Engagement to Lead Rate: {eng_metrics.get('engagement_to_lead_rate', 0):.2f}%")
    
    def _display_comparative_analysis(self, comparative):
        """Display comparative analysis output."""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("COMPARATIVE ANALYSIS")
        self.stdout.write("="*50)
        
        if 'current_period' in comparative and 'previous_period' in comparative:
            current = comparative['current_period']
            previous = comparative['previous_period']
            changes = comparative.get('changes', {})
            
            self.stdout.write("\nPERIOD COMPARISON:")
            self.stdout.write(f"  Leads: {current.get('leads', 0)} vs {previous.get('leads', 0)} ({changes.get('lead_change_percent', 0):+.2f}%)")
            self.stdout.write(f"  Conversions: {current.get('conversions', 0)} vs {previous.get('conversions', 0)} ({changes.get('conversion_change_percent', 0):+.2f}%)")
            self.stdout.write(f"  Revenue: ₹{current.get('revenue', 0):,.2f} vs ₹{previous.get('revenue', 0):,.2f} ({changes.get('revenue_change_percent', 0):+.2f}%)")
            
            # Trend indicators
            lead_trend = "📈" if changes.get('lead_change_percent', 0) > 0 else "📉" if changes.get('lead_change_percent', 0) < 0 else "➡️"
            conv_trend = "📈" if changes.get('conversion_change_percent', 0) > 0 else "📉" if changes.get('conversion_change_percent', 0) < 0 else "➡️"
            rev_trend = "📈" if changes.get('revenue_change_percent', 0) > 0 else "📉" if changes.get('revenue_change_percent', 0) < 0 else "➡️"
            
            self.stdout.write(f"\nTREND INDICATORS:")
            self.stdout.write(f"  Leads: {lead_trend}")
            self.stdout.write(f"  Conversions: {conv_trend}")
            self.stdout.write(f"  Revenue: {rev_trend}")