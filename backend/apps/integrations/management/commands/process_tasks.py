"""
Management command to process background tasks.
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.integrations.tasks import TaskManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process background tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (continuous processing)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=10,
            help='Processing interval in seconds (daemon mode)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum tasks to process per batch',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old completed tasks',
        )
        parser.add_argument(
            '--cleanup-days',
            type=int,
            default=7,
            help='Days to keep completed tasks',
        )
    
    def handle(self, *args, **options):
        if options['cleanup']:
            self.cleanup_tasks(options['cleanup_days'])
            return
        
        if options['daemon']:
            self.run_daemon(options['interval'], options['limit'])
        else:
            self.process_once(options['limit'])
    
    def process_once(self, limit):
        """Process tasks once."""
        self.stdout.write(f"Processing up to {limit} tasks...")
        
        try:
            TaskManager.process_pending_tasks(limit=limit)
            self.stdout.write(
                self.style.SUCCESS('Task processing completed')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Task processing failed: {str(e)}')
            )
            logger.error(f"Task processing error: {str(e)}")
    
    def run_daemon(self, interval, limit):
        """Run as daemon with continuous processing."""
        self.stdout.write(
            f"Starting task processor daemon (interval: {interval}s, limit: {limit})"
        )
        
        try:
            while True:
                try:
                    TaskManager.process_pending_tasks(limit=limit)
                    time.sleep(interval)
                except KeyboardInterrupt:
                    self.stdout.write("\nShutting down task processor...")
                    break
                except Exception as e:
                    logger.error(f"Task processing error: {str(e)}")
                    self.stdout.write(
                        self.style.ERROR(f'Error: {str(e)}')
                    )
                    time.sleep(interval)
        
        except KeyboardInterrupt:
            self.stdout.write("\nTask processor stopped")
    
    def cleanup_tasks(self, days):
        """Clean up old tasks."""
        self.stdout.write(f"Cleaning up tasks older than {days} days...")
        
        try:
            deleted_count = TaskManager.cleanup_old_tasks(days=days)
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned up {deleted_count} old tasks')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Cleanup failed: {str(e)}')
            )
            logger.error(f"Task cleanup error: {str(e)}")