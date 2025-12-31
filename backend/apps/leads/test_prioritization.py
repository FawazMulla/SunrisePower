"""
Tests for lead prioritization system.
"""

from django.test import TestCase
from django.utils import timezone
from decimal import Decimal

from .models import Lead, LeadSource, LeadScore
from .prioritization import LeadPrioritizationService
from ..integrations.models import CalculatorData, ChatbotInteraction


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