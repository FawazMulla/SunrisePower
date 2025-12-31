from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Customer, CustomerHistory

User = get_user_model()


class CustomerHistorySerializer(serializers.ModelSerializer):
    """Serializer for CustomerHistory model."""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    history_type_display = serializers.CharField(source='get_history_type_display', read_only=True)
    
    class Meta:
        model = CustomerHistory
        fields = [
            'id', 'history_type', 'history_type_display', 'title', 'description',
            'user', 'user_name', 'old_values', 'new_values', 'created_at'
        ]
        read_only_fields = ['created_at']


class CustomerListSerializer(serializers.ModelSerializer):
    """Serializer for Customer list view with minimal fields."""
    
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    customer_type_display = serializers.CharField(source='get_customer_type_display', read_only=True)
    lead_id = serializers.IntegerField(source='lead.id', read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone',
            'company_name', 'status', 'status_display', 'customer_type',
            'customer_type_display', 'total_value', 'outstanding_amount',
            'payment_status', 'assigned_to', 'assigned_to_name', 'lead_id',
            'created_at', 'updated_at', 'is_business_customer'
        ]
        read_only_fields = [
            'full_name', 'payment_status', 'is_business_customer', 
            'created_at', 'updated_at'
        ]


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Serializer for Customer detail view with all fields."""
    
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    customer_type_display = serializers.CharField(source='get_customer_type_display', read_only=True)
    lead_id = serializers.IntegerField(source='lead.id', read_only=True)
    history = CustomerHistorySerializer(many=True, read_only=True)
    
    # Related data counts
    service_requests_count = serializers.SerializerMethodField()
    installation_projects_count = serializers.SerializerMethodField()
    amc_contracts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone',
            'company_name', 'gst_number', 'address', 'city', 'state', 'pincode',
            'status', 'status_display', 'customer_type', 'customer_type_display',
            'total_value', 'outstanding_amount', 'payment_status', 'assigned_to',
            'assigned_to_name', 'lead_id', 'created_at', 'updated_at', 'notes',
            'is_business_customer', 'history', 'service_requests_count',
            'installation_projects_count', 'amc_contracts_count'
        ]
        read_only_fields = [
            'full_name', 'payment_status', 'is_business_customer', 
            'created_at', 'updated_at'
        ]
    
    def get_service_requests_count(self, obj):
        """Get count of service requests for this customer."""
        return obj.service_requests.count()
    
    def get_installation_projects_count(self, obj):
        """Get count of installation projects for this customer."""
        return obj.installation_projects.count()
    
    def get_amc_contracts_count(self, obj):
        """Get count of AMC contracts for this customer."""
        return obj.amc_contracts.count()


class CustomerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new customers."""
    
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'company_name',
            'gst_number', 'address', 'city', 'state', 'pincode', 'status',
            'customer_type', 'assigned_to', 'notes'
        ]
    
    def validate_email(self, value):
        """Validate email uniqueness with helpful error message."""
        if Customer.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A customer with this email already exists."
            )
        return value


class CustomerUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing customers."""
    
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'company_name',
            'gst_number', 'address', 'city', 'state', 'pincode', 'status',
            'customer_type', 'assigned_to', 'notes'
        ]
    
    def validate_email(self, value):
        """Validate email uniqueness excluding current instance."""
        if self.instance and Customer.objects.filter(email=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError(
                "A customer with this email already exists."
            )
        return value
    
    def update(self, instance, validated_data):
        """Update customer and create history record."""
        # Store old values for history
        old_values = {
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'email': instance.email,
            'phone': instance.phone,
            'company_name': instance.company_name,
            'status': instance.status,
            'customer_type': instance.customer_type,
        }
        
        # Update instance
        updated_instance = super().update(instance, validated_data)
        
        # Create history record for significant changes
        changed_fields = []
        for field, old_value in old_values.items():
            new_value = getattr(updated_instance, field)
            if old_value != new_value:
                changed_fields.append(f"{field}: {old_value} → {new_value}")
        
        if changed_fields:
            CustomerHistory.objects.create(
                customer=updated_instance,
                history_type='contact_update',
                title='Customer Information Updated',
                description=f"Updated fields: {', '.join(changed_fields)}",
                user=self.context['request'].user if 'request' in self.context else None,
                old_values=old_values,
                new_values={field: getattr(updated_instance, field) for field in old_values.keys()}
            )
        
        return updated_instance