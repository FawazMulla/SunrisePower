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


class FinancialAnalytics(models.Model):
    """
    Financial analytics and reporting data
    """
    
    ANALYTICS_TYPE_CHOICES = [
        ('cash_flow', 'Cash Flow Analysis'),
        ('payment_trends', 'Payment Trends'),
        ('collection_efficiency', 'Collection Efficiency'),
        ('revenue_forecast', 'Revenue Forecast'),
        ('outstanding_analysis', 'Outstanding Analysis'),
        ('payment_method_analysis', 'Payment Method Analysis'),
    ]
    
    analytics_type = models.CharField(
        max_length=50,
        choices=ANALYTICS_TYPE_CHOICES,
        help_text='Type of financial analytics'
    )
    period_start = models.DateTimeField(
        help_text='Start of the analysis period'
    )
    period_end = models.DateTimeField(
        help_text='End of the analysis period'
    )
    
    # Financial metrics
    total_invoiced = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Total amount invoiced'
    )
    total_collected = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Total amount collected'
    )
    total_outstanding = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Total outstanding amount'
    )
    
    # Performance metrics
    collection_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Collection rate percentage'
    )
    average_payment_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Average payment time in days'
    )
    
    # Detailed analytics data
    analytics_data = models.JSONField(
        default=dict,
        help_text='Detailed analytics breakdown and trends'
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_analytics'
        verbose_name = 'Financial Analytics'
        verbose_name_plural = 'Financial Analytics'
        ordering = ['-period_start', 'analytics_type']
        indexes = [
            models.Index(fields=['analytics_type', 'period_start']),
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['calculated_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['analytics_type', 'period_start', 'period_end'],
                name='unique_financial_analytics_period'
            )
        ]
    
    def __str__(self):
        return f"{self.get_analytics_type_display()} - {self.period_start.date()}"
    
    @classmethod
    def calculate_cash_flow_analysis(cls, start_date, end_date):
        """Calculate cash flow analysis for the given period."""
        from apps.services.models import Invoice, Payment
        
        # Get invoices and payments in the period
        invoices = Invoice.objects.filter(
            invoice_date__range=[start_date, end_date]
        )
        payments = Payment.objects.filter(
            payment_date__range=[start_date, end_date],
            status='completed'
        )
        
        # Calculate metrics
        total_invoiced = sum([invoice.total_amount for invoice in invoices])
        total_collected = sum([payment.amount for payment in payments])
        
        # Calculate outstanding (all time, not just period)
        all_invoices = Invoice.objects.filter(status__in=['sent', 'partial', 'overdue'])
        total_outstanding = sum([invoice.outstanding_amount for invoice in all_invoices])
        
        # Collection rate for the period
        collection_rate = (total_collected / total_invoiced * 100) if total_invoiced > 0 else 0
        
        # Daily breakdown
        daily_breakdown = {}
        current_date = start_date
        while current_date <= end_date:
            day_invoices = invoices.filter(invoice_date=current_date)
            day_payments = payments.filter(payment_date=current_date)
            
            daily_breakdown[current_date.isoformat()] = {
                'invoiced': sum([inv.total_amount for inv in day_invoices]),
                'collected': sum([pay.amount for pay in day_payments]),
                'net_flow': sum([pay.amount for pay in day_payments]) - sum([inv.total_amount for inv in day_invoices])
            }
            current_date += timezone.timedelta(days=1)
        
        analytics_data = {
            'daily_breakdown': daily_breakdown,
            'invoice_count': invoices.count(),
            'payment_count': payments.count(),
            'net_cash_flow': total_collected - total_invoiced,
            'largest_invoice': max([inv.total_amount for inv in invoices]) if invoices else 0,
            'largest_payment': max([pay.amount for pay in payments]) if payments else 0,
        }
        
        # Create or update analytics record
        analytics, created = cls.objects.update_or_create(
            analytics_type='cash_flow',
            period_start=timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time())),
            period_end=timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.max.time())),
            defaults={
                'total_invoiced': total_invoiced,
                'total_collected': total_collected,
                'total_outstanding': total_outstanding,
                'collection_rate': collection_rate,
                'analytics_data': analytics_data
            }
        )
        
        return analytics
    
    @classmethod
    def calculate_payment_trends(cls, start_date, end_date):
        """Calculate payment trends analysis."""
        from apps.services.models import Payment
        
        payments = Payment.objects.filter(
            payment_date__range=[start_date, end_date],
            status='completed'
        )
        
        # Payment method breakdown
        payment_methods = {}
        for payment in payments:
            method = payment.payment_method
            if method not in payment_methods:
                payment_methods[method] = {'count': 0, 'amount': 0}
            payment_methods[method]['count'] += 1
            payment_methods[method]['amount'] += float(payment.amount)
        
        # Weekly trends
        weekly_trends = {}
        for payment in payments:
            week_start = payment.payment_date - timezone.timedelta(days=payment.payment_date.weekday())
            week_key = week_start.isoformat()
            
            if week_key not in weekly_trends:
                weekly_trends[week_key] = {'count': 0, 'amount': 0}
            weekly_trends[week_key]['count'] += 1
            weekly_trends[week_key]['amount'] += float(payment.amount)
        
        # Average payment size
        total_amount = sum([payment.amount for payment in payments])
        avg_payment_size = total_amount / payments.count() if payments.count() > 0 else 0
        
        analytics_data = {
            'payment_methods': payment_methods,
            'weekly_trends': weekly_trends,
            'avg_payment_size': float(avg_payment_size),
            'total_payments': payments.count(),
            'payment_velocity': payments.count() / ((end_date - start_date).days + 1)  # payments per day
        }
        
        analytics, created = cls.objects.update_or_create(
            analytics_type='payment_trends',
            period_start=timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time())),
            period_end=timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.max.time())),
            defaults={
                'total_collected': total_amount,
                'analytics_data': analytics_data
            }
        )
        
        return analytics
    
    @classmethod
    def calculate_collection_efficiency(cls, start_date, end_date):
        """Calculate collection efficiency metrics."""
        from apps.services.models import Invoice, Payment
        
        # Get invoices created in the period
        invoices = Invoice.objects.filter(
            invoice_date__range=[start_date, end_date]
        )
        
        # Calculate payment times
        payment_times = []
        for invoice in invoices:
            if invoice.status == 'paid':
                # Find the last payment for this invoice
                last_payment = invoice.payments.filter(status='completed').order_by('-payment_date').first()
                if last_payment:
                    payment_time = (last_payment.payment_date - invoice.invoice_date).days
                    payment_times.append(payment_time)
        
        avg_payment_time = sum(payment_times) / len(payment_times) if payment_times else None
        
        # Collection rate by age buckets
        age_buckets = {
            '0-30': {'count': 0, 'collected': 0, 'total': 0},
            '31-60': {'count': 0, 'collected': 0, 'total': 0},
            '61-90': {'count': 0, 'collected': 0, 'total': 0},
            '90+': {'count': 0, 'collected': 0, 'total': 0}
        }
        
        for invoice in invoices:
            age = (timezone.now().date() - invoice.invoice_date).days
            bucket = '0-30' if age <= 30 else '31-60' if age <= 60 else '61-90' if age <= 90 else '90+'
            
            age_buckets[bucket]['count'] += 1
            age_buckets[bucket]['total'] += float(invoice.total_amount)
            age_buckets[bucket]['collected'] += float(invoice.amount_paid)
        
        # Calculate collection rates for each bucket
        for bucket in age_buckets:
            if age_buckets[bucket]['total'] > 0:
                age_buckets[bucket]['collection_rate'] = (age_buckets[bucket]['collected'] / age_buckets[bucket]['total']) * 100
            else:
                age_buckets[bucket]['collection_rate'] = 0
        
        total_invoiced = sum([invoice.total_amount for invoice in invoices])
        total_collected = sum([invoice.amount_paid for invoice in invoices])
        collection_rate = (total_collected / total_invoiced * 100) if total_invoiced > 0 else 0
        
        analytics_data = {
            'age_buckets': age_buckets,
            'payment_time_distribution': {
                'min': min(payment_times) if payment_times else 0,
                'max': max(payment_times) if payment_times else 0,
                'median': sorted(payment_times)[len(payment_times)//2] if payment_times else 0
            },
            'efficiency_score': min(100, max(0, 100 - (avg_payment_time or 30)))  # Efficiency score based on payment time
        }
        
        analytics, created = cls.objects.update_or_create(
            analytics_type='collection_efficiency',
            period_start=timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time())),
            period_end=timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.max.time())),
            defaults={
                'total_invoiced': total_invoiced,
                'total_collected': total_collected,
                'collection_rate': collection_rate,
                'average_payment_time': avg_payment_time,
                'analytics_data': analytics_data
            }
        )
        
        return analytics


