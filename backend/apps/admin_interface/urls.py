"""
URL configuration for Solar CRM Admin Interface
"""
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'admin_interface'

urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='admin/auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Leads Management
    path('leads/', views.LeadsListView.as_view(), name='leads'),
    path('leads/create/', views.LeadCreateView.as_view(), name='lead_create'),
    path('leads/<int:pk>/', views.LeadDetailView.as_view(), name='lead_detail'),
    path('leads/<int:pk>/edit/', views.LeadUpdateView.as_view(), name='lead_edit'),
    path('leads/<int:pk>/convert/', views.LeadConvertView.as_view(), name='lead_convert'),
    path('leads/<int:pk>/delete/', views.LeadDeleteView.as_view(), name='lead_delete'),
    
    # Customers Management
    path('customers/', views.CustomersListView.as_view(), name='customers'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    
    # Service Requests Management
    path('services/', views.ServiceRequestsListView.as_view(), name='services'),
    path('services/create/', views.ServiceRequestCreateView.as_view(), name='service_create'),
    path('services/<int:pk>/', views.ServiceRequestDetailView.as_view(), name='service_detail'),
    path('services/<int:pk>/edit/', views.ServiceRequestUpdateView.as_view(), name='service_edit'),
    path('services/<int:pk>/delete/', views.ServiceRequestDeleteView.as_view(), name='service_delete'),
    
    # Analytics
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    path('analytics/reports/', views.ReportsView.as_view(), name='reports'),
    
    # API endpoints for AJAX calls
    path('api/dashboard-metrics/', views.DashboardMetricsAPIView.as_view(), name='dashboard_metrics_api'),
    path('api/chart-data/<str:chart_type>/', views.ChartDataAPIView.as_view(), name='chart_data_api'),
    
    # Export endpoints
    path('export/leads/', views.ExportLeadsView.as_view(), name='export_leads'),
    path('export/customers/', views.ExportCustomersView.as_view(), name='export_customers'),
    path('export/services/', views.ExportServiceRequestsView.as_view(), name='export_services'),
]