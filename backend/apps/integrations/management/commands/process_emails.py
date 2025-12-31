"""
Management command to process pending emails.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.integrations.models import EmailLog
from apps.integrations.email_parser import EmailParser
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process pending emails from EmailJS integration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of emails to process'
        )
        parser.add_argument(
            '--status',
            type=str,
            default='pending',
            choices=['pending', 'failed', 'manual_review'],
            help='Status of emails to process'
        )
        parser.add_argument(
            '--email-id',
            type=str,
            help='Process specific email by ID'
        )
    
    def handle(self, *args, **options):
        limit = options['limit']
        status_filter = options['status']
        email_id = options.get('email_id')
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting email processing...')
        )
        
        # Get emails to process
        if email_id:
            emails = EmailLog.objects.filter(email_id=email_id)
        else:
            emails = EmailLog.objects.filter(
                processing_status=status_filter
            ).order_by('received_at')[:limit]
        
        if not emails.exists():
            self.stdout.write(
                self.style.WARNING(f'No emails found with status: {status_filter}')
            )
            return
        
        parser = EmailParser()
        processed_count = 0
        error_count = 0
        
        for email_log in emails:
            try:
                self.stdout.write(f'Processing email: {email_log.email_id}')
                
                result = parser.process_email(email_log)
                
                if 'error' in result:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing {email_log.email_id}: {result["error"]}')
                    )
                    error_count += 1
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Processed {email_log.email_id}: {result["action_taken"]}')
                    )
                    processed_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Exception processing {email_log.email_id}: {str(e)}')
                )
                error_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Email processing complete. Processed: {processed_count}, Errors: {error_count}'
            )
        )