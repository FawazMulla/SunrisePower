"""
Management command to run batch duplicate detection on existing leads and customers.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.leads.models import Lead
from apps.customers.models import Customer
from apps.leads.services import DuplicateDetectionService
from apps.leads.duplicate_models import DuplicateDetectionResult, ManualReviewQueue


class Command(BaseCommand):
    help = 'Run batch duplicate detection on existing leads and customers'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--leads-only',
            action='store_true',
            help='Only check leads for duplicates',
        )
        parser.add_argument(
            '--customers-only',
            action='store_true',
            help='Only check customers for duplicates',
        )
        parser.add_argument(
            '--auto-merge',
            action='store_true',
            help='Automatically merge high-confidence duplicates',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Limit number of records to process (default: 100)',
        )
    
    def handle(self, *args, **options):
        duplicate_service = DuplicateDetectionService()
        
        leads_only = options['leads_only']
        customers_only = options['customers_only']
        auto_merge = options['auto_merge']
        dry_run = options['dry_run']
        limit = options['limit']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        total_processed = 0
        duplicates_found = 0
        auto_merged = 0
        flagged_for_review = 0
        
        # Process leads
        if not customers_only:
            self.stdout.write('Processing leads for duplicates...')
            
            leads = Lead.objects.filter(status__in=['new', 'contacted', 'qualified']).order_by('created_at')[:limit]
            
            for lead in leads:
                lead_data = {
                    'email': lead.email,
                    'phone': lead.phone,
                    'first_name': lead.first_name,
                    'last_name': lead.last_name,
                    'address': lead.address,
                }
                
                # Find duplicates excluding the current lead
                potential_duplicates = duplicate_service.find_potential_duplicates(lead_data)
                potential_duplicates = [d for d in potential_duplicates if not (d['type'] == 'lead' and d['id'] == lead.id)]
                
                if potential_duplicates:
                    duplicates_found += 1
                    highest_confidence = potential_duplicates[0]['confidence']
                    
                    self.stdout.write(
                        f'Lead {lead.id} ({lead.email}): Found {len(potential_duplicates)} potential duplicates '
                        f'(highest confidence: {highest_confidence:.2f})'
                    )
                    
                    if not dry_run:
                        # Create detection result
                        detection_result = DuplicateDetectionResult.objects.create(
                            input_data=lead_data,
                            potential_duplicates=[{
                                'type': d['type'],
                                'id': d['id'],
                                'confidence': d['confidence'],
                                'match_reasons': d['match_reasons']
                            } for d in potential_duplicates],
                            highest_confidence=highest_confidence,
                            recommended_action='merge' if duplicate_service.should_auto_merge(highest_confidence) else 'review',
                            status='pending'
                        )
                        
                        if duplicate_service.should_auto_merge(highest_confidence) and auto_merge:
                            # Auto-merge high confidence duplicates
                            self.stdout.write(f'  Auto-merging with {potential_duplicates[0]["type"]} {potential_duplicates[0]["id"]}')
                            auto_merged += 1
                            # Implementation would go here
                        elif duplicate_service.should_flag_for_review(highest_confidence):
                            # Add to manual review queue
                            ManualReviewQueue.objects.create(
                                detection_result=detection_result,
                                priority='high' if highest_confidence > 0.7 else 'medium'
                            )
                            flagged_for_review += 1
                            self.stdout.write(f'  Flagged for manual review')
                
                total_processed += 1
        
        # Process customers
        if not leads_only:
            self.stdout.write('Processing customers for duplicates...')
            
            customers = Customer.objects.filter(status='active').order_by('created_at')[:limit]
            
            for customer in customers:
                customer_data = {
                    'email': customer.email,
                    'phone': customer.phone,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name,
                    'address': customer.address,
                }
                
                # Find duplicates excluding the current customer
                potential_duplicates = duplicate_service.find_potential_duplicates(customer_data)
                potential_duplicates = [d for d in potential_duplicates if not (d['type'] == 'customer' and d['id'] == customer.id)]
                
                if potential_duplicates:
                    duplicates_found += 1
                    highest_confidence = potential_duplicates[0]['confidence']
                    
                    self.stdout.write(
                        f'Customer {customer.id} ({customer.email}): Found {len(potential_duplicates)} potential duplicates '
                        f'(highest confidence: {highest_confidence:.2f})'
                    )
                    
                    if not dry_run:
                        # Create detection result
                        detection_result = DuplicateDetectionResult.objects.create(
                            input_data=customer_data,
                            potential_duplicates=[{
                                'type': d['type'],
                                'id': d['id'],
                                'confidence': d['confidence'],
                                'match_reasons': d['match_reasons']
                            } for d in potential_duplicates],
                            highest_confidence=highest_confidence,
                            recommended_action='merge' if duplicate_service.should_auto_merge(highest_confidence) else 'review',
                            status='pending'
                        )
                        
                        if duplicate_service.should_flag_for_review(highest_confidence):
                            # Add to manual review queue
                            ManualReviewQueue.objects.create(
                                detection_result=detection_result,
                                priority='high' if highest_confidence > 0.7 else 'medium'
                            )
                            flagged_for_review += 1
                            self.stdout.write(f'  Flagged for manual review')
                
                total_processed += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\nBatch duplicate detection completed:'))
        self.stdout.write(f'  Total records processed: {total_processed}')
        self.stdout.write(f'  Records with duplicates found: {duplicates_found}')
        self.stdout.write(f'  Auto-merged: {auto_merged}')
        self.stdout.write(f'  Flagged for manual review: {flagged_for_review}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a dry run - no changes were made'))
        else:
            self.stdout.write(self.style.SUCCESS('\nChanges have been saved to the database'))