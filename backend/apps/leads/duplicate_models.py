"""
Models for duplicate detection and manual review functionality.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class DuplicateDetectionResult(models.Model):
    """
    Store results of duplicate detection for audit and review purposes.
    """
    
    ACTION_CHOICES = [
        ('create', 'Create New Record'),
        ('merge', 'Auto Merge'),
        ('review', 'Manual Review Required'),
        ('ignore', 'Ignore Duplicates'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('auto_processed', 'Auto Processed'),
    ]
    
    # Input data that was checked for duplicates
    input_data = models.JSONField(
        help_text='Original data that was checked for duplicates'
    )
    
    # Detection results
    potential_duplicates = models.JSONField(
        default=list,
        help_text='List of potential duplicate records found'
    )
    highest_confidence = models.FloatField(
        default=0.0,
        help_text='Highest confidence score among potential duplicates'
    )
    recommended_action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text='Recommended action based on confidence scores'
    )
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Current processing status'
    )
    final_action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        blank=True,
        help_text='Final action taken'
    )
    
    # Result tracking
    created_lead_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID of lead created if action was create'
    )
    merged_into_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID of record merged into if action was merge'
    )
    merged_into_type = models.CharField(
        max_length=20,
        blank=True,
        choices=[('lead', 'Lead'), ('customer', 'Customer')],
        help_text='Type of record merged into'
    )
    
    # User tracking
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='User who processed this detection result'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this was processed'
    )
    
    # Metadata
    notes = models.TextField(
        blank=True,
        help_text='Additional notes about the processing'
    )
    
    class Meta:
        db_table = 'duplicate_detection_results'
        verbose_name = 'Duplicate Detection Result'
        verbose_name_plural = 'Duplicate Detection Results'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['recommended_action']),
            models.Index(fields=['highest_confidence']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        email = self.input_data.get('email', 'Unknown')
        return f"Duplicate check for {email} - {self.get_recommended_action_display()}"
    
    def mark_as_processed(self, action: str, user=None, notes: str = ''):
        """Mark this detection result as processed."""
        self.status = 'approved' if action in ['create', 'merge'] else 'rejected'
        self.final_action = action
        self.processed_by = user
        self.processed_at = timezone.now()
        if notes:
            self.notes = notes
        self.save(update_fields=['status', 'final_action', 'processed_by', 'processed_at', 'notes'])


class ManualReviewQueue(models.Model):
    """
    Queue for manual review of potential duplicates.
    """
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('escalated', 'Escalated'),
    ]
    
    # Reference to detection result
    detection_result = models.OneToOneField(
        DuplicateDetectionResult,
        on_delete=models.CASCADE,
        related_name='review_queue_item',
        help_text='Associated duplicate detection result'
    )
    
    # Review details
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text='Priority level for review'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Current review status'
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_reviews',
        help_text='User assigned to review this item'
    )
    
    # Review tracking
    review_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When review was started'
    )
    review_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When review was completed'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Review notes
    reviewer_notes = models.TextField(
        blank=True,
        help_text='Notes from the reviewer'
    )
    
    class Meta:
        db_table = 'manual_review_queue'
        verbose_name = 'Manual Review Queue Item'
        verbose_name_plural = 'Manual Review Queue'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        email = self.detection_result.input_data.get('email', 'Unknown')
        return f"Review: {email} - {self.get_status_display()}"
    
    def assign_to_user(self, user: User):
        """Assign this review to a user."""
        self.assigned_to = user
        self.status = 'in_progress'
        self.review_started_at = timezone.now()
        self.save(update_fields=['assigned_to', 'status', 'review_started_at', 'updated_at'])
    
    def complete_review(self, action: str, notes: str = '', user=None):
        """Complete the review process."""
        self.status = 'completed'
        self.review_completed_at = timezone.now()
        if notes:
            self.reviewer_notes = notes
        self.save(update_fields=['status', 'review_completed_at', 'reviewer_notes', 'updated_at'])
        
        # Update the associated detection result
        self.detection_result.mark_as_processed(action, user, notes)


class MergeOperation(models.Model):
    """
    Track merge operations for audit purposes.
    """
    
    MERGE_TYPE_CHOICES = [
        ('lead_to_lead', 'Lead to Lead'),
        ('lead_to_customer', 'Lead to Customer'),
        ('customer_to_customer', 'Customer to Customer'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('rolled_back', 'Rolled Back'),
    ]
    
    # Merge details
    merge_type = models.CharField(
        max_length=20,
        choices=MERGE_TYPE_CHOICES,
        help_text='Type of merge operation'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Status of merge operation'
    )
    
    # Source and target records
    source_record_type = models.CharField(
        max_length=20,
        choices=[('lead', 'Lead'), ('customer', 'Customer')],
        help_text='Type of source record'
    )
    source_record_id = models.IntegerField(
        help_text='ID of source record (will be merged/deleted)'
    )
    source_record_data = models.JSONField(
        help_text='Snapshot of source record data before merge'
    )
    
    target_record_type = models.CharField(
        max_length=20,
        choices=[('lead', 'Lead'), ('customer', 'Customer')],
        help_text='Type of target record'
    )
    target_record_id = models.IntegerField(
        help_text='ID of target record (will receive merged data)'
    )
    target_record_data_before = models.JSONField(
        help_text='Snapshot of target record data before merge'
    )
    target_record_data_after = models.JSONField(
        null=True,
        blank=True,
        help_text='Snapshot of target record data after merge'
    )
    
    # Operation tracking
    initiated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='User who initiated the merge'
    )
    confidence_score = models.FloatField(
        help_text='Confidence score that led to this merge'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When merge operation started'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When merge operation completed'
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text='Error message if merge failed'
    )
    
    # Metadata
    notes = models.TextField(
        blank=True,
        help_text='Additional notes about the merge'
    )
    
    class Meta:
        db_table = 'merge_operations'
        verbose_name = 'Merge Operation'
        verbose_name_plural = 'Merge Operations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['merge_type']),
            models.Index(fields=['source_record_type', 'source_record_id']),
            models.Index(fields=['target_record_type', 'target_record_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Merge {self.source_record_type}:{self.source_record_id} → {self.target_record_type}:{self.target_record_id}"
    
    def start_merge(self):
        """Mark merge as started."""
        self.status = 'in_progress'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def complete_merge(self, target_data_after: dict):
        """Mark merge as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.target_record_data_after = target_data_after
        self.save(update_fields=['status', 'completed_at', 'target_record_data_after'])
    
    def fail_merge(self, error_message: str):
        """Mark merge as failed."""
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])