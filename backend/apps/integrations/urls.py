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
    
    # Email processing endpoints
    path('emails/manual-process/', views.manual_email_processing, name='manual_email_processing'),
    path('emails/pending-reviews/', views.pending_email_reviews, name='pending_email_reviews'),
]