"""
API views for duplicate detection and manual review functionality.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from .models import Lead
from apps.customers.models import Customer
from .services import DuplicateDetectionService, LeadMergingService
from .duplicate_models import DuplicateDetectionResult, ManualReviewQueue, MergeOperation


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_duplicates(request):
    """
    Check for potential duplicates before creating a new lead.
    
    POST /api/leads/check-duplicates/
    {
        "email": "john@example.com",
        "phone": "+91-9876543210",
        "first_name": "John",
        "last_name": "Doe",
        "address": "123 Main St"
    }
    """
    try:
        lead_data = request.data
        
        # Validate required fields
        if not lead_data.get('email') and not lead_data.get('phone'):
            return Response(
                {'error': 'Either email or phone is required for duplicate detection'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Run duplicate detection
        duplicate_service = DuplicateDetectionService()
        detection_result = duplicate_service.process_duplicate_detection(lead_data)
        
        # Store detection result for audit
        detection_record = DuplicateDetectionResult.objects.create(
            input_data=lead_data,
            potential_duplicates=detection_result.get('duplicates', []),
            highest_confidence=detection_result.get('duplicates', [{}])[0].get('confidence', 0.0) if detection_result.get('duplicates') else 0.0,
            recommended_action=detection_result['action'],
            status='auto_processed' if detection_result['action'] in ['create', 'merge'] else 'pending'
        )
        
        # If manual review is needed, add to review queue
        if detection_result['action'] == 'review':
            ManualReviewQueue.objects.create(
                detection_result=detection_record,
                priority='high' if detection_record.highest_confidence > 0.7 else 'medium'
            )
        
        # Format response
        response_data = {
            'detection_id': detection_record.id,
            'action': detection_result['action'],
            'message': detection_result['message'],
            'duplicates': []
        }
        
        # Add duplicate information (without the actual record objects)
        for duplicate in detection_result.get('duplicates', []):
            duplicate_info = {
                'type': duplicate['type'],
                'id': duplicate['id'],
                'confidence': duplicate['confidence'],
                'match_reasons': duplicate['match_reasons'],
                'record_info': {
                    'name': duplicate['record'].full_name,
                    'email': duplicate['record'].email,
                    'phone': duplicate['record'].phone,
                    'created_at': duplicate['record'].created_at.isoformat(),
                }
            }
            response_data['duplicates'].append(duplicate_info)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Duplicate detection failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_duplicate_decision(request, detection_id):
    """
    Process a decision on a duplicate detection result.
    
    POST /api/leads/duplicates/{detection_id}/process/
    {
        "action": "create|merge|ignore",
        "target_id": 123,  // Required for merge action
        "target_type": "lead|customer",  // Required for merge action
        "notes": "Optional notes"
    }
    """
    try:
        detection_result = get_object_or_404(DuplicateDetectionResult, id=detection_id)
        
        action = request.data.get('action')
        target_id = request.data.get('target_id')
        target_type = request.data.get('target_type')
        notes = request.data.get('notes', '')
        
        if action not in ['create', 'merge', 'ignore']:
            return Response(
                {'error': 'Invalid action. Must be create, merge, or ignore'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            if action == 'create':
                # Create new lead
                lead_data = detection_result.input_data
                lead = Lead.objects.create(
                    first_name=lead_data.get('first_name', ''),
                    last_name=lead_data.get('last_name', ''),
                    email=lead_data.get('email', ''),
                    phone=lead_data.get('phone', ''),
                    address=lead_data.get('address', ''),
                    city=lead_data.get('city', ''),
                    state=lead_data.get('state', ''),
                    pincode=lead_data.get('pincode', ''),
                    source_id=lead_data.get('source_id', 1),  # Default source
                    original_data=lead_data
                )
                
                detection_result.created_lead_id = lead.id
                detection_result.mark_as_processed('create', request.user, notes)
                
                response_data = {
                    'action': 'create',
                    'lead_id': lead.id,
                    'message': 'New lead created successfully'
                }
                
            elif action == 'merge':
                if not target_id or not target_type:
                    return Response(
                        {'error': 'target_id and target_type are required for merge action'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                merging_service = LeadMergingService()
                lead_data = detection_result.input_data
                
                # Create a temporary lead for merging
                temp_lead = Lead(
                    first_name=lead_data.get('first_name', ''),
                    last_name=lead_data.get('last_name', ''),
                    email=lead_data.get('email', ''),
                    phone=lead_data.get('phone', ''),
                    address=lead_data.get('address', ''),
                    city=lead_data.get('city', ''),
                    state=lead_data.get('state', ''),
                    pincode=lead_data.get('pincode', ''),
                    source_id=lead_data.get('source_id', 1),
                    original_data=lead_data
                )
                
                if target_type == 'lead':
                    target_lead = get_object_or_404(Lead, id=target_id)
                    
                    # Create merge operation record
                    merge_op = MergeOperation.objects.create(
                        merge_type='lead_to_lead',
                        source_record_type='lead',
                        source_record_id=0,  # Temporary lead, no ID yet
                        source_record_data=lead_data,
                        target_record_type='lead',
                        target_record_id=target_id,
                        target_record_data_before={
                            'first_name': target_lead.first_name,
                            'last_name': target_lead.last_name,
                            'email': target_lead.email,
                            'phone': target_lead.phone,
                            'address': target_lead.address,
                            'notes': target_lead.notes,
                        },
                        initiated_by=request.user,
                        confidence_score=detection_result.highest_confidence
                    )
                    
                    merge_op.start_merge()
                    
                    # Save temp lead first to get an ID
                    temp_lead.save()
                    merge_op.source_record_id = temp_lead.id
                    merge_op.save()
                    
                    # Perform merge
                    merged_lead = merging_service.merge_leads(target_lead, temp_lead, request.user)
                    
                    merge_op.complete_merge({
                        'first_name': merged_lead.first_name,
                        'last_name': merged_lead.last_name,
                        'email': merged_lead.email,
                        'phone': merged_lead.phone,
                        'address': merged_lead.address,
                        'notes': merged_lead.notes,
                    })
                    
                    detection_result.merged_into_id = target_id
                    detection_result.merged_into_type = 'lead'
                    
                    response_data = {
                        'action': 'merge',
                        'merged_into_lead_id': target_id,
                        'message': 'Successfully merged into existing lead'
                    }
                    
                elif target_type == 'customer':
                    target_customer = get_object_or_404(Customer, id=target_id)
                    
                    # Create merge operation record
                    merge_op = MergeOperation.objects.create(
                        merge_type='lead_to_customer',
                        source_record_type='lead',
                        source_record_id=0,  # Temporary lead, no ID yet
                        source_record_data=lead_data,
                        target_record_type='customer',
                        target_record_id=target_id,
                        target_record_data_before={
                            'first_name': target_customer.first_name,
                            'last_name': target_customer.last_name,
                            'email': target_customer.email,
                            'phone': target_customer.phone,
                            'notes': target_customer.notes,
                        },
                        initiated_by=request.user,
                        confidence_score=detection_result.highest_confidence
                    )
                    
                    merge_op.start_merge()
                    
                    # Save temp lead first to get an ID
                    temp_lead.save()
                    merge_op.source_record_id = temp_lead.id
                    merge_op.save()
                    
                    # Perform merge
                    merged_customer = merging_service.merge_lead_with_customer(temp_lead, target_customer, request.user)
                    
                    merge_op.complete_merge({
                        'first_name': merged_customer.first_name,
                        'last_name': merged_customer.last_name,
                        'email': merged_customer.email,
                        'phone': merged_customer.phone,
                        'notes': merged_customer.notes,
                    })
                    
                    detection_result.merged_into_id = target_id
                    detection_result.merged_into_type = 'customer'
                    
                    response_data = {
                        'action': 'merge',
                        'merged_into_customer_id': target_id,
                        'message': 'Successfully merged into existing customer'
                    }
                
                detection_result.mark_as_processed('merge', request.user, notes)
                
            else:  # action == 'ignore'
                detection_result.mark_as_processed('ignore', request.user, notes)
                response_data = {
                    'action': 'ignore',
                    'message': 'Duplicate detection result ignored'
                }
            
            # Update review queue if exists
            if hasattr(detection_result, 'review_queue_item'):
                detection_result.review_queue_item.complete_review(action, notes, request.user)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to process duplicate decision: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manual_review_queue(request):
    """
    Get list of items in manual review queue.
    
    GET /api/leads/manual-review/
    """
    try:
        # Filter by status if provided
        status_filter = request.GET.get('status', 'pending')
        assigned_to_me = request.GET.get('assigned_to_me', 'false').lower() == 'true'
        
        queryset = ManualReviewQueue.objects.select_related('detection_result', 'assigned_to')
        
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        if assigned_to_me:
            queryset = queryset.filter(assigned_to=request.user)
        
        review_items = []
        for item in queryset:
            detection = item.detection_result
            
            # Get duplicate information
            duplicates = []
            for dup_data in detection.potential_duplicates:
                if dup_data.get('type') == 'lead':
                    try:
                        lead = Lead.objects.get(id=dup_data.get('id'))
                        duplicates.append({
                            'type': 'lead',
                            'id': lead.id,
                            'name': lead.full_name,
                            'email': lead.email,
                            'phone': lead.phone,
                            'confidence': dup_data.get('confidence', 0),
                            'match_reasons': dup_data.get('match_reasons', [])
                        })
                    except Lead.DoesNotExist:
                        continue
                elif dup_data.get('type') == 'customer':
                    try:
                        customer = Customer.objects.get(id=dup_data.get('id'))
                        duplicates.append({
                            'type': 'customer',
                            'id': customer.id,
                            'name': customer.full_name,
                            'email': customer.email,
                            'phone': customer.phone,
                            'confidence': dup_data.get('confidence', 0),
                            'match_reasons': dup_data.get('match_reasons', [])
                        })
                    except Customer.DoesNotExist:
                        continue
            
            review_items.append({
                'id': item.id,
                'detection_id': detection.id,
                'priority': item.priority,
                'status': item.status,
                'assigned_to': item.assigned_to.username if item.assigned_to else None,
                'created_at': item.created_at.isoformat(),
                'input_data': detection.input_data,
                'highest_confidence': detection.highest_confidence,
                'recommended_action': detection.recommended_action,
                'duplicates': duplicates,
                'reviewer_notes': item.reviewer_notes
            })
        
        return Response({
            'review_items': review_items,
            'total_count': len(review_items)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch review queue: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_review(request, review_id):
    """
    Assign a review item to a user.
    
    POST /api/leads/manual-review/{review_id}/assign/
    {
        "user_id": 123  // Optional, defaults to current user
    }
    """
    try:
        review_item = get_object_or_404(ManualReviewQueue, id=review_id)
        
        user_id = request.data.get('user_id')
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            assigned_user = get_object_or_404(User, id=user_id)
        else:
            assigned_user = request.user
        
        review_item.assign_to_user(assigned_user)
        
        return Response({
            'message': f'Review assigned to {assigned_user.username}',
            'assigned_to': assigned_user.username,
            'status': review_item.status
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to assign review: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def merge_history(request):
    """
    Get history of merge operations.
    
    GET /api/leads/merge-history/
    """
    try:
        # Filter parameters
        merge_type = request.GET.get('type', 'all')
        status_filter = request.GET.get('status', 'all')
        limit = int(request.GET.get('limit', 50))
        
        queryset = MergeOperation.objects.select_related('initiated_by')
        
        if merge_type != 'all':
            queryset = queryset.filter(merge_type=merge_type)
        
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        queryset = queryset[:limit]
        
        merge_operations = []
        for op in queryset:
            merge_operations.append({
                'id': op.id,
                'merge_type': op.merge_type,
                'status': op.status,
                'source_record_type': op.source_record_type,
                'source_record_id': op.source_record_id,
                'target_record_type': op.target_record_type,
                'target_record_id': op.target_record_id,
                'confidence_score': op.confidence_score,
                'initiated_by': op.initiated_by.username if op.initiated_by else None,
                'created_at': op.created_at.isoformat(),
                'completed_at': op.completed_at.isoformat() if op.completed_at else None,
                'error_message': op.error_message,
                'notes': op.notes
            })
        
        return Response({
            'merge_operations': merge_operations,
            'total_count': len(merge_operations)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch merge history: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )