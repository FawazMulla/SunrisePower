"""
Property-based tests for service request lifecycle management.
"""

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase as HypothesisTestCase

from .models import ServiceRequest, ServiceRequestStatusHistory
from ..customers.models import Customer
from ..leads.models import Lead, LeadSource

User = get_user_model()


class ServiceRequestLifecyclePropertyTest(HypothesisTestCase):
    """Property-based tests for service request lifecycle management."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test lead source
        self.source = LeadSource.objects.create(
            name='Website',
            description='Website inquiries'
        )
        
        # Create test lead
        self.lead = Lead.objects.create(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='+919876543210',
            source=self.source
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            lead=self.lead,
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='+919876543210',
            address='123 Test Street',
            city='Test City',
            state='Test State',
            pincode='123456'
        )
    
    @given(
        # Service request data
        request_type=st.sampled_from(['maintenance', 'repair', 'inspection', 'warranty', 'technical_support', 'installation_issue', 'performance_issue', 'other']),
        priority=st.sampled_from(['low', 'medium', 'high', 'urgent']),
        subject=st.text(min_size=5, max_size=200, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Zs'))),
        description=st.text(min_size=10, max_size=1000, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Zs'))),
        initial_status=st.sampled_from(['open', 'in_progress', 'pending_customer', 'pending_parts']),
        
        # Status transitions
        status_transitions=st.lists(
            st.sampled_from(['open', 'in_progress', 'pending_customer', 'pending_parts', 'resolved', 'closed']),
            min_size=0, max_size=5
        ),
        
        # Resolution data
        resolution_notes=st.text(min_size=0, max_size=500, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Zs'))),
        customer_satisfaction=st.one_of(st.none(), st.integers(min_value=1, max_value=5)),
        
        # Source data
        source_email=st.text(min_size=0, max_size=1000, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Zs'))),
        
        # Assignment
        should_assign=st.booleans()
    )
    @settings(max_examples=20, deadline=None)
    def test_service_request_lifecycle_management_property(self, request_type, priority, subject, 
                                                         description, initial_status, status_transitions, 
                                                         resolution_notes, customer_satisfaction, 
                                                         source_email, should_assign):
        """
        **Feature: solar-crm-platform, Property 7: Service Request Lifecycle Management**
        
        Property: For any service request creation (form submission or email), the system should create 
        a ServiceRequest with unique ticket number, initial status, and proper customer association when identifiable.
        
        **Validates: Requirements 7.1, 7.3, 7.5**
        """
        try:
            # Property 1: Service request creation should generate unique ticket number (Requirements 7.1)
            service_request = ServiceRequest.objects.create(
                customer=self.customer,
                request_type=request_type,
                priority=priority,
                subject=subject,
                description=description,
                status=initial_status,
                source_email=source_email,
                assigned_to=self.user if should_assign else None
            )
            
            # Verify unique ticket number generation
            self.assertIsNotNone(service_request.ticket_number, "Service request should have a ticket number")
            self.assertTrue(service_request.ticket_number.startswith('SR'), "Ticket number should start with 'SR'")
            self.assertEqual(len(service_request.ticket_number), 13, "Ticket number should be 13 characters long")
            
            # Verify ticket number uniqueness
            duplicate_request = ServiceRequest.objects.create(
                customer=self.customer,
                request_type=request_type,
                priority=priority,
                subject="Duplicate test",
                description="Duplicate description"
            )
            self.assertNotEqual(service_request.ticket_number, duplicate_request.ticket_number, 
                              "Each service request should have unique ticket number")
            
            # Property 2: Initial status should be set correctly (Requirements 7.1)
            self.assertEqual(service_request.status, initial_status, "Initial status should be set correctly")
            self.assertIn(service_request.status, [choice[0] for choice in ServiceRequest.STATUS_CHOICES], 
                         "Status should be valid")
            
            # Property 3: Customer association should be maintained (Requirements 7.1, 7.5)
            self.assertEqual(service_request.customer, self.customer, "Service request should be associated with correct customer")
            self.assertIn(service_request, self.customer.service_requests.all(), 
                         "Customer should have service request in their requests")
            
            # Property 4: Status transitions should be validated and tracked (Requirements 7.3)
            valid_transitions = {
                'open': ['in_progress', 'pending_customer', 'cancelled'],
                'in_progress': ['pending_customer', 'pending_parts', 'resolved', 'cancelled'],
                'pending_customer': ['in_progress', 'resolved', 'cancelled'],
                'pending_parts': ['in_progress', 'resolved', 'cancelled'],
                'resolved': ['closed', 'in_progress'],
                'closed': [],
                'cancelled': []
            }
            
            current_status = service_request.status
            for new_status in status_transitions:
                if new_status in valid_transitions.get(current_status, []):
                    # Valid transition
                    old_status = service_request.status
                    service_request.update_status(new_status, self.user, f"Status changed to {new_status}")
                    
                    # Verify status was updated
                    self.assertEqual(service_request.status, new_status, f"Status should be updated to {new_status}")
                    
                    # Verify status history was created
                    history_records = ServiceRequestStatusHistory.objects.filter(
                        service_request=service_request,
                        old_status=old_status,
                        new_status=new_status
                    )
                    self.assertGreater(history_records.count(), 0, 
                                     f"Status history should be created for transition from {old_status} to {new_status}")
                    
                    # Verify history record has correct data
                    latest_history = history_records.first()
                    self.assertEqual(latest_history.changed_by, self.user, "Status history should record who made the change")
                    self.assertIsNotNone(latest_history.changed_at, "Status history should have timestamp")
                    
                    current_status = new_status
                else:
                    # Invalid transition should raise error
                    with self.assertRaises(ValueError, msg=f"Invalid transition from {current_status} to {new_status} should raise ValueError"):
                        service_request.update_status(new_status, self.user)
            
            # Property 5: Resolution workflow should work correctly (Requirements 7.3)
            if service_request.status not in ['resolved', 'closed', 'cancelled']:
                # First transition to in_progress if we're in open status
                if service_request.status == 'open':
                    service_request.update_status('in_progress', self.user, "Starting work on request")
                
                # Then resolve from in_progress
                if service_request.status in ['in_progress', 'pending_customer', 'pending_parts']:
                    # Set resolution notes separately if provided
                    if resolution_notes:
                        service_request.resolution_notes = resolution_notes
                        service_request.save()
                    
                    service_request.update_status('resolved', self.user, "Marking as resolved")
                    
                    self.assertEqual(service_request.status, 'resolved', "Service request should be marked as resolved")
                    self.assertIsNotNone(service_request.resolved_at, "Resolved service request should have resolution timestamp")
                    
                    if resolution_notes:
                        self.assertEqual(service_request.resolution_notes, resolution_notes, 
                                       "Resolution notes should be stored correctly")
                    
                    # Test closure after resolution
                    service_request.update_status('closed', self.user, "Closing resolved ticket")
                    
                    self.assertEqual(service_request.status, 'closed', "Service request should be marked as closed")
                    self.assertIsNotNone(service_request.closed_at, "Closed service request should have closure timestamp")
                    self.assertIsNotNone(service_request.resolved_at, "Closed service request should still have resolution timestamp")
            
            # Property 6: Customer satisfaction should be tracked when provided (Requirements 7.3)
            if customer_satisfaction is not None:
                service_request.customer_satisfaction = customer_satisfaction
                service_request.save()
                
                self.assertEqual(service_request.customer_satisfaction, customer_satisfaction, 
                               "Customer satisfaction should be stored correctly")
                self.assertGreaterEqual(service_request.customer_satisfaction, 1, 
                                      "Customer satisfaction should be at least 1")
                self.assertLessEqual(service_request.customer_satisfaction, 5, 
                                   "Customer satisfaction should be at most 5")
            
            # Property 7: Assignment should work correctly (Requirements 7.3)
            if should_assign:
                self.assertEqual(service_request.assigned_to, self.user, "Service request should be assigned to correct user")
            else:
                # Test assignment after creation
                service_request.assigned_to = self.user
                service_request.save()
                self.assertEqual(service_request.assigned_to, self.user, "Service request assignment should work")
            
            # Property 8: SLA and overdue detection should work correctly (Requirements 7.3)
            priority_sla_hours = {
                'urgent': 4,
                'high': 24,
                'medium': 72,
                'low': 168
            }
            
            expected_sla_hours = priority_sla_hours.get(priority, 72)
            
            # Test overdue detection for non-resolved requests
            if service_request.status not in ['resolved', 'closed', 'cancelled']:
                # Simulate old request by modifying created_at
                old_created_at = timezone.now() - timedelta(hours=expected_sla_hours + 1)
                ServiceRequest.objects.filter(id=service_request.id).update(created_at=old_created_at)
                service_request.refresh_from_db()
                
                self.assertTrue(service_request.is_overdue, 
                              f"Service request with priority {priority} should be overdue after {expected_sla_hours} hours")
            
            # Property 9: Time tracking should be accurate (Requirements 7.3)
            age_hours = service_request.age_in_hours
            self.assertGreaterEqual(age_hours, 0, "Service request age should be non-negative")
            
            if service_request.resolved_at:
                time_to_resolution = service_request.time_to_resolution
                self.assertIsNotNone(time_to_resolution, "Resolved requests should have time to resolution")
                self.assertGreaterEqual(time_to_resolution.total_seconds(), 0, 
                                      "Time to resolution should be non-negative")
            
            # Property 10: Source data should be preserved (Requirements 7.1, 7.5)
            if source_email:
                self.assertEqual(service_request.source_email, source_email, 
                               "Source email should be preserved")
            
            # Property 11: Valid status transitions should be calculated correctly (Requirements 7.3)
            valid_next_statuses = service_request.get_next_valid_statuses()
            expected_valid_statuses = valid_transitions.get(service_request.status, [])
            
            self.assertEqual(set(valid_next_statuses), set(expected_valid_statuses), 
                           f"Valid next statuses should match expected transitions for status {service_request.status}")
            
            # Property 12: Status transition validation should work (Requirements 7.3)
            for status_choice in ServiceRequest.STATUS_CHOICES:
                status_value = status_choice[0]
                can_transition = service_request.can_transition_to_status(status_value)
                expected_can_transition = status_value in expected_valid_statuses
                
                self.assertEqual(can_transition, expected_can_transition, 
                               f"Transition validation to {status_value} should be {expected_can_transition}")
            
            # Property 13: Data integrity should be maintained (Requirements 7.1, 7.3, 7.5)
            # Verify all required fields are set
            self.assertIsNotNone(service_request.created_at, "Service request should have creation timestamp")
            self.assertIsNotNone(service_request.updated_at, "Service request should have update timestamp")
            self.assertIsNotNone(service_request.customer, "Service request should have customer")
            self.assertIsNotNone(service_request.request_type, "Service request should have request type")
            self.assertIsNotNone(service_request.priority, "Service request should have priority")
            self.assertIsNotNone(service_request.subject, "Service request should have subject")
            self.assertIsNotNone(service_request.description, "Service request should have description")
            
            # Verify field constraints
            self.assertIn(service_request.request_type, [choice[0] for choice in ServiceRequest.REQUEST_TYPE_CHOICES])
            self.assertIn(service_request.priority, [choice[0] for choice in ServiceRequest.PRIORITY_CHOICES])
            self.assertIn(service_request.status, [choice[0] for choice in ServiceRequest.STATUS_CHOICES])
            
            # Property 14: Status history should maintain complete audit trail (Requirements 7.3)
            all_history = service_request.status_history.all()
            
            # Verify history is ordered by most recent first
            if all_history.count() > 1:
                for i in range(len(all_history) - 1):
                    self.assertGreaterEqual(all_history[i].changed_at, all_history[i + 1].changed_at, 
                                          "Status history should be ordered by most recent first")
            
            # Verify each history record has required data
            for history_record in all_history:
                self.assertIsNotNone(history_record.new_status, "History record should have new status")
                self.assertIsNotNone(history_record.changed_at, "History record should have timestamp")
                self.assertEqual(history_record.service_request, service_request, 
                               "History record should be linked to correct service request")
            
            # Property 15: String representation should be meaningful (Requirements 7.1)
            str_repr = str(service_request)
            self.assertIn(service_request.ticket_number, str_repr, 
                         "String representation should include ticket number")
            self.assertIn(service_request.subject, str_repr, 
                         "String representation should include subject")
            
            # Clean up the duplicate request
            duplicate_request.delete()
            
        except Exception as e:
            # Clean up any created objects on failure
            if 'service_request' in locals():
                service_request.delete()
            if 'duplicate_request' in locals():
                duplicate_request.delete()
            raise e
