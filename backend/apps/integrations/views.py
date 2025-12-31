"""
Views for integrations app.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging

from .tasks import TaskManager, TaskRegistry, BackgroundTask

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enqueue_task(request):
    """
    API endpoint to enqueue a background task.
    """
    try:
        data = request.data
        task_name = data.get('task_name')
        args = data.get('args', [])
        kwargs = data.get('kwargs', {})
        priority = data.get('priority', 5)
        
        if not task_name:
            return Response(
                {'error': 'task_name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if task_name not in TaskRegistry.list_tasks():
            return Response(
                {'error': f'Unknown task: {task_name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task_id = TaskManager.enqueue_task(
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            priority=priority
        )
        
        return Response({
            'task_id': task_id,
            'message': 'Task enqueued successfully'
        })
        
    except Exception as e:
        logger.error(f"Error enqueuing task: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_status(request, task_id):
    """
    API endpoint to get task status.
    """
    try:
        task_info = TaskManager.get_task_status(task_id)
        
        if not task_info:
            return Response(
                {'error': 'Task not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(task_info)
        
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_tasks(request):
    """
    API endpoint to list available tasks.
    """
    try:
        available_tasks = TaskRegistry.list_tasks()
        return Response({
            'available_tasks': available_tasks
        })
        
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_queue_status(request):
    """
    API endpoint to get task queue status.
    """
    try:
        from django.db.models import Count
        
        # Get task counts by status
        status_counts = BackgroundTask.objects.values('status').annotate(
            count=Count('id')
        )
        
        # Convert to dict
        status_dict = {item['status']: item['count'] for item in status_counts}
        
        # Get recent tasks
        recent_tasks = BackgroundTask.objects.order_by('-created_at')[:10]
        recent_task_data = []
        
        for task in recent_tasks:
            recent_task_data.append({
                'task_id': task.task_id,
                'task_name': task.task_name,
                'status': task.status,
                'created_at': task.created_at,
                'priority': task.priority
            })
        
        return Response({
            'status_counts': status_dict,
            'recent_tasks': recent_task_data,
            'total_tasks': BackgroundTask.objects.count()
        })
        
    except Exception as e:
        logger.error(f"Error getting queue status: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Webhook endpoint for EmailJS (no authentication required)
@csrf_exempt
@require_http_methods(["POST"])
def emailjs_webhook(request):
    """
    Webhook endpoint for EmailJS integration.
    Processes form submissions and creates leads/service requests automatically.
    """
    try:
        # Parse the incoming data
        data = json.loads(request.body)
        
        # Log the webhook receipt
        logger.info(f"Received EmailJS webhook: {data}")
        
        # Enqueue a task to process the email with high priority
        task_id = TaskManager.enqueue_task(
            task_name='process_emailjs_submission',
            kwargs={'submission_data': data},
            priority=3  # High priority for customer inquiries
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Email submission received and queued for processing',
            'task_id': task_id
        })
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in EmailJS webhook")
        return JsonResponse(
            {'error': 'Invalid JSON'},
            status=400
        )
    except Exception as e:
        logger.error(f"Error processing EmailJS webhook: {str(e)}")
        return JsonResponse(
            {'error': 'Internal server error'},
            status=500
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manual_email_processing(request):
    """
    API endpoint for manual email processing and review.
    """
    try:
        email_log_id = request.data.get('email_log_id')
        action = request.data.get('action')  # 'process', 'create_lead', 'create_service_request'
        
        if not email_log_id:
            return Response(
                {'error': 'email_log_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from .models import EmailLog
        from .email_parser import EmailParser
        
        try:
            email_log = EmailLog.objects.get(id=email_log_id)
        except EmailLog.DoesNotExist:
            return Response(
                {'error': 'Email log not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        parser = EmailParser()
        
        if action == 'process':
            # Re-process the email
            result = parser.process_email(email_log)
        elif action == 'create_lead':
            # Force create lead
            parsed_data = email_log.parsed_data or {}
            lead_id = parser._create_lead(email_log, parsed_data)
            result = {'action_taken': 'lead_created', 'record_id': lead_id}
            email_log.mark_as_processed(user=request.user, notes="Manually processed as lead")
        elif action == 'create_service_request':
            # Force create service request
            parsed_data = email_log.parsed_data or {}
            sr_id = parser._create_service_request(email_log, parsed_data)
            result = {'action_taken': 'service_request_created', 'record_id': sr_id}
            email_log.mark_as_processed(user=request.user, notes="Manually processed as service request")
        else:
            return Response(
                {'error': 'Invalid action. Use: process, create_lead, or create_service_request'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'message': 'Email processed successfully',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Error in manual email processing: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_email_reviews(request):
    """
    API endpoint to get emails pending manual review.
    """
    try:
        from .models import EmailLog
        
        pending_emails = EmailLog.objects.filter(
            processing_status='manual_review'
        ).order_by('-received_at')[:50]
        
        email_data = []
        for email in pending_emails:
            email_data.append({
                'id': email.id,
                'email_id': email.email_id,
                'sender_email': email.sender_email,
                'sender_name': email.sender_name,
                'subject': email.subject,
                'email_type': email.email_type,
                'confidence_score': float(email.confidence_score),
                'received_at': email.received_at,
                'processing_notes': email.processing_notes,
                'parsed_data': email.parsed_data
            })
        
        return Response({
            'pending_emails': email_data,
            'count': len(email_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting pending email reviews: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Register EmailJS processing task
@TaskRegistry.register('process_emailjs_submission')
def process_emailjs_submission(submission_data):
    """
    Process EmailJS form submission using the email parser.
    Creates leads or service requests based on email content and confidence scoring.
    """
    logger.info(f"Processing EmailJS submission: {submission_data}")
    
    try:
        from .email_parser import process_emailjs_webhook
        
        # Process the webhook data
        result = process_emailjs_webhook(submission_data)
        
        logger.info(f"EmailJS submission processed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing EmailJS submission: {str(e)}")
        return {
            'error': str(e),
            'processed': False
        }