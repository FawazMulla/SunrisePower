"""
Notification service for email processing errors and alerts.
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from typing import List, Dict

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications about email processing events.
    """
    
    @staticmethod
    def notify_processing_error(email_log, error_message: str):
        """
        Notify administrators about email processing errors.
        """
        try:
            # Get admin users
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            admin_emails = [user.email for user in admin_users if user.email]
            
            if not admin_emails:
                logger.warning("No admin emails found for error notification")
                return
            
            subject = f"Email Processing Error - {email_log.email_id}"
            message = f"""
Email processing failed for:

Email ID: {email_log.email_id}
Sender: {email_log.sender_name} <{email_log.sender_email}>
Subject: {email_log.subject}
Received: {email_log.received_at}

Error: {error_message}

Please review this email manually in the admin interface.

Raw Content:
{email_log.raw_content[:500]}...
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sunrisepower.com'),
                recipient_list=admin_emails,
                fail_silently=True
            )
            
            logger.info(f"Error notification sent for email {email_log.email_id}")
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {str(e)}")
    
    @staticmethod
    def notify_manual_review_required(email_log, reason: str):
        """
        Notify administrators about emails requiring manual review.
        """
        try:
            # Get admin users
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            admin_emails = [user.email for user in admin_users if user.email]
            
            if not admin_emails:
                logger.warning("No admin emails found for manual review notification")
                return
            
            subject = f"Email Manual Review Required - {email_log.email_id}"
            message = f"""
An email requires manual review:

Email ID: {email_log.email_id}
Sender: {email_log.sender_name} <{email_log.sender_email}>
Subject: {email_log.subject}
Received: {email_log.received_at}
Confidence Score: {email_log.confidence_score}

Reason: {reason}

Please review this email in the admin interface and take appropriate action.

Parsed Data:
{email_log.parsed_data}
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sunrisepower.com'),
                recipient_list=admin_emails,
                fail_silently=True
            )
            
            logger.info(f"Manual review notification sent for email {email_log.email_id}")
            
        except Exception as e:
            logger.error(f"Failed to send manual review notification: {str(e)}")
    
    @staticmethod
    def notify_high_volume_processing():
        """
        Notify administrators about high volume email processing.
        """
        try:
            from .models import EmailLog
            from django.utils import timezone
            from datetime import timedelta
            
            # Check emails received in last hour
            one_hour_ago = timezone.now() - timedelta(hours=1)
            recent_emails = EmailLog.objects.filter(received_at__gte=one_hour_ago).count()
            
            if recent_emails > 50:  # Threshold for high volume
                admin_users = User.objects.filter(is_staff=True, is_active=True)
                admin_emails = [user.email for user in admin_users if user.email]
                
                if admin_emails:
                    subject = "High Volume Email Processing Alert"
                    message = f"""
High volume of emails detected:

Emails received in last hour: {recent_emails}
Time: {timezone.now()}

Please monitor the system for any issues.
                    """
                    
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sunrisepower.com'),
                        recipient_list=admin_emails,
                        fail_silently=True
                    )
                    
                    logger.info(f"High volume notification sent: {recent_emails} emails in last hour")
            
        except Exception as e:
            logger.error(f"Failed to send high volume notification: {str(e)}")
    
    @staticmethod
    def get_notification_summary() -> Dict:
        """
        Get summary of notification-worthy events.
        """
        try:
            from .models import EmailLog
            from django.utils import timezone
            from datetime import timedelta
            
            # Get counts for last 24 hours
            yesterday = timezone.now() - timedelta(days=1)
            
            summary = {
                'total_emails': EmailLog.objects.filter(received_at__gte=yesterday).count(),
                'processed': EmailLog.objects.filter(
                    received_at__gte=yesterday,
                    processing_status='processed'
                ).count(),
                'failed': EmailLog.objects.filter(
                    received_at__gte=yesterday,
                    processing_status='failed'
                ).count(),
                'manual_review': EmailLog.objects.filter(
                    received_at__gte=yesterday,
                    processing_status='manual_review'
                ).count(),
                'pending': EmailLog.objects.filter(
                    received_at__gte=yesterday,
                    processing_status='pending'
                ).count(),
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get notification summary: {str(e)}")
            return {}