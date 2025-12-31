"""
Signal handlers for automatic audit logging
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import AuditLog
from .middleware import get_current_user, get_current_request
import json

User = get_user_model()


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log successful user login."""
    try:
        AuditLog.log_action(
            user=user,
            action='LOGIN',
            obj=user,
            changes={},
            request=request,
            description=f"User {user.username} logged in successfully"
        )
    except Exception as e:
        print(f"Login audit logging failed: {e}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout."""
    if user:
        try:
            AuditLog.log_action(
                user=user,
                action='LOGOUT',
                obj=user,
                changes={},
                request=request,
                description=f"User {user.username} logged out"
            )
        except Exception as e:
            print(f"Logout audit logging failed: {e}")


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Log failed login attempts."""
    try:
        username = credentials.get('username', 'unknown')
        
        # Try to get the user if they exist
        user = None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            pass
        
        # Create audit log with or without user
        ip_address = AuditLog.get_client_ip(request) if request else '127.0.0.1'
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        from django.contrib.contenttypes.models import ContentType
        
        AuditLog.objects.create(
            user=user,  # Will be None if user doesn't exist
            action='LOGIN_FAILED',
            content_type=ContentType.objects.get_for_model(User),
            object_id=str(user.pk) if user else 'unknown',
            model_name='user_login',
            changes={'attempted_username': username},
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request.path if request else '',
            request_method=request.method if request else '',
            description=f"Failed login attempt for username: {username}"
        )
    except Exception as e:
        print(f"Failed login audit logging failed: {e}")


# Model-specific signal handlers for sensitive models

@receiver(pre_save, sender='leads.Lead')
def audit_lead_changes(sender, instance, **kwargs):
    """Audit changes to Lead model."""
    _audit_model_changes(sender, instance, 'Lead')


@receiver(pre_save, sender='customers.Customer')
def audit_customer_changes(sender, instance, **kwargs):
    """Audit changes to Customer model."""
    _audit_model_changes(sender, instance, 'Customer')


@receiver(pre_save, sender='services.ServiceRequest')
def audit_service_request_changes(sender, instance, **kwargs):
    """Audit changes to ServiceRequest model."""
    _audit_model_changes(sender, instance, 'ServiceRequest')


@receiver(pre_save, sender='services.InstallationProject')
def audit_installation_project_changes(sender, instance, **kwargs):
    """Audit changes to InstallationProject model."""
    _audit_model_changes(sender, instance, 'InstallationProject')


@receiver(pre_save, sender='services.AMCContract')
def audit_amc_contract_changes(sender, instance, **kwargs):
    """Audit changes to AMCContract model."""
    _audit_model_changes(sender, instance, 'AMCContract')


@receiver(post_delete)
def audit_model_deletion(sender, instance, **kwargs):
    """Audit model deletions."""
    user = get_current_user()
    request = get_current_request()
    
    if not user:
        return
    
    # Only audit specific models
    audited_models = [
        'Lead', 'Customer', 'ServiceRequest', 
        'InstallationProject', 'AMCContract', 'User'
    ]
    
    if sender.__name__ not in audited_models:
        return
    
    try:
        # Get field values before deletion
        field_values = {}
        for field in instance._meta.fields:
            try:
                value = getattr(instance, field.name)
                if value is not None:
                    field_values[field.name] = str(value)
            except Exception:
                pass
        
        AuditLog.log_action(
            user=user,
            action='DELETE',
            obj=instance,
            changes={'deleted_data': field_values},
            request=request,
            description=f"Deleted {sender.__name__}: {str(instance)}"
        )
    except Exception as e:
        print(f"Deletion audit logging failed: {e}")


def _audit_model_changes(sender, instance, model_name):
    """Helper function to audit model changes."""
    user = get_current_user()
    request = get_current_request()
    
    if not user:
        return
    
    # Determine if this is a create or update
    is_create = instance.pk is None
    
    if is_create:
        # For new objects, we'll log in post_save
        return
    
    try:
        # Get old values
        old_instance = sender.objects.get(pk=instance.pk)
        old_values = _get_model_field_values(old_instance)
        new_values = _get_model_field_values(instance)
        
        # Calculate changes
        changes = {}
        for field, new_value in new_values.items():
            old_value = old_values.get(field)
            if old_value != new_value:
                changes[field] = {
                    'old': old_value,
                    'new': new_value
                }
        
        # Store changes in instance for post_save handler
        if changes:
            instance._audit_changes = changes
            
    except sender.DoesNotExist:
        # Object doesn't exist yet, this is a create
        pass
    except Exception as e:
        print(f"Pre-save audit logging failed: {e}")


@receiver(post_save)
def audit_model_creation_and_updates(sender, instance, created, **kwargs):
    """Audit model creation and updates."""
    user = get_current_user()
    request = get_current_request()
    
    if not user:
        return
    
    # Only audit specific models
    audited_models = [
        'Lead', 'Customer', 'ServiceRequest', 
        'InstallationProject', 'AMCContract', 'User'
    ]
    
    if sender.__name__ not in audited_models:
        return
    
    try:
        if created:
            # New object created
            field_values = _get_model_field_values(instance)
            changes = {'created_data': field_values}
            action = 'CREATE'
            description = f"Created {sender.__name__}: {str(instance)}"
        else:
            # Object updated
            changes = getattr(instance, '_audit_changes', {})
            if not changes:
                return  # No changes to audit
            
            action = 'UPDATE'
            description = f"Updated {sender.__name__}: {str(instance)}"
        
        AuditLog.log_action(
            user=user,
            action=action,
            obj=instance,
            changes=changes,
            request=request,
            description=description
        )
        
        # Clean up temporary audit changes
        if hasattr(instance, '_audit_changes'):
            delattr(instance, '_audit_changes')
            
    except Exception as e:
        print(f"Post-save audit logging failed: {e}")


def _get_model_field_values(instance):
    """Get field values for audit logging."""
    values = {}
    
    # Fields to exclude from audit logging
    exclude_fields = ['created_at', 'updated_at', 'last_login', 'password']
    
    for field in instance._meta.fields:
        field_name = field.name
        
        if field_name in exclude_fields:
            continue
        
        try:
            value = getattr(instance, field_name)
            
            if value is None:
                values[field_name] = None
            elif hasattr(value, 'isoformat'):
                # DateTime fields
                values[field_name] = value.isoformat()
            elif hasattr(field, 'choices') and field.choices:
                # Choice fields - store both value and display
                display_method = f'get_{field_name}_display'
                if hasattr(instance, display_method):
                    display_value = getattr(instance, display_method)()
                    values[field_name] = f"{value} ({display_value})"
                else:
                    values[field_name] = str(value)
            else:
                values[field_name] = str(value)
                
        except Exception:
            values[field_name] = '<error retrieving value>'
    
    return values