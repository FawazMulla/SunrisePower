"""
Analytics service for calculating and managing business metrics.
"""

from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import Dict, List, Optional, Tuple

from .models import (
    AnalyticsMetric, ConversionFunnel, RevenueTracking, 
    ServiceWorkload, PerformanceIndicator
)
from ..leads.models import Lead, LeadSource, LeadInteraction
from ..customers.models import Customer
from ..services.models import ServiceRequest, AMCContract, InstallationProject
from ..integrations.models import EmailLog, ChatbotInteraction, CalculatorData

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for calculating and managing analytics metrics.
    """
    
    def __init__(self):
        self.current_time = timezone.now()
    
    def calculate_dashboard_metrics(self, period_days: int = 30) -> Dict:
        """
        Calculate key dashboard metrics for the specified period.
        
        Args:
            period_days: Number of days to look back for metrics
            
        Returns:
            Dictionary containing all dashboard metrics
        """
        try:
            period_start = self.current_time - timedelta(days=period_days)
            
            metrics = {
                'lead_metrics': self._calculate_lead_metrics(period_start),
                'conversion_metrics': self._calculate_conversion_metrics(period_start),
                'revenue_metrics': self._calculate_revenue_metrics(period_start),
                'service_metrics': self._calculate_service_metrics(period_start),
                'performance_indicators': self._calculate_performance_indicators(period_start),
                'trending_data': self._calculate_trending_data(period_start),
                'calculated_at': self.current_time,
                'period_days': period_days,
            }
            
            # Store metrics in database
            self._store_calculated_metrics(metrics, period_start)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating dashboard metrics: {e}")
            return self._get_fallback_metrics()
    
    def _calculate_lead_metrics(self, period_start: datetime) -> Dict:
        """Calculate lead-related metrics."""
        try:
            # Basic lead counts
            total_leads = Lead.objects.filter(created_at__gte=period_start).count()
            new_leads = Lead.objects.filter(
                created_at__gte=period_start,
                status='new'
            ).count()
            qualified_leads = Lead.objects.filter(
                created_at__gte=period_start,
                status='qualified'
            ).count()
            converted_leads = Lead.objects.filter(
                created_at__gte=period_start,
                status='converted'
            ).count()
            
            # Lead source breakdown
            lead_sources = Lead.objects.filter(
                created_at__gte=period_start
            ).values('source__name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Priority distribution
            priority_distribution = Lead.objects.filter(
                created_at__gte=period_start
            ).values('priority_level').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Average lead score
            avg_lead_score = Lead.objects.filter(
                created_at__gte=period_start
            ).aggregate(avg_score=Avg('score'))['avg_score'] or 0
            
            # Lead velocity (leads per day)
            days_in_period = (self.current_time - period_start).days or 1
            lead_velocity = total_leads / days_in_period
            
            return {
                'total_leads': total_leads,
                'new_leads': new_leads,
                'qualified_leads': qualified_leads,
                'converted_leads': converted_leads,
                'lead_sources': list(lead_sources),
                'priority_distribution': list(priority_distribution),
                'avg_lead_score': float(avg_lead_score),
                'lead_velocity': round(lead_velocity, 2),
            }
            
        except Exception as e:
            logger.error(f"Error calculating lead metrics: {e}")
            return {}
    
    def _calculate_conversion_metrics(self, period_start: datetime) -> Dict:
        """Calculate conversion-related metrics."""
        try:
            # Overall conversion rate
            total_leads = Lead.objects.filter(created_at__gte=period_start).count()
            converted_leads = Lead.objects.filter(
                created_at__gte=period_start,
                status='converted'
            ).count()
            
            conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
            
            # Conversion by source
            conversion_by_source = []
            for source in LeadSource.objects.filter(is_active=True):
                source_leads = Lead.objects.filter(
                    created_at__gte=period_start,
                    source=source
                ).count()
                source_conversions = Lead.objects.filter(
                    created_at__gte=period_start,
                    source=source,
                    status='converted'
                ).count()
                
                source_rate = (source_conversions / source_leads * 100) if source_leads > 0 else 0
                
                conversion_by_source.append({
                    'source': source.name,
                    'leads': source_leads,
                    'conversions': source_conversions,
                    'rate': round(source_rate, 2)
                })
            
            # Conversion funnel
            funnel_data = self._calculate_conversion_funnel(period_start)
            
            # Average time to conversion
            converted_leads_with_time = Lead.objects.filter(
                created_at__gte=period_start,
                status='converted',
                converted_at__isnull=False
            )
            
            avg_conversion_time = 0
            if converted_leads_with_time.exists():
                total_time = sum([
                    (lead.converted_at - lead.created_at).days
                    for lead in converted_leads_with_time
                ])
                avg_conversion_time = total_time / converted_leads_with_time.count()
            
            return {
                'overall_conversion_rate': round(conversion_rate, 2),
                'total_leads': total_leads,
                'converted_leads': converted_leads,
                'conversion_by_source': conversion_by_source,
                'funnel_data': funnel_data,
                'avg_conversion_time_days': round(avg_conversion_time, 1),
            }
            
        except Exception as e:
            logger.error(f"Error calculating conversion metrics: {e}")
            return {}
    
    def _calculate_revenue_metrics(self, period_start: datetime) -> Dict:
        """Calculate revenue-related metrics."""
        try:
            # Actual revenue from completed projects
            actual_revenue = InstallationProject.objects.filter(
                completion_date__gte=period_start,
                status='completed'
            ).aggregate(
                total=Sum('project_value')
            )['total'] or Decimal('0')
            
            # Pipeline revenue from active projects
            pipeline_revenue = InstallationProject.objects.filter(
                created_at__gte=period_start,
                status__in=['approved', 'in_progress']
            ).aggregate(
                total=Sum('project_value')
            )['total'] or Decimal('0')
            
            # Revenue by project type
            revenue_by_type = InstallationProject.objects.filter(
                created_at__gte=period_start
            ).values('installation_type').annotate(
                total_value=Sum('project_value'),
                count=Count('id')
            ).order_by('-total_value')
            
            # Average deal size
            completed_projects = InstallationProject.objects.filter(
                completion_date__gte=period_start,
                status='completed'
            )
            avg_deal_size = completed_projects.aggregate(
                avg=Avg('project_value')
            )['avg'] or Decimal('0')
            
            # Monthly recurring revenue from AMC contracts
            active_amc_revenue = AMCContract.objects.filter(
                start_date__lte=self.current_time,
                end_date__gte=self.current_time,
                status='active'
            ).aggregate(
                total=Sum('annual_value')
            )['total'] or Decimal('0')
            
            monthly_recurring_revenue = active_amc_revenue / 12
            
            return {
                'actual_revenue': float(actual_revenue),
                'pipeline_revenue': float(pipeline_revenue),
                'revenue_by_type': [
                    {
                        'type': item['installation_type'],
                        'revenue': float(item['total_value']),
                        'count': item['count']
                    }
                    for item in revenue_by_type
                ],
                'avg_deal_size': float(avg_deal_size),
                'monthly_recurring_revenue': float(monthly_recurring_revenue),
                'total_amc_value': float(active_amc_revenue),
            }
            
        except Exception as e:
            logger.error(f"Error calculating revenue metrics: {e}")
            return {}
    
    def _calculate_service_metrics(self, period_start: datetime) -> Dict:
        """Calculate service-related metrics."""
        try:
            # Service request counts
            total_requests = ServiceRequest.objects.filter(
                created_at__gte=period_start
            ).count()
            
            open_requests = ServiceRequest.objects.filter(
                created_at__gte=period_start,
                status__in=['open', 'in_progress']
            ).count()
            
            closed_requests = ServiceRequest.objects.filter(
                created_at__gte=period_start,
                status='resolved'
            ).count()
            
            # Overdue requests (open for more than 7 days)
            overdue_threshold = self.current_time - timedelta(days=7)
            overdue_requests = ServiceRequest.objects.filter(
                created_at__lt=overdue_threshold,
                status__in=['open', 'in_progress']
            ).count()
            
            # Average response and resolution times
            resolved_requests = ServiceRequest.objects.filter(
                created_at__gte=period_start,
                status='resolved',
                resolved_at__isnull=False
            )
            
            avg_resolution_time = 0
            if resolved_requests.exists():
                total_time = sum([
                    (request.resolved_at - request.created_at).total_seconds() / 3600
                    for request in resolved_requests
                ])
                avg_resolution_time = total_time / resolved_requests.count()
            
            # Request breakdown by type and priority
            requests_by_type = ServiceRequest.objects.filter(
                created_at__gte=period_start
            ).values('request_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            requests_by_priority = ServiceRequest.objects.filter(
                created_at__gte=period_start
            ).values('priority').annotate(
                count=Count('id')
            ).order_by('-count')
            
            return {
                'total_requests': total_requests,
                'open_requests': open_requests,
                'closed_requests': closed_requests,
                'overdue_requests': overdue_requests,
                'avg_resolution_time_hours': round(avg_resolution_time, 2),
                'requests_by_type': list(requests_by_type),
                'requests_by_priority': list(requests_by_priority),
                'resolution_rate': round((closed_requests / total_requests * 100) if total_requests > 0 else 0, 2),
            }
            
        except Exception as e:
            logger.error(f"Error calculating service metrics: {e}")
            return {}
    
    def _calculate_performance_indicators(self, period_start: datetime) -> Dict:
        """Calculate key performance indicators."""
        try:
            # Customer acquisition cost (simplified)
            total_leads = Lead.objects.filter(created_at__gte=period_start).count()
            converted_customers = Lead.objects.filter(
                created_at__gte=period_start,
                status='converted'
            ).count()
            
            # Lead quality score (based on average lead score of converted leads)
            converted_lead_scores = Lead.objects.filter(
                created_at__gte=period_start,
                status='converted'
            ).aggregate(avg_score=Avg('score'))['avg_score'] or 0
            
            # Market penetration indicators
            total_calculator_usage = CalculatorData.objects.filter(
                calculation_date__gte=period_start
            ).count()
            
            total_chatbot_interactions = ChatbotInteraction.objects.filter(
                interaction_date__gte=period_start
            ).count()
            
            total_email_inquiries = EmailLog.objects.filter(
                received_at__gte=period_start,
                email_type__in=['lead_inquiry', 'quotation_request']
            ).count()
            
            # Engagement metrics
            engagement_to_lead_rate = (total_leads / (total_calculator_usage + total_chatbot_interactions + total_email_inquiries) * 100) if (total_calculator_usage + total_chatbot_interactions + total_email_inquiries) > 0 else 0
            
            return {
                'lead_to_customer_ratio': round((converted_customers / total_leads * 100) if total_leads > 0 else 0, 2),
                'lead_quality_score': round(float(converted_lead_scores), 2),
                'engagement_metrics': {
                    'calculator_usage': total_calculator_usage,
                    'chatbot_interactions': total_chatbot_interactions,
                    'email_inquiries': total_email_inquiries,
                    'engagement_to_lead_rate': round(engagement_to_lead_rate, 2),
                },
                'market_indicators': {
                    'total_touchpoints': total_calculator_usage + total_chatbot_interactions + total_email_inquiries,
                    'lead_generation_efficiency': round((total_leads / (total_calculator_usage + total_chatbot_interactions + total_email_inquiries) * 100) if (total_calculator_usage + total_chatbot_interactions + total_email_inquiries) > 0 else 0, 2),
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance indicators: {e}")
            return {}
    
    def _calculate_trending_data(self, period_start: datetime) -> Dict:
        """Calculate trending data for charts and comparisons."""
        try:
            # Daily lead generation trend
            daily_leads = []
            current_date = period_start.date()
            end_date = self.current_time.date()
            
            while current_date <= end_date:
                day_leads = Lead.objects.filter(
                    created_at__date=current_date
                ).count()
                daily_leads.append({
                    'date': current_date.isoformat(),
                    'leads': day_leads
                })
                current_date += timedelta(days=1)
            
            # Weekly conversion trend
            weekly_conversions = []
            current_week_start = period_start.date()
            
            while current_week_start <= end_date:
                week_end = min(current_week_start + timedelta(days=6), end_date)
                week_conversions = Lead.objects.filter(
                    converted_at__date__range=[current_week_start, week_end],
                    status='converted'
                ).count()
                
                weekly_conversions.append({
                    'week_start': current_week_start.isoformat(),
                    'week_end': week_end.isoformat(),
                    'conversions': week_conversions
                })
                current_week_start += timedelta(days=7)
            
            return {
                'daily_leads': daily_leads,
                'weekly_conversions': weekly_conversions,
            }
            
        except Exception as e:
            logger.error(f"Error calculating trending data: {e}")
            return {}
    
    def _calculate_conversion_funnel(self, period_start: datetime) -> List[Dict]:
        """Calculate conversion funnel data."""
        try:
            # Define funnel stages with their counts
            funnel_stages = [
                {
                    'stage': 'visitors',
                    'name': 'Website Visitors',
                    'count': CalculatorData.objects.filter(calculation_date__gte=period_start).count() + 
                            ChatbotInteraction.objects.filter(interaction_date__gte=period_start).count() +
                            EmailLog.objects.filter(received_at__gte=period_start).count(),
                },
                {
                    'stage': 'leads',
                    'name': 'Leads Generated',
                    'count': Lead.objects.filter(created_at__gte=period_start).count(),
                },
                {
                    'stage': 'qualified',
                    'name': 'Qualified Leads',
                    'count': Lead.objects.filter(created_at__gte=period_start, status='qualified').count(),
                },
                {
                    'stage': 'proposals',
                    'name': 'Proposals Sent',
                    'count': Lead.objects.filter(created_at__gte=period_start, status='proposal_sent').count(),
                },
                {
                    'stage': 'customers',
                    'name': 'Converted Customers',
                    'count': Lead.objects.filter(created_at__gte=period_start, status='converted').count(),
                },
            ]
            
            # Calculate conversion rates
            for i in range(len(funnel_stages) - 1):
                current_count = funnel_stages[i]['count']
                next_count = funnel_stages[i + 1]['count']
                conversion_rate = (next_count / current_count * 100) if current_count > 0 else 0
                funnel_stages[i]['conversion_rate'] = round(conversion_rate, 2)
            
            return funnel_stages
            
        except Exception as e:
            logger.error(f"Error calculating conversion funnel: {e}")
            return []
    
    def _store_calculated_metrics(self, metrics: Dict, period_start: datetime):
        """Store calculated metrics in the database."""
        try:
            period_end = self.current_time
            
            # Store lead metrics
            if 'lead_metrics' in metrics:
                AnalyticsMetric.objects.update_or_create(
                    metric_type='lead_count',
                    period_type='daily',
                    period_start=period_start,
                    defaults={
                        'period_end': period_end,
                        'value': metrics['lead_metrics'].get('total_leads', 0),
                        'metadata': metrics['lead_metrics']
                    }
                )
            
            # Store conversion metrics
            if 'conversion_metrics' in metrics:
                AnalyticsMetric.objects.update_or_create(
                    metric_type='conversion_rate',
                    period_type='daily',
                    period_start=period_start,
                    defaults={
                        'period_end': period_end,
                        'value': metrics['conversion_metrics'].get('overall_conversion_rate', 0),
                        'metadata': metrics['conversion_metrics']
                    }
                )
            
            # Store revenue metrics
            if 'revenue_metrics' in metrics:
                AnalyticsMetric.objects.update_or_create(
                    metric_type='revenue',
                    period_type='daily',
                    period_start=period_start,
                    defaults={
                        'period_end': period_end,
                        'value': metrics['revenue_metrics'].get('actual_revenue', 0),
                        'metadata': metrics['revenue_metrics']
                    }
                )
            
            logger.info(f"Stored analytics metrics for period {period_start.date()}")
            
        except Exception as e:
            logger.error(f"Error storing calculated metrics: {e}")
    
    def _get_fallback_metrics(self) -> Dict:
        """Return fallback metrics in case of calculation errors."""
        return {
            'lead_metrics': {'total_leads': 0, 'new_leads': 0, 'qualified_leads': 0, 'converted_leads': 0},
            'conversion_metrics': {'overall_conversion_rate': 0, 'total_leads': 0, 'converted_leads': 0},
            'revenue_metrics': {'actual_revenue': 0, 'pipeline_revenue': 0, 'avg_deal_size': 0},
            'service_metrics': {'total_requests': 0, 'open_requests': 0, 'closed_requests': 0},
            'performance_indicators': {'lead_to_customer_ratio': 0, 'lead_quality_score': 0},
            'trending_data': {'daily_leads': [], 'weekly_conversions': []},
            'calculated_at': self.current_time,
            'error': 'Fallback metrics due to calculation error'
        }
    
    def get_real_time_metrics(self) -> Dict:
        """Get real-time metrics for dashboard display."""
        try:
            return {
                'current_leads': Lead.objects.filter(status__in=['new', 'contacted', 'qualified']).count(),
                'open_service_requests': ServiceRequest.objects.filter(status__in=['open', 'in_progress']).count(),
                'active_projects': InstallationProject.objects.filter(status__in=['approved', 'in_progress']).count(),
                'total_customers': Customer.objects.count(),
                'high_priority_leads': Lead.objects.filter(priority_level__in=['high', 'critical']).count(),
                'overdue_service_requests': ServiceRequest.objects.filter(
                    created_at__lt=self.current_time - timedelta(days=7),
                    status__in=['open', 'in_progress']
                ).count(),
                'updated_at': self.current_time,
            }
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            return {}
    
    def generate_comparative_analysis(self, current_period_days: int = 30, comparison_period_days: int = 30) -> Dict:
        """Generate comparative analysis between two periods."""
        try:
            current_start = self.current_time - timedelta(days=current_period_days)
            comparison_start = current_start - timedelta(days=comparison_period_days)
            comparison_end = current_start
            
            # Current period metrics
            current_metrics = self.calculate_dashboard_metrics(current_period_days)
            
            # Comparison period metrics
            previous_leads = Lead.objects.filter(
                created_at__gte=comparison_start,
                created_at__lt=comparison_end
            ).count()
            
            previous_conversions = Lead.objects.filter(
                created_at__gte=comparison_start,
                created_at__lt=comparison_end,
                status='converted'
            ).count()
            
            previous_revenue = InstallationProject.objects.filter(
                completion_date__gte=comparison_start,
                completion_date__lt=comparison_end,
                status='completed'
            ).aggregate(total=Sum('project_value'))['total'] or Decimal('0')
            
            # Calculate changes
            current_leads = current_metrics.get('lead_metrics', {}).get('total_leads', 0)
            current_conversions = current_metrics.get('conversion_metrics', {}).get('converted_leads', 0)
            current_revenue = current_metrics.get('revenue_metrics', {}).get('actual_revenue', 0)
            
            lead_change = ((current_leads - previous_leads) / previous_leads * 100) if previous_leads > 0 else 0
            conversion_change = ((current_conversions - previous_conversions) / previous_conversions * 100) if previous_conversions > 0 else 0
            revenue_change = ((current_revenue - float(previous_revenue)) / float(previous_revenue) * 100) if previous_revenue > 0 else 0
            
            return {
                'current_period': {
                    'leads': current_leads,
                    'conversions': current_conversions,
                    'revenue': current_revenue,
                },
                'previous_period': {
                    'leads': previous_leads,
                    'conversions': previous_conversions,
                    'revenue': float(previous_revenue),
                },
                'changes': {
                    'lead_change_percent': round(lead_change, 2),
                    'conversion_change_percent': round(conversion_change, 2),
                    'revenue_change_percent': round(revenue_change, 2),
                },
                'period_info': {
                    'current_days': current_period_days,
                    'comparison_days': comparison_period_days,
                    'current_start': current_start,
                    'comparison_start': comparison_start,
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating comparative analysis: {e}")
            return {}


# Convenience functions
def get_dashboard_metrics(period_days: int = 30) -> Dict:
    """Get dashboard metrics for the specified period."""
    service = AnalyticsService()
    return service.calculate_dashboard_metrics(period_days)


def get_real_time_metrics() -> Dict:
    """Get real-time metrics."""
    service = AnalyticsService()
    return service.get_real_time_metrics()


def get_comparative_analysis(current_period_days: int = 30, comparison_period_days: int = 30) -> Dict:
    """Get comparative analysis between periods."""
    service = AnalyticsService()
    return service.generate_comparative_analysis(current_period_days, comparison_period_days)