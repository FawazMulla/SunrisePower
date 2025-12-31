from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, EmailValidator
from django.utils import timezone

User = get_user_model()


class Customer(models.Model):
    """
    Customer model representing converted leads and direct customers
    """
    
    CUSTOMER_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('churned', 'Churned'),
    ]
    
    CUSTOMER_TYPE_CHOICES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('agricultural', 'Agricultural'),
    ]
    
    # Relationship to Lead (if converted)
    lead = models.OneToOneField(
        'leads.Lead',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='customer',
        help_text='Original lead if this customer was converted from a lead'
    )
    
    # Basic Information
    first_name = models.CharField(
        max_length=100,
        help_text='First name of the customer'
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Last name of the customer'
    )
    email = models.EmailField(
        validators=[EmailValidator()],
        help_text='Email address of the customer'
    )
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        help_text='Phone number of the customer'
    )
    
    # Enhanced Information
    company_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Company name (for commercial customers)'
    )
    gst_number = models.CharField(
        max_length=15,
        blank=True,
        help_text='GST number for business customers'
    )
    
    # Address Information
    address = models.TextField(
        help_text='Full address of the customer'
    )
    city = models.CharField(
        max_length=100,
        help_text='City'
    )
    state = models.CharField(
        max_length=100,
        help_text='State'
    )
    pincode = models.CharField(
        max_length=10,
        help_text='PIN code'
    )
    
    # Customer Classification
    status = models.CharField(
        max_length=20,
        choices=CUSTOMER_STATUS_CHOICES,
        default='active',
        help_text='Current status of the customer'
    )
    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
        default='residential',
        help_text='Type of customer'
    )
    
    # Financial Information
    total_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Total value of all projects/contracts'
    )
    outstanding_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Outstanding amount to be paid'
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_customers',
        help_text='User assigned to manage this customer'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Metadata
    notes = models.TextField(
        blank=True,
        help_text='Internal notes about this customer'
    )
    
    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['status']),
            models.Index(fields=['customer_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['assigned_to']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_value__gte=0),
                name='valid_total_value'
            ),
            models.CheckConstraint(
                condition=models.Q(outstanding_amount__gte=0),
                name='valid_outstanding_amount'
            ),
        ]
    
    def __str__(self):
        if self.company_name:
            return f"{self.company_name} ({self.full_name})"
        return f"{self.full_name} ({self.email})"
    
    @property
    def full_name(self):
        """Return full name of the customer."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_business_customer(self):
        """Check if this is a business customer."""
        return bool(self.company_name or self.gst_number)
    
    @property
    def payment_status(self):
        """Get payment status based on outstanding amount."""
        if self.outstanding_amount == 0:
            return 'paid'
        elif self.outstanding_amount < self.total_value:
            return 'partial'
        else:
            return 'pending'
    
    def update_financial_totals(self):
        """Update total value and outstanding amount from related projects."""
        from apps.services.models import InstallationProject
        
        projects = InstallationProject.objects.filter(customer=self)
        self.total_value = sum(project.project_value for project in projects)
        self.outstanding_amount = sum(
            project.project_value - project.amount_paid 
            for project in projects
        )
        self.save(update_fields=['total_value', 'outstanding_amount', 'updated_at'])
    
    @classmethod
    def create_from_lead(cls, lead):
        """Create a customer from a lead."""
        customer = cls.objects.create(
            lead=lead,
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=lead.email,
            phone=lead.phone,
            address=lead.address,
            city=lead.city,
            state=lead.state,
            pincode=lead.pincode,
            customer_type=lead.property_type,
            assigned_to=lead.assigned_to,
            notes=f"Converted from lead on {timezone.now().date()}"
        )
        
        # Mark lead as converted
        lead.mark_as_converted()
        
        return customer


class CustomerHistory(models.Model):
    """
    Track history of customer interactions and changes
    """
    
    HISTORY_TYPE_CHOICES = [
        ('status_change', 'Status Change'),
        ('contact_update', 'Contact Update'),
        ('financial_update', 'Financial Update'),
        ('interaction', 'Interaction'),
        ('project_update', 'Project Update'),
        ('service_request', 'Service Request'),
        ('other', 'Other'),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='history',
        help_text='Customer this history entry belongs to'
    )
    history_type = models.CharField(
        max_length=20,
        choices=HISTORY_TYPE_CHOICES,
        help_text='Type of history entry'
    )
    title = models.CharField(
        max_length=200,
        help_text='Title or summary of the history entry'
    )
    description = models.TextField(
        help_text='Detailed description of what happened'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='User who made this change or interaction'
    )
    
    # Metadata
    old_values = models.JSONField(
        default=dict,
        help_text='Previous values (for change tracking)'
    )
    new_values = models.JSONField(
        default=dict,
        help_text='New values (for change tracking)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'customer_history'
        verbose_name = 'Customer History'
        verbose_name_plural = 'Customer History'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'created_at']),
            models.Index(fields=['history_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.customer.full_name} - {self.title} ({self.created_at.date()})"
