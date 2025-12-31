"""
User models for Solar CRM Platform.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model with role-based access control.
    """
    
    ROLE_CHOICES = [
        ('owner', 'Business Owner'),
        ('sales_manager', 'Sales Manager'),
        ('sales_staff', 'Sales Staff'),
        ('support_staff', 'Support Staff'),
    ]
    
    # Additional fields
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='sales_staff',
        help_text='User role for access control'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Contact phone number'
    )
    is_active_crm_user = models.BooleanField(
        default=True,
        help_text='Whether user can access CRM features'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def full_name(self):
        """Return full name of the user."""
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def has_role(self, role):
        """Check if user has specific role."""
        return self.role == role
    
    def can_view_all_leads(self):
        """Check if user can view all leads."""
        return self.role in ['owner', 'sales_manager']
    
    def can_edit_all_leads(self):
        """Check if user can edit all leads."""
        return self.role in ['owner', 'sales_manager']
    
    def can_delete_leads(self):
        """Check if user can delete leads."""
        return self.role == 'owner'
    
    def can_manage_users(self):
        """Check if user can manage other users."""
        return self.role == 'owner'
    
    def can_view_analytics(self):
        """Check if user can view analytics."""
        return self.role in ['owner', 'sales_manager']
    
    def can_handle_service_requests(self):
        """Check if user can handle service requests."""
        return self.role in ['owner', 'support_staff']


class UserProfile(models.Model):
    """
    Extended profile information for users.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Profile information
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        help_text='User avatar image'
    )
    bio = models.TextField(
        blank=True,
        help_text='Short bio or description'
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text='Department or team'
    )
    
    # Preferences
    email_notifications = models.BooleanField(
        default=True,
        help_text='Receive email notifications'
    )
    dashboard_layout = models.JSONField(
        default=dict,
        help_text='Dashboard layout preferences'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.username}'s Profile"