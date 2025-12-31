"""
URL configuration for analytics app.
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Financial Analytics endpoints
    path('financial/dashboard/', views.financial_analytics_dashboard, name='financial-analytics-dashboard'),
    path('financial/revenue/', views.revenue_analytics, name='revenue-analytics'),
    path('financial/payments/', views.payment_analytics, name='payment-analytics'),
    path('financial/outstanding/', views.outstanding_analysis, name='outstanding-analysis'),
    path('financial/report/', views.generate_financial_report, name='generate-financial-report'),
]