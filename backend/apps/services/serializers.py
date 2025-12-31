from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    ServiceRequest, InstallationProject, AMCContract, ServiceRequestStatusHistory, 
    AMCRenewalAlert, ProjectStatusHistory, ProjectMilestone, ProjectNotification,
    PaymentMilestone, Invoice, Payment, FinancialSummary
)

User = get_user_model()


class ServiceRequestStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for ServiceRequestStatusHistory."""
    
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    old_status_display = serializers.SerializerMethodField()
    new_status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequestStatusHistory
        fields = [
            'id', 'old_status', 'old_status_display', 'new_status', 
            'new_status_display', 'changed_by', 'changed_by_name', 
            'changed_at', 'notes'
        ]
    
    def get_old_status_display(self, obj):
        """Get display name for old status."""
        if obj.old_status:
            choices_dict = dict(ServiceRequest.STATUS_CHOICES)
            return choices_dict.get(obj.old_status, obj.old_status)
        return None
    
    def get_new_status_display(self, obj):
        """Get display name for new status."""
        choices_dict = dict(ServiceRequest.STATUS_CHOICES)
        return choices_dict.get(obj.new_status, obj.new_status)


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
    
    # Lifecycle information
    is_overdue = serializers.ReadOnlyField()
    age_in_hours = serializers.ReadOnlyField()
    time_to_resolution = serializers.SerializerMethodField()
    valid_next_statuses = serializers.ReadOnlyField(source='get_next_valid_statuses')
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'ticket_number', 'customer', 'customer_name', 'customer_email',
            'customer_phone', 'request_type', 'request_type_display', 'priority',
            'priority_display', 'subject', 'description', 'status', 'status_display',
            'assigned_to', 'assigned_to_name', 'installation_project',
            'installation_project_number', 'created_at', 'updated_at', 'resolved_at',
            'closed_at', 'source_email', 'source_data', 'resolution_notes',
            'customer_satisfaction', 'is_overdue', 'age_in_hours', 'time_to_resolution',
            'valid_next_statuses'
        ]
        read_only_fields = ['ticket_number', 'created_at', 'updated_at']
    
    def get_time_to_resolution(self, obj):
        """Get time to resolution in hours."""
        if obj.time_to_resolution:
            return obj.time_to_resolution.total_seconds() / 3600
        return None


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


class ProjectMilestoneSerializer(serializers.ModelSerializer):
    """Serializer for ProjectMilestone."""
    
    milestone_type_display = serializers.CharField(source='get_milestone_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    days_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = ProjectMilestone
        fields = [
            'id', 'milestone_type', 'milestone_type_display', 'name', 'description',
            'planned_date', 'actual_date', 'status', 'status_display',
            'assigned_to', 'assigned_to_name', 'notes', 'is_overdue', 'days_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ProjectNotificationSerializer(serializers.ModelSerializer):
    """Serializer for ProjectNotification."""
    
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ProjectNotification
        fields = [
            'id', 'notification_type', 'notification_type_display', 'title', 'message',
            'recipients', 'status', 'status_display', 'created_at', 'sent_at',
            'acknowledged_at', 'metadata'
        ]
        read_only_fields = ['created_at', 'sent_at', 'acknowledged_at']


class AMCRenewalAlertSerializer(serializers.ModelSerializer):
    """Serializer for AMCRenewalAlert."""
    
    contract_number = serializers.CharField(source='amc_contract.contract_number', read_only=True)
    customer_name = serializers.CharField(source='amc_contract.customer.full_name', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True)
    
    class Meta:
        model = AMCRenewalAlert
        fields = [
            'id', 'amc_contract', 'contract_number', 'customer_name',
            'alert_type', 'alert_type_display', 'alert_date', 'status',
            'status_display', 'sent_at', 'sent_to', 'acknowledged_by',
            'acknowledged_by_name', 'acknowledged_at', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


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


class PaymentMilestoneSerializer(serializers.ModelSerializer):
    """Serializer for PaymentMilestone."""
    
    project_number = serializers.CharField(source='installation_project.project_number', read_only=True)
    customer_name = serializers.CharField(source='installation_project.customer.full_name', read_only=True)
    milestone_type_display = serializers.CharField(source='get_milestone_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount_paid = serializers.ReadOnlyField()
    outstanding_amount = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    days_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = PaymentMilestone
        fields = [
            'id', 'installation_project', 'project_number', 'customer_name',
            'milestone_type', 'milestone_type_display', 'name', 'description',
            'amount', 'percentage', 'due_date', 'status', 'status_display',
            'amount_paid', 'outstanding_amount', 'is_overdue', 'days_overdue',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class InvoiceListSerializer(serializers.ModelSerializer):
    """Serializer for Invoice list view."""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    project_number = serializers.CharField(source='installation_project.project_number', read_only=True)
    invoice_type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount_paid = serializers.ReadOnlyField()
    outstanding_amount = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    days_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'customer', 'customer_name', 'invoice_type',
            'invoice_type_display', 'installation_project', 'project_number',
            'subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'outstanding_amount',
            'invoice_date', 'due_date', 'status', 'status_display', 'is_overdue',
            'days_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'invoice_number', 'tax_amount', 'total_amount', 'amount_paid',
            'outstanding_amount', 'is_overdue', 'days_overdue', 'created_at', 'updated_at'
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Serializer for Invoice detail view."""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    project_number = serializers.CharField(source='installation_project.project_number', read_only=True)
    contract_number = serializers.CharField(source='amc_contract.contract_number', read_only=True)
    service_ticket = serializers.CharField(source='service_request.ticket_number', read_only=True)
    milestone_name = serializers.CharField(source='payment_milestone.name', read_only=True)
    invoice_type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount_paid = serializers.ReadOnlyField()
    outstanding_amount = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    days_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'customer', 'customer_name', 'invoice_type',
            'invoice_type_display', 'installation_project', 'project_number',
            'amc_contract', 'contract_number', 'service_request', 'service_ticket',
            'payment_milestone', 'milestone_name', 'subtotal', 'tax_rate',
            'tax_amount', 'total_amount', 'amount_paid', 'outstanding_amount',
            'invoice_date', 'due_date', 'status', 'status_display', 'line_items',
            'notes', 'is_overdue', 'days_overdue', 'created_at', 'updated_at', 'sent_at'
        ]
        read_only_fields = [
            'invoice_number', 'tax_amount', 'total_amount', 'amount_paid',
            'outstanding_amount', 'is_overdue', 'days_overdue', 'created_at',
            'updated_at', 'sent_at'
        ]


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating invoices."""
    
    class Meta:
        model = Invoice
        fields = [
            'customer', 'invoice_type', 'installation_project', 'amc_contract',
            'service_request', 'payment_milestone', 'subtotal', 'tax_rate',
            'invoice_date', 'due_date', 'line_items', 'notes'
        ]
    
    def validate(self, data):
        """Validate invoice data."""
        invoice_type = data.get('invoice_type')
        
        # Validate related objects based on invoice type
        if invoice_type == 'project' and not data.get('installation_project'):
            raise serializers.ValidationError(
                "Installation project is required for project invoices"
            )
        elif invoice_type == 'amc' and not data.get('amc_contract'):
            raise serializers.ValidationError(
                "AMC contract is required for AMC invoices"
            )
        elif invoice_type == 'service' and not data.get('service_request'):
            raise serializers.ValidationError(
                "Service request is required for service invoices"
            )
        
        return data


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment."""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    project_number = serializers.CharField(source='installation_project.project_number', read_only=True)
    milestone_name = serializers.CharField(source='payment_milestone.name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_number', 'customer', 'customer_name', 'invoice',
            'invoice_number', 'payment_milestone', 'milestone_name',
            'installation_project', 'project_number', 'amount', 'payment_method',
            'payment_method_display', 'transaction_id', 'cheque_number', 'bank_name',
            'payment_date', 'cleared_date', 'status', 'status_display',
            'processed_by', 'processed_by_name', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['payment_number', 'created_at', 'updated_at']


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payments."""
    
    class Meta:
        model = Payment
        fields = [
            'customer', 'invoice', 'payment_milestone', 'installation_project',
            'amount', 'payment_method', 'transaction_id', 'cheque_number',
            'bank_name', 'payment_date', 'notes'
        ]
    
    def validate(self, data):
        """Validate payment data."""
        payment_method = data.get('payment_method')
        
        # Validate required fields based on payment method
        if payment_method == 'cheque' and not data.get('cheque_number'):
            raise serializers.ValidationError(
                "Cheque number is required for cheque payments"
            )
        elif payment_method in ['bank_transfer', 'upi', 'online'] and not data.get('transaction_id'):
            raise serializers.ValidationError(
                "Transaction ID is required for electronic payments"
            )
        
        # Validate amount against invoice/milestone
        amount = data.get('amount')
        invoice = data.get('invoice')
        milestone = data.get('payment_milestone')
        
        if invoice and amount > invoice.outstanding_amount:
            raise serializers.ValidationError(
                f"Payment amount cannot exceed outstanding invoice amount of ₹{invoice.outstanding_amount}"
            )
        elif milestone and amount > milestone.outstanding_amount:
            raise serializers.ValidationError(
                f"Payment amount cannot exceed outstanding milestone amount of ₹{milestone.outstanding_amount}"
            )
        
        return data


class PaymentStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating payment status."""
    
    status = serializers.ChoiceField(choices=Payment.PAYMENT_STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    cleared_date = serializers.DateField(required=False)
    
    def validate(self, data):
        """Validate status update data."""
        status = data.get('status')
        
        # If marking as completed and it's a cheque, cleared_date is required
        if status == 'completed' and hasattr(self, 'instance'):
            if self.instance.payment_method == 'cheque' and not data.get('cleared_date'):
                data['cleared_date'] = data.get('payment_date') or self.instance.payment_date
        
        return data


class FinancialSummarySerializer(serializers.ModelSerializer):
    """Serializer for FinancialSummary."""
    
    summary_type_display = serializers.CharField(source='get_summary_type_display', read_only=True)
    collection_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = FinancialSummary
        fields = [
            'id', 'summary_type', 'summary_type_display', 'period_start', 'period_end',
            'total_invoiced', 'total_collected', 'total_outstanding', 'collection_rate',
            'projects_invoiced', 'projects_completed', 'payments_received',
            'average_payment_time', 'overdue_invoices_count', 'overdue_amount',
            'calculated_at', 'updated_at'
        ]
        read_only_fields = ['calculated_at', 'updated_at']
    
    def get_collection_rate(self, obj):
        """Calculate collection rate percentage."""
        if obj.total_invoiced > 0:
            return round((obj.total_collected / obj.total_invoiced) * 100, 2)
        return 0


class FinancialDashboardSerializer(serializers.Serializer):
    """Serializer for financial dashboard data."""
    
    # Current period metrics
    total_invoiced_current = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_collected_current = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_outstanding = serializers.DecimalField(max_digits=15, decimal_places=2)
    collection_rate_current = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    # Previous period comparison
    total_invoiced_previous = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_collected_previous = serializers.DecimalField(max_digits=15, decimal_places=2)
    collection_rate_previous = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    # Growth metrics
    invoiced_growth = serializers.DecimalField(max_digits=5, decimal_places=2)
    collected_growth = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    # Overdue metrics
    overdue_invoices_count = serializers.IntegerField()
    overdue_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Recent activity
    recent_payments = PaymentSerializer(many=True, read_only=True)
    recent_invoices = InvoiceListSerializer(many=True, read_only=True)
    pending_milestones = PaymentMilestoneSerializer(many=True, read_only=True)