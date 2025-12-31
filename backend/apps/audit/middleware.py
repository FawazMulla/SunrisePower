"""
Audit middleware for automatic logging of user actions
"""
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import AuditLog
import json
import threading

User = get_user_model()

# Thread-local storage for request context
_thread_locals = threading.local()


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to capture request context for audit logging
    """
    
    def process_request(self, request):
        """Store request in thread-local storage."""
        _thread_locals.request = request
        return None
    
    def process_response(self, request, response):
        """Clean up thread-local storage."""
        if hasattr(_thread_locals, 'request'):
            delattr(_thread_locals, 'request')
        return response


def get_current_request():
    """Get current request from thread-local storage."""
    return getattr(_thread_locals, 'request', None)


def get_current_user():
    """Get current user from thread-local storage."""
    request = get_current_request()
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None


class ModelAuditMixin:
    """
    Mixin to add audit logging to Django models
    """
    
    # Fields to exclude from audit logging
    AUDIT_EXCLUDE_FIELDS = ['created_at', 'updated_at', 'last_login']
    
    # Fields that contain sensitive data
    SENSITIVE_FIELDS = ['email', 'phone', 'address', 'gst_number']
    
    def save(self, *args, **kwargs):
        """Override save to add audit logging."""
        user = get_current_user()
        request = get_current_request()
        
        # Skip audit logging if no user context
        if not user:
            return super().save(*args, **kwargs)
        
        # Determine if this is a create or update
        is_create = self.pk is None
        action = 'CREATE' if is_create else 'UPDATE'
        
        # Get old values for update operations
        old_values = {}
        if not is_create:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_values = self._get_field_values(old_instance)
            except self.__class__.DoesNotExist:
                pass
        
        # Save the object
        result = super().save(*args, **kwargs)
        
        # Get new values
        new_values = self._get_field_values(self)
        
        # Calculate changes
        changes = {}
        if is_create:
            changes = {'created': new_values}
        else:
            for field, new_value in new_values.items():
                old_value = old_values.get(field)
                if old_value != new_value:
                    changes[field] = {
                        'old': old_value,
                        'new': new_value
                    }
        
        # Create audit log entry
        if changes:
            try:
                AuditLog.log_action(
                    user=user,
                    action=action,
                    obj=self,
                    changes=changes,
                    request=request,
                    description=f"{action.title()} {self.__class__.__name__}"
                )
            except Exception as e:
                # Don't fail the save operation if audit logging fails
                print(f"Audit logging failed: {e}")
        
        return result
    
    def delete(self, *args, **kwargs):
        """Override delete to add audit logging."""
        user = get_current_user()
        request = get_current_request()
        
        if user:
            # Get current values before deletion
            current_values = self._get_field_values(self)
            
            try:
                AuditLog.log_action(
                    user=user,
                    action='DELETE',
                    obj=self,
                    changes={'deleted': current_values},
                    request=request,
                    description=f"Delete {self.__class__.__name__}"
                )
            except Exception as e:
                print(f"Audit logging failed: {e}")
        
        return super().delete(*args, **kwargs)
    
    def _get_field_values(self, instance):
        """Get field values for audit logging."""
        values = {}
        
        for field in instance._meta.fields:
            field_name = field.name
            
            # Skip excluded fields
            if field_name in self.AUDIT_EXCLUDE_FIELDS:
                continue
            
            try:
                value = getattr(instance, field_name)
                
                # Handle special field types
                if hasattr(field, 'choices') and field.choices:
                    # For choice fields, store both value and display
                    display_method = f'get_{field_name}_display'
                    if hasattr(instance, display_method):
                        display_value = getattr(instance, display_method)()
                        values[field_name] = f"{value} ({display_value})"
                    else:
                        values[field_name] = value
                elif hasattr(value, 'isoformat'):
                    # For datetime fields
                    values[field_name] = value.isoformat()
                elif value is None:
                    values[field_name] = None
                else:
                    values[field_name] = str(value)
                    
            except Exception:
                values[field_name] = '<error retrieving value>'
        
        return values


# Utility functions for manual audit logging

def log_user_action(user, action, description, additional_data=None, request=None):
    """
    Log a user action that doesn't involve model changes
    
    Args:
        user: User who performed the action
        action: Type of action
        description: Description of the action
        additional_data: Additional context data
        request: HTTP request object
    """
    try:
        # Create a dummy object for the audit log
        from django.contrib.contenttypes.models import ContentType
        
        AuditLog.objects.create(
            user=user,
            action=action,
            content_type=ContentType.objects.get_for_model(User),
            object_id=str(user.pk),
            model_name='user_action',
            changes={},
            ip_address=AuditLog.get_client_ip(request) if request else '127.0.0.1',
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            request_path=request.path if request else '',
            request_method=request.method if request else '',
            description=description,
            additional_data=additional_data or {}
        )
    except Exception as e:
        print(f"Manual audit logging failed: {e}")


def log_data_export(user, model_name, record_count, export_format, request=None):
    """Log data export operations."""
    log_user_action(
        user=user,
        action='EXPORT',
        description=f"Exported {record_count} {model_name} records in {export_format} format",
        additional_data={
            'model_name': model_name,
            'record_count': record_count,
            'export_format': export_format
        },
        request=request
    )


def log_login_attempt(user, success, ip_address, user_agent):
    """Log login attempts."""
    action = 'LOGIN' if success else 'LOGIN_FAILED'
    description = f"{'Successful' if success else 'Failed'} login attempt"
    
    try:
        from django.contrib.contenttypes.models import ContentType
        
        AuditLog.objects.create(
            user=user if success else None,
            action=action,
            content_type=ContentType.objects.get_for_model(User),
            object_id=str(user.pk) if user else 'unknown',
            model_name='user_login',
            changes={},
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
            additional_data={'success': success}
        )
    except Exception as e:
        print(f"Login audit logging failed: {e}")