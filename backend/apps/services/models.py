from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()


class ServiceRequestStatusHistory(models.Model):
    """
    Track status changes for service requests
    """
    service_request = models.ForeignKey(
        'ServiceRequest',
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'service_request_status_history'
        verbose_name = 'Service Request Status History'
        verbose_name_plural = 'Service Request Status Histories'
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.service_request.ticket_number}: {self.old_status} → {self.new_status}"


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
        # Track status changes
        old_status = None
        if self.pk:
            try:
                old_instance = ServiceRequest.objects.get(pk=self.pk)
                old_status = old_instance.status
            except ServiceRequest.DoesNotExist:
                pass
        
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        
        super().save(*args, **kwargs)
        
        # Create status history record if status changed
        if old_status and old_status != self.status:
            ServiceRequestStatusHistory.objects.create(
                service_request=self,
                old_status=old_status,
                new_status=self.status,
                changed_by=getattr(self, '_changed_by', None),
                notes=getattr(self, '_status_change_notes', '')
            )
    
    def update_status(self, new_status, changed_by=None, notes=''):
        """Update status with proper tracking."""
        if not self.can_transition_to_status(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")
        
        self._changed_by = changed_by
        self._status_change_notes = notes
        self.status = new_status
        
        # Handle status-specific logic
        if new_status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()
            if notes:
                self.resolution_notes = notes
        elif new_status == 'closed' and not self.closed_at:
            if self.status != 'resolved':
                self.resolved_at = timezone.now()
            self.closed_at = timezone.now()
        
        self.save()
    
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
    
    def get_status_history(self):
        """Get status change history for this service request."""
        from apps.audit.models import AuditLog
        return AuditLog.objects.filter(
            model_name='ServiceRequest',
            object_id=str(self.id),
            action='UPDATE'
        ).order_by('-timestamp')
    
    def can_transition_to_status(self, new_status):
        """Check if service request can transition to the given status."""
        valid_transitions = {
            'open': ['in_progress', 'pending_customer', 'cancelled'],
            'in_progress': ['pending_customer', 'pending_parts', 'resolved', 'cancelled'],
            'pending_customer': ['in_progress', 'resolved', 'cancelled'],
            'pending_parts': ['in_progress', 'resolved', 'cancelled'],
            'resolved': ['closed', 'in_progress'],  # Can reopen if needed
            'closed': [],  # Cannot change from closed
            'cancelled': []  # Cannot change from cancelled
        }
        
        return new_status in valid_transitions.get(self.status, [])
    
    def get_next_valid_statuses(self):
        """Get list of valid next statuses for this service request."""
        valid_transitions = {
            'open': ['in_progress', 'pending_customer', 'cancelled'],
            'in_progress': ['pending_customer', 'pending_parts', 'resolved', 'cancelled'],
            'pending_customer': ['in_progress', 'resolved', 'cancelled'],
            'pending_parts': ['in_progress', 'resolved', 'cancelled'],
            'resolved': ['closed', 'in_progress'],
            'closed': [],
            'cancelled': []
        }
        
        return valid_transitions.get(self.status, [])
    
    @property
    def is_overdue(self):
        """Check if service request is overdue based on priority."""
        if self.status in ['resolved', 'closed', 'cancelled']:
            return False
        
        priority_sla_hours = {
            'urgent': 4,
            'high': 24,
            'medium': 72,
            'low': 168  # 1 week
        }
        
        sla_hours = priority_sla_hours.get(self.priority, 72)
        deadline = self.created_at + timezone.timedelta(hours=sla_hours)
        
        return timezone.now() > deadline
    
    @property
    def time_to_resolution(self):
        """Calculate time taken to resolve the request."""
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return None
    
    @property
    def age_in_hours(self):
        """Calculate age of service request in hours."""
        return (timezone.now() - self.created_at).total_seconds() / 3600


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
                check=models.Q(progress_percentage__gte=0) & models.Q(progress_percentage__lte=100),
                name='valid_progress_percentage'
            ),
            models.CheckConstraint(
                check=models.Q(project_value__gte=0),
                name='valid_project_value'
            ),
            models.CheckConstraint(
                check=models.Q(amount_paid__gte=0),
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
    
    def update_status_with_notification(self, new_status, updated_by=None, notes=''):
        """Update project status with stakeholder notification."""
        old_status = self.status
        self.status = new_status
        
        # Update progress based on status
        status_progress_map = {
            'quotation': 5,
            'approved': 10,
            'design': 20,
            'permits': 30,
            'procurement': 40,
            'installation': 70,
            'testing': 90,
            'completed': 100,
            'on_hold': self.progress_percentage,  # Keep current progress
            'cancelled': self.progress_percentage  # Keep current progress
        }
        
        if new_status in status_progress_map:
            self.progress_percentage = status_progress_map[new_status]
        
        # Set completion date if completed
        if new_status == 'completed' and not self.completion_date:
            self.completion_date = timezone.now().date()
        
        self.save()
        
        # Create status history record
        ProjectStatusHistory.objects.create(
            installation_project=self,
            old_status=old_status,
            new_status=new_status,
            changed_by=updated_by,
            notes=notes
        )
        
        # Create stakeholder notification
        if old_status != new_status:
            ProjectNotification.create_status_change_notification(
                project=self,
                old_status=old_status,
                new_status=new_status,
                changed_by=updated_by
            )
    
    def get_project_milestones(self):
        """Get project milestones based on current status and dates."""
        milestones = []
        
        milestone_configs = [
            ('quotation_provided', 'Quotation Provided', self.quotation_date),
            ('project_approved', 'Project Approved', self.approval_date),
            ('installation_started', 'Installation Started', self.installation_start_date),
            ('installation_completed', 'Installation Completed', self.installation_end_date),
            ('system_commissioned', 'System Commissioned', self.commissioning_date),
            ('project_completed', 'Project Completed', self.completion_date),
        ]
        
        for milestone_key, milestone_name, milestone_date in milestone_configs:
            milestone_status = 'completed' if milestone_date else 'pending'
            if milestone_date and milestone_date > timezone.now().date():
                milestone_status = 'scheduled'
            
            milestones.append({
                'key': milestone_key,
                'name': milestone_name,
                'date': milestone_date,
                'status': milestone_status
            })
        
        return milestones
    
    @property
    def project_duration_days(self):
        """Calculate project duration in days."""
        if self.completion_date and self.approval_date:
            return (self.completion_date - self.approval_date).days
        elif self.approval_date:
            return (timezone.now().date() - self.approval_date).days
        return None
    
    @property
    def is_overdue(self):
        """Check if project is overdue based on expected completion."""
        if self.status == 'completed':
            return False
        
        # Simple logic: projects should complete within 90 days of approval
        if self.approval_date:
            expected_completion = self.approval_date + timezone.timedelta(days=90)
            return timezone.now().date() > expected_completion
        
        return False
    
    @classmethod
    def get_overdue_projects(cls):
        """Get projects that are overdue."""
        return [project for project in cls.objects.exclude(status__in=['completed', 'cancelled']) if project.is_overdue]
    
    @classmethod
    def get_projects_by_status_summary(cls):
        """Get project count summary by status."""
        from django.db.models import Count
        return cls.objects.values('status').annotate(count=Count('id')).order_by('status')


class ProjectStatusHistory(models.Model):
    """
    Track status changes for installation projects
    """
    installation_project = models.ForeignKey(
        InstallationProject,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'project_status_history'
        verbose_name = 'Project Status History'
        verbose_name_plural = 'Project Status Histories'
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.installation_project.project_number}: {self.old_status} → {self.new_status}"


class ProjectMilestone(models.Model):
    """
    Track project milestones and deliverables
    """
    
    MILESTONE_TYPE_CHOICES = [
        ('quotation', 'Quotation'),
        ('approval', 'Customer Approval'),
        ('design', 'Design Completion'),
        ('permits', 'Permits Obtained'),
        ('procurement', 'Equipment Procurement'),
        ('installation_start', 'Installation Start'),
        ('installation_complete', 'Installation Complete'),
        ('testing', 'Testing & Commissioning'),
        ('handover', 'Project Handover'),
        ('custom', 'Custom Milestone'),
    ]
    
    MILESTONE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
        ('cancelled', 'Cancelled'),
    ]
    
    installation_project = models.ForeignKey(
        InstallationProject,
        on_delete=models.CASCADE,
        related_name='milestones'
    )
    milestone_type = models.CharField(
        max_length=30,
        choices=MILESTONE_TYPE_CHOICES
    )
    name = models.CharField(
        max_length=200,
        help_text='Milestone name or description'
    )
    description = models.TextField(blank=True)
    
    # Dates
    planned_date = models.DateField(
        null=True,
        blank=True,
        help_text='Planned completion date'
    )
    actual_date = models.DateField(
        null=True,
        blank=True,
        help_text='Actual completion date'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=MILESTONE_STATUS_CHOICES,
        default='pending'
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Person responsible for this milestone'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'project_milestones'
        verbose_name = 'Project Milestone'
        verbose_name_plural = 'Project Milestones'
        ordering = ['planned_date', 'created_at']
        indexes = [
            models.Index(fields=['installation_project', 'status']),
            models.Index(fields=['planned_date']),
            models.Index(fields=['assigned_to']),
        ]
    
    def __str__(self):
        return f"{self.installation_project.project_number} - {self.name}"
    
    def mark_as_completed(self, completed_by=None, notes=''):
        """Mark milestone as completed."""
        self.status = 'completed'
        self.actual_date = timezone.now().date()
        if notes:
            self.notes = notes
        self.save(update_fields=['status', 'actual_date', 'notes', 'updated_at'])
        
        # Create notification
        ProjectNotification.create_milestone_completion_notification(
            milestone=self,
            completed_by=completed_by
        )
    
    @property
    def is_overdue(self):
        """Check if milestone is overdue."""
        if self.status == 'completed':
            return False
        
        if self.planned_date:
            return timezone.now().date() > self.planned_date
        
        return False
    
    @property
    def days_overdue(self):
        """Calculate days overdue."""
        if self.is_overdue:
            return (timezone.now().date() - self.planned_date).days
        return 0


class ProjectNotification(models.Model):
    """
    Stakeholder notifications for project updates
    """
    
    NOTIFICATION_TYPE_CHOICES = [
        ('status_change', 'Status Change'),
        ('milestone_completed', 'Milestone Completed'),
        ('milestone_overdue', 'Milestone Overdue'),
        ('project_overdue', 'Project Overdue'),
        ('payment_due', 'Payment Due'),
        ('custom', 'Custom Notification'),
    ]
    
    NOTIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('acknowledged', 'Acknowledged'),
    ]
    
    installation_project = models.ForeignKey(
        InstallationProject,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPE_CHOICES
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Recipients
    recipients = models.JSONField(
        default=list,
        help_text='List of email addresses to notify'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=NOTIFICATION_STATUS_CHOICES,
        default='pending'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        help_text='Additional notification data'
    )
    
    class Meta:
        db_table = 'project_notifications'
        verbose_name = 'Project Notification'
        verbose_name_plural = 'Project Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['installation_project', 'status']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.installation_project.project_number} - {self.title}"
    
    def mark_as_sent(self):
        """Mark notification as sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_acknowledged(self):
        """Mark notification as acknowledged."""
        self.status = 'acknowledged'
        self.acknowledged_at = timezone.now()
        self.save(update_fields=['status', 'acknowledged_at'])
    
    @classmethod
    def create_status_change_notification(cls, project, old_status, new_status, changed_by=None):
        """Create notification for project status change."""
        recipients = []
        
        # Add customer email
        if project.customer.email:
            recipients.append(project.customer.email)
        
        # Add project manager email
        if project.project_manager and project.project_manager.email:
            recipients.append(project.project_manager.email)
        
        # Add sales person email
        if project.sales_person and project.sales_person.email:
            recipients.append(project.sales_person.email)
        
        title = f"Project Status Update - {project.project_number}"
        message = f"""
        Dear Stakeholder,
        
        The status of your solar installation project {project.project_number} has been updated.
        
        Previous Status: {old_status.replace('_', ' ').title()}
        New Status: {new_status.replace('_', ' ').title()}
        
        Project Details:
        - Customer: {project.customer.full_name}
        - System Capacity: {project.system_capacity} kW
        - Progress: {project.progress_percentage}%
        
        For any questions, please contact your project manager.
        
        Best regards,
        Sunrise Power Team
        """
        
        return cls.objects.create(
            installation_project=project,
            notification_type='status_change',
            title=title,
            message=message.strip(),
            recipients=recipients,
            metadata={
                'old_status': old_status,
                'new_status': new_status,
                'changed_by': changed_by.get_full_name() if changed_by else None
            }
        )
    
    @classmethod
    def create_milestone_completion_notification(cls, milestone, completed_by=None):
        """Create notification for milestone completion."""
        project = milestone.installation_project
        recipients = []
        
        # Add customer email
        if project.customer.email:
            recipients.append(project.customer.email)
        
        # Add project manager email
        if project.project_manager and project.project_manager.email:
            recipients.append(project.project_manager.email)
        
        title = f"Milestone Completed - {project.project_number}"
        message = f"""
        Dear Stakeholder,
        
        A milestone has been completed for your solar installation project {project.project_number}.
        
        Milestone: {milestone.name}
        Completed Date: {milestone.actual_date}
        Project Progress: {project.progress_percentage}%
        
        Project Details:
        - Customer: {project.customer.full_name}
        - System Capacity: {project.system_capacity} kW
        - Current Status: {project.get_status_display()}
        
        Thank you for choosing Sunrise Power.
        
        Best regards,
        Sunrise Power Team
        """
        
        return cls.objects.create(
            installation_project=project,
            notification_type='milestone_completed',
            title=title,
            message=message.strip(),
            recipients=recipients,
            metadata={
                'milestone_id': milestone.id,
                'milestone_name': milestone.name,
                'completed_by': completed_by.get_full_name() if completed_by else None
            }
        )


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
                check=models.Q(end_date__gt=models.F('start_date')),
                name='valid_contract_dates'
            ),
            models.CheckConstraint(
                check=models.Q(annual_value__gte=0),
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
    
    def check_renewal_status(self):
        """Check and update renewal status based on dates."""
        today = timezone.now().date()
        
        if self.end_date < today and self.status == 'active':
            self.status = 'expired'
            self.save(update_fields=['status', 'updated_at'])
        elif self.is_expiring_soon(30) and self.status == 'active' and not self.renewal_reminder_sent:
            self.status = 'renewal_pending'
            self.save(update_fields=['status', 'updated_at'])
    
    @classmethod
    def get_contracts_needing_renewal_alerts(cls, days_ahead=30):
        """Get contracts that need renewal alerts."""
        today = timezone.now().date()
        alert_date = today + timezone.timedelta(days=days_ahead)
        
        return cls.objects.filter(
            status='active',
            end_date__lte=alert_date,
            renewal_reminder_sent=False
        )
    
    @classmethod
    def get_expired_contracts(cls):
        """Get contracts that have expired."""
        today = timezone.now().date()
        return cls.objects.filter(
            end_date__lt=today,
            status__in=['active', 'renewal_pending']
        )
    
    @classmethod
    def get_expiring_soon_contracts(cls, days=30):
        """Get contracts expiring within specified days."""
        today = timezone.now().date()
        expiry_date = today + timezone.timedelta(days=days)
        
        return cls.objects.filter(
            status='active',
            end_date__lte=expiry_date,
            end_date__gte=today
        )


class AMCRenewalAlert(models.Model):
    """
    Track AMC contract renewal alerts
    """
    
    ALERT_TYPE_CHOICES = [
        ('30_days', '30 Days Before Expiry'),
        ('15_days', '15 Days Before Expiry'),
        ('7_days', '7 Days Before Expiry'),
        ('expired', 'Contract Expired'),
    ]
    
    ALERT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('acknowledged', 'Acknowledged'),
        ('dismissed', 'Dismissed'),
    ]
    
    amc_contract = models.ForeignKey(
        AMCContract,
        on_delete=models.CASCADE,
        related_name='renewal_alerts'
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPE_CHOICES
    )
    alert_date = models.DateField(
        help_text='Date when alert should be triggered'
    )
    status = models.CharField(
        max_length=20,
        choices=ALERT_STATUS_CHOICES,
        default='pending'
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_to = models.JSONField(
        default=list,
        help_text='List of email addresses alert was sent to'
    )
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'amc_renewal_alerts'
        verbose_name = 'AMC Renewal Alert'
        verbose_name_plural = 'AMC Renewal Alerts'
        ordering = ['-alert_date']
        unique_together = ['amc_contract', 'alert_type']
        indexes = [
            models.Index(fields=['alert_date', 'status']),
            models.Index(fields=['amc_contract', 'alert_type']),
        ]
    
    def __str__(self):
        return f"{self.amc_contract.contract_number} - {self.get_alert_type_display()}"
    
    def mark_as_sent(self, sent_to_emails):
        """Mark alert as sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.sent_to = sent_to_emails
        self.save(update_fields=['status', 'sent_at', 'sent_to', 'updated_at'])
    
    def acknowledge(self, user, notes=''):
        """Acknowledge the alert."""
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        if notes:
            self.notes = notes
        self.save(update_fields=['status', 'acknowledged_by', 'acknowledged_at', 'notes', 'updated_at'])
    
    @classmethod
    def create_alerts_for_contract(cls, amc_contract):
        """Create all necessary alerts for a contract."""
        alerts_to_create = []
        
        # Calculate alert dates
        alert_configs = [
            ('30_days', 30),
            ('15_days', 15),
            ('7_days', 7),
            ('expired', 0)  # On expiry date
        ]
        
        for alert_type, days_before in alert_configs:
            alert_date = amc_contract.end_date - timezone.timedelta(days=days_before)
            
            # Only create future alerts
            if alert_date >= timezone.now().date():
                alert, created = cls.objects.get_or_create(
                    amc_contract=amc_contract,
                    alert_type=alert_type,
                    defaults={'alert_date': alert_date}
                )
                if created:
                    alerts_to_create.append(alert)
        
        return alerts_to_create
    
    @classmethod
    def get_pending_alerts(cls):
        """Get alerts that should be sent today."""
        today = timezone.now().date()
        return cls.objects.filter(
            alert_date__lte=today,
            status='pending'
        ).select_related('amc_contract', 'amc_contract__customer')


class PaymentMilestone(models.Model):
    """
    Payment milestones for installation projects
    """
    
    MILESTONE_TYPE_CHOICES = [
        ('advance', 'Advance Payment'),
        ('material_delivery', 'Material Delivery'),
        ('installation_start', 'Installation Start'),
        ('installation_complete', 'Installation Complete'),
        ('commissioning', 'Commissioning'),
        ('final_payment', 'Final Payment'),
        ('custom', 'Custom Milestone'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived'),
    ]
    
    installation_project = models.ForeignKey(
        InstallationProject,
        on_delete=models.CASCADE,
        related_name='payment_milestones',
        help_text='Related installation project'
    )
    milestone_type = models.CharField(
        max_length=30,
        choices=MILESTONE_TYPE_CHOICES,
        help_text='Type of payment milestone'
    )
    name = models.CharField(
        max_length=200,
        help_text='Milestone name or description'
    )
    description = models.TextField(
        blank=True,
        help_text='Detailed description of the milestone'
    )
    
    # Financial Details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Milestone payment amount'
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Percentage of total project value'
    )
    
    # Dates
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text='Payment due date'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        help_text='Payment status'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text='Internal notes about this milestone'
    )
    
    class Meta:
        db_table = 'payment_milestones'
        verbose_name = 'Payment Milestone'
        verbose_name_plural = 'Payment Milestones'
        ordering = ['due_date', 'created_at']
        indexes = [
            models.Index(fields=['installation_project', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gte=0),
                name='valid_milestone_amount'
            ),
        ]
    
    def __str__(self):
        return f"{self.installation_project.project_number} - {self.name}"
    
    @property
    def amount_paid(self):
        """Calculate total amount paid for this milestone."""
        # Workaround for Python 3.13 compatibility issue
        completed_payments = self.payments.filter(status='completed')
        total = sum(payment.amount for payment in completed_payments)
        return total
    
    @property
    def outstanding_amount(self):
        """Calculate outstanding amount for this milestone."""
        return self.amount - self.amount_paid
    
    @property
    def is_overdue(self):
        """Check if milestone payment is overdue."""
        if self.status in ['paid', 'waived']:
            return False
        
        if self.due_date:
            return timezone.now().date() > self.due_date
        
        return False
    
    @property
    def days_overdue(self):
        """Calculate days overdue."""
        if self.is_overdue:
            return (timezone.now().date() - self.due_date).days
        return 0
    
    def update_status_based_on_payments(self):
        """Update milestone status based on payment records."""
        total_paid = self.amount_paid
        
        if total_paid >= self.amount:
            self.status = 'paid'
        elif total_paid > 0:
            self.status = 'partial'
        elif self.is_overdue:
            self.status = 'overdue'
        else:
            self.status = 'pending'
        
        self.save(update_fields=['status', 'updated_at'])
    
    @classmethod
    def create_default_milestones_for_project(cls, project):
        """Create default payment milestones for a project."""
        default_milestones = [
            ('advance', 'Advance Payment', 30.0),
            ('material_delivery', 'Material Delivery Payment', 40.0),
            ('installation_complete', 'Installation Completion Payment', 25.0),
            ('final_payment', 'Final Payment', 5.0),
        ]
        
        milestones = []
        for milestone_type, name, percentage in default_milestones:
            amount = (project.project_value * percentage) / 100
            
            milestone = cls.objects.create(
                installation_project=project,
                milestone_type=milestone_type,
                name=name,
                amount=amount,
                percentage=percentage
            )
            milestones.append(milestone)
        
        return milestones


