from django.shortcuts import render
from django.db.models import Q
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model

from .models import Lead, LeadSource, LeadInteraction
from .serializers import (
    LeadListSerializer, LeadDetailSerializer, LeadCreateSerializer,
    LeadUpdateSerializer, LeadConversionSerializer, LeadScoreUpdateSerializer,
    LeadSourceSerializer, LeadInteractionSerializer
)

User = get_user_model()


class LeadListCreateView(generics.ListCreateAPIView):
    """
    List all leads or create a new lead.
    
    GET: Returns paginated list of leads with filtering and search
    POST: Creates a new lead
    """
    queryset = Lead.objects.select_related('source', 'assigned_to').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'interest_level', 'property_type', 'source', 'assigned_to']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'city']
    ordering_fields = ['created_at', 'updated_at', 'score', 'last_contacted_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LeadCreateSerializer
        return LeadListSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # If user is not superuser or manager, only show assigned leads
        if not (user.is_superuser or user.role in ['owner', 'sales_manager']):
            queryset = queryset.filter(assigned_to=user)
        
        return queryset


class LeadDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a lead.
    
    GET: Returns detailed lead information with interactions
    PUT/PATCH: Updates lead information
    DELETE: Deletes the lead
    """
    queryset = Lead.objects.select_related('source', 'assigned_to').prefetch_related('interactions')
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return LeadUpdateSerializer
        return LeadDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # If user is not superuser or manager, only show assigned leads
        if not (user.is_superuser or user.role in ['owner', 'sales_manager']):
            queryset = queryset.filter(assigned_to=user)
        
        return queryset


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_lead_to_customer(request, lead_id):
    """
    Convert a lead to a customer.
    
    POST: Converts the specified lead to a customer record
    """
    try:
        lead = Lead.objects.get(id=lead_id)
    except Lead.DoesNotExist:
        return Response(
            {'error': 'Lead not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if lead is already converted
    if lead.is_converted:
        return Response(
            {'error': 'Lead is already converted to customer'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or lead.assigned_to == user):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = LeadConversionSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Import here to avoid circular imports
            from apps.customers.models import Customer
            
            # Create customer from lead
            customer_data = {
                'lead': lead,
                'first_name': lead.first_name,
                'last_name': lead.last_name,
                'email': lead.email,
                'phone': lead.phone,
                'address': serializer.validated_data.get('address', lead.address),
                'city': serializer.validated_data.get('city', lead.city),
                'state': serializer.validated_data.get('state', lead.state),
                'pincode': serializer.validated_data.get('pincode', lead.pincode),
                'company_name': serializer.validated_data.get('company_name', ''),
                'gst_number': serializer.validated_data.get('gst_number', ''),
                'customer_type': serializer.validated_data.get('customer_type', lead.property_type),
                'assigned_to': lead.assigned_to,
                'notes': serializer.validated_data.get('notes', f"Converted from lead on {lead.converted_at}")
            }
            
            customer = Customer.objects.create(**customer_data)
            
            # Mark lead as converted
            lead.mark_as_converted()
            
            # Create interaction record
            LeadInteraction.objects.create(
                lead=lead,
                interaction_type='other',
                subject='Lead Converted to Customer',
                description=f'Lead converted to customer (ID: {customer.id}) by {user.get_full_name()}',
                user=user,
                interaction_data={'customer_id': customer.id}
            )
            
            return Response({
                'message': 'Lead successfully converted to customer',
                'customer_id': customer.id,
                'lead_id': lead.id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to convert lead: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_lead_score(request, lead_id):
    """
    Update lead score with optional reason.
    
    POST: Updates the lead score and records the change
    """
    try:
        lead = Lead.objects.get(id=lead_id)
    except Lead.DoesNotExist:
        return Response(
            {'error': 'Lead not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or lead.assigned_to == user):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = LeadScoreUpdateSerializer(data=request.data)
    if serializer.is_valid():
        old_score = lead.score
        new_score = serializer.validated_data['score']
        reason = serializer.validated_data.get('reason', '')
        
        try:
            lead.update_score(new_score)
            
            # Create interaction record
            LeadInteraction.objects.create(
                lead=lead,
                interaction_type='other',
                subject='Lead Score Updated',
                description=f'Score updated from {old_score} to {new_score}. Reason: {reason}' if reason else f'Score updated from {old_score} to {new_score}',
                user=user,
                interaction_data={
                    'old_score': old_score,
                    'new_score': new_score,
                    'reason': reason
                }
            )
            
            return Response({
                'message': 'Lead score updated successfully',
                'old_score': old_score,
                'new_score': new_score
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LeadSourceListView(generics.ListCreateAPIView):
    """
    List all lead sources or create a new lead source.
    """
    queryset = LeadSource.objects.filter(is_active=True)
    serializer_class = LeadSourceSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['name']


class LeadInteractionListCreateView(generics.ListCreateAPIView):
    """
    List interactions for a specific lead or create a new interaction.
    """
    serializer_class = LeadInteractionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        lead_id = self.kwargs['lead_id']
        return LeadInteraction.objects.filter(lead_id=lead_id).select_related('user')
    
    def perform_create(self, serializer):
        lead_id = self.kwargs['lead_id']
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response(
                {'error': 'Lead not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer.save(lead=lead, user=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lead_search(request):
    """
    Advanced lead search with multiple criteria.
    
    GET: Search leads by various criteria
    """
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    source_filter = request.GET.get('source', '')
    assigned_to_filter = request.GET.get('assigned_to', '')
    score_min = request.GET.get('score_min', '')
    score_max = request.GET.get('score_max', '')
    
    queryset = Lead.objects.select_related('source', 'assigned_to').all()
    
    # Apply user permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager']):
        queryset = queryset.filter(assigned_to=user)
    
    # Apply search filters
    if query:
        queryset = queryset.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(city__icontains=query)
        )
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if source_filter:
        queryset = queryset.filter(source_id=source_filter)
    
    if assigned_to_filter:
        queryset = queryset.filter(assigned_to_id=assigned_to_filter)
    
    if score_min:
        try:
            queryset = queryset.filter(score__gte=int(score_min))
        except ValueError:
            pass
    
    if score_max:
        try:
            queryset = queryset.filter(score__lte=int(score_max))
        except ValueError:
            pass
    
    # Paginate results
    from django.core.paginator import Paginator
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    serializer = LeadListSerializer(page_obj, many=True)
    
    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })
