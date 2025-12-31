"""
URL configuration for leads app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import duplicate_views

app_name = 'leads'

router = DefaultRouter()
# ViewSets will be registered here in future tasks

urlpatterns = [
    # Lead management endpoints
    path('leads/', views.LeadListCreateView.as_view(), name='lead-list-create'),
    path('leads/<int:pk>/', views.LeadDetailView.as_view(), name='lead-detail'),
    path('leads/<int:lead_id>/convert/', views.convert_lead_to_customer, name='lead-convert'),
    path('leads/<int:lead_id>/score/', views.update_lead_score, name='lead-score-update'),
    path('leads/search/', views.lead_search, name='lead-search'),
    
    # Lead interactions
    path('leads/<int:lead_id>/interactions/', views.LeadInteractionListCreateView.as_view(), name='lead-interactions'),
    
    # Lead sources
    path('lead-sources/', views.LeadSourceListView.as_view(), name='lead-sources'),
    
    # Duplicate detection endpoints
    path('leads/check-duplicates/', duplicate_views.check_duplicates, name='check-duplicates'),
    path('leads/duplicates/<int:detection_id>/process/', duplicate_views.process_duplicate_decision, name='process-duplicate-decision'),
    path('leads/manual-review/', duplicate_views.manual_review_queue, name='manual-review-queue'),
    path('leads/manual-review/<int:review_id>/assign/', duplicate_views.assign_review, name='assign-review'),
    path('leads/merge-history/', duplicate_views.merge_history, name='merge-history'),
]