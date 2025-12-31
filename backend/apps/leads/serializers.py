from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Lead, LeadSource, LeadInteraction

User = get_user_model()


class LeadSourceSerializer(serializers.ModelSerializer):
    """Serializer for LeadSource model."""
    
    class Meta:
        model = LeadSource
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class LeadInteractionSerializer(serializers.ModelSerializer):
    """Serializer for LeadInteraction model."""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    interaction_type_display = serializers.CharField(source='get_interaction_type_display', read_only=True)
    
    class Meta:
        model = LeadInteraction
        fields = [
            'id', 'interaction_type', 'interaction_type_display', 'subject', 
            'description', 'user', 'user_name', 'interaction_data', 
            'interaction_date', 'created_at'
        ]
        read_only_fields = ['created_at']


class LeadListSerializer(serializers.ModelSerializer):
    """Serializer for Lead list view with minimal fields."""
    
    source_name = serializers.CharField(source='source.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    interest_level_display = serializers.CharField(source='get_interest_level_display', read_only=True)
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    
    class Meta:
        model = Lead
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone',
            'source', 'source_name', 'status', 'status_display', 'score',
            'interest_level', 'interest_level_display', 'property_type', 
            'property_type_display', 'assigned_to', 'assigned_to_name',
            'created_at', 'updated_at', 'last_contacted_at', 'is_converted'
        ]
        read_only_fields = ['full_name', 'is_converted', 'created_at', 'updated_at']


class LeadDetailSerializer(serializers.ModelSerializer):
    """Serializer for Lead detail view with all fields."""
    
    source_name = serializers.CharField(source='source.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    interest_level_display = serializers.CharField(source='get_interest_level_display', read_only=True)
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    budget_range_display = serializers.CharField(source='get_budget_range_display', read_only=True)
    interactions = LeadInteractionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Lead
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone',
            'source', 'source_name', 'status', 'status_display', 'score',
            'interest_level', 'interest_level_display', 'property_type', 
            'property_type_display', 'estimated_capacity', 'budget_range',
            'budget_range_display', 'address', 'city', 'state', 'pincode',
            'assigned_to', 'assigned_to_name', 'created_at', 'updated_at',
            'converted_at', 'last_contacted_at', 'original_data', 'notes',
            'is_converted', 'interactions'
        ]
        read_only_fields = ['full_name', 'is_converted', 'created_at', 'updated_at']


class LeadCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new leads."""
    
    class Meta:
        model = Lead
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'source',
            'status', 'interest_level', 'property_type', 'estimated_capacity',
            'budget_range', 'address', 'city', 'state', 'pincode',
            'assigned_to', 'original_data', 'notes'
        ]
    
    def validate_email(self, value):
        """Validate email uniqueness with helpful error message."""
        if Lead.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A lead with this email already exists. Consider updating the existing lead."
            )
        return value
    
    def validate_score(self, value):
        """Validate lead score range."""
        if value is not None and not (0 <= value <= 100):
            raise serializers.ValidationError("Score must be between 0 and 100.")
        return value


class LeadUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing leads."""
    
    class Meta:
        model = Lead
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'status', 'score',
            'interest_level', 'property_type', 'estimated_capacity',
            'budget_range', 'address', 'city', 'state', 'pincode',
            'assigned_to', 'notes'
        ]
    
    def validate_email(self, value):
        """Validate email uniqueness excluding current instance."""
        if self.instance and Lead.objects.filter(email=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError(
                "A lead with this email already exists."
            )
        return value
    
    def validate_score(self, value):
        """Validate lead score range."""
        if value is not None and not (0 <= value <= 100):
            raise serializers.ValidationError("Score must be between 0 and 100.")
        return value


class LeadConversionSerializer(serializers.Serializer):
    """Serializer for lead conversion to customer."""
    
    company_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    gst_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    pincode = serializers.CharField(max_length=10, required=False, allow_blank=True)
    customer_type = serializers.ChoiceField(
        choices=[
            ('residential', 'Residential'),
            ('commercial', 'Commercial'),
            ('industrial', 'Industrial'),
            ('agricultural', 'Agricultural'),
        ],
        required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate conversion data."""
        # If company_name is provided, it's likely a business customer
        if data.get('company_name') and not data.get('customer_type'):
            data['customer_type'] = 'commercial'
        
        return data


class LeadScoreUpdateSerializer(serializers.Serializer):
    """Serializer for updating lead score."""
    
    score = serializers.IntegerField(min_value=0, max_value=100)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)