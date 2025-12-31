from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Lead, LeadSource, LeadInteraction
from .duplicate_models import DuplicateDetectionResult, ManualReviewQueue, MergeOperation


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'phone', 'status', 'score', 'source', 'assigned_to', 'created_at']
    list_filter = ['status', 'interest_level', 'property_type', 'source', 'assigned_to', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'address']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'converted_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Lead Details', {
            'fields': ('source', 'status', 'score', 'interest_level', 'assigned_to')
        }),
        ('Solar Information', {
            'fields': ('property_type', 'estimated_capacity', 'budget_range')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'pincode')
        }),
        ('Tracking', {
            'fields': ('created_at', 'updated_at', 'converted_at', 'last_contacted_at')
        }),
        ('Metadata', {
            'fields': ('notes', 'original_data'),
            'classes': ('collapse',)
        })
    )


@admin.register(LeadInteraction)
class LeadInteractionAdmin(admin.ModelAdmin):
    list_display = ['lead', 'interaction_type', 'subject', 'user', 'interaction_date']
    list_filter = ['interaction_type', 'interaction_date', 'user']
    search_fields = ['lead__first_name', 'lead__last_name', 'lead__email', 'subject', 'description']
    ordering = ['-interaction_date']
    readonly_fields = ['created_at']


@admin.register(DuplicateDetectionResult)
class DuplicateDetectionResultAdmin(admin.ModelAdmin):
    list_display = ['get_email', 'recommended_action', 'highest_confidence', 'status', 'processed_by', 'created_at']
    list_filter = ['recommended_action', 'status', 'created_at', 'processed_by']
    search_fields = ['input_data']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'processed_at', 'input_data', 'potential_duplicates']
    
    fieldsets = (
        ('Detection Input', {
            'fields': ('input_data',)
        }),
        ('Detection Results', {
            'fields': ('potential_duplicates', 'highest_confidence', 'recommended_action')
        }),
        ('Processing Status', {
            'fields': ('status', 'final_action', 'processed_by', 'processed_at')
        }),
        ('Result Tracking', {
            'fields': ('created_lead_id', 'merged_into_id', 'merged_into_type')
        }),
        ('Notes', {
            'fields': ('notes',)
        })
    )
    
    def get_email(self, obj):
        """Extract email from input data for display."""
        return obj.input_data.get('email', 'N/A')
    get_email.short_description = 'Email'
    
    def has_add_permission(self, request):
        """Disable manual creation of detection results."""
        return False


@admin.register(ManualReviewQueue)
class ManualReviewQueueAdmin(admin.ModelAdmin):
    list_display = ['get_email', 'priority', 'status', 'assigned_to', 'get_confidence', 'created_at']
    list_filter = ['priority', 'status', 'assigned_to', 'created_at']
    search_fields = ['detection_result__input_data']
    ordering = ['-priority', '-created_at']
    readonly_fields = ['created_at', 'updated_at', 'review_started_at', 'review_completed_at']
    
    fieldsets = (
        ('Review Details', {
            'fields': ('detection_result', 'priority', 'status', 'assigned_to')
        }),
        ('Review Tracking', {
            'fields': ('review_started_at', 'review_completed_at', 'created_at', 'updated_at')
        }),
        ('Notes', {
            'fields': ('reviewer_notes',)
        })
    )
    
    def get_email(self, obj):
        """Extract email from detection result for display."""
        return obj.detection_result.input_data.get('email', 'N/A')
    get_email.short_description = 'Email'
    
    def get_confidence(self, obj):
        """Get confidence score from detection result."""
        return f"{obj.detection_result.highest_confidence:.2f}"
    get_confidence.short_description = 'Confidence'
    
    actions = ['assign_to_me', 'mark_high_priority']
    
    def assign_to_me(self, request, queryset):
        """Assign selected reviews to current user."""
        updated = 0
        for review in queryset.filter(status='pending'):
            review.assign_to_user(request.user)
            updated += 1
        self.message_user(request, f'{updated} reviews assigned to you.')
    assign_to_me.short_description = 'Assign selected reviews to me'
    
    def mark_high_priority(self, request, queryset):
        """Mark selected reviews as high priority."""
        updated = queryset.update(priority='high')
        self.message_user(request, f'{updated} reviews marked as high priority.')
    mark_high_priority.short_description = 'Mark as high priority'


@admin.register(MergeOperation)
class MergeOperationAdmin(admin.ModelAdmin):
    list_display = ['get_merge_summary', 'merge_type', 'status', 'confidence_score', 'initiated_by', 'created_at']
    list_filter = ['merge_type', 'status', 'initiated_by', 'created_at']
    search_fields = ['source_record_data', 'target_record_data_before', 'notes']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'started_at', 'completed_at', 'source_record_data', 'target_record_data_before', 'target_record_data_after']
    
    fieldsets = (
        ('Merge Details', {
            'fields': ('merge_type', 'status', 'confidence_score', 'initiated_by')
        }),
        ('Source Record', {
            'fields': ('source_record_type', 'source_record_id', 'source_record_data')
        }),
        ('Target Record', {
            'fields': ('target_record_type', 'target_record_id', 'target_record_data_before', 'target_record_data_after')
        }),
        ('Timing', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
        ('Error Handling', {
            'fields': ('error_message',)
        }),
        ('Notes', {
            'fields': ('notes',)
        })
    )
    
    def get_merge_summary(self, obj):
        """Create a summary of the merge operation."""
        return f"{obj.source_record_type}:{obj.source_record_id} → {obj.target_record_type}:{obj.target_record_id}"
    get_merge_summary.short_description = 'Merge Summary'
    
    def has_add_permission(self, request):
        """Disable manual creation of merge operations."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Only allow viewing, not editing."""
        return False
