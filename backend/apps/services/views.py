from django.shortcuts import render
from django.db.models import Q
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model

from .models import ServiceRequest, InstallationProject, AMCContract
from .serializers import (
    ServiceRequestListSerializer, ServiceRequestDetailSerializer,
    ServiceRequestCreateSerializer, ServiceRequestUpdateSerializer,
    ServiceRequestStatusUpdateSerializer, InstallationProjectListSerializer,
    InstallationProjectDetailSerializer, AMCContractListSerializer,
    AMCContractDetailSerializer
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
            service_request.status = new_status
            
            if resolution_notes:
                service_request.resolution_notes = resolution_notes
            
            if customer_satisfaction:
                service_request.customer_satisfaction = customer_satisfaction
            
            # Handle status-specific logic
            if new_status == 'resolved':
                service_request.mark_as_resolved(resolution_notes)
            elif new_status == 'closed':
                service_request.mark_as_closed()
            else:
                service_request.save()
            
            return Response({
                'message': 'Service request status updated successfully',
                'old_status': old_status,
                'new_status': new_status,
                'ticket_number': service_request.ticket_number
            }, status=status.HTTP_200_OK)
            
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
