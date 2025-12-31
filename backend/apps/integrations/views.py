"""
Views for integrations app with comprehensive error handling.
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

logger = logging.getLogger(__name__)

from .tasks import TaskManager, TaskRegistry, BackgroundTask
from .error_handler import (
    handle_api_error, 
    error_handler, 
    ErrorCategory, 
    ErrorSeverity,
    safe_external_api_call,
    graceful_degradation
)
from .email_parser import process_emailjs_webhook
from .monitoring import system_monitor, performance_tracker


@handle_api_error
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enqueue_task(request):
    """
    API endpoint to enqueue a background task.
    """
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


@handle_api_error
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_status(request, task_id):
    """
    API endpoint to get task status.
    """
    task_info = TaskManager.get_task_status(task_id)
    
    if not task_info:
        return Response(
            {'error': 'Task not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return Response(task_info)


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
    Webhook endpoint for EmailJS integration with comprehensive error handling.
    Processes form submissions and creates leads/service requests automatically.
    """
    try:
        # Parse the incoming data
        data = json.loads(request.body)
        
        # Log the webhook receipt
        logger.info(f"Received EmailJS webhook: {data}")
        
        # Process the email directly with error handling
        result = safe_external_api_call(
            process_emailjs_webhook,
            data,
            service_name='emailjs_processing'
        )
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': 'Email submission processed successfully',
                'result': result['result']
            })
        else:
            # Log error but return success to EmailJS to prevent retries
            logger.error(f"EmailJS processing failed: {result['error']}")
            return JsonResponse({
                'status': 'received',
                'message': 'Email received and queued for manual processing',
                'error_id': result.get('error_id')
            })
        
    except json.JSONDecodeError as e:
        error_handler.handle_error(
            error=e,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            context={'request_body': request.body.decode('utf-8', errors='ignore')}
        )
        return JsonResponse(
            {'error': 'Invalid JSON'},
            status=400
        )
    except Exception as e:
        error_handler.handle_error(
            error=e,
            category=ErrorCategory.EMAIL_PROCESSING,
            severity=ErrorSeverity.HIGH,
            context={'request_data': request.body.decode('utf-8', errors='ignore')}
        )
        return JsonResponse(
            {'error': 'Internal server error'},
            status=500
        )


# Chatbot data submission endpoint (no authentication required for frontend integration)
@csrf_exempt
@require_http_methods(["POST"])
def chatbot_data_submission(request):
    """
    Endpoint for chatbot data submission from frontend.
    Captures chatbot interactions and creates leads when appropriate.
    """
    try:
        # Parse the incoming data
        data = json.loads(request.body)
        
        # Log the chatbot data receipt
        logger.info(f"Received chatbot data: {data}")
        
        # Enqueue a task to process the chatbot interaction
        task_id = TaskManager.enqueue_task(
            task_name='process_chatbot_interaction',
            kwargs={'interaction_data': data},
            priority=4  # Medium-high priority for chatbot interactions
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Chatbot interaction received and queued for processing',
            'task_id': task_id
        })
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in chatbot data submission")
        return JsonResponse(
            {'error': 'Invalid JSON'},
            status=400
        )
    except Exception as e:
        logger.error(f"Error processing chatbot data: {str(e)}")
        return JsonResponse(
            {'error': 'Internal server error'},
            status=500
        )


# Solar calculator data submission endpoint (no authentication required for frontend integration)
@csrf_exempt
@require_http_methods(["POST"])
def calculator_data_submission(request):
    """
    Endpoint for solar calculator data submission from frontend.
    Captures calculator results and creates leads when contact information is provided.
    """
    try:
        # Parse the incoming data
        data = json.loads(request.body)
        
        # Log the calculator data receipt
        logger.info(f"Received calculator data: {data}")
        
        # Enqueue a task to process the calculator data
        task_id = TaskManager.enqueue_task(
            task_name='process_calculator_data',
            kwargs={'calculator_data': data},
            priority=3  # High priority for calculator interactions (shows strong intent)
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Calculator data received and queued for processing',
            'task_id': task_id
        })
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in calculator data submission")
        return JsonResponse(
            {'error': 'Invalid JSON'},
            status=400
        )
    except Exception as e:
        logger.error(f"Error processing calculator data: {str(e)}")
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


# Register chatbot interaction processing task
@TaskRegistry.register('process_chatbot_interaction')
def process_chatbot_interaction(interaction_data):
    """
    Process chatbot interaction data and create leads when appropriate.
    Analyzes conversation context to determine if lead creation is warranted.
    """
    logger.info(f"Processing chatbot interaction: {interaction_data}")
    
    try:
        from apps.leads.models import Lead, LeadSource
        from apps.integrations.models import ChatbotInteraction
        
        # Extract data from interaction
        user_messages = interaction_data.get('user_messages', [])
        bot_responses = interaction_data.get('bot_responses', [])
        user_info = interaction_data.get('user_info', {})
        conversation_context = interaction_data.get('conversation_context', {})
        
        # Create chatbot interaction record
        chatbot_interaction = ChatbotInteraction.objects.create(
            session_id=interaction_data.get('session_id', ''),
            user_messages=user_messages,
            bot_responses=bot_responses,
            user_info=user_info,
            conversation_context=conversation_context,
            interaction_metadata=interaction_data
        )
        
        # Determine if this should create a lead
        should_create_lead = _analyze_chatbot_interaction_for_lead(interaction_data)
        
        result = {
            'interaction_id': chatbot_interaction.id,
            'processed': True,
            'lead_created': False
        }
        
        if should_create_lead and user_info:
            # Create lead from chatbot interaction
            lead_source, _ = LeadSource.objects.get_or_create(
                name='Chatbot',
                defaults={'description': 'Lead generated from chatbot interaction'}
            )
            
            lead_data = {
                'source': lead_source,
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
                'email': user_info.get('email', ''),
                'phone': user_info.get('phone', ''),
                'interest_level': _determine_interest_level(interaction_data),
                'original_data': interaction_data
            }
            
            # Only create lead if we have at least email or phone
            if lead_data['email'] or lead_data['phone']:
                lead = Lead.objects.create(**lead_data)
                result['lead_created'] = True
                result['lead_id'] = lead.id
                
                # Link the interaction to the lead
                chatbot_interaction.lead = lead
                chatbot_interaction.save()
                
                logger.info(f"Created lead {lead.id} from chatbot interaction")
        
        logger.info(f"Chatbot interaction processed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing chatbot interaction: {str(e)}")
        return {
            'error': str(e),
            'processed': False
        }


# Register calculator data processing task
@TaskRegistry.register('process_calculator_data')
def process_calculator_data(calculator_data):
    """
    Process solar calculator data and create leads when contact information is provided.
    Calculator interactions indicate high purchase intent.
    """
    logger.info(f"Processing calculator data: {calculator_data}")
    
    try:
        from apps.leads.models import Lead, LeadSource
        from apps.integrations.models import CalculatorData
        
        # Extract data from calculator submission
        calculation_results = calculator_data.get('calculation_results', {})
        user_inputs = calculator_data.get('user_inputs', {})
        user_info = calculator_data.get('user_info', {})
        
        # Create calculator data record
        calculator_record = CalculatorData.objects.create(
            session_id=calculator_data.get('session_id', ''),
            calculation_results=calculation_results,
            user_inputs=user_inputs,
            user_info=user_info,
            calculator_metadata=calculator_data
        )
        
        result = {
            'calculator_id': calculator_record.id,
            'processed': True,
            'lead_created': False
        }
        
        # Create lead if user provided contact information
        # Calculator usage indicates high purchase intent
        if user_info and (user_info.get('email') or user_info.get('phone')):
            lead_source, _ = LeadSource.objects.get_or_create(
                name='Solar Calculator',
                defaults={'description': 'Lead generated from solar calculator usage'}
            )
            
            # Extract system details from calculation results
            estimated_capacity = calculation_results.get('system_capacity_kw', 0)
            estimated_savings = calculation_results.get('annual_savings', 0)
            property_type = user_inputs.get('property_type', 'residential')
            
            lead_data = {
                'source': lead_source,
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
                'email': user_info.get('email', ''),
                'phone': user_info.get('phone', ''),
                'interest_level': 'high',  # Calculator usage indicates high intent
                'property_type': property_type,
                'estimated_capacity': estimated_capacity,
                'budget_range': _estimate_budget_range(calculation_results),
                'original_data': calculator_data
            }
            
            lead = Lead.objects.create(**lead_data)
            result['lead_created'] = True
            result['lead_id'] = lead.id
            
            # Link the calculator data to the lead
            calculator_record.lead = lead
            calculator_record.save()
            
            logger.info(f"Created lead {lead.id} from calculator data")
        
        logger.info(f"Calculator data processed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing calculator data: {str(e)}")
        return {
            'error': str(e),
            'processed': False
        }


