"""
Management command to clean up old duplicate detection data and completed merge operations.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.leads.duplicate_models import DuplicateDetectionResult, ManualReviewQueue, MergeOperation


class Command(BaseCommand):
    help = 'Clean up old duplicate detection data and completed merge operations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete records older than this many days (default: 90)',
        )
        parser.add_argument(
            '--keep-failed',
            action='store_true',
            help='Keep failed merge operations for debugging',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without making changes',
        )
    
    def handle(self, *args, **options):
        days = options['days']
        keep_failed = options['keep_failed']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No deletions will be made'))
        
        self.stdout.write(f'Cleaning up records older than {cutoff_date.date()}...')
        
        # Clean up completed detection results
        completed_detections = DuplicateDetectionResult.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['approved', 'auto_processed']
        )
        
        detection_count = completed_detections.count()
        self.stdout.write(f'Found {detection_count} completed detection results to clean up')
        
        if not dry_run and detection_count > 0:
            completed_detections.delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {detection_count} completed detection results'))
        
        # Clean up completed review queue items
        completed_reviews = ManualReviewQueue.objects.filter(
            created_at__lt=cutoff_date,
            status='completed'
        )
        
        review_count = completed_reviews.count()
        self.stdout.write(f'Found {review_count} completed review queue items to clean up')
        
        if not dry_run and review_count > 0:
            completed_reviews.delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {review_count} completed review queue items'))
        
        # Clean up completed merge operations
        merge_filter = {
            'created_at__lt': cutoff_date,
            'status': 'completed'
        }
        
        if keep_failed:
            # Only delete completed merges, keep failed ones
            completed_merges = MergeOperation.objects.filter(**merge_filter)
        else:
            # Delete both completed and failed merges
            merge_filter['status__in'] = ['completed', 'failed']
            completed_merges = MergeOperation.objects.filter(
                created_at__lt=cutoff_date,
                status__in=['completed', 'failed']
            )
        
        merge_count = completed_merges.count()
        status_text = 'completed' if keep_failed else 'completed and failed'
        self.stdout.write(f'Found {merge_count} {status_text} merge operations to clean up')
        
        if not dry_run and merge_count > 0:
            completed_merges.delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {merge_count} {status_text} merge operations'))
        
        # Summary
        total_cleaned = detection_count + review_count + merge_count
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nWould delete {total_cleaned} total records'))
            self.stdout.write(self.style.WARNING('This was a dry run - no deletions were made'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nCleaned up {total_cleaned} total records'))
        
        # Show remaining counts
        remaining_detections = DuplicateDetectionResult.objects.count()
        remaining_reviews = ManualReviewQueue.objects.count()
        remaining_merges = MergeOperation.objects.count()
        
        self.stdout.write(f'\nRemaining records:')
        self.stdout.write(f'  Detection results: {remaining_detections}')
        self.stdout.write(f'  Review queue items: {remaining_reviews}')
        self.stdout.write(f'  Merge operations: {remaining_merges}')