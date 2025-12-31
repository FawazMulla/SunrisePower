"""
URL configuration for services app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'services'

router = DefaultRouter()
# ViewSets will be registered here in future tasks

urlpatterns = [
    # Service Request management endpoints
    path('service-requests/', views.ServiceRequestListCreateView.as_view(), name='service-request-list-create'),
    path('service-requests/<int:pk>/', views.ServiceRequestDetailView.as_view(), name='service-request-detail'),
    path('service-requests/<int:request_id>/status/', views.update_service_request_status, name='service-request-status-update'),
    path('service-requests/<int:request_id>/status-history/', views.service_request_status_history, name='service-request-status-history'),
    path('service-requests/<int:request_id>/workflow/', views.service_request_workflow_info, name='service-request-workflow'),
    path('service-requests/<int:request_id>/assign/', views.assign_service_request, name='service-request-assign'),
    path('service-requests/search/', views.service_request_search, name='service-request-search'),
    path('service-requests/dashboard-stats/', views.service_request_dashboard_stats, name='service-request-dashboard-stats'),
    
    # Installation Project management endpoints
    path('installation-projects/', views.InstallationProjectListCreateView.as_view(), name='installation-project-list-create'),
    path('installation-projects/<int:pk>/', views.InstallationProjectDetailView.as_view(), name='installation-project-detail'),
    path('installation-projects/<int:project_id>/update-status/', views.update_project_status, name='update-project-status'),
    path('installation-projects/<int:project_id>/milestones/', views.project_milestones, name='project-milestones'),
    path('installation-projects/<int:project_id>/create-milestone/', views.create_project_milestone, name='create-project-milestone'),
    path('installation-projects/<int:project_id>/notifications/', views.project_notifications, name='project-notifications'),
    path('installation-projects/dashboard-stats/', views.installation_project_dashboard_stats, name='installation-project-dashboard-stats'),
    path('installation-projects/send-notifications/', views.send_project_notifications, name='send-project-notifications'),
    path('project-milestones/<int:milestone_id>/complete/', views.complete_project_milestone, name='complete-project-milestone'),
    
    # AMC Contract management endpoints
    path('amc-contracts/', views.AMCContractListCreateView.as_view(), name='amc-contract-list-create'),
    path('amc-contracts/<int:pk>/', views.AMCContractDetailView.as_view(), name='amc-contract-detail'),
    path('amc-contracts/renewal-alerts/', views.amc_contract_renewal_alerts, name='amc-contract-renewal-alerts'),
    path('amc-contracts/<int:contract_id>/create-alerts/', views.create_amc_renewal_alerts, name='create-amc-renewal-alerts'),
    path('amc-contracts/<int:contract_id>/renew/', views.renew_amc_contract, name='renew-amc-contract'),
    path('amc-contracts/dashboard-stats/', views.amc_contract_dashboard_stats, name='amc-contract-dashboard-stats'),
    path('amc-contracts/process-alerts/', views.process_renewal_alerts, name='process-renewal-alerts'),
    path('renewal-alerts/<int:alert_id>/acknowledge/', views.acknowledge_renewal_alert, name='acknowledge-renewal-alert'),
    
    # Financial Management endpoints
    path('payment-milestones/', views.PaymentMilestoneListCreateView.as_view(), name='payment-milestone-list-create'),
    path('payment-milestones/<int:pk>/', views.PaymentMilestoneDetailView.as_view(), name='payment-milestone-detail'),
    path('payment-milestones/<int:milestone_id>/create-invoice/', views.create_milestone_invoice, name='create-milestone-invoice'),
    
    path('invoices/', views.InvoiceListCreateView.as_view(), name='invoice-list-create'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('invoices/<int:invoice_id>/send/', views.send_invoice, name='send-invoice'),
    path('invoices/overdue/', views.overdue_invoices, name='overdue-invoices'),
    
    path('payments/', views.PaymentListCreateView.as_view(), name='payment-list-create'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    path('payments/<int:payment_id>/status/', views.update_payment_status, name='update-payment-status'),
    path('payments/pending/', views.pending_payments, name='pending-payments'),
    
    path('projects/<int:project_id>/create-milestones/', views.create_default_milestones, name='create-default-milestones'),
    
    # Financial Dashboard and Reporting
    path('financial/dashboard/', views.financial_dashboard, name='financial-dashboard'),
    path('financial/summary/', views.financial_summary, name='financial-summary'),
]