def _analyze_chatbot_interaction_for_lead(interaction_data):
    """
    Analyze chatbot interaction to determine if a lead should be created.
    Returns True if the interaction indicates purchase intent or information request.
    """
    user_messages = interaction_data.get('user_messages', [])
    user_info = interaction_data.get('user_info', {})
    
    # Check if user provided contact information
    has_contact_info = bool(user_info.get('email') or user_info.get('phone'))
    
    # Keywords that indicate purchase intent or serious inquiry
    intent_keywords = [
        'price', 'cost', 'quote', 'quotation', 'install', 'installation',
        'buy', 'purchase', 'interested', 'contact', 'call', 'visit',
        'solar panel', 'solar system', 'electricity bill', 'savings',
        'maintenance', 'service', 'warranty', 'financing'
    ]
    
    # Check if any user message contains intent keywords
    has_intent = False
    for message in user_messages:
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in intent_keywords):
            has_intent = True
            break
    
    # Create lead if user provided contact info AND showed intent
    return has_contact_info and has_intent


def _determine_interest_level(interaction_data):
    """
    Determine interest level based on chatbot interaction content.
    """
    user_messages = interaction_data.get('user_messages', [])
    
    # High interest keywords
    high_interest_keywords = [
        'quote', 'quotation', 'price', 'cost', 'install', 'buy', 'purchase'
    ]
    
    # Medium interest keywords
    medium_interest_keywords = [
        'interested', 'information', 'details', 'learn more', 'tell me'
    ]
    
    message_text = ' '.join(user_messages).lower()
    
    if any(keyword in message_text for keyword in high_interest_keywords):
        return 'high'
    elif any(keyword in message_text for keyword in medium_interest_keywords):
        return 'medium'
    else:
        return 'low'


def _estimate_budget_range(calculation_results):
    """
    Estimate budget range based on calculator results.
    """
    system_cost = calculation_results.get('total_system_cost', 0)
    
    if system_cost == 0:
        return 'not_specified'
    elif system_cost < 100000:  # Less than 1 lakh
        return 'under_1_lakh'
    elif system_cost < 300000:  # 1-3 lakhs
        return '1_to_3_lakhs'
    elif system_cost < 500000:  # 3-5 lakhs
        return '3_to_5_lakhs'
    elif system_cost < 1000000:  # 5-10 lakhs
        return '5_to_10_lakhs'
    else:
        return 'above_10_lakhs'


# System Monitoring and Health Check Endpoints

@handle_api_error
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_health(request):
    """
    Get comprehensive system health status.
    """
    health_data = system_monitor.get_system_health()
    return Response(health_data)


@handle_api_error
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_metrics(request):
    """
    Get system performance metrics.
    """
    from django.utils import timezone
    
    metrics = {
        'performance': performance_tracker.get_performance_summary(),
        'health': system_monitor.get_system_health(),
        'timestamp': timezone.now()
    }
    return Response(metrics)


@handle_api_error
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def error_dashboard(request):
    """
    Get error dashboard data for monitoring.
    """
    from django.db.models import Count
    from datetime import timedelta
    from django.utils import timezone
    from .models import ErrorLog
    
    # Get error statistics
    one_hour_ago = timezone.now() - timedelta(hours=1)
    one_day_ago = timezone.now() - timedelta(days=1)
    
    # Recent errors by severity
    recent_errors = ErrorLog.objects.filter(
        timestamp__gte=one_hour_ago
    ).values('severity').annotate(
        count=Count('id')
    )
    
    # Recent errors by category
    error_categories = ErrorLog.objects.filter(
        timestamp__gte=one_day_ago
    ).values('category').annotate(
        count=Count('id')
    )
    
    # Unresolved errors
    unresolved_errors = ErrorLog.objects.filter(
        resolved=False,
        timestamp__gte=one_day_ago
    ).order_by('-timestamp')[:10]
    
    # Error trends (last 24 hours by hour)
    error_trends = []
    for i in range(24):
        hour_start = timezone.now() - timedelta(hours=i+1)
        hour_end = timezone.now() - timedelta(hours=i)
        
        hour_errors = ErrorLog.objects.filter(
            timestamp__gte=hour_start,
            timestamp__lt=hour_end
        ).count()
        
        error_trends.append({
            'hour': hour_start.strftime('%H:00'),
            'error_count': hour_errors
        })
    
    error_trends.reverse()  # Show chronologically
    
    dashboard_data = {
        'recent_errors_by_severity': {item['severity']: item['count'] for item in recent_errors},
        'errors_by_category': {item['category']: item['count'] for item in error_categories},
        'unresolved_errors': [
            {
                'id': error.id,
                'error_id': error.error_id,
                'category': error.category,
                'severity': error.severity,
                'error_type': error.error_type,
                'error_message': error.error_message[:100],
                'timestamp': error.timestamp
            }
            for error in unresolved_errors
        ],
        'error_trends': error_trends,
        'total_unresolved': ErrorLog.objects.filter(resolved=False).count(),
        'timestamp': timezone.now()
    }
    
    return Response(dashboard_data)


@handle_api_error
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resolve_error(request, error_id):
    """
    Mark an error as resolved.
    """
    from .models import ErrorLog
    
    try:
        error_log = ErrorLog.objects.get(error_id=error_id)
        resolution_notes = request.data.get('resolution_notes', '')
        
        error_log.mark_as_resolved(
            user=request.user,
            notes=resolution_notes
        )
        
        return Response({
            'message': 'Error marked as resolved',
            'error_id': error_id
        })
        
    except ErrorLog.DoesNotExist:
        return Response(
            {'error': 'Error not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
def health_check(request):
    """
    Simple health check endpoint (no authentication required).
    Used by load balancers and monitoring systems.
    """
    try:
        # Basic health check - just verify database connectivity
        from django.db import connection
        from django.utils import timezone
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now(),
            'version': '1.0.0'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now()
        }, status=503)


@handle_api_error
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_health_check(request):
    """
    Trigger a comprehensive health check and alerting.
    """
    result = system_monitor.check_and_alert()
    return Response(result)


# Configuration endpoints for frontend
@api_view(['GET'])
@permission_classes([])  # No authentication required for config endpoints
def get_cohere_api_key(request):
    """
    Provide Cohere API key for frontend chatbot.
    This endpoint is used by the frontend to get the API key securely.
    """
    try:
        from decouple import config
        
        # Get API key from environment variables using decouple
        api_key = config('COHERE_API_KEY', default='')
        
        if not api_key:
            logger.warning("Cohere API key not found in environment variables")
            return JsonResponse({
                'error': 'Cohere API key not configured'
            }, status=500)
        
        return JsonResponse({
            'api_key': api_key
        })
        
    except Exception as e:
        logger.error(f"Error getting Cohere API key: {str(e)}")
        return JsonResponse({
            'error': 'Failed to get API key'
        }, status=500)