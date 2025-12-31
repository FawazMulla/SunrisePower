"""
Tests for lead prioritization system.
"""

from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase as HypothesisTestCase

from .models import Lead, LeadSource, LeadScore, LeadInteraction
from .prioritization import LeadPrioritizationService
from ..integrations.models import CalculatorData, ChatbotInteraction, EmailLog


class LeadPrioritizationTest(TestCase):
    """Test lead prioritization functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.service = LeadPrioritizationService()
        
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
            source=self.source,
            budget_range='5_to_10_lakh',
            property_type='residential'
        )
    
    def test_basic_lead_scoring(self):
        """Test basic lead scoring without additional data."""
        score, factors, reasoning = self.service.calculate_lead_score(self.lead)
        
        # Should have some score from budget and property type
        self.assertGreater(score, 0)
        self.assertIn('budget_range', factors)
        self.assertIn('property_type', factors)
        self.assertIsInstance(reasoning, str)
        self.assertGreater(len(reasoning), 0)
    
    def test_calculator_data_scoring(self):
        """Test scoring with calculator data."""
        # Create calculator data for the lead
        CalculatorData.objects.create(
            user_email=self.lead.email,
            property_type='residential',
            estimated_capacity=Decimal('8.5'),
            estimated_cost=Decimal('400000'),
            calculation_date=timezone.now()
        )
        
        score, factors, reasoning = self.service.calculate_lead_score(self.lead)
        
        # Should have calculator score
        self.assertGreater(factors.get('calculator_data', 0), 0)
        self.assertIn('calculator', reasoning.lower())
    
    def test_chatbot_engagement_scoring(self):
        """Test scoring with chatbot engagement."""
        # Create chatbot interaction for the lead
        ChatbotInteraction.objects.create(
            session_id='test-session',
            user_email=self.lead.email,
            user_intent='quotation',
            interaction_date=timezone.now()
        )
        
        score, factors, reasoning = self.service.calculate_lead_score(self.lead)
        
        # Should have chatbot score
        self.assertGreater(factors.get('chatbot_engagement', 0), 0)
        self.assertIn('chatbot', reasoning.lower())
    
    def test_priority_level_assignment(self):
        """Test priority level assignment based on score."""
        # Test different score ranges
        test_cases = [
            (90, 'critical'),
            (70, 'high'),
            (50, 'medium'),
            (20, 'low'),
        ]
        
        for score, expected_priority in test_cases:
            priority = self.service._get_priority_level(score)
            self.assertEqual(priority, expected_priority)
    
    def test_update_lead_priority(self):
        """Test updating lead priority."""
        original_score = self.lead.score
        original_priority = self.lead.priority_level
        
        # Update priority
        lead_score = self.service.update_lead_priority(self.lead)
        
        # Refresh from database
        self.lead.refresh_from_db()
        
        # Should have updated score and priority
        self.assertIsInstance(lead_score, LeadScore)
        self.assertEqual(lead_score.lead, self.lead)
        self.assertEqual(lead_score.score, self.lead.score)
        self.assertEqual(lead_score.priority_level, self.lead.priority_level)
        
        # Should have reasoning
        self.assertIsInstance(lead_score.reasoning, str)
        self.assertGreater(len(lead_score.reasoning), 0)
    
    def test_bulk_update_priorities(self):
        """Test bulk priority updates."""
        # Create additional leads
        leads = []
        for i in range(3):
            lead = Lead.objects.create(
                first_name=f'Test{i}',
                last_name='User',
                email=f'test{i}@example.com',
                phone=f'+9198765432{i}0',
                source=self.source
            )
            leads.append(lead)
        
        # Update priorities for specific leads
        lead_ids = [lead.id for lead in leads]
        updated_count = self.service.bulk_update_priorities(lead_ids)
        
        self.assertEqual(updated_count, 3)
        
        # Check that scores were created
        for lead in leads:
            lead.refresh_from_db()
            self.assertGreaterEqual(lead.score, 0)
            self.assertIn(lead.priority_level, ['low', 'medium', 'high', 'critical'])
    
    def test_priority_explanation(self):
        """Test getting priority explanation."""
        # Update priority first
        self.service.update_lead_priority(self.lead)
        
        # Get explanation
        explanation = self.service.get_priority_explanation(self.lead)
        
        self.assertIn('score', explanation)
        self.assertIn('priority_level', explanation)
        self.assertIn('factors', explanation)
        self.assertIn('reasoning', explanation)
        self.assertIn('calculated_at', explanation)
        self.assertTrue(explanation['is_current'])


class LeadPrioritizationPropertyTest(HypothesisTestCase):
    """Property-based tests for lead prioritization system."""
    
    def setUp(self):
        """Set up test data."""
        self.service = LeadPrioritizationService()
        
        # Create test lead source
        self.source = LeadSource.objects.create(
            name='Website',
            description='Website inquiries'
        )
    
    @given(
        first_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        last_name=st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        email=st.emails(),
        phone=st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=('Nd',))).map(lambda x: '+91' + x[:10]),
        budget_range=st.sampled_from(['under_1_lakh', '1_to_3_lakh', '3_to_5_lakh', '5_to_10_lakh', 'above_10_lakh', 'not_specified']),
        property_type=st.sampled_from(['residential', 'commercial', 'industrial', 'agricultural']),
        estimated_capacity=st.one_of(st.none(), st.decimals(min_value=1, max_value=100, places=2)),
        has_calculator_data=st.booleans(),
        has_chatbot_data=st.booleans(),
        has_email_data=st.booleans(),
        interaction_count=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_rule_based_lead_prioritization_property(self, first_name, last_name, email, phone, budget_range, 
                                                   property_type, estimated_capacity, has_calculator_data, 
                                                   has_chatbot_data, has_email_data, interaction_count):
        """
        **Feature: solar-crm-platform, Property 8: Rule-Based Lead Prioritization**
        
        Property: For any lead record, the prioritization system should analyze available data sources 
        (calculator, chatbot, engagement) using rule-based logic and assign priority levels with reasoning.
        
        **Validates: Requirements 11.1, 11.2, 11.3, 11.4**
        """
        try:
            # Create lead with generated data
            lead = Lead.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                source=self.source,
                budget_range=budget_range,
                property_type=property_type,
                estimated_capacity=estimated_capacity
            )
            
            # Add calculator data if specified
            if has_calculator_data:
                CalculatorData.objects.create(
                    user_email=lead.email,
                    property_type=property_type,
                    estimated_capacity=estimated_capacity or Decimal('5.0'),
                    estimated_cost=Decimal('300000'),
                    calculation_date=timezone.now()
                )
            
            # Add chatbot data if specified
            if has_chatbot_data:
                ChatbotInteraction.objects.create(
                    session_id=f'test-session-{lead.id}',
                    user_email=lead.email,
                    user_intent='quotation',
                    interaction_date=timezone.now()
                )
            
            # Add email data if specified
            if has_email_data:
                EmailLog.objects.create(
                    email_id=f'test-email-{lead.id}',
                    sender_email=lead.email,
                    subject='Solar Installation Inquiry',
                    raw_content='I am interested in solar installation',
                    email_type='quotation_request',
                    received_at=timezone.now()
                )
            
            # Add interactions if specified
            for i in range(interaction_count):
                LeadInteraction.objects.create(
                    lead=lead,
                    interaction_type='call',
                    description=f'Test interaction {i}',
                    interaction_date=timezone.now() - timezone.timedelta(days=i)
                )
            
            # Test the prioritization system
            score, factors, reasoning = self.service.calculate_lead_score(lead)
            
            # Property 1: Score should be within valid range (0-100)
            self.assertGreaterEqual(score, 0, "Lead score should be >= 0")
            self.assertLessEqual(score, 100, "Lead score should be <= 100")
            
            # Property 2: Priority level should be assigned based on score
            priority_level = self.service._get_priority_level(score)
            expected_priorities = ['low', 'medium', 'high', 'critical']
            self.assertIn(priority_level, expected_priorities, "Priority level should be valid")
            
            # Property 3: Score should correlate with priority level
            if score >= 80:
                self.assertEqual(priority_level, 'critical')
            elif score >= 60:
                self.assertEqual(priority_level, 'high')
            elif score >= 40:
                self.assertEqual(priority_level, 'medium')
            else:
                self.assertEqual(priority_level, 'low')
            
            # Property 4: Factors should be analyzed (Requirements 11.1)
            self.assertIsInstance(factors, dict, "Scoring factors should be a dictionary")
            expected_factor_keys = ['calculator_data', 'chatbot_engagement', 'email_interactions', 
                                  'budget_range', 'property_type', 'interaction_frequency']
            for key in expected_factor_keys:
                self.assertIn(key, factors, f"Factor '{key}' should be analyzed")
                self.assertGreaterEqual(factors[key], 0, f"Factor '{key}' should be non-negative")
            
            # Property 5: Calculator data should contribute to score when present (Requirements 11.1)
            if has_calculator_data:
                self.assertGreater(factors['calculator_data'], 0, 
                                 "Calculator data should contribute to score when present")
            
            # Property 6: Chatbot engagement should contribute to score when present (Requirements 11.1)
            if has_chatbot_data:
                self.assertGreater(factors['chatbot_engagement'], 0, 
                                 "Chatbot engagement should contribute to score when present")
            
            # Property 7: Email interactions should contribute to score when present (Requirements 11.1)
            if has_email_data:
                self.assertGreater(factors['email_interactions'], 0, 
                                 "Email interactions should contribute to score when present")
            
            # Property 8: Interaction frequency should contribute to score when interactions exist (Requirements 11.1)
            if interaction_count > 0:
                self.assertGreater(factors['interaction_frequency'], 0, 
                                 "Interaction frequency should contribute to score when interactions exist")
            
            # Property 9: Budget range should always contribute to score (Requirements 11.2)
            if budget_range != 'not_specified':
                self.assertGreater(factors['budget_range'], 0, 
                                 "Budget range should contribute to score when specified")
            
            # Property 10: Property type should always contribute to score (Requirements 11.2)
            self.assertGreater(factors['property_type'], 0, 
                             "Property type should always contribute to score")
            
            # Property 11: Reasoning should be provided (Requirements 11.4)
            self.assertIsInstance(reasoning, str, "Reasoning should be a string")
            self.assertGreater(len(reasoning), 0, "Reasoning should not be empty")
            self.assertIn(str(score), reasoning, "Reasoning should include the calculated score")
            self.assertIn(priority_level, reasoning, "Reasoning should include the priority level")
            
            # Property 12: Update lead priority should work correctly (Requirements 11.3)
            lead_score_record = self.service.update_lead_priority(lead)
            
            # Refresh lead from database
            lead.refresh_from_db()
            
            # Verify lead was updated
            self.assertEqual(lead.score, score, "Lead score should be updated")
            self.assertEqual(lead.priority_level, priority_level, "Lead priority level should be updated")
            
            # Verify score record was created
            self.assertIsInstance(lead_score_record, LeadScore, "LeadScore record should be created")
            self.assertEqual(lead_score_record.lead, lead, "LeadScore should be linked to correct lead")
            self.assertEqual(lead_score_record.score, score, "LeadScore should have correct score")
            self.assertEqual(lead_score_record.priority_level, priority_level, "LeadScore should have correct priority")
            self.assertEqual(lead_score_record.scoring_factors, factors, "LeadScore should have correct factors")
            self.assertEqual(lead_score_record.reasoning, reasoning, "LeadScore should have correct reasoning")
            
            # Property 13: Data source flags should be set correctly
            self.assertEqual(lead_score_record.calculator_data_used, has_calculator_data and factors['calculator_data'] > 0)
            self.assertEqual(lead_score_record.chatbot_data_used, has_chatbot_data and factors['chatbot_engagement'] > 0)
            self.assertEqual(lead_score_record.interaction_data_used, interaction_count > 0 and factors['interaction_frequency'] > 0)
            
            # Property 14: Priority explanation should be available (Requirements 11.4)
            explanation = self.service.get_priority_explanation(lead)
            self.assertIsInstance(explanation, dict, "Priority explanation should be a dictionary")
            self.assertEqual(explanation['score'], score, "Explanation should have correct score")
            self.assertEqual(explanation['priority_level'], priority_level, "Explanation should have correct priority")
            self.assertEqual(explanation['factors'], factors, "Explanation should have correct factors")
            self.assertEqual(explanation['reasoning'], reasoning, "Explanation should have correct reasoning")
            
        except Exception as e:
            # Clean up any created objects on failure
            if 'lead' in locals():
                lead.delete()
            raise e