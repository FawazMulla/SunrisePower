from django.shortcuts import render
from django.db.models import Q
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model

from .models import Customer, CustomerHistory
from .serializers import (
    CustomerListSerializer, CustomerDetailSerializer, CustomerCreateSerializer,
    CustomerUpdateSerializer, CustomerHistorySerializer
)

User = get_user_model()


class CustomerListCreateView(generics.ListCreateAPIView):
    """
    List all customers or create a new customer.
    
    GET: Returns paginated list of customers with filtering and search
    POST: Creates a new customer
    """
    queryset = Customer.objects.select_related('assigned_to', 'lead').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'customer_type', 'assigned_to']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'company_name', 'city']
    ordering_fields = ['created_at', 'updated_at', 'total_value', 'outstanding_amount']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CustomerCreateSerializer
        return CustomerListSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # If user is not superuser or manager, only show assigned customers
        if not (user.is_superuser or user.role in ['owner', 'sales_manager']):
            queryset = queryset.filter(assigned_to=user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create customer and add history record."""
        customer = serializer.save()
        
        # Create initial history record
        CustomerHistory.objects.create(
            customer=customer,
            history_type='other',
            title='Customer Created',
            description=f'Customer record created by {self.request.user.get_full_name()}',
            user=self.request.user,
            new_values={
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'email': customer.email,
                'phone': customer.phone,
                'status': customer.status,
                'customer_type': customer.customer_type,
            }
        )


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a customer.
    
    GET: Returns detailed customer information with history
    PUT/PATCH: Updates customer information
    DELETE: Deletes the customer
    """
    queryset = Customer.objects.select_related('assigned_to', 'lead').prefetch_related('history')
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CustomerUpdateSerializer
        return CustomerDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # If user is not superuser or manager, only show assigned customers
        if not (user.is_superuser or user.role in ['owner', 'sales_manager']):
            queryset = queryset.filter(assigned_to=user)
        
        return queryset


class CustomerHistoryListView(generics.ListAPIView):
    """
    List history for a specific customer.
    """
    serializer_class = CustomerHistorySerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-created_at']
    
    def get_queryset(self):
        customer_id = self.kwargs['customer_id']
        return CustomerHistory.objects.filter(customer_id=customer_id).select_related('user')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_customer_financial_totals(request, customer_id):
    """
    Update customer financial totals from related projects.
    
    POST: Recalculates and updates total_value and outstanding_amount
    """
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.role in ['owner', 'sales_manager'] or customer.assigned_to == user):
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        old_total = customer.total_value
        old_outstanding = customer.outstanding_amount
        
        # Update financial totals
        customer.update_financial_totals()
        
        # Create history record
        CustomerHistory.objects.create(
            customer=customer,
            history_type='financial_update',
            title='Financial Totals Updated',
            description=f'Financial totals recalculated by {user.get_full_name()}',
            user=user,
            old_values={
                'total_value': float(old_total),
                'outstanding_amount': float(old_outstanding)
            },
            new_values={
                'total_value': float(customer.total_value),
                'outstanding_amount': float(customer.outstanding_amount)
            }
        )
        
        return Response({
            'message': 'Financial totals updated successfully',
            'old_total_value': old_total,
            'new_total_value': customer.total_value,
            'old_outstanding_amount': old_outstanding,
            'new_outstanding_amount': customer.outstanding_amount
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to update financial totals: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_search(request):
    """
    Advanced customer search with multiple criteria.
    
    GET: Search customers by various criteria
    """
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    customer_type_filter = request.GET.get('customer_type', '')
    assigned_to_filter = request.GET.get('assigned_to', '')
    has_outstanding = request.GET.get('has_outstanding', '')
    
    queryset = Customer.objects.select_related('assigned_to', 'lead').all()
    
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
            Q(company_name__icontains=query) |
            Q(city__icontains=query)
        )
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if customer_type_filter:
        queryset = queryset.filter(customer_type=customer_type_filter)
    
    if assigned_to_filter:
        queryset = queryset.filter(assigned_to_id=assigned_to_filter)
    
    if has_outstanding == 'true':
        queryset = queryset.filter(outstanding_amount__gt=0)
    elif has_outstanding == 'false':
        queryset = queryset.filter(outstanding_amount=0)
    
    # Paginate results
    from django.core.paginator import Paginator
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    serializer = CustomerListSerializer(page_obj, many=True)
    
    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })
