"""
Admin configuration for users app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin configuration for custom User model.
    """
    
    # Fields to display in the user list
    list_display = (
        'username', 'email', 'first_name', 'last_name', 
        'role', 'is_active_crm_user', 'is_staff', 'date_joined'
    )
    
    # Fields to filter by
    list_filter = (
        'role', 'is_active_crm_user', 'is_staff', 
        'is_superuser', 'is_active', 'date_joined'
    )
    
    # Fields to search
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    # Ordering
    ordering = ('username',)
    
    # Fieldsets for the user form
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        (_('CRM Settings'), {
            'fields': ('role', 'is_active_crm_user')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    # Fields for adding a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for UserProfile model.
    """
    
    list_display = ('user', 'department', 'email_notifications', 'created_at')
    list_filter = ('department', 'email_notifications', 'created_at')
    search_fields = ('user__username', 'user__email', 'department')
    
    fieldsets = (
        (_('User'), {'fields': ('user',)}),
        (_('Profile Information'), {
            'fields': ('avatar', 'bio', 'department')
        }),
        (_('Preferences'), {
            'fields': ('email_notifications', 'dashboard_layout')
        }),
    )