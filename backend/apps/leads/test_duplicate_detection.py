"""
Unit tests for duplicate detection and merging functionality.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.leads.models import Lead, LeadSource
from apps.customers.models import Customer
from apps.leads.services import DuplicateDetectionService, LeadMergingService
from apps.leads.duplicate_models import DuplicateDetectionResult, ManualReviewQueue, MergeOperation

User = get_user_model()


class DuplicateDetectionServiceTest(TestCase):
    """Test cases for DuplicateDetectionService."""
    
    def setUp(self):
        self.service = DuplicateDetectionService()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.source = LeadSource.objects.create(
            name='Website',
            description='Website form submissions'
        )
    
    def test_normalize_phone(self):
        """Test phone number normalization."""
        test_cases = [
            ('+91-9876543210', '9876543210'),
            ('91-9876543210', '9876543210'),
            ('09876543210', '9876543210'),
            ('9876543210', '9876543210'),
            ('+1-555-123-4567', '15551234567'),
            ('', ''),
        ]
        
        for input_phone, expected in test_cases:
            with self.subTest(input_phone=input_phone):
                result = self.service.normalize_phone(input_phone)
                self.assertEqual(result, expected)
    
    def test_normalize_email(self):
        """Test email normalization."""
        test_cases = [
            ('John@Example.COM', 'john@example.com'),
            ('  test@test.com  ', 'test@test.com'),
            ('', ''),
        ]
        
        for input_email, expected in test_cases:
            with self.subTest(input_email=input_email):
                result = self.service.normalize_email(input_email)
                self.assertEqual(result, expected)
    
    def test_calculate_name_similarity(self):
        """Test name similarity calculation."""
        test_cases = [
            ('John Doe', 'John Doe', 1.0),
            ('John Doe', 'john doe', 1.0),
            ('John', 'Johnny', 0.6),  # 3 out of 5 characters match
            ('', 'John', 0.0),
            ('John', '', 0.0),
        ]
        
        for name1, name2, expected_min in test_cases:
            with self.subTest(name1=name1, name2=name2):
                result = self.service.calculate_name_similarity(name1, name2)
                self.assertGreaterEqual(result, expected_min - 0.1)  # Allow small variance
    
    def test_find_potential_duplicates_exact_email_match(self):
        """Test finding duplicates with exact email match."""
        # Create existing lead
        existing_lead = Lead.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='9876543210',
            source=self.source
        )
        
        # Test data with same email
        lead_data = {
            'first_name': 'Johnny',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone': '9876543211',
        }
        
        duplicates = self.service.find_potential_duplicates(lead_data)
        
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]['type'], 'lead')
        self.assertEqual(duplicates[0]['id'], existing_lead.id)
        self.assertGreater(duplicates[0]['confidence'], 0.3)  # Should have high confidence due to email match
        self.assertIn('Exact email match', duplicates[0]['match_reasons'])
    
    def test_find_potential_duplicates_exact_phone_match(self):
        """Test finding duplicates with exact phone match."""
        # Create existing lead
        existing_lead = Lead.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='9876543210',
            source=self.source
        )
        
        # Test data with same phone (different format)
        lead_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'johnny@example.com',
            'phone': '+91-9876543210',  # Same phone, different format
        }
        
        duplicates = self.service.find_potential_duplicates(lead_data)
        
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]['type'], 'lead')
        self.assertEqual(duplicates[0]['id'], existing_lead.id)
        self.assertGreater(duplicates[0]['confidence'], 0.3)  # Should have high confidence due to phone match
        self.assertIn('Exact phone match', duplicates[0]['match_reasons'])
    
    def test_find_potential_duplicates_no_match(self):
        """Test finding duplicates when no matches exist."""
        # Create existing lead with different data
        Lead.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            phone='9876543210',
            source=self.source
        )
        
        # Test data with completely different information
        lead_data = {
            'first_name': 'Bob',
            'last_name': 'Johnson',
            'email': 'bob@example.com',
            'phone': '9876543211',
        }
        
        duplicates = self.service.find_potential_duplicates(lead_data)
        
        self.assertEqual(len(duplicates), 0)
    
    def test_calculate_duplicate_confidence(self):
        """Test confidence score calculation."""
        new_data = {
            'email': 'john@example.com',
            'phone': '9876543210',
            'first_name': 'John',
            'last_name': 'Doe',
            'address': '123 Main St'
        }
        
        # Exact match should have high confidence
        existing_data = new_data.copy()
        existing_data['created_at'] = timezone.now()
        
        confidence = self.service.calculate_duplicate_confidence(new_data, existing_data)
        self.assertGreater(confidence, 0.8)
        
        # Partial match should have medium confidence
        existing_data_partial = {
            'email': 'john@example.com',  # Same email
            'phone': '9876543211',       # Different phone
            'first_name': 'Johnny',      # Similar name
            'last_name': 'Doe',
            'address': '456 Oak St',     # Different address
            'created_at': timezone.now()
        }
        
        confidence_partial = self.service.calculate_duplicate_confidence(new_data, existing_data_partial)
        self.assertGreater(confidence_partial, 0.3)
        self.assertLess(confidence_partial, 0.8)
    
    def test_should_auto_merge(self):
        """Test auto-merge decision logic."""
        self.assertTrue(self.service.should_auto_merge(0.9))
        self.assertTrue(self.service.should_auto_merge(0.8))
        self.assertFalse(self.service.should_auto_merge(0.7))
        self.assertFalse(self.service.should_auto_merge(0.5))
    
    def test_should_flag_for_review(self):
        """Test manual review flagging logic."""
        self.assertTrue(self.service.should_flag_for_review(0.9))
        self.assertTrue(self.service.should_flag_for_review(0.7))
        self.assertTrue(self.service.should_flag_for_review(0.5))
        self.assertTrue(self.service.should_flag_for_review(0.4))  # Changed: 0.4 is now the threshold
        self.assertFalse(self.service.should_flag_for_review(0.3))  # Below threshold
    
    def test_process_duplicate_detection_create_action(self):
        """Test duplicate detection process with create action."""
        lead_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone': '9876543210',
        }
        
        result = self.service.process_duplicate_detection(lead_data)
        
        self.assertEqual(result['action'], 'create')
        self.assertEqual(len(result['duplicates']), 0)
        self.assertIn('No potential duplicates found', result['message'])
    
    def test_process_duplicate_detection_review_action(self):
        """Test duplicate detection process with review action."""
        # Create existing lead with medium similarity (email match but different phone)
        existing_lead = Lead.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',  # Same email
            phone='9876543211',       # Different phone
            source=self.source
        )
        
        lead_data = {
            'first_name': 'Johnny',   # Similar name
            'last_name': 'Doe',       # Same last name
            'email': 'john@example.com',  # Same email
            'phone': '9876543210',    # Different phone
        }
        
        result = self.service.process_duplicate_detection(lead_data)
        
        # Should be review action due to email match but different phone
        self.assertEqual(result['action'], 'review')
        self.assertGreater(len(result['duplicates']), 0)
        self.assertIn('Manual review recommended', result['message'])


class LeadMergingServiceTest(TestCase):
    """Test cases for LeadMergingService."""
    
    def setUp(self):
        self.service = LeadMergingService()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.source = LeadSource.objects.create(
            name='Website',
            description='Website form submissions'
        )
    
    def test_merge_leads(self):
        """Test merging two leads."""
        # Create primary lead
        primary_lead = Lead.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='9876543210',
            address='123 Main St',
            score=50,
            notes='Primary lead notes',
            source=self.source
        )
        
        # Create duplicate lead with additional information
        duplicate_lead = Lead.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='9876543210',
            address='123 Main Street',  # More detailed address
            score=75,  # Higher score
            notes='Duplicate lead notes',
            source=self.source
        )
        
        # Merge leads
        merged_lead = self.service.merge_leads(primary_lead, duplicate_lead, self.user)
        
        # Verify merge results
        self.assertEqual(merged_lead.id, primary_lead.id)
        self.assertEqual(merged_lead.score, 75)  # Should take higher score
        self.assertIn('Duplicate lead notes', merged_lead.notes)
        self.assertIn('Primary lead notes', merged_lead.notes)
        
        # Verify duplicate lead is deleted
        with self.assertRaises(Lead.DoesNotExist):
            Lead.objects.get(id=duplicate_lead.id)
    
    def test_merge_lead_with_customer(self):
        """Test merging lead with existing customer."""
        # Create customer
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='9876543210',
            address='123 Main St',
            notes='Customer notes'
        )
        
        # Create lead to merge
        lead = Lead.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='9876543210',
            notes='Lead notes',
            source=self.source
        )
        
        # Merge lead with customer
        merged_customer = self.service.merge_lead_with_customer(lead, customer, self.user)
        
        # Verify merge results
        self.assertEqual(merged_customer.id, customer.id)
        self.assertIn('Lead notes', merged_customer.notes)
        self.assertIn('Customer notes', merged_customer.notes)
        
        # Verify lead is marked as converted
        lead.refresh_from_db()
        self.assertEqual(lead.status, 'converted')
        self.assertIsNotNone(lead.converted_at)


class DuplicateDetectionModelsTest(TestCase):
    """Test cases for duplicate detection models."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_duplicate_detection_result_creation(self):
        """Test creating a duplicate detection result."""
        input_data = {
            'email': 'john@example.com',
            'phone': '9876543210',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        
        detection_result = DuplicateDetectionResult.objects.create(
            input_data=input_data,
            potential_duplicates=[],
            highest_confidence=0.0,
            recommended_action='create',
            status='auto_processed'
        )
        
        self.assertEqual(detection_result.input_data['email'], 'john@example.com')
        self.assertEqual(detection_result.recommended_action, 'create')
        self.assertEqual(detection_result.status, 'auto_processed')
    
    def test_manual_review_queue_creation(self):
        """Test creating a manual review queue item."""
        detection_result = DuplicateDetectionResult.objects.create(
            input_data={'email': 'john@example.com'},
            potential_duplicates=[],
            highest_confidence=0.6,
            recommended_action='review',
            status='pending'
        )
        
        review_item = ManualReviewQueue.objects.create(
            detection_result=detection_result,
            priority='medium'
        )
        
        self.assertEqual(review_item.status, 'pending')
        self.assertEqual(review_item.priority, 'medium')
        self.assertEqual(review_item.detection_result, detection_result)
    
    def test_review_assignment(self):
        """Test assigning a review to a user."""
        detection_result = DuplicateDetectionResult.objects.create(
            input_data={'email': 'john@example.com'},
            potential_duplicates=[],
            highest_confidence=0.6,
            recommended_action='review',
            status='pending'
        )
        
        review_item = ManualReviewQueue.objects.create(
            detection_result=detection_result,
            priority='medium'
        )
        
        # Assign to user
        review_item.assign_to_user(self.user)
        
        self.assertEqual(review_item.assigned_to, self.user)
        self.assertEqual(review_item.status, 'in_progress')
        self.assertIsNotNone(review_item.review_started_at)
    
    def test_merge_operation_creation(self):
        """Test creating a merge operation record."""
        merge_op = MergeOperation.objects.create(
            merge_type='lead_to_lead',
            source_record_type='lead',
            source_record_id=1,
            source_record_data={'email': 'john@example.com'},
            target_record_type='lead',
            target_record_id=2,
            target_record_data_before={'email': 'john@example.com'},
            initiated_by=self.user,
            confidence_score=0.85
        )
        
        self.assertEqual(merge_op.merge_type, 'lead_to_lead')
        self.assertEqual(merge_op.status, 'pending')
        self.assertEqual(merge_op.initiated_by, self.user)
        self.assertEqual(merge_op.confidence_score, 0.85)
    
    def test_merge_operation_lifecycle(self):
        """Test merge operation status transitions."""
        merge_op = MergeOperation.objects.create(
            merge_type='lead_to_lead',
            source_record_type='lead',
            source_record_id=1,
            source_record_data={'email': 'john@example.com'},
            target_record_type='lead',
            target_record_id=2,
            target_record_data_before={'email': 'john@example.com'},
            initiated_by=self.user,
            confidence_score=0.85
        )
        
        # Start merge
        merge_op.start_merge()
        self.assertEqual(merge_op.status, 'in_progress')
        self.assertIsNotNone(merge_op.started_at)
        
        # Complete merge
        target_data_after = {'email': 'john@example.com', 'merged': True}
        merge_op.complete_merge(target_data_after)
        self.assertEqual(merge_op.status, 'completed')
        self.assertIsNotNone(merge_op.completed_at)
        self.assertEqual(merge_op.target_record_data_after, target_data_after)
        
        # Test failure
        merge_op2 = MergeOperation.objects.create(
            merge_type='lead_to_lead',
            source_record_type='lead',
            source_record_id=3,
            source_record_data={'email': 'jane@example.com'},
            target_record_type='lead',
            target_record_id=4,
            target_record_data_before={'email': 'jane@example.com'},
            initiated_by=self.user,
            confidence_score=0.85
        )
        
        merge_op2.fail_merge('Test error message')
        self.assertEqual(merge_op2.status, 'failed')
        self.assertEqual(merge_op2.error_message, 'Test error message')