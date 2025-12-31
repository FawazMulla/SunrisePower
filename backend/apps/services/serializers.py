from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ServiceRequest, InstallationProject, AMCContract

User = get_user_model()


class ServiceRequestListSerializer(serializers.ModelSerializer):
    """Serializer for ServiceRequest list view with minimal fields."""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'ticket_number', 'customer', 'customer_name', 'customer_email',
            'request_type', 'request_type_display', 'priority', 'priority_display',
            'subject', 'status', 'status_display', 'assigned_to', 'assigned_to_name',
            'created_at', 'updated_at', 'resolved_at'
        ]
        read_only_fields = ['ticket_number', 'created_at', 'updated_at']


class ServiceRequestDetailSerializer(serializers.ModelSerializer):
    """Serializer for ServiceRequest detail view with all fields."""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    installation_project_number = serializers.CharField(source='installation_project.project_number', read_only=True)
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'ticket_number', 'customer', 'customer_name', 'customer_email',
            'customer_phone', 'request_type', 'request_type_display', 'priority',
            'priority_display', 'subject', 'description', 'status', 'status_display',
            'assigned_to', 'assigned_to_name', 'installation_project',
            'installation_project_number', 'created_at', 'updated_at', 'resolved_at',
            'closed_at', 'source_email', 'source_data', 'resolution_notes',
            'customer_satisfaction'
        ]
        read_only_fields = ['ticket_number', 'created_at', 'updated_at']


class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new service requests."""
    
    class Meta:
        model = ServiceRequest
        fields = [
            'customer', 'request_type', 'priority', 'subject', 'description',
            'assigned_to', 'installation_project', 'source_email', 'source_data'
        ]
    
    def validate_customer(self, value):
        """Validate that customer exists and is active."""
        if value.status != 'active':
            raise serializers.ValidationError(
                "Cannot create service request for inactive customer."
            )
        return value


class ServiceRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing service requests."""
    
    class Meta:
        model = ServiceRequest
        fields = [
            'request_type', 'priority', 'subject', 'description', 'status',
            'assigned_to', 'resolution_notes', 'customer_satisfaction'
        ]
    
    def validate_status(self, value):
        """Validate status transitions."""
        if self.instance:
            current_status = self.instance.status
            
            # Define valid status transitions
            valid_transitions = {
                'open': ['in_progress', 'pending_customer', 'cancelled'],
                'in_progress': ['pending_customer', 'pending_parts', 'resolved', 'cancelled'],
                'pending_customer': ['in_progress', 'resolved', 'cancelled'],
                'pending_parts': ['in_progress', 'resolved', 'cancelled'],
                'resolved': ['closed', 'in_progress'],  # Can reopen if needed
                'closed': [],  # Cannot change from closed
                'cancelled': []  # Cannot change from cancelled
            }
            
            if current_status in valid_transitions and value not in valid_transitions[current_status]:
                raise serializers.ValidationError(
                    f"Cannot change status from '{current_status}' to '{value}'"
                )
        
        return value


class ServiceRequestStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating service request status."""
    
    status = serializers.ChoiceField(choices=ServiceRequest.STATUS_CHOICES)
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    customer_satisfaction = serializers.IntegerField(min_value=1, max_value=5, required=False)
    
    def validate(self, data):
        """Validate status update data."""
        status = data.get('status')
        
        # If marking as resolved, resolution notes are recommended
        if status == 'resolved' and not data.get('resolution_notes'):
            data['resolution_notes'] = 'Resolved without specific notes'
        
        # Customer satisfaction only valid for resolved/closed requests
        if data.get('customer_satisfaction') and status not in ['resolved', 'closed']:
            raise serializers.ValidationError(
                "Customer satisfaction can only be set for resolved or closed requests"
            )
        
        return data


class InstallationProjectListSerializer(serializers.ModelSerializer):
    """Serializer for InstallationProject list view."""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    project_manager_name = serializers.CharField(source='project_manager.get_full_name', read_only=True)
    sales_person_name = serializers.CharField(source='sales_person.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    installation_type_display = serializers.CharField(source='get_installation_type_display', read_only=True)
    
    class Meta:
        model = InstallationProject
        fields = [
            'id', 'project_number', 'customer', 'customer_name', 'system_capacity',
            'status', 'status_display', 'progress_percentage', 'project_value',
            'amount_paid', 'outstanding_amount', 'payment_percentage',
            'project_manager', 'project_manager_name', 'sales_person',
            'sales_person_name', 'installation_type', 'installation_type_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'project_number', 'outstanding_amount', 'payment_percentage',
            'created_at', 'updated_at'
        ]


class InstallationProjectDetailSerializer(serializers.ModelSerializer):
    """Serializer for InstallationProject detail view."""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    project_manager_name = serializers.CharField(source='project_manager.get_full_name', read_only=True)
    sales_person_name = serializers.CharField(source='sales_person.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    installation_type_display = serializers.CharField(source='get_installation_type_display', read_only=True)
    
    class Meta:
        model = InstallationProject
        fields = '__all__'
        read_only_fields = [
            'project_number', 'outstanding_amount', 'payment_percentage',
            'created_at', 'updated_at'
        ]


class AMCContractListSerializer(serializers.ModelSerializer):
    """Serializer for AMCContract list view."""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    project_number = serializers.CharField(source='installation_project.project_number', read_only=True)
    contact_person_name = serializers.CharField(source='contact_person.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AMCContract
        fields = [
            'id', 'contract_number', 'customer', 'customer_name', 'installation_project',
            'project_number', 'start_date', 'end_date', 'annual_value', 'status',
            'status_display', 'contact_person', 'contact_person_name', 'is_active',
            'is_expiring_soon', 'days_until_expiry', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'contract_number', 'is_active', 'is_expiring_soon', 'days_until_expiry',
            'created_at', 'updated_at'
        ]


class AMCContractDetailSerializer(serializers.ModelSerializer):
    """Serializer for AMCContract detail view."""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    project_number = serializers.CharField(source='installation_project.project_number', read_only=True)
    contact_person_name = serializers.CharField(source='contact_person.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AMCContract
        fields = '__all__'
        read_only_fields = [
            'contract_number', 'is_active', 'is_expiring_soon', 'days_until_expiry',
            'created_at', 'updated_at'
        ]