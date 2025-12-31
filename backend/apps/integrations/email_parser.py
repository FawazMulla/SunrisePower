"""
Email parsing system with comprehensive error handling and confidence scoring.
Processes EmailJS submissions and creates appropriate CRM records.
"""

import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from django.utils import timezone
from django.db import transaction

from .error_handler import (
    handle_email_processing_error, 
    error_handler, 
    ErrorCategory, 
    ErrorSeverity,
    safe_database_operation
)
from .models import EmailLog

logger = logging.getLogger(__name__)


class EmailParser:
    """
    Parses emails from EmailJS with confidence scoring and error handling.
    """
    
    def __init__(self):
        self.confidence_thresholds = {
            'auto_process': 0.8,      # Auto-create records
            'manual_review': 0.5,     # Flag for manual review
            'store_only': 0.0         # Store raw email only
        }
        
        # Keywords for different email types
        self.service_keywords = [
            'maintenance', 'repair', 'service', 'problem', 'issue', 'fault',
            'not working', 'broken', 'help', 'support', 'complaint'
        ]
        
        self.lead_keywords = [
            'quote', 'quotation', 'price', 'cost', 'install', 'installation',
            'solar panel', 'solar system', 'interested', 'inquiry', 'enquiry'
        ]
        
        # Required fields for different record types
        self.required_fields = {
            'lead': ['email', 'name'],
            'service_request': ['email', 'description']
        }
    
    @handle_email_processing_error
    def process_emailjs_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process EmailJS webhook data and create appropriate CRM records.
        
        Args:
            webhook_data: Data received from EmailJS webhook
            
        Returns:
            Dict containing processing results
        """
        logger.info(f"Processing EmailJS webhook: {webhook_data}")
        
        try:
            # Extract email information from webhook
            email_data = self._extract_email_data(webhook_data)
            
            # Create email log entry
            email_log = self._create_email_log(email_data)
            
            # Parse email content
            parsed_data = self._parse_email_content(email_data)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(parsed_data, email_data)
            
            # Update email log with parsed data
            email_log.parsed_data = parsed_data
            email_log.confidence_score = confidence_score
            email_log.email_type = parsed_data.get('email_type', 'unknown')
            email_log.save()
            
            # Determine action based on confidence score
            if confidence_score >= self.confidence_thresholds['auto_process']:
                result = self._auto_process_email(email_log, parsed_data)
            elif confidence_score >= self.confidence_thresholds['manual_review']:
                result = self._flag_for_manual_review(email_log, parsed_data)
            else:
                result = self._store_for_manual_processing(email_log, parsed_data)
            
            logger.info(f"Email processing completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing EmailJS webhook: {e}")
            raise
    
    def _extract_email_data(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract email data from webhook payload."""
        try:
            # EmailJS webhook structure may vary, adapt as needed
            email_data = {
                'email_id': webhook_data.get('email_id', f"emailjs_{int(datetime.now().timestamp())}"),
                'sender_email': webhook_data.get('from_email', webhook_data.get('email', '')),
                'sender_name': webhook_data.get('from_name', webhook_data.get('name', '')),
                'subject': webhook_data.get('subject', 'Contact Form Submission'),
                'message': webhook_data.get('message', ''),
                'phone': webhook_data.get('phone', ''),
                'company': webhook_data.get('company', ''),
                'service_type': webhook_data.get('service_type', ''),
                'raw_data': webhook_data,
                'received_at': timezone.now()
            }
            
            return email_data
            
        except Exception as e:
            error_handler.handle_error(
                error=e,
                category=ErrorCategory.EMAIL_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                context={'webhook_data': webhook_data}
            )
            raise
    
    def _create_email_log(self, email_data: Dict[str, Any]) -> EmailLog:
        """Create email log entry."""
        try:
            email_log = EmailLog.objects.create(
                email_id=email_data['email_id'],
                sender_email=email_data['sender_email'],
                sender_name=email_data['sender_name'],
                subject=email_data['subject'],
                raw_content=str(email_data['raw_data']),
                received_at=email_data['received_at'],
                processing_status='processing'
            )
            
            logger.info(f"Created email log entry: {email_log.id}")
            return email_log
            
        except Exception as e:
            error_handler.handle_error(
                error=e,
                category=ErrorCategory.DATABASE,
                severity=ErrorSeverity.HIGH,
                context={'email_data': email_data}
            )
            raise
    
    def _parse_email_content(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse email content and extract structured data."""
        try:
            message = email_data.get('message', '').lower()
            subject = email_data.get('subject', '').lower()
            combined_text = f"{subject} {message}"
            
            parsed_data = {
                'sender_email': email_data.get('sender_email', ''),
                'sender_name': email_data.get('sender_name', ''),
                'phone': email_data.get('phone', ''),
                'company': email_data.get('company', ''),
                'service_type': email_data.get('service_type', ''),
                'message': email_data.get('message', ''),
                'extracted_info': {}
            }
            
            # Determine email type based on keywords
            if any(keyword in combined_text for keyword in self.service_keywords):
                parsed_data['email_type'] = 'service_request'
                parsed_data['extracted_info']['request_type'] = self._extract_service_type(combined_text)
            elif any(keyword in combined_text for keyword in self.lead_keywords):
                parsed_data['email_type'] = 'lead_inquiry'
                parsed_data['extracted_info']['interest_type'] = self._extract_interest_type(combined_text)
            else:
                parsed_data['email_type'] = 'general_inquiry'
            
            # Extract additional information
            parsed_data['extracted_info'].update({
                'urgency': self._extract_urgency(combined_text),
                'property_type': self._extract_property_type(combined_text),
                'location': self._extract_location(message),
                'budget_mentioned': self._extract_budget_info(message)
            })
            
            return parsed_data
            
        except Exception as e:
            error_handler.handle_error(
                error=e,
                category=ErrorCategory.EMAIL_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                context={'email_data': email_data}
            )
            # Return basic parsed data even if extraction fails
            return {
                'sender_email': email_data.get('sender_email', ''),
                'sender_name': email_data.get('sender_name', ''),
                'email_type': 'unknown',
                'extracted_info': {}
            }
    
    def _calculate_confidence_score(self, parsed_data: Dict[str, Any], email_data: Dict[str, Any]) -> float:
        """Calculate confidence score for email parsing."""
        try:
            score = 0.0
            
            # Base score for having email
            if parsed_data.get('sender_email'):
                score += 0.3
            
            # Score for having name
            if parsed_data.get('sender_name'):
                score += 0.2
            
            # Score for having phone
            if parsed_data.get('phone'):
                score += 0.2
            
            # Score for clear email type detection
            email_type = parsed_data.get('email_type', 'unknown')
            if email_type != 'unknown':
                score += 0.2
            
            # Score for structured content
            if parsed_data.get('extracted_info'):
                info = parsed_data['extracted_info']
                if info.get('property_type'):
                    score += 0.05
                if info.get('location'):
                    score += 0.05
                if info.get('urgency'):
                    score += 0.05
                if info.get('budget_mentioned'):
                    score += 0.05
            
            # Penalty for missing critical information
            if email_type == 'service_request' and not parsed_data.get('phone'):
                score -= 0.1
            
            # Ensure score is between 0 and 1
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.warning(f"Error calculating confidence score: {e}")
            return 0.0
    
    def _auto_process_email(self, email_log: EmailLog, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically process email with high confidence score."""
        try:
            email_type = parsed_data.get('email_type')
            
            if email_type == 'lead_inquiry':
                result = self._create_lead_from_email(email_log, parsed_data)
            elif email_type == 'service_request':
                result = self._create_service_request_from_email(email_log, parsed_data)
            else:
                result = self._flag_for_manual_review(email_log, parsed_data)
            
            email_log.mark_as_processed(notes="Auto-processed with high confidence")
            
            return {
                'processed': True,
                'action': 'auto_processed',
                'confidence_score': float(email_log.confidence_score),
                'result': result
            }
            
        except Exception as e:
            email_log.mark_as_failed(str(e))
            raise
    
    def _flag_for_manual_review(self, email_log: EmailLog, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flag email for manual review."""
        try:
            email_log.mark_for_manual_review("Medium confidence - requires manual review")
            
            return {
                'processed': True,
                'action': 'manual_review',
                'confidence_score': float(email_log.confidence_score),
                'reason': 'Medium confidence score requires manual review'
            }
            
        except Exception as e:
            logger.error(f"Error flagging email for manual review: {e}")
            raise
    
    def _store_for_manual_processing(self, email_log: EmailLog, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store email for manual processing."""
        try:
            email_log.mark_for_manual_review("Low confidence - manual processing required")
            
            return {
                'processed': True,
                'action': 'manual_processing',
                'confidence_score': float(email_log.confidence_score),
                'reason': 'Low confidence score requires manual processing'
            }
            
        except Exception as e:
            logger.error(f"Error storing email for manual processing: {e}")
            raise
    
    def _create_lead_from_email(self, email_log: EmailLog, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create lead record from email data."""
        try:
            from apps.leads.models import Lead, LeadSource
            
            # Get or create email lead source
            lead_source, _ = LeadSource.objects.get_or_create(
                name='Email',
                defaults={'description': 'Leads from email inquiries'}
            )
            
            # Prepare lead data
            lead_data = {
                'source': lead_source,
                'first_name': self._extract_first_name(parsed_data.get('sender_name', '')),
                'last_name': self._extract_last_name(parsed_data.get('sender_name', '')),
                'email': parsed_data.get('sender_email', ''),
                'phone': parsed_data.get('phone', ''),
                'company_name': parsed_data.get('company', ''),
                'interest_level': 'medium',  # Default for email inquiries
                'property_type': parsed_data.get('extracted_info', {}).get('property_type', 'residential'),
                'notes': parsed_data.get('message', ''),
                'original_data': parsed_data
            }
            
            # Create lead using safe database operation
            def create_lead():
                return Lead.objects.create(**lead_data)
            
            result = safe_database_operation(create_lead)
            
            if result['success']:
                lead = result['result']
                email_log.created_lead_id = lead.id
                email_log.save()
                
                logger.info(f"Created lead {lead.id} from email {email_log.id}")
                
                return {
                    'action_taken': 'lead_created',
                    'record_id': lead.id,
                    'record_type': 'lead'
                }
            else:
                raise Exception(f"Failed to create lead: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error creating lead from email: {e}")
            raise
    
    def _create_service_request_from_email(self, email_log: EmailLog, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create service request from email data."""
        try:
            from apps.services.models import ServiceRequest
            from apps.customers.models import Customer
            
            # Try to find existing customer by email
            customer = None
            sender_email = parsed_data.get('sender_email')
            if sender_email:
                try:
                    customer = Customer.objects.get(email=sender_email)
                except Customer.DoesNotExist:
                    pass
            
            # Prepare service request data
            sr_data = {
                'customer': customer,
                'request_type': parsed_data.get('extracted_info', {}).get('request_type', 'general'),
                'priority': self._determine_priority(parsed_data),
                'subject': f"Email Service Request - {parsed_data.get('sender_name', 'Customer')}",
                'description': parsed_data.get('message', ''),
                'source_email': str(parsed_data),
                'contact_email': sender_email,
                'contact_name': parsed_data.get('sender_name', ''),
                'contact_phone': parsed_data.get('phone', '')
            }
            
            # Create service request using safe database operation
            def create_service_request():
                return ServiceRequest.objects.create(**sr_data)
            
            result = safe_database_operation(create_service_request)
            
            if result['success']:
                service_request = result['result']
                email_log.created_service_request_id = service_request.id
                email_log.save()
                
                logger.info(f"Created service request {service_request.id} from email {email_log.id}")
                
                return {
                    'action_taken': 'service_request_created',
                    'record_id': service_request.id,
                    'record_type': 'service_request'
                }
            else:
                raise Exception(f"Failed to create service request: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error creating service request from email: {e}")
            raise
    
    # Helper methods for data extraction
    
    def _extract_service_type(self, text: str) -> str:
        """Extract service type from text."""
        if 'maintenance' in text or 'amc' in text:
            return 'maintenance'
        elif 'repair' in text or 'fix' in text or 'broken' in text:
            return 'repair'
        elif 'installation' in text or 'install' in text:
            return 'installation'
        else:
            return 'general'
    
    def _extract_interest_type(self, text: str) -> str:
        """Extract interest type from text."""
        if 'residential' in text or 'home' in text or 'house' in text:
            return 'residential'
        elif 'commercial' in text or 'business' in text or 'office' in text:
            return 'commercial'
        elif 'industrial' in text or 'factory' in text:
            return 'industrial'
        else:
            return 'general'
    
    def _extract_urgency(self, text: str) -> str:
        """Extract urgency level from text."""
        urgent_keywords = ['urgent', 'emergency', 'asap', 'immediately', 'critical']
        if any(keyword in text for keyword in urgent_keywords):
            return 'high'
        elif 'soon' in text or 'quickly' in text:
            return 'medium'
        else:
            return 'low'
    
    def _extract_property_type(self, text: str) -> str:
        """Extract property type from text."""
        if 'residential' in text or 'home' in text or 'house' in text:
            return 'residential'
        elif 'commercial' in text or 'business' in text:
            return 'commercial'
        elif 'industrial' in text or 'factory' in text:
            return 'industrial'
        else:
            return 'residential'  # Default
    
    def _extract_location(self, text: str) -> str:
        """Extract location information from text."""
        # Simple location extraction - can be enhanced with NLP
        location_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*(?:city|town|area|location)\b',
            r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            r'\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return ''
    
    def _extract_budget_info(self, text: str) -> bool:
        """Check if budget information is mentioned."""
        budget_keywords = ['budget', 'cost', 'price', 'rupees', 'rs', 'lakh', 'crore', '₹']
        return any(keyword in text.lower() for keyword in budget_keywords)
    
    def _extract_first_name(self, full_name: str) -> str:
        """Extract first name from full name."""
        if not full_name:
            return ''
        parts = full_name.strip().split()
        return parts[0] if parts else ''
    
    def _extract_last_name(self, full_name: str) -> str:
        """Extract last name from full name."""
        if not full_name:
            return ''
        parts = full_name.strip().split()
        return ' '.join(parts[1:]) if len(parts) > 1 else ''
    
    def _determine_priority(self, parsed_data: Dict[str, Any]) -> str:
        """Determine priority based on parsed data."""
        urgency = parsed_data.get('extracted_info', {}).get('urgency', 'low')
        
        if urgency == 'high':
            return 'high'
        elif urgency == 'medium':
            return 'medium'
        else:
            return 'low'


# Global email parser instance
email_parser = EmailParser()


def process_emailjs_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process EmailJS webhook data.
    This is the main entry point for email processing.
    """
    return email_parser.process_emailjs_webhook(webhook_data)