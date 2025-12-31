"""
Management command to update lead priorities using the prioritization service.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
import logging

from ...models import Lead
from ...prioritization import LeadPrioritizationService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update lead priorities using the rule-based prioritization system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--lead-ids',
            nargs='+',
            type=int,
            help='Specific lead IDs to update (default: all active leads)',
        )
        parser.add_argument(
            '--status',
            nargs='+',
            default=['new', 'contacted', 'qualified'],
            help='Lead statuses to include (default: new, contacted, qualified)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of leads to process in each batch (default: 100)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
    
    def handle(self, *args, **options):
        try:
            start_time = timezone.now()
            service = LeadPrioritizationService()
            
            # Get leads to update
            if options['lead_ids']:
                leads = Lead.objects.filter(id__in=options['lead_ids'])
                self.stdout.write(f"Processing {len(options['lead_ids'])} specific leads...")
            else:
                leads = Lead.objects.filter(status__in=options['status'])
                self.stdout.write(f"Processing all leads with status: {', '.join(options['status'])}...")
            
            total_leads = leads.count()
            if total_leads == 0:
                self.stdout.write(self.style.WARNING('No leads found to process.'))
                return
            
            self.stdout.write(f"Found {total_leads} leads to process.")
            
            if options['dry_run']:
                self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
                
                # Show sample calculations
                sample_leads = leads[:5]
                for lead in sample_leads:
                    score, factors, reasoning = service.calculate_lead_score(lead)
                    priority = service._get_priority_level(score)
                    
                    self.stdout.write(f"\nLead: {lead.full_name} ({lead.email})")
                    self.stdout.write(f"  Current: Score={lead.score}, Priority={lead.priority_level}")
                    self.stdout.write(f"  New: Score={score}, Priority={priority}")
                    self.stdout.write(f"  Reasoning: {reasoning}")
                
                return
            
            # Process leads in batches
            batch_size = options['batch_size']
            updated_count = 0
            error_count = 0
            
            for i in range(0, total_leads, batch_size):
                batch_leads = leads[i:i + batch_size]
                
                with transaction.atomic():
                    for lead in batch_leads:
                        try:
                            old_score = lead.score
                            old_priority = lead.priority_level
                            
                            # Update priority
                            lead_score = service.update_lead_priority(lead)
                            
                            # Log significant changes
                            if abs(lead.score - old_score) >= 10 or lead.priority_level != old_priority:
                                self.stdout.write(
                                    f"Updated {lead.full_name}: "
                                    f"{old_score}→{lead.score} score, "
                                    f"{old_priority}→{lead.priority_level} priority"
                                )
                            
                            updated_count += 1
                            
                        except Exception as e:
                            error_count += 1
                            logger.error(f"Error updating lead {lead.id}: {e}")
                            self.stderr.write(f"Error updating lead {lead.id}: {e}")
                
                # Progress update
                progress = min(i + batch_size, total_leads)
                self.stdout.write(f"Processed {progress}/{total_leads} leads...")
            
            # Summary
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nCompleted lead priority update:\n"
                    f"  - Total leads: {total_leads}\n"
                    f"  - Successfully updated: {updated_count}\n"
                    f"  - Errors: {error_count}\n"
                    f"  - Duration: {duration:.2f} seconds"
                )
            )
            
            if error_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"There were {error_count} errors. Check logs for details."
                    )
                )
            
        except Exception as e:
            logger.error(f"Error in update_lead_priorities command: {e}")
            raise CommandError(f"Command failed: {e}")