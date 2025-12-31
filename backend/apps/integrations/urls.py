"""
URL configuration for integrations app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'integrations'

router = DefaultRouter()
# ViewSets will be registered here in future tasks

urlpatterns = [
    # Task management endpoints
    path('tasks/enqueue/', views.enqueue_task, name='enqueue_task'),
    path('tasks/status/<str:task_id>/', views.task_status, name='task_status'),
    path('tasks/list/', views.list_tasks, name='list_tasks'),
    path('tasks/queue-status/', views.task_queue_status, name='task_queue_status'),
    
    # Webhook endpoints
    path('webhooks/emailjs/', views.emailjs_webhook, name='emailjs_webhook'),
    path('webhooks/chatbot/', views.chatbot_data_submission, name='chatbot_data_submission'),
    path('webhooks/calculator/', views.calculator_data_submission, name='calculator_data_submission'),
    
    # Email processing endpoints
    path('emails/manual-process/', views.manual_email_processing, name='manual_email_processing'),
    path('emails/pending-reviews/', views.pending_email_reviews, name='pending_email_reviews'),
    
    # System monitoring endpoints
    path('monitoring/health/', views.system_health, name='system_health'),
    path('monitoring/metrics/', views.system_metrics, name='system_metrics'),
    path('monitoring/errors/', views.error_dashboard, name='error_dashboard'),
    path('monitoring/errors/<str:error_id>/resolve/', views.resolve_error, name='resolve_error'),
    path('monitoring/health-check/', views.trigger_health_check, name='trigger_health_check'),
    
    # Public health check endpoint
    path('health/', views.health_check, name='health_check'),
    
    # Configuration endpoints
    path('config/cohere-key/', views.get_cohere_api_key, name='get_cohere_api_key'),
]