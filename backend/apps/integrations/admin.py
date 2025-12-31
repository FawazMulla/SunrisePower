"""
Admin configuration for integrations app.
"""
from django.contrib import admin
from .tasks import BackgroundTask


@admin.register(BackgroundTask)
class BackgroundTaskAdmin(admin.ModelAdmin):
    """
    Admin configuration for BackgroundTask model.
    """
    
    list_display = (
        'task_name', 'task_id', 'status', 'priority',
        'created_at', 'started_at', 'completed_at', 'retry_count'
    )
    
    list_filter = (
        'status', 'task_name', 'priority', 'created_at'
    )
    
    search_fields = ('task_name', 'task_id')
    
    readonly_fields = (
        'task_id', 'created_at', 'started_at', 'completed_at'
    )
    
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Task Information', {
            'fields': ('task_name', 'task_id', 'status', 'priority')
        }),
        ('Task Data', {
            'fields': ('args', 'kwargs', 'result'),
            'classes': ('collapse',)
        }),
        ('Execution Details', {
            'fields': (
                'created_at', 'started_at', 'completed_at',
                'retry_count', 'max_retries', 'retry_delay'
            )
        }),
    )
    
    def has_add_permission(self, request):
        """Disable adding tasks through admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow viewing but limit editing."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting completed tasks."""
        if obj and obj.status in ['success', 'failed']:
            return True
        return False