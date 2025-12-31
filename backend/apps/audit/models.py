from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
import json

User = get_user_model()


class AuditLog(models.Model):
    """
    Audit log model for tracking all changes to sensitive data
    """
    
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
    ]
    
    # User who performed the action
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text='User who performed the action'
    )
    
    # Action details
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text='Type of action performed'
    )
    
    # Generic foreign key to track any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text='Type of object that was modified'
    )
    object_id = models.CharField(
        max_length=50,
        help_text='ID of the object that was modified'
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Model and field information
    model_name = models.CharField(
        max_length=50,
        help_text='Name of the model that was modified'
    )
    
    # Change tracking
    changes = models.JSONField(
        default=dict,
        help_text='Before and after values for changes'
    )
    
    # Request information
    ip_address = models.GenericIPAddressField(
        help_text='IP address of the user'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='User agent string from the request'
    )
    request_path = models.CharField(
        max_length=500,
        blank=True,
        help_text='URL path of the request'
    )
    request_method = models.CharField(
        max_length=10,
        blank=True,
        help_text='HTTP method of the request'
    )
    
    # Additional context
    description = models.TextField(
        blank=True,
        help_text='Human-readable description of the action'
    )
    additional_data = models.JSONField(
        default=dict,
        help_text='Additional context data'
    )
    
    # Timestamp
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text='When the action was performed'
    )
    
    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['model_name', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.model_name} ({self.timestamp})"
    
    @classmethod
    def log_action(cls, user, action, obj, changes=None, request=None, description=""):
        """
        Create an audit log entry
        
        Args:
            user: User who performed the action
            action: Type of action (CREATE, UPDATE, DELETE, etc.)
            obj: Object that was modified
            changes: Dictionary of changes (before/after values)
            request: HTTP request object
            description: Human-readable description
        """
        # Get IP address and user agent from request
        ip_address = '127.0.0.1'
        user_agent = ''
        request_path = ''
        request_method = ''
        
        if request:
            ip_address = cls.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            request_path = request.path
            request_method = request.method
        
        # Create audit log entry
        audit_log = cls.objects.create(
            user=user,
            action=action,
            content_object=obj,
            model_name=obj._meta.model_name,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            request_method=request_method,
            description=description
        )
        
        return audit_log
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_changes_display(self):
        """Get human-readable changes display."""
        if not self.changes:
            return "No changes recorded"
        
        changes_text = []
        for field, change_data in self.changes.items():
            if isinstance(change_data, dict) and 'old' in change_data and 'new' in change_data:
                old_val = change_data['old']
                new_val = change_data['new']
                changes_text.append(f"{field}: '{old_val}' → '{new_val}'")
            else:
                changes_text.append(f"{field}: {change_data}")
        
        return "; ".join(changes_text)


class AuditLogRetention(models.Model):
    """
    Configuration for audit log retention policies
    """
    
    RETENTION_PERIOD_CHOICES = [
        (30, '30 days'),
        (90, '90 days'),
        (180, '6 months'),
        (365, '1 year'),
        (1095, '3 years'),
        (1825, '5 years'),
        (0, 'Never delete'),
    ]
    
    model_name = models.CharField(
        max_length=50,
        unique=True,
        help_text='Model name for which this retention policy applies'
    )
    retention_days = models.IntegerField(
        choices=RETENTION_PERIOD_CHOICES,
        default=365,
        help_text='Number of days to retain audit logs (0 = never delete)'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this retention policy is active'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'audit_log_retention'
        verbose_name = 'Audit Log Retention Policy'
        verbose_name_plural = 'Audit Log Retention Policies'
        ordering = ['model_name']
    
    def __str__(self):
        return f"{self.model_name} - {self.get_retention_days_display()}"
    
    @classmethod
    def cleanup_old_logs(cls):
        """
        Clean up old audit logs based on retention policies
        """
        from django.utils import timezone
        
        deleted_count = 0
        
        for policy in cls.objects.filter(is_active=True, retention_days__gt=0):
            cutoff_date = timezone.now() - timezone.timedelta(days=policy.retention_days)
            
            # Delete old logs for this model
            old_logs = AuditLog.objects.filter(
                model_name=policy.model_name,
                timestamp__lt=cutoff_date
            )
            
            count = old_logs.count()
            old_logs.delete()
            deleted_count += count
        
        return deleted_count


class SensitiveDataAccess(models.Model):
    """
    Track access to sensitive data fields
    """
    
    ACCESS_TYPE_CHOICES = [
        ('VIEW', 'View'),
        ('EXPORT', 'Export'),
        ('PRINT', 'Print'),
        ('COPY', 'Copy'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text='User who accessed the data'
    )
    
    # Data access details
    model_name = models.CharField(
        max_length=50,
        help_text='Model containing the sensitive data'
    )
    object_id = models.CharField(
        max_length=50,
        help_text='ID of the object accessed'
    )
    field_name = models.CharField(
        max_length=50,
        help_text='Name of the sensitive field accessed'
    )
    access_type = models.CharField(
        max_length=10,
        choices=ACCESS_TYPE_CHOICES,
        help_text='Type of access'
    )
    
    # Request information
    ip_address = models.GenericIPAddressField(
        help_text='IP address of the user'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='User agent string'
    )
    
    # Justification
    justification = models.TextField(
        blank=True,
        help_text='Business justification for accessing this data'
    )
    
    # Timestamp
    accessed_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the data was accessed'
    )
    
    class Meta:
        db_table = 'sensitive_data_access'
        verbose_name = 'Sensitive Data Access'
        verbose_name_plural = 'Sensitive Data Access'
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['user', 'accessed_at']),
            models.Index(fields=['model_name', 'field_name']),
            models.Index(fields=['accessed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} accessed {self.model_name}.{self.field_name} ({self.accessed_at})"
    
    @classmethod
    def log_access(cls, user, model_name, object_id, field_name, access_type, request=None, justification=""):
        """Log access to sensitive data."""
        ip_address = '127.0.0.1'
        user_agent = ''
        
        if request:
            ip_address = AuditLog.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        return cls.objects.create(
            user=user,
            model_name=model_name,
            object_id=str(object_id),
            field_name=field_name,
            access_type=access_type,
            ip_address=ip_address,
            user_agent=user_agent,
            justification=justification
        )