class PaymentTrendAnalysis(models.Model):
    """
    Detailed payment trend analysis
    """
    
    TREND_TYPE_CHOICES = [
        ('daily', 'Daily Trends'),
        ('weekly', 'Weekly Trends'),
        ('monthly', 'Monthly Trends'),
        ('seasonal', 'Seasonal Trends'),
    ]
    
    trend_type = models.CharField(
        max_length=20,
        choices=TREND_TYPE_CHOICES,
        help_text='Type of trend analysis'
    )
    period_start = models.DateTimeField(
        help_text='Start of the analysis period'
    )
    period_end = models.DateTimeField(
        help_text='End of the analysis period'
    )
    
    # Trend data
    trend_data = models.JSONField(
        default=dict,
        help_text='Detailed trend analysis data'
    )
    
    # Summary metrics
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Total amount in the trend period'
    )
    average_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Average amount per period unit'
    )
    growth_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Growth rate compared to previous period'
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_trend_analysis'
        verbose_name = 'Payment Trend Analysis'
        verbose_name_plural = 'Payment Trend Analysis'
        ordering = ['-period_start', 'trend_type']
        indexes = [
            models.Index(fields=['trend_type', 'period_start']),
            models.Index(fields=['calculated_at']),
        ]
    
    def __str__(self):
        return f"{self.get_trend_type_display()} - {self.period_start.date()}"
