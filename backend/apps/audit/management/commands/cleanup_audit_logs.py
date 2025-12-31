"""
Management command to clean up old audit logs based on retention policies
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.audit.models import AuditLogRetention


class Command(BaseCommand):
    help = 'Clean up old audit logs based on retention policies'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Clean up logs for specific model only',
        )
        parser.add_argument(
            '--days',
            type=int,
            help='Override retention days for this run',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_model = options['model']
        override_days = options['days']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No logs will be deleted')
            )
        
        total_deleted = 0
        
        # Get retention policies
        policies = AuditLogRetention.objects.filter(is_active=True)
        
        if specific_model:
            policies = policies.filter(model_name=specific_model)
        
        if override_days is not None:
            # Create temporary policy for override
            if specific_model:
                policies = [type('Policy', (), {
                    'model_name': specific_model,
                    'retention_days': override_days
                })]
            else:
                self.stdout.write(
                    self.style.ERROR('--model is required when using --days')
                )
                return
        
        if not policies:
            self.stdout.write(
                self.style.WARNING('No retention policies found')
            )
            return
        
        for policy in policies:
            if policy.retention_days == 0:
                self.stdout.write(
                    f"Skipping {policy.model_name} - never delete policy"
                )
                continue
            
            cutoff_date = timezone.now() - timezone.timedelta(days=policy.retention_days)
            
            from apps.audit.models import AuditLog
            old_logs = AuditLog.objects.filter(
                model_name=policy.model_name,
                timestamp__lt=cutoff_date
            )
            
            count = old_logs.count()
            
            if count == 0:
                self.stdout.write(
                    f"No old logs found for {policy.model_name}"
                )
                continue
            
            self.stdout.write(
                f"Found {count} old logs for {policy.model_name} "
                f"(older than {policy.retention_days} days)"
            )
            
            if not dry_run:
                old_logs.delete()
                total_deleted += count
                self.stdout.write(
                    self.style.SUCCESS(f"Deleted {count} logs for {policy.model_name}")
                )
            else:
                self.stdout.write(
                    f"Would delete {count} logs for {policy.model_name}"
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would delete {total_deleted} total logs")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully deleted {total_deleted} total logs")
            )