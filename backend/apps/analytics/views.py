from django.shortcuts import render
from django.db.models import Q, Sum, Count, Avg
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from .models import (
    AnalyticsMetric, ConversionFunnel, RevenueTracking, ServiceWorkload,
    PerformanceIndicator, FinancialAnalytics, PaymentTrendAnalysis
)
from apps.services.models import Invoice, Payment, PaymentMilestone, InstallationProject
from apps.leads.models import Lead
from apps.customers.models import Customer

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_analytics_dashboard(request):
    """
    Get comprehensive financial analytics dashboard data.
    
    GET: Returns financial metrics, trends, and analytics
    """
    user = request.user
    
    # Get period parameters
    period = request.GET.get('period', 'monthly')  # daily, weekly, monthly, quarterly
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    # Calculate period dates
    today = timezone.now().date()
    
    if start_date_str and end_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        # Default to current month
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    # Calculate or get cached analytics
    try:
        cash_flow = FinancialAnalytics.calculate_cash_flow_analysis(start_date, end_date)
        payment_trends = FinancialAnalytics.calculate_payment_trends(start_date, end_date)
        collection_efficiency = FinancialAnalytics.calculate_collection_efficiency(start_date, end_date)
        
        # Get recent analytics for comparison
        previous_start = start_date - timedelta(days=(end_date - start_date).days + 1)
        previous_end = start_date - timedelta(days=1)
        
        previous_cash_flow = FinancialAnalytics.calculate_cash_flow_analysis(previous_start, previous_end)
        
        # Calculate growth metrics
        invoiced_growth = 0
        collected_growth = 0
        
        if previous_cash_flow.total_invoiced > 0:
            invoiced_growth = ((cash_flow.total_invoiced - previous_cash_flow.total_invoiced) / previous_cash_flow.total_invoiced) * 100
        
        if previous_cash_flow.total_collected > 0:
            collected_growth = ((cash_flow.total_collected - previous_cash_flow.total_collected) / previous_cash_flow.total_collected) * 100
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'type': period
            },
            'cash_flow': {
                'total_invoiced': cash_flow.total_invoiced,
                'total_collected': cash_flow.total_collected,
                'total_outstanding': cash_flow.total_outstanding,
                'collection_rate': cash_flow.collection_rate,
                'net_cash_flow': cash_flow.analytics_data.get('net_cash_flow', 0),
                'daily_breakdown': cash_flow.analytics_data.get('daily_breakdown', {}),
                'growth': {
                    'invoiced_growth': invoiced_growth,
                    'collected_growth': collected_growth
                }
            },
            'payment_trends': {
                'total_payments': payment_trends.analytics_data.get('total_payments', 0),
                'avg_payment_size': payment_trends.analytics_data.get('avg_payment_size', 0),
                'payment_velocity': payment_trends.analytics_data.get('payment_velocity', 0),
                'payment_methods': payment_trends.analytics_data.get('payment_methods', {}),
                'weekly_trends': payment_trends.analytics_data.get('weekly_trends', {})
            },
            'collection_efficiency': {
                'collection_rate': collection_efficiency.collection_rate,
                'average_payment_time': collection_efficiency.average_payment_time,
                'age_buckets': collection_efficiency.analytics_data.get('age_buckets', {}),
                'efficiency_score': collection_efficiency.analytics_data.get('efficiency_score', 0)
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to calculate financial analytics: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def revenue_analytics(request):
    """
    Get revenue analytics and projections.
    
    GET: Returns revenue metrics, trends, and forecasts
    """
    user = request.user
    
    # Get period parameters
    months_back = int(request.GET.get('months', 12))  # Default to 12 months
    
    # Calculate monthly revenue for the past N months
    monthly_revenue = []
    today = timezone.now().date()
    
    for i in range(months_back):
        # Calculate month start and end
        if today.month - i <= 0:
            month = 12 + (today.month - i)
            year = today.year - 1
        else:
            month = today.month - i
            year = today.year
        
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        # Get invoices for the month
        month_invoices = Invoice.objects.filter(
            invoice_date__range=[month_start, month_end]
        )
        
        # Get payments for the month
        month_payments = Payment.objects.filter(
            payment_date__range=[month_start, month_end],
            status='completed'
        )
        
        # Apply user permissions
        if user.role == 'sales_staff':
            month_invoices = month_invoices.filter(customer__assigned_to=user)
            month_payments = month_payments.filter(customer__assigned_to=user)
        
        total_invoiced = sum([inv.total_amount for inv in month_invoices])
        total_collected = sum([pay.amount for pay in month_payments])
        
        monthly_revenue.append({
            'month': f"{year}-{month:02d}",
            'month_name': month_start.strftime('%B %Y'),
            'invoiced': float(total_invoiced),
            'collected': float(total_collected),
            'invoice_count': month_invoices.count(),
            'payment_count': month_payments.count()
        })
    
    # Reverse to get chronological order
    monthly_revenue.reverse()
    
    # Calculate projections based on trends
    if len(monthly_revenue) >= 3:
        # Simple linear projection based on last 3 months
        recent_months = monthly_revenue[-3:]
        avg_growth = sum([
            (recent_months[i]['collected'] - recent_months[i-1]['collected']) / recent_months[i-1]['collected'] * 100
            for i in range(1, len(recent_months))
            if recent_months[i-1]['collected'] > 0
        ]) / (len(recent_months) - 1) if len(recent_months) > 1 else 0
        
        # Project next 3 months
        last_month_collected = recent_months[-1]['collected']
        projections = []
        
        for i in range(1, 4):
            projected_amount = last_month_collected * (1 + avg_growth/100) ** i
            next_month = today.replace(day=1) + timedelta(days=32*i)
            next_month = next_month.replace(day=1)
            
            projections.append({
                'month': f"{next_month.year}-{next_month.month:02d}",
                'month_name': next_month.strftime('%B %Y'),
                'projected_collected': projected_amount,
                'confidence': max(50, 90 - i*10)  # Decreasing confidence
            })
    else:
        projections = []
    
    # Calculate year-over-year comparison
    current_year_revenue = sum([
        month['collected'] for month in monthly_revenue 
        if month['month'].startswith(str(today.year))
    ])
    
    previous_year_revenue = sum([
        month['collected'] for month in monthly_revenue 
        if month['month'].startswith(str(today.year - 1))
    ])
    
    yoy_growth = 0
    if previous_year_revenue > 0:
        yoy_growth = ((current_year_revenue - previous_year_revenue) / previous_year_revenue) * 100
    
    return Response({
        'monthly_revenue': monthly_revenue,
        'projections': projections,
        'summary': {
            'total_revenue_period': sum([month['collected'] for month in monthly_revenue]),
            'avg_monthly_revenue': sum([month['collected'] for month in monthly_revenue]) / len(monthly_revenue) if monthly_revenue else 0,
            'current_year_revenue': current_year_revenue,
            'previous_year_revenue': previous_year_revenue,
            'yoy_growth': yoy_growth,
            'avg_growth_rate': avg_growth if 'avg_growth' in locals() else 0
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_analytics(request):
    """
    Get detailed payment analytics.
    
    GET: Returns payment method analysis, timing patterns, and trends
    """
    user = request.user
    
    # Get period parameters
    days_back = int(request.GET.get('days', 90))  # Default to 90 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days_back)
    
    # Base payment queryset
    payments = Payment.objects.filter(
        payment_date__range=[start_date, end_date],
        status='completed'
    )
    
    # Apply user permissions
    if user.role == 'sales_staff':
        payments = payments.filter(customer__assigned_to=user)
    
    # Payment method analysis
    payment_methods = {}
    for payment in payments:
        method = payment.get_payment_method_display()
        if method not in payment_methods:
            payment_methods[method] = {
                'count': 0,
                'total_amount': 0,
                'avg_amount': 0,
                'percentage': 0
            }
        payment_methods[method]['count'] += 1
        payment_methods[method]['total_amount'] += float(payment.amount)
    
    # Calculate percentages and averages
    total_payments = payments.count()
    total_amount = sum([float(p.amount) for p in payments])
    
    for method in payment_methods:
        payment_methods[method]['avg_amount'] = payment_methods[method]['total_amount'] / payment_methods[method]['count']
        payment_methods[method]['percentage'] = (payment_methods[method]['count'] / total_payments) * 100 if total_payments > 0 else 0
        payment_methods[method]['amount_percentage'] = (payment_methods[method]['total_amount'] / total_amount) * 100 if total_amount > 0 else 0
    
    # Daily payment patterns
    daily_patterns = {}
    for payment in payments:
        day_name = payment.payment_date.strftime('%A')
        if day_name not in daily_patterns:
            daily_patterns[day_name] = {'count': 0, 'amount': 0}
        daily_patterns[day_name]['count'] += 1
        daily_patterns[day_name]['amount'] += float(payment.amount)
    
    # Payment size distribution
    payment_amounts = [float(p.amount) for p in payments]
    payment_amounts.sort()
    
    size_buckets = {
        '0-10K': {'count': 0, 'amount': 0},
        '10K-50K': {'count': 0, 'amount': 0},
        '50K-100K': {'count': 0, 'amount': 0},
        '100K-500K': {'count': 0, 'amount': 0},
        '500K+': {'count': 0, 'amount': 0}
    }
    
    for amount in payment_amounts:
        if amount < 10000:
            bucket = '0-10K'
        elif amount < 50000:
            bucket = '10K-50K'
        elif amount < 100000:
            bucket = '50K-100K'
        elif amount < 500000:
            bucket = '100K-500K'
        else:
            bucket = '500K+'
        
        size_buckets[bucket]['count'] += 1
        size_buckets[bucket]['amount'] += amount
    
    # Payment timing analysis (time from invoice to payment)
    payment_timing = []
    for payment in payments:
        if payment.invoice:
            days_to_pay = (payment.payment_date - payment.invoice.invoice_date).days
            payment_timing.append(days_to_pay)
    
    timing_stats = {}
    if payment_timing:
        timing_stats = {
            'avg_days': sum(payment_timing) / len(payment_timing),
            'min_days': min(payment_timing),
            'max_days': max(payment_timing),
            'median_days': sorted(payment_timing)[len(payment_timing)//2]
        }
    
    return Response({
        'period': {
            'start_date': start_date,
            'end_date': end_date,
            'days': days_back
        },
        'summary': {
            'total_payments': total_payments,
            'total_amount': total_amount,
            'avg_payment_size': total_amount / total_payments if total_payments > 0 else 0,
            'payments_per_day': total_payments / days_back if days_back > 0 else 0
        },
        'payment_methods': payment_methods,
        'daily_patterns': daily_patterns,
        'size_distribution': size_buckets,
        'timing_analysis': timing_stats
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def outstanding_analysis(request):
    """
    Get analysis of outstanding amounts and aging.
    
    GET: Returns aging analysis, collection predictions, and risk assessment
    """
    user = request.user
    
    # Get outstanding invoices
    outstanding_invoices = Invoice.objects.filter(
        status__in=['sent', 'partial', 'overdue']
    ).select_related('customer', 'installation_project')
    
    # Apply user permissions
    if user.role == 'sales_staff':
        outstanding_invoices = outstanding_invoices.filter(customer__assigned_to=user)
    
    # Aging analysis
    today = timezone.now().date()
    aging_buckets = {
        'current': {'count': 0, 'amount': 0, 'invoices': []},
        '1-30': {'count': 0, 'amount': 0, 'invoices': []},
        '31-60': {'count': 0, 'amount': 0, 'invoices': []},
        '61-90': {'count': 0, 'amount': 0, 'invoices': []},
        '90+': {'count': 0, 'amount': 0, 'invoices': []}
    }
    
    total_outstanding = 0
    
    for invoice in outstanding_invoices:
        outstanding_amount = invoice.outstanding_amount
        total_outstanding += outstanding_amount
        
        days_outstanding = (today - invoice.due_date).days
        
        if days_outstanding <= 0:
            bucket = 'current'
        elif days_outstanding <= 30:
            bucket = '1-30'
        elif days_outstanding <= 60:
            bucket = '31-60'
        elif days_outstanding <= 90:
            bucket = '61-90'
        else:
            bucket = '90+'
        
        aging_buckets[bucket]['count'] += 1
        aging_buckets[bucket]['amount'] += float(outstanding_amount)
        aging_buckets[bucket]['invoices'].append({
            'invoice_number': invoice.invoice_number,
            'customer_name': invoice.customer.full_name,
            'amount': float(outstanding_amount),
            'days_outstanding': days_outstanding,
            'due_date': invoice.due_date
        })
    
    # Calculate collection risk scores
    risk_analysis = {
        'low_risk': {'count': 0, 'amount': 0},      # 0-30 days
        'medium_risk': {'count': 0, 'amount': 0},   # 31-60 days
        'high_risk': {'count': 0, 'amount': 0},     # 61-90 days
        'critical_risk': {'count': 0, 'amount': 0}  # 90+ days
    }
    
    risk_analysis['low_risk'] = {
        'count': aging_buckets['current']['count'] + aging_buckets['1-30']['count'],
        'amount': aging_buckets['current']['amount'] + aging_buckets['1-30']['amount']
    }
    risk_analysis['medium_risk'] = aging_buckets['31-60']
    risk_analysis['high_risk'] = aging_buckets['61-90']
    risk_analysis['critical_risk'] = aging_buckets['90+']
    
    # Top outstanding customers
    customer_outstanding = {}
    for invoice in outstanding_invoices:
        customer_id = invoice.customer.id
        if customer_id not in customer_outstanding:
            customer_outstanding[customer_id] = {
                'customer_name': invoice.customer.full_name,
                'customer_email': invoice.customer.email,
                'total_outstanding': 0,
                'invoice_count': 0,
                'oldest_invoice_days': 0
            }
        
        customer_outstanding[customer_id]['total_outstanding'] += float(invoice.outstanding_amount)
        customer_outstanding[customer_id]['invoice_count'] += 1
        
        days_outstanding = (today - invoice.due_date).days
        if days_outstanding > customer_outstanding[customer_id]['oldest_invoice_days']:
            customer_outstanding[customer_id]['oldest_invoice_days'] = days_outstanding
    
    # Sort by outstanding amount
    top_customers = sorted(
        customer_outstanding.values(),
        key=lambda x: x['total_outstanding'],
        reverse=True
    )[:10]
    
    return Response({
        'summary': {
            'total_outstanding': total_outstanding,
            'total_invoices': outstanding_invoices.count(),
            'avg_outstanding_per_invoice': total_outstanding / outstanding_invoices.count() if outstanding_invoices.count() > 0 else 0
        },
        'aging_analysis': aging_buckets,
        'risk_analysis': risk_analysis,
        'top_customers': top_customers,
        'collection_priority': [
            invoice for bucket in ['90+', '61-90', '31-60'] 
            for invoice in aging_buckets[bucket]['invoices']
        ][:20]  # Top 20 priority invoices
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_financial_report(request):
    """
    Generate comprehensive financial report.
    
    POST: Creates a detailed financial report for specified period
    """
    user = request.user
    
    # Check permissions
    if not (user.is_superuser or user.role in ['owner', 'sales_manager']):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get report parameters
    report_type = request.data.get('report_type', 'monthly')  # monthly, quarterly, yearly
    start_date_str = request.data.get('start_date')
    end_date_str = request.data.get('end_date')
    
    if not start_date_str or not end_date_str:
        return Response(
            {'error': 'start_date and end_date are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Generate all analytics for the period
        cash_flow = FinancialAnalytics.calculate_cash_flow_analysis(start_date, end_date)
        payment_trends = FinancialAnalytics.calculate_payment_trends(start_date, end_date)
        collection_efficiency = FinancialAnalytics.calculate_collection_efficiency(start_date, end_date)
        
        # Get additional metrics
        invoices = Invoice.objects.filter(invoice_date__range=[start_date, end_date])
        payments = Payment.objects.filter(payment_date__range=[start_date, end_date], status='completed')
        projects = InstallationProject.objects.filter(created_at__date__range=[start_date, end_date])
        
        # Calculate project metrics
        project_metrics = {
            'total_projects': projects.count(),
            'completed_projects': projects.filter(status='completed').count(),
            'total_project_value': sum([p.project_value for p in projects]),
            'avg_project_value': sum([p.project_value for p in projects]) / projects.count() if projects.count() > 0 else 0
        }
        
        # Generate comprehensive report
        report = {
            'report_info': {
                'type': report_type,
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'generated_at': timezone.now(),
                'generated_by': user.get_full_name()
            },
            'executive_summary': {
                'total_invoiced': float(cash_flow.total_invoiced),
                'total_collected': float(cash_flow.total_collected),
                'collection_rate': float(cash_flow.collection_rate),
                'total_outstanding': float(cash_flow.total_outstanding),
                'net_cash_flow': cash_flow.analytics_data.get('net_cash_flow', 0)
            },
            'detailed_metrics': {
                'cash_flow': {
                    'total_invoiced': float(cash_flow.total_invoiced),
                    'total_collected': float(cash_flow.total_collected),
                    'daily_breakdown': cash_flow.analytics_data.get('daily_breakdown', {}),
                    'invoice_count': cash_flow.analytics_data.get('invoice_count', 0),
                    'payment_count': cash_flow.analytics_data.get('payment_count', 0)
                },
                'payment_analysis': {
                    'payment_methods': payment_trends.analytics_data.get('payment_methods', {}),
                    'weekly_trends': payment_trends.analytics_data.get('weekly_trends', {}),
                    'avg_payment_size': payment_trends.analytics_data.get('avg_payment_size', 0),
                    'payment_velocity': payment_trends.analytics_data.get('payment_velocity', 0)
                },
                'collection_performance': {
                    'collection_rate': float(collection_efficiency.collection_rate),
                    'avg_payment_time': float(collection_efficiency.average_payment_time or 0),
                    'age_buckets': collection_efficiency.analytics_data.get('age_buckets', {}),
                    'efficiency_score': collection_efficiency.analytics_data.get('efficiency_score', 0)
                },
                'project_metrics': project_metrics
            },
            'recommendations': []
        }
        
        # Add recommendations based on metrics
        if cash_flow.collection_rate < 80:
            report['recommendations'].append({
                'type': 'collection_improvement',
                'message': 'Collection rate is below 80%. Consider implementing stricter payment terms and follow-up procedures.',
                'priority': 'high'
            })
        
        if collection_efficiency.average_payment_time and collection_efficiency.average_payment_time > 45:
            report['recommendations'].append({
                'type': 'payment_timing',
                'message': f'Average payment time is {collection_efficiency.average_payment_time} days. Consider offering early payment discounts.',
                'priority': 'medium'
            })
        
        if cash_flow.total_outstanding > cash_flow.total_collected:
            report['recommendations'].append({
                'type': 'outstanding_management',
                'message': 'Outstanding amount exceeds collected amount. Focus on aging receivables management.',
                'priority': 'high'
            })
        
        return Response(report, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to generate financial report: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )