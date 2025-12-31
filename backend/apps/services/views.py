from django.shortcuts import render
from django.db.models import Q, Sum, Count, Avg
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from .models import (
    ServiceRequest, InstallationProject, AMCContract, ServiceRequestStatusHistory, 
    AMCRenewalAlert, ProjectStatusHistory, ProjectMilestone, ProjectNotification,
    PaymentMilestone, Invoice, Payment, FinancialSummary
)
from .serializers import (
    ServiceRequestListSerializer, ServiceRequestDetailSerializer,
    ServiceRequestCreateSerializer, ServiceRequestUpdateSerializer,
    ServiceRequestStatusUpdateSerializer, InstallationProjectListSerializer,
    InstallationProjectDetailSerializer, AMCContractListSerializer,
    AMCContractDetailSerializer, ServiceRequestStatusHistorySerializer,
    AMCRenewalAlertSerializer, ProjectMilestoneSerializer, ProjectNotificationSerializer,
    PaymentMilestoneSerializer, InvoiceListSerializer, InvoiceDetailSerializer,
    InvoiceCreateSerializer, PaymentSerializer, PaymentCreateSerializer,
    PaymentStatusUpdateSerializer, FinancialSummarySerializer, FinancialDashboardSerializer
)

User = get_user_model()


class ServiceRequestListCreateView(generics.ListCreateAPIView):
    """
    List all service requests or create a new service request.
    
    GET: Returns paginated list of service requests with filtering and search
    POST: Creates a new service request
    """
    queryset = ServiceRequest.objects.select_related('customer', 'assigned_to', 'installation_project').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'request_type', 'assigned_to', 'customer']
    search_fields = ['ticket_number', 'subject', 'customer__first_name', 'customer__last_name', 'customer__email']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'resolved_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ServiceRequestCreateSerializer
        return ServiceRequestListSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # If user is support staff, only show assigned requests
        if user.role == 'support_staff':
            queryset = queryset.filter(assigned_to=user)
        # If user is sales staff, show requests for their customers
        elif user.role == 'sales_staff':
            queryset = queryset.filter(customer__assigned_to=user)
        # Managers and owners see all
        
        return queryset


class ServiceRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a service request.
    
    GET: Returns detailed service request information
    PUT/PATCH: Updates service request information
    DELETE: Deletes the service request
    """
    queryset = ServiceRequest.objects.select_related('customer', 'assigned_to', 'installation_project').all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ServiceRequestUpdateSerializer
        return ServiceRequestDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Apply same permission logic as list view
        if user.role == 'support_staff':
            queryset = queryset.filter(assigned_to=user)
        elif user.role == 'sales_staff':
            queryset = queryset.filter(customer__assigned_to=user)
        
        return queryset


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_service_request_status(request, request_id):
    """
    Update service request status with validation.
    
    POST: Updates the service request status and handles resolution/closure
    """
    try:
        service_request = ServiceRequest.objects.get(id=request_id)
    except ServiceRequest.DoesNotExist:
        return Response(
            {'error': 'Service request not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            service_request.assigned_to == user or 
            (user.role == 'sales_staff' and service_request.customer.assigned_to == user)):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ServiceRequestStatusUpdateSerializer(data=request.data)
    if serializer.is_valid():
        new_status = serializer.validated_data['status']
        resolution_notes = serializer.validated_data.get('resolution_notes', '')
        customer_satisfaction = serializer.validated_data.get('customer_satisfaction')
        
        try:
            old_status = service_request.status
            
            # Use the new update_status method for proper tracking
            service_request.update_status(
                new_status=new_status,
                changed_by=request.user,
                notes=resolution_notes
            )
            
            if customer_satisfaction:
                service_request.customer_satisfaction = customer_satisfaction
                service_request.save(update_fields=['customer_satisfaction', 'updated_at'])
            
            return Response({
                'message': 'Service request status updated successfully',
                'old_status': old_status,
                'new_status': new_status,
                'ticket_number': service_request.ticket_number
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to update status: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InstallationProjectListCreateView(generics.ListCreateAPIView):
    """
    List all installation projects or create a new project.
    """
    queryset = InstallationProject.objects.select_related('customer', 'project_manager', 'sales_person').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'customer', 'project_manager', 'sales_person']
    search_fields = ['project_number', 'customer__first_name', 'customer__last_name', 'customer__company_name']
    ordering_fields = ['created_at', 'updated_at', 'project_value', 'progress_percentage']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        return InstallationProjectListSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # If user is sales staff, only show their projects
        if user.role == 'sales_staff':
            queryset = queryset.filter(Q(sales_person=user) | Q(customer__assigned_to=user))
        
        return queryset


class InstallationProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete an installation project.
    """
    queryset = InstallationProject.objects.select_related('customer', 'project_manager', 'sales_person').all()
    serializer_class = InstallationProjectDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Apply same permission logic as list view
        if user.role == 'sales_staff':
            queryset = queryset.filter(Q(sales_person=user) | Q(customer__assigned_to=user))
        
        return queryset


class AMCContractListCreateView(generics.ListCreateAPIView):
    """
    List all AMC contracts or create a new contract.
    """
    queryset = AMCContract.objects.select_related('customer', 'installation_project', 'contact_person').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'customer', 'contact_person']
    search_fields = ['contract_number', 'customer__first_name', 'customer__last_name', 'customer__company_name']
    ordering_fields = ['created_at', 'updated_at', 'end_date', 'annual_value']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        return AMCContractListSerializer


class AMCContractDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete an AMC contract.
    """
    queryset = AMCContract.objects.select_related('customer', 'installation_project', 'contact_person').all()
    serializer_class = AMCContractDetailSerializer
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_request_search(request):
    """
    Advanced service request search with multiple criteria.
    
    GET: Search service requests by various criteria
    """
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    request_type_filter = request.GET.get('request_type', '')
    assigned_to_filter = request.GET.get('assigned_to', '')
    customer_filter = request.GET.get('customer', '')
    
    queryset = ServiceRequest.objects.select_related('customer', 'assigned_to', 'installation_project').all()
    
    # Apply user permissions
    user = request.user
    if user.role == 'support_staff':
        queryset = queryset.filter(assigned_to=user)
    elif user.role == 'sales_staff':
        queryset = queryset.filter(customer__assigned_to=user)
    
    # Apply search filters
    if query:
        queryset = queryset.filter(
            Q(ticket_number__icontains=query) |
            Q(subject__icontains=query) |
            Q(description__icontains=query) |
            Q(customer__first_name__icontains=query) |
            Q(customer__last_name__icontains=query) |
            Q(customer__email__icontains=query)
        )
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if priority_filter:
        queryset = queryset.filter(priority=priority_filter)
    
    if request_type_filter:
        queryset = queryset.filter(request_type=request_type_filter)
    
    if assigned_to_filter:
        queryset = queryset.filter(assigned_to_id=assigned_to_filter)
    
    if customer_filter:
        queryset = queryset.filter(customer_id=customer_filter)
    
    # Paginate results
    from django.core.paginator import Paginator
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    serializer = ServiceRequestListSerializer(page_obj, many=True)
    
    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_request_status_history(request, request_id):
    """
    Get status history for a service request.
    
    GET: Returns chronological status changes for the service request
    """
    try:
        service_request = ServiceRequest.objects.get(id=request_id)
    except ServiceRequest.DoesNotExist:
        return Response(
            {'error': 'Service request not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            service_request.assigned_to == user or 
            (user.role == 'sales_staff' and service_request.customer.assigned_to == user)):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    history = service_request.status_history.all()
    serializer = ServiceRequestStatusHistorySerializer(history, many=True)
    
    return Response({
        'ticket_number': service_request.ticket_number,
        'current_status': service_request.status,
        'status_history': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_request_workflow_info(request, request_id):
    """
    Get workflow information for a service request.
    
    GET: Returns current status, valid next statuses, and workflow metadata
    """
    try:
        service_request = ServiceRequest.objects.get(id=request_id)
    except ServiceRequest.DoesNotExist:
        return Response(
            {'error': 'Service request not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            service_request.assigned_to == user or 
            (user.role == 'sales_staff' and service_request.customer.assigned_to == user)):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    return Response({
        'ticket_number': service_request.ticket_number,
        'current_status': service_request.status,
        'current_status_display': service_request.get_status_display(),
        'valid_next_statuses': service_request.get_next_valid_statuses(),
        'is_overdue': service_request.is_overdue,
        'age_in_hours': service_request.age_in_hours,
        'time_to_resolution': service_request.time_to_resolution.total_seconds() / 3600 if service_request.time_to_resolution else None,
        'can_be_closed': service_request.status in ['resolved'],
        'can_be_reopened': service_request.status in ['closed', 'resolved']
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_service_request(request, request_id):
    """
    Assign service request to a user.
    
    POST: Assigns the service request to specified user
    """
    try:
        service_request = ServiceRequest.objects.get(id=request_id)
    except ServiceRequest.DoesNotExist:
        return Response(
            {'error': 'Service request not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions - only managers and owners can assign
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager']):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    assigned_to_id = request.data.get('assigned_to')
    if not assigned_to_id:
        return Response(
            {'error': 'assigned_to field is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        assigned_user = User.objects.get(id=assigned_to_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'Assigned user not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Validate that user can be assigned service requests
    if assigned_user.role not in ['support_staff', 'sales_staff', 'sales_manager', 'owner']:
        return Response(
            {'error': 'User cannot be assigned service requests'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    old_assigned_to = service_request.assigned_to
    service_request.assigned_to = assigned_user
    service_request.save(update_fields=['assigned_to', 'updated_at'])
    
    return Response({
        'message': 'Service request assigned successfully',
        'ticket_number': service_request.ticket_number,
        'old_assigned_to': old_assigned_to.get_full_name() if old_assigned_to else None,
        'new_assigned_to': assigned_user.get_full_name()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_request_dashboard_stats(request):
    """
    Get dashboard statistics for service requests.
    
    GET: Returns various statistics for dashboard display
    """
    user = request.user
    
    # Base queryset based on user permissions
    queryset = ServiceRequest.objects.all()
    if user.role == 'support_staff':
        queryset = queryset.filter(assigned_to=user)
    elif user.role == 'sales_staff':
        queryset = queryset.filter(customer__assigned_to=user)
    
    # Calculate statistics
    total_requests = queryset.count()
    open_requests = queryset.filter(status='open').count()
    in_progress_requests = queryset.filter(status='in_progress').count()
    pending_requests = queryset.filter(status__in=['pending_customer', 'pending_parts']).count()
    resolved_requests = queryset.filter(status='resolved').count()
    closed_requests = queryset.filter(status='closed').count()
    
    # Overdue requests
    overdue_requests = []
    for request in queryset.filter(status__in=['open', 'in_progress', 'pending_customer', 'pending_parts']):
        if request.is_overdue:
            overdue_requests.append(request)
    
    # Recent requests (last 7 days)
    from datetime import timedelta
    recent_date = timezone.now() - timedelta(days=7)
    recent_requests = queryset.filter(created_at__gte=recent_date).count()
    
    # Average resolution time (in hours)
    resolved_with_time = queryset.filter(resolved_at__isnull=False)
    avg_resolution_time = None
    if resolved_with_time.exists():
        total_time = sum([
            (req.resolved_at - req.created_at).total_seconds() / 3600 
            for req in resolved_with_time
        ])
        avg_resolution_time = total_time / resolved_with_time.count()
    
    return Response({
        'total_requests': total_requests,
        'open_requests': open_requests,
        'in_progress_requests': in_progress_requests,
        'pending_requests': pending_requests,
        'resolved_requests': resolved_requests,
        'closed_requests': closed_requests,
        'overdue_requests': len(overdue_requests),
        'recent_requests': recent_requests,
        'avg_resolution_time_hours': avg_resolution_time,
        'overdue_tickets': [
            {
                'ticket_number': req.ticket_number,
                'subject': req.subject,
                'customer_name': req.customer.full_name,
                'age_hours': req.age_in_hours,
                'priority': req.priority
            } for req in overdue_requests[:10]  # Limit to 10 most overdue
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def amc_contract_renewal_alerts(request):
    """
    Get AMC contract renewal alerts.
    
    GET: Returns contracts needing renewal alerts and pending alerts
    """
    user = request.user
    
    # Get contracts needing renewal alerts (next 30 days)
    contracts_needing_alerts = AMCContract.get_contracts_needing_renewal_alerts(30)
    
    # Get expired contracts
    expired_contracts = AMCContract.get_expired_contracts()
    
    # Get contracts expiring soon
    expiring_soon = AMCContract.get_expiring_soon_contracts(30)
    
    # Get pending alerts
    pending_alerts = AMCRenewalAlert.get_pending_alerts()
    
    return Response({
        'contracts_needing_alerts': AMCContractListSerializer(contracts_needing_alerts, many=True).data,
        'expired_contracts': AMCContractListSerializer(expired_contracts, many=True).data,
        'expiring_soon': AMCContractListSerializer(expiring_soon, many=True).data,
        'pending_alerts': AMCRenewalAlertSerializer(pending_alerts, many=True).data,
        'summary': {
            'total_needing_alerts': contracts_needing_alerts.count(),
            'total_expired': expired_contracts.count(),
            'total_expiring_soon': expiring_soon.count(),
            'total_pending_alerts': pending_alerts.count()
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_amc_renewal_alerts(request, contract_id):
    """
    Create renewal alerts for an AMC contract.
    
    POST: Creates all necessary renewal alerts for the contract
    """
    try:
        amc_contract = AMCContract.objects.get(id=contract_id)
    except AMCContract.DoesNotExist:
        return Response(
            {'error': 'AMC contract not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager']):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Create alerts
    alerts_created = AMCRenewalAlert.create_alerts_for_contract(amc_contract)
    
    return Response({
        'message': f'Created {len(alerts_created)} renewal alerts',
        'contract_number': amc_contract.contract_number,
        'alerts_created': len(alerts_created),
        'alerts': AMCRenewalAlertSerializer(alerts_created, many=True).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def acknowledge_renewal_alert(request, alert_id):
    """
    Acknowledge a renewal alert.
    
    POST: Marks the renewal alert as acknowledged
    """
    try:
        alert = AMCRenewalAlert.objects.get(id=alert_id)
    except AMCRenewalAlert.DoesNotExist:
        return Response(
            {'error': 'Renewal alert not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager', 'sales_staff']):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    notes = request.data.get('notes', '')
    alert.acknowledge(user, notes)
    
    return Response({
        'message': 'Renewal alert acknowledged',
        'alert_id': alert.id,
        'contract_number': alert.amc_contract.contract_number,
        'acknowledged_by': user.get_full_name(),
        'acknowledged_at': alert.acknowledged_at
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def renew_amc_contract(request, contract_id):
    """
    Renew an AMC contract.
    
    POST: Renews the contract with new end date and optionally new value
    """
    try:
        amc_contract = AMCContract.objects.get(id=contract_id)
    except AMCContract.DoesNotExist:
        return Response(
            {'error': 'AMC contract not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager']):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    new_end_date_str = request.data.get('new_end_date')
    new_annual_value = request.data.get('new_annual_value')
    
    if not new_end_date_str:
        return Response(
            {'error': 'new_end_date is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from datetime import datetime
        new_end_date = datetime.strptime(new_end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate new end date is in the future
    if new_end_date <= amc_contract.end_date:
        return Response(
            {'error': 'New end date must be after current end date'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    old_end_date = amc_contract.end_date
    old_annual_value = amc_contract.annual_value
    
    # Renew the contract
    amc_contract.renew_contract(new_end_date, new_annual_value)
    
    # Create new renewal alerts for the renewed contract
    AMCRenewalAlert.create_alerts_for_contract(amc_contract)
    
    return Response({
        'message': 'AMC contract renewed successfully',
        'contract_number': amc_contract.contract_number,
        'old_end_date': old_end_date,
        'new_end_date': new_end_date,
        'old_annual_value': old_annual_value,
        'new_annual_value': amc_contract.annual_value,
        'new_status': amc_contract.status
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_renewal_alerts(request):
    """
    Process pending renewal alerts (send notifications).
    
    POST: Processes all pending alerts that should be sent today
    """
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager']):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    pending_alerts = AMCRenewalAlert.get_pending_alerts()
    processed_alerts = []
    
    for alert in pending_alerts:
        # In a real implementation, you would send actual emails here
        # For now, we'll just mark them as sent
        
        # Get email addresses to send to
        emails_to_send = []
        
        # Add customer email
        if alert.amc_contract.customer.email:
            emails_to_send.append(alert.amc_contract.customer.email)
        
        # Add contact person email
        if alert.amc_contract.contact_person and alert.amc_contract.contact_person.email:
            emails_to_send.append(alert.amc_contract.contact_person.email)
        
        # Add sales person email if available
        if hasattr(alert.amc_contract.customer, 'assigned_to') and alert.amc_contract.customer.assigned_to:
            if alert.amc_contract.customer.assigned_to.email:
                emails_to_send.append(alert.amc_contract.customer.assigned_to.email)
        
        if emails_to_send:
            alert.mark_as_sent(emails_to_send)
            processed_alerts.append(alert)
            
            # Also mark the contract renewal reminder as sent
            if alert.alert_type in ['30_days', '15_days', '7_days']:
                alert.amc_contract.mark_renewal_reminder_sent()
    
    return Response({
        'message': f'Processed {len(processed_alerts)} renewal alerts',
        'processed_alerts': len(processed_alerts),
        'alerts_processed': [
            {
                'contract_number': alert.amc_contract.contract_number,
                'alert_type': alert.get_alert_type_display(),
                'sent_to': alert.sent_to,
                'sent_at': alert.sent_at
            } for alert in processed_alerts
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def amc_contract_dashboard_stats(request):
    """
    Get dashboard statistics for AMC contracts.
    
    GET: Returns various statistics for dashboard display
    """
    user = request.user
    
    # Base queryset
    queryset = AMCContract.objects.all()
    
    # Calculate statistics
    total_contracts = queryset.count()
    active_contracts = queryset.filter(status='active').count()
    expired_contracts = queryset.filter(status='expired').count()
    renewal_pending = queryset.filter(status='renewal_pending').count()
    
    # Contracts expiring in next 30 days
    expiring_soon = AMCContract.get_expiring_soon_contracts(30).count()
    
    # Contracts needing renewal alerts
    needing_alerts = AMCContract.get_contracts_needing_renewal_alerts(30).count()
    
    # Total annual value of active contracts
    active_contracts_qs = queryset.filter(status='active')
    total_annual_value = sum([contract.annual_value for contract in active_contracts_qs])
    
    # Recent contracts (last 30 days)
    from datetime import timedelta
    recent_date = timezone.now() - timedelta(days=30)
    recent_contracts = queryset.filter(created_at__gte=recent_date).count()
    
    # Pending alerts
    pending_alerts = AMCRenewalAlert.objects.filter(status='pending').count()
    
    return Response({
        'total_contracts': total_contracts,
        'active_contracts': active_contracts,
        'expired_contracts': expired_contracts,
        'renewal_pending': renewal_pending,
        'expiring_soon': expiring_soon,
        'needing_alerts': needing_alerts,
        'total_annual_value': total_annual_value,
        'recent_contracts': recent_contracts,
        'pending_alerts': pending_alerts,
        'contracts_by_status': {
            'active': active_contracts,
            'expired': expired_contracts,
            'renewal_pending': renewal_pending,
            'cancelled': queryset.filter(status='cancelled').count(),
            'suspended': queryset.filter(status='suspended').count()
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_project_status(request, project_id):
    """
    Update installation project status with stakeholder notification.
    
    POST: Updates project status and creates notifications
    """
    try:
        project = InstallationProject.objects.get(id=project_id)
    except InstallationProject.DoesNotExist:
        return Response(
            {'error': 'Installation project not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            project.project_manager == user or project.sales_person == user):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    new_status = request.data.get('status')
    notes = request.data.get('notes', '')
    
    if not new_status:
        return Response(
            {'error': 'status field is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate status
    valid_statuses = [choice[0] for choice in InstallationProject.PROJECT_STATUS_CHOICES]
    if new_status not in valid_statuses:
        return Response(
            {'error': f'Invalid status. Valid options: {valid_statuses}'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    old_status = project.status
    project.update_status_with_notification(new_status, user, notes)
    
    return Response({
        'message': 'Project status updated successfully',
        'project_number': project.project_number,
        'old_status': old_status,
        'new_status': new_status,
        'progress_percentage': project.progress_percentage
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_milestones(request, project_id):
    """
    Get milestones for an installation project.
    
    GET: Returns project milestones and progress information
    """
    try:
        project = InstallationProject.objects.get(id=project_id)
    except InstallationProject.DoesNotExist:
        return Response(
            {'error': 'Installation project not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            project.project_manager == user or project.sales_person == user or
            (user.role == 'sales_staff' and project.customer.assigned_to == user)):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get custom milestones
    custom_milestones = project.milestones.all()
    
    # Get system-generated milestones
    system_milestones = project.get_project_milestones()
    
    return Response({
        'project_number': project.project_number,
        'current_status': project.status,
        'progress_percentage': project.progress_percentage,
        'system_milestones': system_milestones,
        'custom_milestones': ProjectMilestoneSerializer(custom_milestones, many=True).data,
        'project_duration_days': project.project_duration_days,
        'is_overdue': project.is_overdue
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_project_milestone(request, project_id):
    """
    Create a custom milestone for an installation project.
    
    POST: Creates a new milestone for the project
    """
    try:
        project = InstallationProject.objects.get(id=project_id)
    except InstallationProject.DoesNotExist:
        return Response(
            {'error': 'Installation project not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            project.project_manager == user):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ProjectMilestoneSerializer(data=request.data)
    if serializer.is_valid():
        milestone = serializer.save(installation_project=project)
        return Response({
            'message': 'Milestone created successfully',
            'milestone': ProjectMilestoneSerializer(milestone).data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_project_milestone(request, milestone_id):
    """
    Mark a project milestone as completed.
    
    POST: Marks milestone as completed and creates notifications
    """
    try:
        milestone = ProjectMilestone.objects.get(id=milestone_id)
    except ProjectMilestone.DoesNotExist:
        return Response(
            {'error': 'Project milestone not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    project = milestone.installation_project
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            project.project_manager == user or milestone.assigned_to == user):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if milestone.status == 'completed':
        return Response(
            {'error': 'Milestone is already completed'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    notes = request.data.get('notes', '')
    milestone.mark_as_completed(user, notes)
    
    return Response({
        'message': 'Milestone marked as completed',
        'milestone_id': milestone.id,
        'milestone_name': milestone.name,
        'completed_date': milestone.actual_date,
        'project_number': project.project_number
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_notifications(request, project_id):
    """
    Get notifications for an installation project.
    
    GET: Returns project notifications and their status
    """
    try:
        project = InstallationProject.objects.get(id=project_id)
    except InstallationProject.DoesNotExist:
        return Response(
            {'error': 'Installation project not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            project.project_manager == user or project.sales_person == user):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    notifications = project.notifications.all()
    
    return Response({
        'project_number': project.project_number,
        'notifications': ProjectNotificationSerializer(notifications, many=True).data,
        'summary': {
            'total_notifications': notifications.count(),
            'pending_notifications': notifications.filter(status='pending').count(),
            'sent_notifications': notifications.filter(status='sent').count(),
            'failed_notifications': notifications.filter(status='failed').count()
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_project_notifications(request):
    """
    Send pending project notifications.
    
    POST: Processes and sends all pending project notifications
    """
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager']):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    pending_notifications = ProjectNotification.objects.filter(status='pending')
    sent_notifications = []
    
    for notification in pending_notifications:
        # In a real implementation, you would send actual emails here
        # For now, we'll just mark them as sent
        if notification.recipients:
            notification.mark_as_sent()
            sent_notifications.append(notification)
    
    return Response({
        'message': f'Sent {len(sent_notifications)} project notifications',
        'sent_count': len(sent_notifications),
        'notifications_sent': [
            {
                'project_number': notif.installation_project.project_number,
                'notification_type': notif.get_notification_type_display(),
                'recipients': notif.recipients,
                'sent_at': notif.sent_at
            } for notif in sent_notifications
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def installation_project_dashboard_stats(request):
    """
    Get dashboard statistics for installation projects.
    
    GET: Returns various statistics for dashboard display
    """
    user = request.user
    
    # Base queryset based on user permissions
    queryset = InstallationProject.objects.all()
    if user.role == 'sales_staff':
        queryset = queryset.filter(Q(sales_person=user) | Q(customer__assigned_to=user))
    
    # Calculate statistics
    total_projects = queryset.count()
    
    # Projects by status
    status_counts = {}
    for status_choice in InstallationProject.PROJECT_STATUS_CHOICES:
        status_key = status_choice[0]
        status_counts[status_key] = queryset.filter(status=status_key).count()
    
    # Financial statistics
    total_project_value = sum([project.project_value for project in queryset])
    total_amount_paid = sum([project.amount_paid for project in queryset])
    total_outstanding = total_project_value - total_amount_paid
    
    # Overdue projects
    overdue_projects = InstallationProject.get_overdue_projects()
    overdue_count = len([p for p in overdue_projects if p in queryset])
    
    # Recent projects (last 30 days)
    from datetime import timedelta
    recent_date = timezone.now() - timedelta(days=30)
    recent_projects = queryset.filter(created_at__gte=recent_date).count()
    
    # Completed projects this month
    this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    completed_this_month = queryset.filter(
        status='completed',
        completion_date__gte=this_month_start.date()
    ).count()
    
    # Average project value
    avg_project_value = total_project_value / total_projects if total_projects > 0 else 0
    
    return Response({
        'total_projects': total_projects,
        'projects_by_status': status_counts,
        'financial_summary': {
            'total_project_value': total_project_value,
            'total_amount_paid': total_amount_paid,
            'total_outstanding': total_outstanding,
            'avg_project_value': avg_project_value
        },
        'overdue_projects': overdue_count,
        'recent_projects': recent_projects,
        'completed_this_month': completed_this_month,
        'active_projects': status_counts.get('installation', 0) + status_counts.get('testing', 0),
        'pending_approval': status_counts.get('quotation', 0),
        'in_design': status_counts.get('design', 0) + status_counts.get('permits', 0)
    })


# Financial Management Views

class PaymentMilestoneListCreateView(generics.ListCreateAPIView):
    """
    List all payment milestones or create a new milestone.
    """
    queryset = PaymentMilestone.objects.select_related('installation_project', 'installation_project__customer').all()
    serializer_class = PaymentMilestoneSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'milestone_type', 'installation_project', 'installation_project__customer']
    search_fields = ['name', 'installation_project__project_number', 'installation_project__customer__first_name', 'installation_project__customer__last_name']
    ordering_fields = ['due_date', 'amount', 'created_at']
    ordering = ['due_date']
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # If user is sales staff, only show their projects' milestones
        if user.role == 'sales_staff':
            queryset = queryset.filter(
                Q(installation_project__sales_person=user) | 
                Q(installation_project__customer__assigned_to=user)
            )
        
        return queryset


class PaymentMilestoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a payment milestone.
    """
    queryset = PaymentMilestone.objects.select_related('installation_project', 'installation_project__customer').all()
    serializer_class = PaymentMilestoneSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Apply same permission logic as list view
        if user.role == 'sales_staff':
            queryset = queryset.filter(
                Q(installation_project__sales_person=user) | 
                Q(installation_project__customer__assigned_to=user)
            )
        
        return queryset


class InvoiceListCreateView(generics.ListCreateAPIView):
    """
    List all invoices or create a new invoice.
    """
    queryset = Invoice.objects.select_related('customer', 'installation_project', 'amc_contract', 'service_request', 'payment_milestone').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'invoice_type', 'customer', 'installation_project']
    search_fields = ['invoice_number', 'customer__first_name', 'customer__last_name', 'customer__company_name']
    ordering_fields = ['invoice_date', 'due_date', 'total_amount', 'created_at']
    ordering = ['-invoice_date']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InvoiceCreateSerializer
        return InvoiceListSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # If user is sales staff, only show their customers' invoices
        if user.role == 'sales_staff':
            queryset = queryset.filter(customer__assigned_to=user)
        
        return queryset


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete an invoice.
    """
    queryset = Invoice.objects.select_related('customer', 'installation_project', 'amc_contract', 'service_request', 'payment_milestone').all()
    serializer_class = InvoiceDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Apply same permission logic as list view
        if user.role == 'sales_staff':
            queryset = queryset.filter(customer__assigned_to=user)
        
        return queryset


class PaymentListCreateView(generics.ListCreateAPIView):
    """
    List all payments or create a new payment.
    """
    queryset = Payment.objects.select_related('customer', 'invoice', 'payment_milestone', 'installation_project', 'processed_by').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method', 'customer', 'invoice', 'installation_project']
    search_fields = ['payment_number', 'transaction_id', 'cheque_number', 'customer__first_name', 'customer__last_name']
    ordering_fields = ['payment_date', 'amount', 'created_at']
    ordering = ['-payment_date']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PaymentCreateSerializer
        return PaymentSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # If user is sales staff, only show their customers' payments
        if user.role == 'sales_staff':
            queryset = queryset.filter(customer__assigned_to=user)
        
        return queryset


class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a payment.
    """
    queryset = Payment.objects.select_related('customer', 'invoice', 'payment_milestone', 'installation_project', 'processed_by').all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Apply same permission logic as list view
        if user.role == 'sales_staff':
            queryset = queryset.filter(customer__assigned_to=user)
        
        return queryset


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_payment_status(request, payment_id):
    """
    Update payment status.
    
    POST: Updates payment status with validation and tracking
    """
    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        return Response(
            {'error': 'Payment not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            (user.role == 'sales_staff' and payment.customer.assigned_to == user)):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = PaymentStatusUpdateSerializer(data=request.data, instance=payment)
    if serializer.is_valid():
        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')
        cleared_date = serializer.validated_data.get('cleared_date')
        
        old_status = payment.status
        
        if new_status == 'completed':
            payment.mark_as_completed(processed_by=user, notes=notes)
            if cleared_date:
                payment.cleared_date = cleared_date
                payment.save(update_fields=['cleared_date', 'updated_at'])
        elif new_status == 'failed':
            payment.mark_as_failed(reason=notes)
        else:
            payment.status = new_status
            if notes:
                payment.notes = notes
            payment.save(update_fields=['status', 'notes', 'updated_at'])
        
        return Response({
            'message': 'Payment status updated successfully',
            'payment_number': payment.payment_number,
            'old_status': old_status,
            'new_status': new_status,
            'amount': payment.amount
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_milestone_invoice(request, milestone_id):
    """
    Create invoice for a payment milestone.
    
    POST: Creates an invoice for the specified milestone
    """
    try:
        milestone = PaymentMilestone.objects.get(id=milestone_id)
    except PaymentMilestone.DoesNotExist:
        return Response(
            {'error': 'Payment milestone not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            (user.role == 'sales_staff' and milestone.installation_project.customer.assigned_to == user)):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if invoice already exists for this milestone
    existing_invoice = Invoice.objects.filter(payment_milestone=milestone).first()
    if existing_invoice:
        return Response(
            {'error': f'Invoice {existing_invoice.invoice_number} already exists for this milestone'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get line items from request or create default
    line_items = request.data.get('line_items')
    
    try:
        invoice = Invoice.create_milestone_invoice(milestone, line_items)
        
        return Response({
            'message': 'Invoice created successfully',
            'invoice': InvoiceDetailSerializer(invoice).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to create invoice: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_invoice(request, invoice_id):
    """
    Mark invoice as sent to customer.
    
    POST: Updates invoice status to sent and records timestamp
    """
    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return Response(
            {'error': 'Invoice not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            (user.role == 'sales_staff' and invoice.customer.assigned_to == user)):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if invoice.status != 'draft':
        return Response(
            {'error': 'Only draft invoices can be sent'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    invoice.mark_as_sent()
    
    return Response({
        'message': 'Invoice marked as sent',
        'invoice_number': invoice.invoice_number,
        'sent_at': invoice.sent_at,
        'customer_email': invoice.customer.email
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_default_milestones(request, project_id):
    """
    Create default payment milestones for a project.
    
    POST: Creates standard payment milestones for the project
    """
    try:
        project = InstallationProject.objects.get(id=project_id)
    except InstallationProject.DoesNotExist:
        return Response(
            {'error': 'Installation project not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or 
            project.project_manager == user or project.sales_person == user):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if milestones already exist
    existing_milestones = PaymentMilestone.objects.filter(installation_project=project).count()
    if existing_milestones > 0:
        return Response(
            {'error': f'Project already has {existing_milestones} payment milestones'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        milestones = PaymentMilestone.create_default_milestones_for_project(project)
        
        return Response({
            'message': f'Created {len(milestones)} default payment milestones',
            'project_number': project.project_number,
            'milestones_created': len(milestones),
            'milestones': PaymentMilestoneSerializer(milestones, many=True).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to create milestones: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_dashboard(request):
    """
    Get financial dashboard data.
    
    GET: Returns comprehensive financial metrics and recent activity
    """
    user = request.user
    
    # Calculate current month metrics
    today = timezone.now().date()
    current_month_start = today.replace(day=1)
    
    # Previous month for comparison
    if current_month_start.month == 1:
        previous_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
        previous_month_end = current_month_start - timedelta(days=1)
    else:
        previous_month_start = current_month_start.replace(month=current_month_start.month - 1)
        previous_month_end = current_month_start - timedelta(days=1)
    
    # Base querysets based on user permissions
    invoice_qs = Invoice.objects.all()
    payment_qs = Payment.objects.filter(status='completed')
    
    if user.role == 'sales_staff':
        invoice_qs = invoice_qs.filter(customer__assigned_to=user)
        payment_qs = payment_qs.filter(customer__assigned_to=user)
    
    # Current month metrics
    current_invoices = invoice_qs.filter(invoice_date__gte=current_month_start)
    current_payments = payment_qs.filter(payment_date__gte=current_month_start)
    
    total_invoiced_current = current_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    total_collected_current = current_payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    # Previous month metrics
    previous_invoices = invoice_qs.filter(
        invoice_date__gte=previous_month_start,
        invoice_date__lte=previous_month_end
    )
    previous_payments = payment_qs.filter(
        payment_date__gte=previous_month_start,
        payment_date__lte=previous_month_end
    )
    
    total_invoiced_previous = previous_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    total_collected_previous = previous_payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    # Calculate growth rates
    invoiced_growth = Decimal('0')
    if total_invoiced_previous > 0:
        invoiced_growth = ((total_invoiced_current - total_invoiced_previous) / total_invoiced_previous) * 100
    
    collected_growth = Decimal('0')
    if total_collected_previous > 0:
        collected_growth = ((total_collected_current - total_collected_previous) / total_collected_previous) * 100
    
    # Collection rates
    collection_rate_current = Decimal('0')
    if total_invoiced_current > 0:
        collection_rate_current = (total_collected_current / total_invoiced_current) * 100
    
    collection_rate_previous = Decimal('0')
    if total_invoiced_previous > 0:
        collection_rate_previous = (total_collected_previous / total_invoiced_previous) * 100
    
    # Outstanding amounts
    total_outstanding = sum([invoice.outstanding_amount for invoice in invoice_qs.filter(status__in=['sent', 'partial', 'overdue'])])
    
    # Overdue metrics
    overdue_invoices = invoice_qs.filter(due_date__lt=today, status__in=['sent', 'partial', 'overdue'])
    overdue_amount = sum([invoice.outstanding_amount for invoice in overdue_invoices])
    
    # Recent activity (last 7 days)
    recent_date = today - timedelta(days=7)
    recent_payments = payment_qs.filter(payment_date__gte=recent_date).order_by('-payment_date')[:10]
    recent_invoices = invoice_qs.filter(invoice_date__gte=recent_date).order_by('-invoice_date')[:10]
    
    # Pending milestones
    milestone_qs = PaymentMilestone.objects.filter(status__in=['pending', 'overdue'])
    if user.role == 'sales_staff':
        milestone_qs = milestone_qs.filter(installation_project__customer__assigned_to=user)
    
    pending_milestones = milestone_qs.order_by('due_date')[:10]
    
    dashboard_data = {
        'total_invoiced_current': total_invoiced_current,
        'total_collected_current': total_collected_current,
        'total_outstanding': total_outstanding,
        'collection_rate_current': collection_rate_current,
        'total_invoiced_previous': total_invoiced_previous,
        'total_collected_previous': total_collected_previous,
        'collection_rate_previous': collection_rate_previous,
        'invoiced_growth': invoiced_growth,
        'collected_growth': collected_growth,
        'overdue_invoices_count': overdue_invoices.count(),
        'overdue_amount': overdue_amount,
        'recent_payments': PaymentSerializer(recent_payments, many=True).data,
        'recent_invoices': InvoiceListSerializer(recent_invoices, many=True).data,
        'pending_milestones': PaymentMilestoneSerializer(pending_milestones, many=True).data
    }
    
    serializer = FinancialDashboardSerializer(dashboard_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_summary(request):
    """
    Get financial summary for specified period.
    
    GET: Returns financial summary with optional period parameters
    """
    # Get period parameters
    period_type = request.GET.get('period', 'monthly')  # daily, weekly, monthly, quarterly, yearly
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    # Calculate period dates
    today = timezone.now().date()
    
    if start_date_str and end_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        # Default to current month
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    # Get or create financial summary
    try:
        summary = FinancialSummary.calculate_summary_for_period(period_type, start_date, end_date)
        return Response(FinancialSummarySerializer(summary).data)
    except Exception as e:
        return Response(
            {'error': f'Failed to calculate financial summary: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overdue_invoices(request):
    """
    Get list of overdue invoices.
    
    GET: Returns invoices that are past their due date
    """
    user = request.user
    
    # Base queryset
    queryset = Invoice.objects.filter(
        due_date__lt=timezone.now().date(),
        status__in=['sent', 'partial', 'overdue']
    ).select_related('customer', 'installation_project')
    
    # Apply user permissions
    if user.role == 'sales_staff':
        queryset = queryset.filter(customer__assigned_to=user)
    
    # Order by days overdue (most overdue first)
    overdue_invoices = []
    for invoice in queryset:
        if invoice.is_overdue:
            overdue_invoices.append(invoice)
    
    # Sort by days overdue
    overdue_invoices.sort(key=lambda x: x.days_overdue, reverse=True)
    
    serializer = InvoiceListSerializer(overdue_invoices, many=True)
    
    return Response({
        'overdue_invoices': serializer.data,
        'total_count': len(overdue_invoices),
        'total_overdue_amount': sum([invoice.outstanding_amount for invoice in overdue_invoices])
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_payments(request):
    """
    Get list of pending payments and milestones.
    
    GET: Returns payments and milestones that need attention
    """
    user = request.user
    
    # Pending payments
    payment_qs = Payment.objects.filter(status__in=['pending', 'processing']).select_related('customer', 'invoice')
    
    # Pending milestones
    milestone_qs = PaymentMilestone.objects.filter(status__in=['pending', 'overdue']).select_related('installation_project', 'installation_project__customer')
    
    # Apply user permissions
    if user.role == 'sales_staff':
        payment_qs = payment_qs.filter(customer__assigned_to=user)
        milestone_qs = milestone_qs.filter(installation_project__customer__assigned_to=user)
    
    # Cheque clearances pending
    cheque_clearances = Payment.get_pending_cheque_clearances()
    if user.role == 'sales_staff':
        cheque_clearances = cheque_clearances.filter(customer__assigned_to=user)
    
    return Response({
        'pending_payments': PaymentSerializer(payment_qs, many=True).data,
        'pending_milestones': PaymentMilestoneSerializer(milestone_qs, many=True).data,
        'cheque_clearances': PaymentSerializer(cheque_clearances, many=True).data,
        'summary': {
            'total_pending_payments': payment_qs.count(),
            'total_pending_milestones': milestone_qs.count(),
            'total_cheque_clearances': cheque_clearances.count()
        }
    })
