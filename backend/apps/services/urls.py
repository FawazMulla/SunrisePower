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
    path('service-requests/search/', views.service_request_search, name='service-request-search'),
    
    # Installation Project management endpoints
    path('installation-projects/', views.InstallationProjectListCreateView.as_view(), name='installation-project-list-create'),
    path('installation-projects/<int:pk>/', views.InstallationProjectDetailView.as_view(), name='installation-project-detail'),
    
    # AMC Contract management endpoints
    path('amc-contracts/', views.AMCContractListCreateView.as_view(), name='amc-contract-list-create'),
    path('amc-contracts/<int:pk>/', views.AMCContractDetailView.as_view(), name='amc-contract-detail'),
]