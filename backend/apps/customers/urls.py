"""
URL configuration for customers app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'customers'

router = DefaultRouter()
# ViewSets will be registered here in future tasks

urlpatterns = [
    # Customer management endpoints
    path('customers/', views.CustomerListCreateView.as_view(), name='customer-list-create'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
    path('customers/<int:customer_id>/financial-update/', views.update_customer_financial_totals, name='customer-financial-update'),
    path('customers/search/', views.customer_search, name='customer-search'),
    
    # Customer history
    path('customers/<int:customer_id>/history/', views.CustomerHistoryListView.as_view(), name='customer-history'),
]