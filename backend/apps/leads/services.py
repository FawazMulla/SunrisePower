"""
Lead management services including duplicate detection and merging.
"""

import re
from typing import List, Dict, Tuple, Optional
from django.db.models import Q
from django.utils import timezone
from .models import Lead, LeadInteraction
from apps.customers.models import Customer


class DuplicateDetectionService:
    """
    Service for detecting and handling duplicate leads and customers.
    """
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.8
    MEDIUM_CONFIDENCE_THRESHOLD = 0.4  # Lowered from 0.5 to catch email matches
    
    def __init__(self):
        self.confidence_factors = {
            'exact_email_match': 0.4,
            'exact_phone_match': 0.4,
            'name_similarity': 0.2,
            'address_similarity': 0.1,
            'recent_interaction': -0.1,  # Negative because recent means less likely to be duplicate
        }
    
    def normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number for comparison.
        Removes all non-digit characters and handles country codes.
        """
        if not phone:
            return ""
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        # Handle Indian phone numbers
        if digits_only.startswith('91') and len(digits_only) == 12:
            # Remove country code for Indian numbers
            digits_only = digits_only[2:]
        elif digits_only.startswith('0') and len(digits_only) == 11:
            # Remove leading 0 for Indian numbers
            digits_only = digits_only[1:]
        
        return digits_only
    
    def normalize_email(self, email: str) -> str:
        """
        Normalize email for comparison.
        """
        if not email:
            return ""
        return email.lower().strip()
    
    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two names.
        Simple implementation using character overlap.
        """
        if not name1 or not name2:
            return 0.0
        
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()
        
        if name1 == name2:
            return 1.0
        
        # Calculate character overlap
        set1 = set(name1.replace(' ', ''))
        set2 = set(name2.replace(' ', ''))
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_address_similarity(self, addr1: str, addr2: str) -> float:
        """
        Calculate similarity between two addresses.
        """
        if not addr1 or not addr2:
            return 0.0
        
        addr1 = addr1.lower().strip()
        addr2 = addr2.lower().strip()
        
        if addr1 == addr2:
            return 1.0
        
        # Simple word overlap calculation
        words1 = set(addr1.split())
        words2 = set(addr2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def find_potential_duplicates(self, lead_data: Dict) -> List[Dict]:
        """
        Find potential duplicate leads and customers based on email and phone.
        
        Args:
            lead_data: Dictionary containing lead information
            
        Returns:
            List of potential duplicates with confidence scores
        """
        email = self.normalize_email(lead_data.get('email', ''))
        phone = self.normalize_phone(lead_data.get('phone', ''))
        
        if not email and not phone:
            return []
        
        potential_duplicates = []
        
        # Search in existing leads
        lead_query = Q()
        if email:
            lead_query |= Q(email__iexact=email)
        if phone:
            # Use a more efficient approach for phone matching
            leads_with_phone = Lead.objects.exclude(status='converted')
            for lead in leads_with_phone:
                if self.normalize_phone(lead.phone) == phone:
                    lead_query |= Q(id=lead.id)
        
        if lead_query:
            existing_leads = Lead.objects.filter(lead_query).exclude(
                status='converted'  # Don't match converted leads
            )
            
            for lead in existing_leads:
                confidence = self.calculate_duplicate_confidence(lead_data, {
                    'email': lead.email,
                    'phone': lead.phone,
                    'first_name': lead.first_name,
                    'last_name': lead.last_name,
                    'address': lead.address,
                    'created_at': lead.created_at,
                })
                
                if confidence > 0:
                    potential_duplicates.append({
                        'type': 'lead',
                        'id': lead.id,
                        'record': lead,
                        'confidence': confidence,
                        'match_reasons': self.get_match_reasons(lead_data, {
                            'email': lead.email,
                            'phone': lead.phone,
                            'first_name': lead.first_name,
                            'last_name': lead.last_name,
                        })
                    })
        
        # Search in existing customers
        customer_query = Q()
        if email:
            customer_query |= Q(email__iexact=email)
        if phone:
            # Use a more efficient approach for phone matching
            customers_with_phone = Customer.objects.all()
            for customer in customers_with_phone:
                if self.normalize_phone(customer.phone) == phone:
                    customer_query |= Q(id=customer.id)
        
        if customer_query:
            existing_customers = Customer.objects.filter(customer_query)
            
            for customer in existing_customers:
                confidence = self.calculate_duplicate_confidence(lead_data, {
                    'email': customer.email,
                    'phone': customer.phone,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name,
                    'address': customer.address,
                    'created_at': customer.created_at,
                })
                
                if confidence > 0:
                    potential_duplicates.append({
                        'type': 'customer',
                        'id': customer.id,
                        'record': customer,
                        'confidence': confidence,
                        'match_reasons': self.get_match_reasons(lead_data, {
                            'email': customer.email,
                            'phone': customer.phone,
                            'first_name': customer.first_name,
                            'last_name': customer.last_name,
                        })
                    })
        
        # Sort by confidence score (highest first)
        potential_duplicates.sort(key=lambda x: x['confidence'], reverse=True)
        
        return potential_duplicates
    
    def calculate_duplicate_confidence(self, new_data: Dict, existing_data: Dict) -> float:
        """
        Calculate confidence score for potential duplicate.
        
        Args:
            new_data: New lead/customer data
            existing_data: Existing record data
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.0
        
        # Email match
        new_email = self.normalize_email(new_data.get('email', ''))
        existing_email = self.normalize_email(existing_data.get('email', ''))
        if new_email and existing_email and new_email == existing_email:
            confidence += self.confidence_factors['exact_email_match']
        
        # Phone match
        new_phone = self.normalize_phone(new_data.get('phone', ''))
        existing_phone = self.normalize_phone(existing_data.get('phone', ''))
        if new_phone and existing_phone and new_phone == existing_phone:
            confidence += self.confidence_factors['exact_phone_match']
        
        # Name similarity
        new_name = f"{new_data.get('first_name', '')} {new_data.get('last_name', '')}".strip()
        existing_name = f"{existing_data.get('first_name', '')} {existing_data.get('last_name', '')}".strip()
        name_similarity = self.calculate_name_similarity(new_name, existing_name)
        confidence += name_similarity * self.confidence_factors['name_similarity']
        
        # Address similarity
        new_address = new_data.get('address', '')
        existing_address = existing_data.get('address', '')
        address_similarity = self.calculate_address_similarity(new_address, existing_address)
        confidence += address_similarity * self.confidence_factors['address_similarity']
        
        # Recent interaction penalty (if record was created recently, less likely to be duplicate)
        existing_created_at = existing_data.get('created_at')
        if existing_created_at:
            days_since_creation = (timezone.now() - existing_created_at).days
            if days_since_creation < 7:  # Created within last week
                confidence += self.confidence_factors['recent_interaction']
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    def get_match_reasons(self, new_data: Dict, existing_data: Dict) -> List[str]:
        """
        Get human-readable reasons for the match.
        """
        reasons = []
        
        # Email match
        new_email = self.normalize_email(new_data.get('email', ''))
        existing_email = self.normalize_email(existing_data.get('email', ''))
        if new_email and existing_email and new_email == existing_email:
            reasons.append("Exact email match")
        
        # Phone match
        new_phone = self.normalize_phone(new_data.get('phone', ''))
        existing_phone = self.normalize_phone(existing_data.get('phone', ''))
        if new_phone and existing_phone and new_phone == existing_phone:
            reasons.append("Exact phone match")
        
        # Name similarity
        new_name = f"{new_data.get('first_name', '')} {new_data.get('last_name', '')}".strip()
        existing_name = f"{existing_data.get('first_name', '')} {existing_data.get('last_name', '')}".strip()
        name_similarity = self.calculate_name_similarity(new_name, existing_name)
        if name_similarity > 0.7:
            reasons.append("Similar name")
        
        return reasons
    
    def should_auto_merge(self, confidence: float) -> bool:
        """
        Determine if records should be automatically merged based on confidence.
        """
        return confidence >= self.HIGH_CONFIDENCE_THRESHOLD
    
    def should_flag_for_review(self, confidence: float) -> bool:
        """
        Determine if potential duplicate should be flagged for manual review.
        """
        return confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD
    
    def process_duplicate_detection(self, lead_data: Dict) -> Dict:
        """
        Process duplicate detection for new lead data.
        
        Returns:
            Dictionary with detection results and recommended actions
        """
        potential_duplicates = self.find_potential_duplicates(lead_data)
        
        if not potential_duplicates:
            return {
                'action': 'create',
                'duplicates': [],
                'message': 'No potential duplicates found. Safe to create new lead.'
            }
        
        highest_confidence = potential_duplicates[0]['confidence']
        
        if self.should_auto_merge(highest_confidence):
            return {
                'action': 'merge',
                'duplicates': potential_duplicates,
                'recommended_merge': potential_duplicates[0],
                'message': f'High confidence duplicate found (confidence: {highest_confidence:.2f}). Recommend automatic merge.'
            }
        elif self.should_flag_for_review(highest_confidence):
            return {
                'action': 'review',
                'duplicates': potential_duplicates,
                'message': f'Potential duplicates found (highest confidence: {highest_confidence:.2f}). Manual review recommended.'
            }
        else:
            return {
                'action': 'create',
                'duplicates': potential_duplicates,
                'message': f'Low confidence duplicates found (highest confidence: {highest_confidence:.2f}). Safe to create new lead.'
            }


class LeadMergingService:
    """
    Service for merging duplicate leads and preserving history.
    """
    
    def __init__(self):
        self.duplicate_service = DuplicateDetectionService()
    
    def merge_leads(self, primary_lead: Lead, duplicate_lead: Lead, user=None) -> Lead:
        """
        Merge duplicate lead into primary lead, preserving all history.
        
        Args:
            primary_lead: The lead to keep (target of merge)
            duplicate_lead: The lead to merge and remove (source of merge)
            user: User performing the merge
            
        Returns:
            The updated primary lead
        """
        # Store original data for audit trail
        original_primary_data = {
            'first_name': primary_lead.first_name,
            'last_name': primary_lead.last_name,
            'email': primary_lead.email,
            'phone': primary_lead.phone,
            'address': primary_lead.address,
            'score': primary_lead.score,
            'notes': primary_lead.notes,
        }
        
        # Merge data - prefer non-empty values from duplicate if primary is empty
        if not primary_lead.last_name and duplicate_lead.last_name:
            primary_lead.last_name = duplicate_lead.last_name
        
        if not primary_lead.address and duplicate_lead.address:
            primary_lead.address = duplicate_lead.address
            primary_lead.city = duplicate_lead.city
            primary_lead.state = duplicate_lead.state
            primary_lead.pincode = duplicate_lead.pincode
        
        # Merge scores - take the higher score
        if duplicate_lead.score > primary_lead.score:
            primary_lead.score = duplicate_lead.score
        
        # Merge notes
        if duplicate_lead.notes:
            if primary_lead.notes:
                primary_lead.notes += f"\n\n--- Merged from duplicate lead ---\n{duplicate_lead.notes}"
            else:
                primary_lead.notes = duplicate_lead.notes
        
        # Merge original data
        if duplicate_lead.original_data:
            if not primary_lead.original_data:
                primary_lead.original_data = {}
            primary_lead.original_data['merged_data'] = primary_lead.original_data.get('merged_data', [])
            primary_lead.original_data['merged_data'].append({
                'source_lead_id': duplicate_lead.id,
                'source_data': duplicate_lead.original_data,
                'merged_at': timezone.now().isoformat(),
                'merged_by': user.id if user else None,
            })
        
        # Update timestamps
        primary_lead.updated_at = timezone.now()
        
        # Save primary lead
        primary_lead.save()
        
        # Move all interactions from duplicate to primary
        LeadInteraction.objects.filter(lead=duplicate_lead).update(lead=primary_lead)
        
        # Create merge interaction record
        LeadInteraction.objects.create(
            lead=primary_lead,
            interaction_type='other',
            subject='Lead Merge Operation',
            description=f'Merged duplicate lead (ID: {duplicate_lead.id}) into this lead. '
                       f'Original email: {duplicate_lead.email}, phone: {duplicate_lead.phone}',
            user=user,
            interaction_data={
                'merge_operation': True,
                'source_lead_id': duplicate_lead.id,
                'source_lead_data': {
                    'first_name': duplicate_lead.first_name,
                    'last_name': duplicate_lead.last_name,
                    'email': duplicate_lead.email,
                    'phone': duplicate_lead.phone,
                    'created_at': duplicate_lead.created_at.isoformat(),
                }
            }
        )
        
        # Delete the duplicate lead
        duplicate_lead.delete()
        
        return primary_lead
    
    def merge_lead_with_customer(self, lead: Lead, customer: Customer, user=None) -> Customer:
        """
        Merge lead data into existing customer record.
        
        Args:
            lead: The lead to merge
            customer: The existing customer to merge into
            user: User performing the merge
            
        Returns:
            The updated customer
        """
        # Add lead interaction history to customer
        from apps.customers.models import CustomerHistory
        
        # Create history entry for the merge
        CustomerHistory.objects.create(
            customer=customer,
            history_type='other',
            title='Lead Merge Operation',
            description=f'Merged lead (ID: {lead.id}) into customer record. '
                       f'Lead created: {lead.created_at}, Status: {lead.status}',
            user=user,
            new_values={
                'merged_lead_id': lead.id,
                'merged_lead_data': {
                    'first_name': lead.first_name,
                    'last_name': lead.last_name,
                    'email': lead.email,
                    'phone': lead.phone,
                    'status': lead.status,
                    'score': lead.score,
                    'created_at': lead.created_at.isoformat(),
                }
            }
        )
        
        # Update customer notes if lead has additional information
        if lead.notes:
            if customer.notes:
                customer.notes += f"\n\n--- Merged from lead ---\n{lead.notes}"
            else:
                customer.notes = lead.notes
        
        # Mark lead as converted and link to customer
        lead.status = 'converted'
        lead.converted_at = timezone.now()
        lead.save()
        
        # Update customer timestamp
        customer.updated_at = timezone.now()
        customer.save()
        
        return customer
    
    def merge_customers(self, primary_customer: 'Customer', duplicate_customer: 'Customer', user=None) -> 'Customer':
        """
        Merge duplicate customer into primary customer, preserving all history.
        
        Args:
            primary_customer: The customer to keep (target of merge)
            duplicate_customer: The customer to merge and remove (source of merge)
            user: User performing the merge
            
        Returns:
            The updated primary customer
        """
        from apps.customers.models import CustomerHistory
        from apps.services.models import ServiceRequest, AMCContract, InstallationProject
        
        # Store original data for audit trail
        original_primary_data = {
            'first_name': primary_customer.first_name,
            'last_name': primary_customer.last_name,
            'email': primary_customer.email,
            'phone': primary_customer.phone,
            'address': primary_customer.address,
            'company_name': primary_customer.company_name,
            'gst_number': primary_customer.gst_number,
            'notes': primary_customer.notes,
        }
        
        # Merge data - prefer non-empty values from duplicate if primary is empty
        if not primary_customer.last_name and duplicate_customer.last_name:
            primary_customer.last_name = duplicate_customer.last_name
        
        if not primary_customer.company_name and duplicate_customer.company_name:
            primary_customer.company_name = duplicate_customer.company_name
        
        if not primary_customer.gst_number and duplicate_customer.gst_number:
            primary_customer.gst_number = duplicate_customer.gst_number
        
        if not primary_customer.address and duplicate_customer.address:
            primary_customer.address = duplicate_customer.address
            primary_customer.city = duplicate_customer.city
            primary_customer.state = duplicate_customer.state
            primary_customer.pincode = duplicate_customer.pincode
        
        # Merge financial data
        primary_customer.total_value += duplicate_customer.total_value
        primary_customer.outstanding_amount += duplicate_customer.outstanding_amount
        
        # Merge notes
        if duplicate_customer.notes:
            if primary_customer.notes:
                primary_customer.notes += f"\n\n--- Merged from duplicate customer ---\n{duplicate_customer.notes}"
            else:
                primary_customer.notes = duplicate_customer.notes
        
        # Update timestamps
        primary_customer.updated_at = timezone.now()
        
        # Save primary customer
        primary_customer.save()
        
        # Move all related records from duplicate to primary
        ServiceRequest.objects.filter(customer=duplicate_customer).update(customer=primary_customer)
        AMCContract.objects.filter(customer=duplicate_customer).update(customer=primary_customer)
        InstallationProject.objects.filter(customer=duplicate_customer).update(customer=primary_customer)
        
        # Move customer history
        CustomerHistory.objects.filter(customer=duplicate_customer).update(customer=primary_customer)
        
        # Create merge history record
        CustomerHistory.objects.create(
            customer=primary_customer,
            history_type='other',
            title='Customer Merge Operation',
            description=f'Merged duplicate customer (ID: {duplicate_customer.id}) into this customer. '
                       f'Original email: {duplicate_customer.email}, phone: {duplicate_customer.phone}',
            user=user,
            new_values={
                'merge_operation': True,
                'source_customer_id': duplicate_customer.id,
                'source_customer_data': {
                    'first_name': duplicate_customer.first_name,
                    'last_name': duplicate_customer.last_name,
                    'email': duplicate_customer.email,
                    'phone': duplicate_customer.phone,
                    'company_name': duplicate_customer.company_name,
                    'total_value': str(duplicate_customer.total_value),
                    'outstanding_amount': str(duplicate_customer.outstanding_amount),
                    'created_at': duplicate_customer.created_at.isoformat(),
                }
            }
        )
        
        # Delete the duplicate customer
        duplicate_customer.delete()
        
        return primary_customer