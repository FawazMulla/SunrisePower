from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()


class ServiceRequest(models.Model):
    """
    Service request/ticket model for customer support
    """
    
    REQUEST_TYPE_CHOICES = [
        ('maintenance', 'Maintenance'),
        ('repair', 'Repair'),
        ('inspection', 'Inspection'),
        ('warranty', 'Warranty Claim'),
        ('technical_support', 'Technical Support'),
        ('installation_issue', 'Installation Issue'),
        ('performance_issue', 'Performance Issue'),
        ('other', 'Other'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('pending_customer', 'Pending Customer Response'),
        ('pending_parts', 'Pending Parts'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Request Details
    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        help_text='Unique ticket number'
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='service_requests',
        help_text='Customer who raised this request'
    )
    request_type = models.CharField(
        max_length=50,
        choices=REQUEST_TYPE_CHOICES,
        help_text='Type of service request'
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text='Priority level of the request'
    )
    
    # Content
    subject = models.CharField(
        max_length=200,
        help_text='Subject or title of the request'
    )
    description = models.TextField(
        help_text='Detailed description of the issue or request'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        help_text='Current status of the request'
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_service_requests',
        help_text='User assigned to handle this request'
    )
    
    # Related Installation Project (if applicable)
    installation_project = models.ForeignKey(
        'InstallationProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_requests',
        help_text='Related installation project'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date when request was resolved'
    )
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date when request was closed'
    )
    
    # Source tracking
    source_email = models.TextField(
        blank=True,
        help_text='Original email content if created from email'
    )
    source_data = models.JSONField(
        default=dict,
        help_text='Additional source data (chatbot, form, etc.)'
    )
    
    # Resolution
    resolution_notes = models.TextField(
        blank=True,
        help_text='Notes about how the request was resolved'
    )
    customer_satisfaction = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Customer satisfaction rating (1-5)'
    )
    
    class Meta:
        db_table = 'service_requests'
        verbose_name = 'Service Request'
        verbose_name_plural = 'Service Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.ticket_number} - {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_ticket_number(cls):
        """Generate unique ticket number."""
        import datetime
        today = datetime.date.today()
        prefix = f"SR{today.strftime('%Y%m%d')}"
        
        # Get the last ticket number for today
        last_ticket = cls.objects.filter(
            ticket_number__startswith=prefix
        ).order_by('-ticket_number').first()
        
        if last_ticket:
            last_number = int(last_ticket.ticket_number[-3:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:03d}"
    
    def mark_as_resolved(self, resolution_notes=""):
        """Mark service request as resolved."""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        if resolution_notes:
            self.resolution_notes = resolution_notes
        self.save(update_fields=['status', 'resolved_at', 'resolution_notes', 'updated_at'])
    
    def mark_as_closed(self):
        """Mark service request as closed."""
        if self.status != 'resolved':
            self.mark_as_resolved()
        self.status = 'closed'
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at', 'updated_at'])


class InstallationProject(models.Model):
    """
    Solar installation project tracking
    """
    
    PROJECT_STATUS_CHOICES = [
        ('quotation', 'Quotation'),
        ('approved', 'Approved'),
        ('design', 'Design Phase'),
        ('permits', 'Permits & Approvals'),
        ('procurement', 'Procurement'),
        ('installation', 'Installation'),
        ('testing', 'Testing & Commissioning'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]
    
    INSTALLATION_TYPE_CHOICES = [
        ('rooftop', 'Rooftop'),
        ('ground_mount', 'Ground Mount'),
        ('carport', 'Carport'),
        ('floating', 'Floating Solar'),
        ('agri_solar', 'Agri Solar'),
    ]
    
    # Project Details
    project_number = models.CharField(
        max_length=20,
        unique=True,
        help_text='Unique project number'
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='installation_projects',
        help_text='Customer for this project'
    )
    
    # Technical Details
    system_capacity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='System capacity in kW'
    )
    panel_brand = models.CharField(
        max_length=100,
        help_text='Solar panel brand'
    )
    panel_model = models.CharField(
        max_length=100,
        blank=True,
        help_text='Solar panel model'
    )
    panel_quantity = models.IntegerField(
        help_text='Number of solar panels'
    )
    inverter_brand = models.CharField(
        max_length=100,
        help_text='Inverter brand'
    )
    inverter_model = models.CharField(
        max_length=100,
        blank=True,
        help_text='Inverter model'
    )
    inverter_quantity = models.IntegerField(
        default=1,
        help_text='Number of inverters'
    )
    installation_type = models.CharField(
        max_length=50,
        choices=INSTALLATION_TYPE_CHOICES,
        default='rooftop',
        help_text='Type of installation'
    )
    
    # Project Status
    status = models.CharField(
        max_length=30,
        choices=PROJECT_STATUS_CHOICES,
        default='quotation',
        help_text='Current project status'
    )
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Project completion percentage'
    )
    
    # Financial
    project_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Total project value'
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Amount paid by customer'
    )
    
    # Project Team
    project_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_projects',
        help_text='Project manager'
    )
    sales_person = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_projects',
        help_text='Sales person who closed this project'
    )
    
    # Important Dates
    quotation_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date when quotation was provided'
    )
    approval_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date when project was approved by customer'
    )
    installation_start_date = models.DateField(
        null=True,
        blank=True,
        help_text='Installation start date'
    )
    installation_end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Installation completion date'
    )
    commissioning_date = models.DateField(
        null=True,
        blank=True,
        help_text='System commissioning date'
    )
    completion_date = models.DateField(
        null=True,
        blank=True,
        help_text='Project completion date'
    )
    
    # Installation Address (if different from customer address)
    installation_address = models.TextField(
        blank=True,
        help_text='Installation site address (if different from customer address)'
    )
    
    # Technical Specifications
    estimated_annual_generation = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Estimated annual energy generation in kWh'
    )
    warranty_years = models.IntegerField(
        default=25,
        help_text='Warranty period in years'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text='Project notes and comments'
    )
    
    class Meta:
        db_table = 'installation_projects'
        verbose_name = 'Installation Project'
        verbose_name_plural = 'Installation Projects'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['project_manager']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(progress_percentage__gte=0) & models.Q(progress_percentage__lte=100),
                name='valid_progress_percentage'
            ),
            models.CheckConstraint(
                condition=models.Q(project_value__gte=0),
                name='valid_project_value'
            ),
            models.CheckConstraint(
                condition=models.Q(amount_paid__gte=0),
                name='valid_amount_paid'
            ),
        ]
    
    def __str__(self):
        return f"{self.project_number} - {self.customer.full_name} ({self.system_capacity}kW)"
    
    def save(self, *args, **kwargs):
        if not self.project_number:
            self.project_number = self.generate_project_number()
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_project_number(cls):
        """Generate unique project number."""
        import datetime
        today = datetime.date.today()
        prefix = f"PRJ{today.strftime('%Y%m%d')}"
        
        # Get the last project number for today
        last_project = cls.objects.filter(
            project_number__startswith=prefix
        ).order_by('-project_number').first()
        
        if last_project:
            last_number = int(last_project.project_number[-3:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:03d}"
    
    @property
    def outstanding_amount(self):
        """Calculate outstanding amount."""
        return self.project_value - self.amount_paid
    
    @property
    def payment_percentage(self):
        """Calculate payment completion percentage."""
        if self.project_value > 0:
            return (self.amount_paid / self.project_value) * 100
        return 0
    
    def update_progress(self, percentage):
        """Update project progress percentage."""
        if 0 <= percentage <= 100:
            self.progress_percentage = percentage
            self.save(update_fields=['progress_percentage', 'updated_at'])
        else:
            raise ValueError("Progress percentage must be between 0 and 100")
    
    def mark_as_completed(self):
        """Mark project as completed."""
        self.status = 'completed'
        self.progress_percentage = 100
        self.completion_date = timezone.now().date()
        self.save(update_fields=['status', 'progress_percentage', 'completion_date', 'updated_at'])


class AMCContract(models.Model):
    """
    Annual Maintenance Contract model
    """
    
    CONTRACT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
        ('renewal_pending', 'Renewal Pending'),
    ]
    
    # Contract Details
    contract_number = models.CharField(
        max_length=20,
        unique=True,
        help_text='Unique contract number'
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='amc_contracts',
        help_text='Customer for this AMC contract'
    )
    installation_project = models.ForeignKey(
        InstallationProject,
        on_delete=models.CASCADE,
        related_name='amc_contracts',
        help_text='Related installation project'
    )
    
    # Contract Terms
    start_date = models.DateField(
        help_text='Contract start date'
    )
    end_date = models.DateField(
        help_text='Contract end date'
    )
    annual_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Annual contract value'
    )
    
    # Service Details
    maintenance_frequency = models.CharField(
        max_length=50,
        default='quarterly',
        help_text='Maintenance frequency (monthly, quarterly, bi-annual, annual)'
    )
    services_included = models.JSONField(
        default=list,
        help_text='List of services included in the contract'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=CONTRACT_STATUS_CHOICES,
        default='active',
        help_text='Current contract status'
    )
    renewal_reminder_sent = models.BooleanField(
        default=False,
        help_text='Whether renewal reminder has been sent'
    )
    auto_renewal = models.BooleanField(
        default=False,
        help_text='Whether contract auto-renews'
    )
    
    # Contact Person
    contact_person = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_amc_contracts',
        help_text='Person responsible for this contract'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    terms_and_conditions = models.TextField(
        blank=True,
        help_text='Contract terms and conditions'
    )
    notes = models.TextField(
        blank=True,
        help_text='Internal notes about this contract'
    )
    
    class Meta:
        db_table = 'amc_contracts'
        verbose_name = 'AMC Contract'
        verbose_name_plural = 'AMC Contracts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contract_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['end_date']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gt=models.F('start_date')),
                name='valid_contract_dates'
            ),
            models.CheckConstraint(
                condition=models.Q(annual_value__gte=0),
                name='valid_annual_value'
            ),
        ]
    
    def __str__(self):
        return f"{self.contract_number} - {self.customer.full_name}"
    
    def save(self, *args, **kwargs):
        if not self.contract_number:
            self.contract_number = self.generate_contract_number()
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_contract_number(cls):
        """Generate unique contract number."""
        import datetime
        today = datetime.date.today()
        prefix = f"AMC{today.strftime('%Y%m%d')}"
        
        # Get the last contract number for today
        last_contract = cls.objects.filter(
            contract_number__startswith=prefix
        ).order_by('-contract_number').first()
        
        if last_contract:
            last_number = int(last_contract.contract_number[-3:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:03d}"
    
    @property
    def is_active(self):
        """Check if contract is currently active."""
        today = timezone.now().date()
        return (
            self.status == 'active' and
            self.start_date <= today <= self.end_date
        )
    
    @property
    def is_expiring_soon(self, days=30):
        """Check if contract is expiring within specified days."""
        today = timezone.now().date()
        expiry_threshold = today + timezone.timedelta(days=days)
        return self.end_date <= expiry_threshold
    
    @property
    def days_until_expiry(self):
        """Calculate days until contract expiry."""
        today = timezone.now().date()
        if self.end_date > today:
            return (self.end_date - today).days
        return 0
    
    def renew_contract(self, new_end_date, new_annual_value=None):
        """Renew the contract with new end date and optionally new value."""
        self.start_date = self.end_date + timezone.timedelta(days=1)
        self.end_date = new_end_date
        if new_annual_value:
            self.annual_value = new_annual_value
        self.status = 'active'
        self.renewal_reminder_sent = False
        self.save(update_fields=[
            'start_date', 'end_date', 'annual_value', 'status', 
            'renewal_reminder_sent', 'updated_at'
        ])
    
    def mark_renewal_reminder_sent(self):
        """Mark that renewal reminder has been sent."""
        self.renewal_reminder_sent = True
        self.save(update_fields=['renewal_reminder_sent', 'updated_at'])