class Invoice(models.Model):
    """
    Invoice management for projects and services
    """
    
    INVOICE_TYPE_CHOICES = [
        ('project', 'Project Invoice'),
        ('amc', 'AMC Invoice'),
        ('service', 'Service Invoice'),
        ('maintenance', 'Maintenance Invoice'),
        ('other', 'Other'),
    ]
    
    INVOICE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Invoice Details
    invoice_number = models.CharField(
        max_length=20,
        unique=True,
        help_text='Unique invoice number'
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text='Customer for this invoice'
    )
    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPE_CHOICES,
        help_text='Type of invoice'
    )
    
    # Related Records
    installation_project = models.ForeignKey(
        InstallationProject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invoices',
        help_text='Related installation project'
    )
    amc_contract = models.ForeignKey(
        AMCContract,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invoices',
        help_text='Related AMC contract'
    )
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invoices',
        help_text='Related service request'
    )
    payment_milestone = models.ForeignKey(
        PaymentMilestone,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invoices',
        help_text='Related payment milestone'
    )
    
    # Financial Details
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Invoice subtotal before taxes'
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        help_text='Tax rate percentage (GST/VAT)'
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Tax amount'
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Total invoice amount including tax'
    )
    
    # Dates
    invoice_date = models.DateField(
        help_text='Invoice date'
    )
    due_date = models.DateField(
        help_text='Payment due date'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=INVOICE_STATUS_CHOICES,
        default='draft',
        help_text='Invoice status'
    )
    
    # Invoice Content
    line_items = models.JSONField(
        default=list,
        help_text='Invoice line items with description, quantity, rate, amount'
    )
    notes = models.TextField(
        blank=True,
        help_text='Invoice notes or terms'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date when invoice was sent to customer'
    )
    
    class Meta:
        db_table = 'invoices'
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-invoice_date']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['invoice_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0),
                name='valid_total_amount'
            ),
            models.CheckConstraint(
                check=models.Q(due_date__gte=models.F('invoice_date')),
                name='valid_due_date'
            ),
        ]
    
    def __str__(self):
        return f"{self.invoice_number} - {self.customer.full_name}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        
        # Calculate tax amount and total
        self.tax_amount = (self.subtotal * self.tax_rate) / 100
        self.total_amount = self.subtotal + self.tax_amount
        
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_invoice_number(cls):
        """Generate unique invoice number."""
        import datetime
        today = datetime.date.today()
        prefix = f"INV{today.strftime('%Y%m%d')}"
        
        # Get the last invoice number for today
        last_invoice = cls.objects.filter(
            invoice_number__startswith=prefix
        ).order_by('-invoice_number').first()
        
        if last_invoice:
            last_number = int(last_invoice.invoice_number[-3:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:03d}"
    
    @property
    def amount_paid(self):
        """Calculate total amount paid for this invoice."""
        # Workaround for Python 3.13 compatibility issue
        completed_payments = self.payments.filter(status='completed')
        total = sum(payment.amount for payment in completed_payments)
        return total
    
    @property
    def outstanding_amount(self):
        """Calculate outstanding amount for this invoice."""
        return self.total_amount - self.amount_paid
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue."""
        if self.status in ['paid', 'cancelled']:
            return False
        
        return timezone.now().date() > self.due_date
    
    @property
    def days_overdue(self):
        """Calculate days overdue."""
        if self.is_overdue:
            return (timezone.now().date() - self.due_date).days
        return 0
    
    def mark_as_sent(self):
        """Mark invoice as sent to customer."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])
    
    def update_status_based_on_payments(self):
        """Update invoice status based on payment records."""
        total_paid = self.amount_paid
        
        if total_paid >= self.total_amount:
            self.status = 'paid'
        elif total_paid > 0:
            self.status = 'partial'
        elif self.is_overdue:
            self.status = 'overdue'
        elif self.sent_at:
            self.status = 'sent'
        else:
            self.status = 'draft'
        
        self.save(update_fields=['status', 'updated_at'])
    
    @classmethod
    def create_milestone_invoice(cls, milestone, line_items=None):
        """Create invoice for a payment milestone."""
        if not line_items:
            line_items = [{
                'description': milestone.name,
                'quantity': 1,
                'rate': float(milestone.amount),
                'amount': float(milestone.amount)
            }]
        
        return cls.objects.create(
            customer=milestone.installation_project.customer,
            invoice_type='project',
            installation_project=milestone.installation_project,
            payment_milestone=milestone,
            subtotal=milestone.amount,
            invoice_date=timezone.now().date(),
            due_date=milestone.due_date or (timezone.now().date() + timezone.timedelta(days=30)),
            line_items=line_items,
            notes=f"Payment for {milestone.name} - Project {milestone.installation_project.project_number}"
        )


class Payment(models.Model):
    """
    Payment records for invoices and milestones
    """
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('card', 'Credit/Debit Card'),
        ('online', 'Online Payment'),
        ('other', 'Other'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Payment Details
    payment_number = models.CharField(
        max_length=20,
        unique=True,
        help_text='Unique payment reference number'
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='payments',
        help_text='Customer who made the payment'
    )
    
    # Related Records
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        help_text='Related invoice'
    )
    payment_milestone = models.ForeignKey(
        PaymentMilestone,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        help_text='Related payment milestone'
    )
    installation_project = models.ForeignKey(
        InstallationProject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        help_text='Related installation project'
    )
    
    # Financial Details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Payment amount'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        help_text='Payment method used'
    )
    
    # Payment Details
    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Bank/Gateway transaction ID'
    )
    cheque_number = models.CharField(
        max_length=50,
        blank=True,
        help_text='Cheque number (if applicable)'
    )
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Bank name (for cheque/transfer)'
    )
    
    # Dates
    payment_date = models.DateField(
        help_text='Date of payment'
    )
    cleared_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date when payment was cleared (for cheques)'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        help_text='Payment status'
    )
    
    # Processing Details
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payments',
        help_text='User who processed this payment'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text='Payment notes or remarks'
    )
    
    class Meta:
        db_table = 'payments'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['transaction_id']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='valid_payment_amount'
            ),
        ]
    
    def __str__(self):
        return f"{self.payment_number} - {self.customer.full_name} - ₹{self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        
        super().save(*args, **kwargs)
        
        # Update related invoice/milestone status
        if self.invoice:
            self.invoice.update_status_based_on_payments()
        if self.payment_milestone:
            self.payment_milestone.update_status_based_on_payments()
    
    @classmethod
    def generate_payment_number(cls):
        """Generate unique payment number."""
        import datetime
        today = datetime.date.today()
        prefix = f"PAY{today.strftime('%Y%m%d')}"
        
        # Get the last payment number for today
        last_payment = cls.objects.filter(
            payment_number__startswith=prefix
        ).order_by('-payment_number').first()
        
        if last_payment:
            last_number = int(last_payment.payment_number[-3:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:03d}"
    
    def mark_as_completed(self, processed_by=None, notes=''):
        """Mark payment as completed."""
        self.status = 'completed'
        self.processed_by = processed_by
        if notes:
            self.notes = notes
        if self.payment_method == 'cheque' and not self.cleared_date:
            self.cleared_date = timezone.now().date()
        
        self.save(update_fields=['status', 'processed_by', 'notes', 'cleared_date', 'updated_at'])
    
    def mark_as_failed(self, reason=''):
        """Mark payment as failed."""
        self.status = 'failed'
        if reason:
            self.notes = reason
        self.save(update_fields=['status', 'notes', 'updated_at'])
    
    @classmethod
    def get_pending_cheque_clearances(cls):
        """Get cheque payments pending clearance."""
        return cls.objects.filter(
            payment_method='cheque',
            status='processing',
            cleared_date__isnull=True
        )
    
    @classmethod
    def get_payments_by_date_range(cls, start_date, end_date, status='completed'):
        """Get payments within date range."""
        return cls.objects.filter(
            payment_date__range=[start_date, end_date],
            status=status
        )


class FinancialSummary(models.Model):
    """
    Financial summary and analytics data
    """
    
    SUMMARY_TYPE_CHOICES = [
        ('daily', 'Daily Summary'),
        ('weekly', 'Weekly Summary'),
        ('monthly', 'Monthly Summary'),
        ('quarterly', 'Quarterly Summary'),
        ('yearly', 'Yearly Summary'),
    ]
    
    summary_type = models.CharField(
        max_length=20,
        choices=SUMMARY_TYPE_CHOICES,
        help_text='Type of financial summary'
    )
    period_start = models.DateField(
        help_text='Start date of the summary period'
    )
    period_end = models.DateField(
        help_text='End date of the summary period'
    )
    
    # Revenue Metrics
    total_invoiced = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Total amount invoiced in period'
    )
    total_collected = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Total amount collected in period'
    )
    total_outstanding = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Total outstanding amount'
    )
    
    # Project Metrics
    projects_invoiced = models.IntegerField(
        default=0,
        help_text='Number of projects invoiced'
    )
    projects_completed = models.IntegerField(
        default=0,
        help_text='Number of projects completed'
    )
    
    # Payment Metrics
    payments_received = models.IntegerField(
        default=0,
        help_text='Number of payments received'
    )
    average_payment_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Average payment time in days'
    )
    
    # Overdue Metrics
    overdue_invoices_count = models.IntegerField(
        default=0,
        help_text='Number of overdue invoices'
    )
    overdue_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Total overdue amount'
    )
    
    # Tracking
    calculated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_summaries'
        verbose_name = 'Financial Summary'
        verbose_name_plural = 'Financial Summaries'
        ordering = ['-period_end']
        unique_together = ['summary_type', 'period_start', 'period_end']
        indexes = [
            models.Index(fields=['summary_type', 'period_end']),
            models.Index(fields=['period_start', 'period_end']),
        ]
    
    def __str__(self):
        return f"{self.get_summary_type_display()} - {self.period_start} to {self.period_end}"
    
    @classmethod
    def calculate_summary_for_period(cls, summary_type, start_date, end_date):
        """Calculate financial summary for a given period."""
        from django.db.models import Sum, Count, Avg
        
        # Get invoices in period
        invoices = Invoice.objects.filter(
            invoice_date__range=[start_date, end_date]
        )
        
        # Get payments in period
        payments = Payment.objects.filter(
            payment_date__range=[start_date, end_date],
            status='completed'
        )
        
        # Get overdue invoices
        overdue_invoices = Invoice.objects.filter(
            due_date__lt=end_date,
            status__in=['sent', 'partial', 'overdue']
        )
        
        # Calculate metrics
        # Workaround for Python 3.13 compatibility issue
        total_invoiced = sum(invoice.total_amount for invoice in invoices)
        total_collected = sum(payment.amount for payment in payments)
        
        # Calculate outstanding amounts manually
        outstanding_invoices = Invoice.objects.filter(
            status__in=['sent', 'partial', 'overdue']
        )
        total_outstanding = sum(invoice.outstanding_amount for invoice in outstanding_invoices)
        
        projects_invoiced = invoices.filter(invoice_type='project').values('installation_project').distinct().count()
        projects_completed = InstallationProject.objects.filter(
            completion_date__range=[start_date, end_date]
        ).count()
        
        payments_received = payments.count()
        
        # Calculate average payment time
        completed_invoices = Invoice.objects.filter(
            status='paid',
            invoice_date__range=[start_date, end_date]
        )
        avg_payment_days = []
        for invoice in completed_invoices:
            last_payment = invoice.payments.filter(status='completed').order_by('-payment_date').first()
            if last_payment:
                days = (last_payment.payment_date - invoice.invoice_date).days
                avg_payment_days.append(days)
        
        average_payment_time = sum(avg_payment_days) / len(avg_payment_days) if avg_payment_days else None
        
        overdue_invoices_count = overdue_invoices.count()
        overdue_amount = sum(invoice.outstanding_amount for invoice in overdue_invoices)
        
        # Create or update summary
        summary, created = cls.objects.update_or_create(
            summary_type=summary_type,
            period_start=start_date,
            period_end=end_date,
            defaults={
                'total_invoiced': total_invoiced,
                'total_collected': total_collected,
                'total_outstanding': total_outstanding,
                'projects_invoiced': projects_invoiced,
                'projects_completed': projects_completed,
                'payments_received': payments_received,
                'average_payment_time': average_payment_time,
                'overdue_invoices_count': overdue_invoices_count,
                'overdue_amount': overdue_amount,
            }
        )
        
        return summary
