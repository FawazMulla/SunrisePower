from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class EmailLog(models.Model):
    """
    Log all emails received through EmailJS integration
    """
    
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('manual_review', 'Manual Review Required'),
    ]
    
    EMAIL_TYPE_CHOICES = [
        ('lead_inquiry', 'Lead Inquiry'),
        ('service_request', 'Service Request'),
        ('quotation_request', 'Quotation Request'),
        ('general_inquiry', 'General Inquiry'),
        ('unknown', 'Unknown'),
    ]
    
    # Email metadata
    email_id = models.CharField(
        max_length=100,
        unique=True,
        help_text='Unique email ID from EmailJS'
    )
    sender_email = models.EmailField(
        help_text='Email address of the sender'
    )
    sender_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Name of the sender'
    )
    subject = models.CharField(
        max_length=500,
        help_text='Email subject line'
    )
    
    # Email content
    raw_content = models.TextField(
        help_text='Raw email content as received'
    )
    parsed_data = models.JSONField(
        default=dict,
        help_text='Parsed data extracted from email'
    )
    
    # Processing information
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='pending',
        help_text='Current processing status'
    )
    email_type = models.CharField(
        max_length=20,
        choices=EMAIL_TYPE_CHOICES,
        default='unknown',
        help_text='Detected email type'
    )
    confidence_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0,
        help_text='Confidence score for email parsing (0.0 to 1.0)'
    )
    
    # Processing results
    created_lead_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID of created lead record'
    )
    created_service_request_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID of created service request'
    )
    processing_notes = models.TextField(
        blank=True,
        help_text='Notes from processing'
    )
    error_message = models.TextField(
        blank=True,
        help_text='Error message if processing failed'
    )
    
    # Processing user
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='User who processed this email (if manual)'
    )
    
    # Timestamps
    received_at = models.DateTimeField(
        help_text='When email was received'
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When email was processed'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_logs'
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['email_id']),
            models.Index(fields=['sender_email']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['email_type']),
            models.Index(fields=['received_at']),
        ]
    
    def __str__(self):
        return f"{self.sender_email} - {self.subject[:50]} ({self.received_at.date()})"
    
    def mark_as_processed(self, user=None, notes=""):
        """Mark email as processed."""
        self.processing_status = 'processed'
        self.processed_at = timezone.now()
        self.processed_by = user
        if notes:
            self.processing_notes = notes
        self.save(update_fields=['processing_status', 'processed_at', 'processed_by', 'processing_notes', 'updated_at'])
    
    def mark_as_failed(self, error_message, user=None):
        """Mark email processing as failed."""
        self.processing_status = 'failed'
        self.processed_at = timezone.now()
        self.processed_by = user
        self.error_message = error_message
        self.save(update_fields=['processing_status', 'processed_at', 'processed_by', 'error_message', 'updated_at'])
    
    def mark_for_manual_review(self, reason="", user=None):
        """Mark email for manual review."""
        self.processing_status = 'manual_review'
        self.processed_at = timezone.now()
        self.processed_by = user
        self.processing_notes = f"Manual review required: {reason}"
        self.save(update_fields=['processing_status', 'processed_at', 'processed_by', 'processing_notes', 'updated_at'])


class ChatbotInteraction(models.Model):
    """
    Log chatbot interactions from the frontend
    """
    
    INTERACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]
    
    # Interaction metadata
    session_id = models.CharField(
        max_length=100,
        help_text='Chatbot session ID'
    )
    user_email = models.EmailField(
        blank=True,
        help_text='User email if provided'
    )
    user_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='User name if provided'
    )
    user_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='User phone if provided'
    )
    
    # Interaction content
    conversation_data = models.JSONField(
        default=dict,
        help_text='Full conversation data from chatbot'
    )
    user_intent = models.CharField(
        max_length=100,
        blank=True,
        help_text='Detected user intent'
    )
    extracted_data = models.JSONField(
        default=dict,
        help_text='Extracted structured data from conversation'
    )
    
    # Processing information
    processing_status = models.CharField(
        max_length=20,
        choices=INTERACTION_STATUS_CHOICES,
        default='pending',
        help_text='Processing status'
    )
    created_lead_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID of created lead record'
    )
    processing_notes = models.TextField(
        blank=True,
        help_text='Processing notes'
    )
    error_message = models.TextField(
        blank=True,
        help_text='Error message if processing failed'
    )
    
    # Timestamps
    interaction_date = models.DateTimeField(
        help_text='When interaction occurred'
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When interaction was processed'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chatbot_interactions'
        verbose_name = 'Chatbot Interaction'
        verbose_name_plural = 'Chatbot Interactions'
        ordering = ['-interaction_date']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user_email']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['interaction_date']),
        ]
    
    def __str__(self):
        return f"Chatbot - {self.user_email or self.session_id} ({self.interaction_date.date()})"


class CalculatorData(models.Model):
    """
    Store solar calculator data from frontend
    """
    
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]
    
    # User information
    user_email = models.EmailField(
        blank=True,
        help_text='User email if provided'
    )
    user_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='User name if provided'
    )
    user_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='User phone if provided'
    )
    
    # Calculator inputs
    property_type = models.CharField(
        max_length=50,
        help_text='Type of property'
    )
    monthly_bill = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Monthly electricity bill'
    )
    roof_area = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Available roof area in sq ft'
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text='Installation location'
    )
    
    # Calculator results
    estimated_capacity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Estimated system capacity in kW'
    )
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Estimated system cost'
    )
    estimated_savings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Estimated annual savings'
    )
    payback_period = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text='Payback period in years'
    )
    
    # Raw data
    raw_data = models.JSONField(
        default=dict,
        help_text='Raw calculator data'
    )
    
    # Processing information
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='pending',
        help_text='Processing status'
    )
    created_lead_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID of created lead record'
    )
    processing_notes = models.TextField(
        blank=True,
        help_text='Processing notes'
    )
    error_message = models.TextField(
        blank=True,
        help_text='Error message if processing failed'
    )
    
    # Timestamps
    calculation_date = models.DateTimeField(
        help_text='When calculation was performed'
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When data was processed'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'calculator_data'
        verbose_name = 'Calculator Data'
        verbose_name_plural = 'Calculator Data'
        ordering = ['-calculation_date']
        indexes = [
            models.Index(fields=['user_email']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['calculation_date']),
        ]
    
    def __str__(self):
        return f"Calculator - {self.user_email or 'Anonymous'} ({self.calculation_date.date()})"


# Import the BackgroundTask model from tasks.py
from .tasks import BackgroundTask
