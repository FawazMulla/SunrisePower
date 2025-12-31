from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, EmailValidator
from django.utils import timezone
import uuid

User = get_user_model()


class LeadSource(models.Model):
    """
    Source of lead generation (website, chatbot, email, etc.)
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Name of the lead source'
    )
    description = models.TextField(
        blank=True,
        help_text='Description of the lead source'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this source is currently active'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lead_sources'
        verbose_name = 'Lead Source'
        verbose_name_plural = 'Lead Sources'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Lead(models.Model):
    """
    Lead model representing potential customers
    """
    
    LEAD_STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('proposal_sent', 'Proposal Sent'),
        ('negotiation', 'Negotiation'),
        ('converted', 'Converted'),
        ('lost', 'Lost'),
        ('on_hold', 'On Hold'),
    ]
    
    INTEREST_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('very_high', 'Very High'),
    ]
    
    PROPERTY_TYPE_CHOICES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('agricultural', 'Agricultural'),
    ]
    
    BUDGET_RANGE_CHOICES = [
        ('under_1_lakh', 'Under ₹1 Lakh'),
        ('1_to_3_lakh', '₹1-3 Lakh'),
        ('3_to_5_lakh', '₹3-5 Lakh'),
        ('5_to_10_lakh', '₹5-10 Lakh'),
        ('above_10_lakh', 'Above ₹10 Lakh'),
        ('not_specified', 'Not Specified'),
    ]
    
    # Basic Information
    first_name = models.CharField(
        max_length=100,
        help_text='First name of the lead'
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Last name of the lead'
    )
    email = models.EmailField(
        validators=[EmailValidator()],
        help_text='Email address of the lead'
    )
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        help_text='Phone number of the lead'
    )
    
    # Lead Details
    source = models.ForeignKey(
        LeadSource,
        on_delete=models.CASCADE,
        help_text='Source of this lead'
    )
    status = models.CharField(
        max_length=20,
        choices=LEAD_STATUS_CHOICES,
        default='new',
        help_text='Current status of the lead'
    )
    score = models.IntegerField(
        default=0,
        help_text='Lead score (0-100)'
    )
    priority_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium',
        help_text='Priority level of the lead'
    )
    interest_level = models.CharField(
        max_length=20,
        choices=INTEREST_LEVEL_CHOICES,
        default='medium',
        help_text='Interest level of the lead'
    )
    
    # Solar Specific Information
    property_type = models.CharField(
        max_length=50,
        choices=PROPERTY_TYPE_CHOICES,
        default='residential',
        help_text='Type of property for solar installation'
    )
    estimated_capacity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Estimated solar capacity in kW'
    )
    budget_range = models.CharField(
        max_length=50,
        choices=BUDGET_RANGE_CHOICES,
        default='not_specified',
        help_text='Budget range for solar installation'
    )
    
    # Address Information
    address = models.TextField(
        blank=True,
        help_text='Full address of the lead'
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        help_text='City'
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        help_text='State'
    )
    pincode = models.CharField(
        max_length=10,
        blank=True,
        help_text='PIN code'
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads',
        help_text='User assigned to this lead'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    converted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date when lead was converted to customer'
    )
    last_contacted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last time this lead was contacted'
    )
    
    # Metadata
    original_data = models.JSONField(
        default=dict,
        help_text='Store original interaction data from frontend'
    )
    notes = models.TextField(
        blank=True,
        help_text='Internal notes about this lead'
    )
    
    class Meta:
        db_table = 'leads'
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['status']),
            models.Index(fields=['score']),
            models.Index(fields=['created_at']),
            models.Index(fields=['assigned_to']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(score__gte=0) & models.Q(score__lte=100),
                name='valid_lead_score'
            ),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        """Return full name of the lead."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_converted(self):
        """Check if lead is converted to customer."""
        return self.status == 'converted' and self.converted_at is not None
    
    def mark_as_converted(self):
        """Mark lead as converted."""
        self.status = 'converted'
        self.converted_at = timezone.now()
        self.save(update_fields=['status', 'converted_at', 'updated_at'])
    
    def update_score(self, new_score):
        """Update lead score with validation."""
        if 0 <= new_score <= 100:
            self.score = new_score
            self.save(update_fields=['score', 'updated_at'])
        else:
            raise ValueError("Score must be between 0 and 100")
    
    def record_contact(self):
        """Record that this lead was contacted."""
        self.last_contacted_at = timezone.now()
        self.save(update_fields=['last_contacted_at', 'updated_at'])


class LeadPriority(models.Model):
    """
    Lead prioritization configuration and rules
    """
    
    PRIORITY_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Name of the priority rule'
    )
    description = models.TextField(
        help_text='Description of the priority rule'
    )
    priority_level = models.CharField(
        max_length=20,
        choices=PRIORITY_LEVEL_CHOICES,
        help_text='Priority level assigned by this rule'
    )
    score_weight = models.IntegerField(
        default=10,
        help_text='Weight added to lead score when this rule matches'
    )
    
    # Rule conditions (JSON format for flexibility)
    conditions = models.JSONField(
        default=dict,
        help_text='Conditions that must be met for this rule to apply'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this rule is currently active'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lead_priorities'
        verbose_name = 'Lead Priority Rule'
        verbose_name_plural = 'Lead Priority Rules'
        ordering = ['-score_weight', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_priority_level_display()})"


class LeadScore(models.Model):
    """
    Track lead scoring history and reasoning
    """
    
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='score_history',
        help_text='Lead this score belongs to'
    )
    score = models.IntegerField(
        help_text='Calculated score (0-100)'
    )
    priority_level = models.CharField(
        max_length=20,
        choices=LeadPriority.PRIORITY_LEVEL_CHOICES,
        help_text='Assigned priority level'
    )
    
    # Scoring breakdown
    scoring_factors = models.JSONField(
        default=dict,
        help_text='Breakdown of factors contributing to the score'
    )
    applied_rules = models.JSONField(
        default=list,
        help_text='List of priority rules that were applied'
    )
    reasoning = models.TextField(
        help_text='Human-readable explanation of the score'
    )
    
    # Data sources used
    calculator_data_used = models.BooleanField(
        default=False,
        help_text='Whether calculator data was used in scoring'
    )
    chatbot_data_used = models.BooleanField(
        default=False,
        help_text='Whether chatbot data was used in scoring'
    )
    interaction_data_used = models.BooleanField(
        default=False,
        help_text='Whether interaction history was used in scoring'
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'lead_scores'
        verbose_name = 'Lead Score'
        verbose_name_plural = 'Lead Scores'
        ordering = ['-calculated_at']
        indexes = [
            models.Index(fields=['lead', 'calculated_at']),
            models.Index(fields=['score']),
            models.Index(fields=['priority_level']),
        ]
    
    def __str__(self):
        return f"{self.lead.full_name} - Score: {self.score} ({self.get_priority_level_display()})"


class LeadInteraction(models.Model):
    """
    Track interactions with leads
    """
    
    INTERACTION_TYPE_CHOICES = [
        ('call', 'Phone Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('chatbot', 'Chatbot'),
        ('website', 'Website Visit'),
        ('form', 'Form Submission'),
        ('calculator', 'Solar Calculator'),
        ('other', 'Other'),
    ]
    
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='interactions',
        help_text='Lead this interaction belongs to'
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPE_CHOICES,
        help_text='Type of interaction'
    )
    subject = models.CharField(
        max_length=200,
        blank=True,
        help_text='Subject or title of the interaction'
    )
    description = models.TextField(
        help_text='Description of the interaction'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='User who recorded this interaction'
    )
    
    # Metadata
    interaction_data = models.JSONField(
        default=dict,
        help_text='Additional data related to the interaction'
    )
    
    # Timestamps
    interaction_date = models.DateTimeField(
        default=timezone.now,
        help_text='Date and time of the interaction'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'lead_interactions'
        verbose_name = 'Lead Interaction'
        verbose_name_plural = 'Lead Interactions'
        ordering = ['-interaction_date']
        indexes = [
            models.Index(fields=['lead', 'interaction_date']),
            models.Index(fields=['interaction_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.lead.full_name} - {self.get_interaction_type_display()} ({self.interaction_date.date()})"
