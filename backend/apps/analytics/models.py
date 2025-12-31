from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class AnalyticsMetric(models.Model):
    """
    Store calculated analytics metrics for dashboard display
    """
    
    METRIC_TYPE_CHOICES = [
        ('lead_count', 'Lead Count'),
        ('conversion_rate', 'Conversion Rate'),
        ('revenue', 'Revenue'),
        ('service_requests', 'Service Requests'),
        ('avg_deal_size', 'Average Deal Size'),
        ('lead_source_performance', 'Lead Source Performance'),
        ('priority_distribution', 'Priority Distribution'),
        ('response_time', 'Response Time'),
    ]
    
    PERIOD_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('all_time', 'All Time'),
    ]
    
    metric_type = models.CharField(
        max_length=50,
        choices=METRIC_TYPE_CHOICES,
        help_text='Type of metric'
    )
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        help_text='Time period for this metric'
    )
    period_start = models.DateTimeField(
        help_text='Start of the period'
    )
    period_end = models.DateTimeField(
        help_text='End of the period'
    )
    
    # Metric values
    value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Primary metric value'
    )
    secondary_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Secondary metric value (for ratios, percentages, etc.)'
    )
    
    # Additional data
    metadata = models.JSONField(
        default=dict,
        help_text='Additional metric data and breakdowns'
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_metrics'
        verbose_name = 'Analytics Metric'
        verbose_name_plural = 'Analytics Metrics'
        ordering = ['-period_start', 'metric_type']
        indexes = [
            models.Index(fields=['metric_type', 'period_type']),
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['calculated_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['metric_type', 'period_type', 'period_start'],
                name='unique_metric_period'
            )
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()} - {self.get_period_type_display()} ({self.period_start.date()})"


class ConversionFunnel(models.Model):
    """
    Track conversion funnel metrics
    """
    
    FUNNEL_STAGE_CHOICES = [
        ('visitor', 'Website Visitor'),
        ('lead', 'Lead Generated'),
        ('qualified', 'Qualified Lead'),
        ('proposal', 'Proposal Sent'),
        ('negotiation', 'In Negotiation'),
        ('customer', 'Converted Customer'),
    ]
    
    stage = models.CharField(
        max_length=20,
        choices=FUNNEL_STAGE_CHOICES,
        help_text='Funnel stage'
    )
    period_start = models.DateTimeField(
        help_text='Start of the period'
    )
    period_end = models.DateTimeField(
        help_text='End of the period'
    )
    
    # Counts
    count = models.IntegerField(
        default=0,
        help_text='Number of records in this stage'
    )
    converted_count = models.IntegerField(
        default=0,
        help_text='Number that converted to next stage'
    )
    
    # Conversion rate
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text='Conversion rate to next stage (%)'
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'conversion_funnel'
        verbose_name = 'Conversion Funnel'
        verbose_name_plural = 'Conversion Funnel'
        ordering = ['period_start', 'stage']
        indexes = [
            models.Index(fields=['stage', 'period_start']),
            models.Index(fields=['calculated_at']),
        ]
    
    def __str__(self):
        return f"{self.get_stage_display()} - {self.period_start.date()} ({self.count} records)"


class RevenueTracking(models.Model):
    """
    Track revenue metrics and projections
    """
    
    REVENUE_TYPE_CHOICES = [
        ('actual', 'Actual Revenue'),
        ('projected', 'Projected Revenue'),
        ('pipeline', 'Pipeline Value'),
    ]
    
    revenue_type = models.CharField(
        max_length=20,
        choices=REVENUE_TYPE_CHOICES,
        help_text='Type of revenue tracking'
    )
    period_start = models.DateTimeField(
        help_text='Start of the period'
    )
    period_end = models.DateTimeField(
        help_text='End of the period'
    )
    
    # Revenue amounts
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Revenue amount'
    )
    currency = models.CharField(
        max_length=3,
        default='INR',
        help_text='Currency code'
    )
    
    # Breakdown
    breakdown = models.JSONField(
        default=dict,
        help_text='Revenue breakdown by source, product, etc.'
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'revenue_tracking'
        verbose_name = 'Revenue Tracking'
        verbose_name_plural = 'Revenue Tracking'
        ordering = ['-period_start', 'revenue_type']
        indexes = [
            models.Index(fields=['revenue_type', 'period_start']),
            models.Index(fields=['calculated_at']),
        ]
    
    def __str__(self):
        return f"{self.get_revenue_type_display()} - {self.period_start.date()} (₹{self.amount:,.2f})"


class ServiceWorkload(models.Model):
    """
    Track service request workload and performance
    """
    
    period_start = models.DateTimeField(
        help_text='Start of the period'
    )
    period_end = models.DateTimeField(
        help_text='End of the period'
    )
    
    # Request counts
    total_requests = models.IntegerField(
        default=0,
        help_text='Total service requests'
    )
    open_requests = models.IntegerField(
        default=0,
        help_text='Open service requests'
    )
    closed_requests = models.IntegerField(
        default=0,
        help_text='Closed service requests'
    )
    overdue_requests = models.IntegerField(
        default=0,
        help_text='Overdue service requests'
    )
    
    # Performance metrics
    avg_response_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Average response time in hours'
    )
    avg_resolution_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Average resolution time in hours'
    )
    
    # Satisfaction metrics
    satisfaction_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Average satisfaction score (1-5)'
    )
    
    # Breakdown by type, priority, etc.
    breakdown = models.JSONField(
        default=dict,
        help_text='Workload breakdown by various dimensions'
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'service_workload'
        verbose_name = 'Service Workload'
        verbose_name_plural = 'Service Workload'
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['calculated_at']),
        ]
    
    def __str__(self):
        return f"Service Workload - {self.period_start.date()} ({self.total_requests} requests)"


class PerformanceIndicator(models.Model):
    """
    Key Performance Indicators (KPIs) for the business
    """
    
    KPI_TYPE_CHOICES = [
        ('lead_velocity', 'Lead Velocity'),
        ('conversion_velocity', 'Conversion Velocity'),
        ('customer_acquisition_cost', 'Customer Acquisition Cost'),
        ('customer_lifetime_value', 'Customer Lifetime Value'),
        ('service_efficiency', 'Service Efficiency'),
        ('revenue_growth', 'Revenue Growth'),
        ('market_penetration', 'Market Penetration'),
    ]
    
    kpi_type = models.CharField(
        max_length=50,
        choices=KPI_TYPE_CHOICES,
        help_text='Type of KPI'
    )
    period_start = models.DateTimeField(
        help_text='Start of the period'
    )
    period_end = models.DateTimeField(
        help_text='End of the period'
    )
    
    # KPI values
    current_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Current KPI value'
    )
    previous_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Previous period KPI value'
    )
    target_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Target KPI value'
    )
    
    # Performance indicators
    change_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Percentage change from previous period'
    )
    target_achievement = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Target achievement percentage'
    )
    
    # Additional context
    context_data = models.JSONField(
        default=dict,
        help_text='Additional context and breakdown data'
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'performance_indicators'
        verbose_name = 'Performance Indicator'
        verbose_name_plural = 'Performance Indicators'
        ordering = ['-period_start', 'kpi_type']
        indexes = [
            models.Index(fields=['kpi_type', 'period_start']),
            models.Index(fields=['calculated_at']),
        ]
    
    def __str__(self):
        return f"{self.get_kpi_type_display()} - {self.period_start.date()} ({self.current_value})"
