"""
Lead prioritization service for rule-based lead scoring and priority assignment.
"""

from django.utils import timezone
from django.db.models import Q, Count, Avg
from decimal import Decimal
import logging
from typing import Dict, List, Tuple, Optional

from .models import Lead, LeadPriority, LeadScore, LeadInteraction
from ..integrations.models import ChatbotInteraction, CalculatorData, EmailLog

logger = logging.getLogger(__name__)


class LeadPrioritizationService:
    """
    Service for calculating lead scores and assigning priorities based on rules.
    """
    
    def __init__(self):
        self.scoring_factors = {
            'calculator_usage': 25,
            'chatbot_engagement': 20,
            'email_interactions': 15,
            'budget_range': 20,
            'property_type': 10,
            'interaction_frequency': 10,
        }
    
    def calculate_lead_score(self, lead: Lead) -> Tuple[int, Dict, str]:
        """
        Calculate comprehensive lead score based on multiple data sources.
        
        Returns:
            Tuple of (score, scoring_factors, reasoning)
        """
        score = 0
        factors = {}
        reasoning_parts = []
        
        # Calculator data scoring
        calculator_score, calculator_reasoning = self._score_calculator_data(lead)
        score += calculator_score
        factors['calculator_data'] = calculator_score
        if calculator_reasoning:
            reasoning_parts.append(calculator_reasoning)
        
        # Chatbot engagement scoring
        chatbot_score, chatbot_reasoning = self._score_chatbot_engagement(lead)
        score += chatbot_score
        factors['chatbot_engagement'] = chatbot_score
        if chatbot_reasoning:
            reasoning_parts.append(chatbot_reasoning)
        
        # Email interaction scoring
        email_score, email_reasoning = self._score_email_interactions(lead)
        score += email_score
        factors['email_interactions'] = email_score
        if email_reasoning:
            reasoning_parts.append(email_reasoning)
        
        # Budget range scoring
        budget_score, budget_reasoning = self._score_budget_range(lead)
        score += budget_score
        factors['budget_range'] = budget_score
        if budget_reasoning:
            reasoning_parts.append(budget_reasoning)
        
        # Property type scoring
        property_score, property_reasoning = self._score_property_type(lead)
        score += property_score
        factors['property_type'] = property_score
        if property_reasoning:
            reasoning_parts.append(property_reasoning)
        
        # Interaction frequency scoring
        interaction_score, interaction_reasoning = self._score_interaction_frequency(lead)
        score += interaction_score
        factors['interaction_frequency'] = interaction_score
        if interaction_reasoning:
            reasoning_parts.append(interaction_reasoning)
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        # Generate reasoning text
        reasoning = self._generate_reasoning(lead, score, reasoning_parts)
        
        return score, factors, reasoning
    
    def _score_calculator_data(self, lead: Lead) -> Tuple[int, str]:
        """Score based on solar calculator usage."""
        try:
            calculator_data = CalculatorData.objects.filter(
                Q(user_email=lead.email) | Q(user_phone=lead.phone)
            ).order_by('-calculation_date').first()
            
            if not calculator_data:
                return 0, ""
            
            score = 0
            reasoning_parts = []
            
            # Base score for using calculator
            score += 10
            reasoning_parts.append("used solar calculator")
            
            # Score based on estimated capacity
            if calculator_data.estimated_capacity:
                if calculator_data.estimated_capacity >= 10:
                    score += 10
                    reasoning_parts.append("large system capacity (10+ kW)")
                elif calculator_data.estimated_capacity >= 5:
                    score += 7
                    reasoning_parts.append("medium system capacity (5-10 kW)")
                else:
                    score += 5
                    reasoning_parts.append("small system capacity (<5 kW)")
            
            # Score based on estimated cost
            if calculator_data.estimated_cost:
                if calculator_data.estimated_cost >= 500000:  # 5 lakh+
                    score += 5
                    reasoning_parts.append("high-value project (₹5L+)")
                elif calculator_data.estimated_cost >= 300000:  # 3 lakh+
                    score += 3
                    reasoning_parts.append("medium-value project (₹3-5L)")
            
            reasoning = f"Calculator usage: {', '.join(reasoning_parts)}"
            return min(score, self.scoring_factors['calculator_usage']), reasoning
            
        except Exception as e:
            logger.error(f"Error scoring calculator data for lead {lead.id}: {e}")
            return 0, ""
    
    def _score_chatbot_engagement(self, lead: Lead) -> Tuple[int, str]:
        """Score based on chatbot interactions."""
        try:
            chatbot_interactions = ChatbotInteraction.objects.filter(
                Q(user_email=lead.email) | Q(user_phone=lead.phone)
            ).order_by('-interaction_date')
            
            if not chatbot_interactions.exists():
                return 0, ""
            
            score = 0
            reasoning_parts = []
            
            # Base score for chatbot usage
            score += 8
            reasoning_parts.append("engaged with chatbot")
            
            # Score based on number of interactions
            interaction_count = chatbot_interactions.count()
            if interaction_count >= 3:
                score += 8
                reasoning_parts.append("multiple chatbot sessions")
            elif interaction_count >= 2:
                score += 5
                reasoning_parts.append("repeated chatbot usage")
            
            # Score based on extracted intent
            latest_interaction = chatbot_interactions.first()
            if latest_interaction.user_intent:
                intent_scores = {
                    'purchase': 8,
                    'quotation': 7,
                    'information': 4,
                    'support': 2,
                }
                intent_score = intent_scores.get(latest_interaction.user_intent.lower(), 0)
                score += intent_score
                if intent_score > 0:
                    reasoning_parts.append(f"showed {latest_interaction.user_intent} intent")
            
            reasoning = f"Chatbot engagement: {', '.join(reasoning_parts)}"
            return min(score, self.scoring_factors['chatbot_engagement']), reasoning
            
        except Exception as e:
            logger.error(f"Error scoring chatbot engagement for lead {lead.id}: {e}")
            return 0, ""
    
    def _score_email_interactions(self, lead: Lead) -> Tuple[int, str]:
        """Score based on email interactions."""
        try:
            email_logs = EmailLog.objects.filter(sender_email=lead.email)
            
            if not email_logs.exists():
                return 0, ""
            
            score = 0
            reasoning_parts = []
            
            # Base score for email contact
            score += 5
            reasoning_parts.append("initiated email contact")
            
            # Score based on email type
            email_types = email_logs.values_list('email_type', flat=True)
            if 'quotation_request' in email_types:
                score += 8
                reasoning_parts.append("requested quotation")
            elif 'lead_inquiry' in email_types:
                score += 6
                reasoning_parts.append("sent inquiry")
            elif 'service_request' in email_types:
                score += 4
                reasoning_parts.append("existing customer")
            
            # Score based on email frequency
            email_count = email_logs.count()
            if email_count >= 3:
                score += 2
                reasoning_parts.append("multiple emails")
            
            reasoning = f"Email interactions: {', '.join(reasoning_parts)}"
            return min(score, self.scoring_factors['email_interactions']), reasoning
            
        except Exception as e:
            logger.error(f"Error scoring email interactions for lead {lead.id}: {e}")
            return 0, ""
    
    def _score_budget_range(self, lead: Lead) -> Tuple[int, str]:
        """Score based on budget range."""
        budget_scores = {
            'above_10_lakh': 20,
            '5_to_10_lakh': 15,
            '3_to_5_lakh': 10,
            '1_to_3_lakh': 5,
            'under_1_lakh': 2,
            'not_specified': 0,
        }
        
        score = budget_scores.get(lead.budget_range, 0)
        
        if score > 0:
            budget_display = dict(lead.BUDGET_RANGE_CHOICES).get(lead.budget_range, lead.budget_range)
            reasoning = f"Budget range: {budget_display}"
            return score, reasoning
        
        return 0, ""
    
    def _score_property_type(self, lead: Lead) -> Tuple[int, str]:
        """Score based on property type."""
        property_scores = {
            'industrial': 10,
            'commercial': 8,
            'agricultural': 6,
            'residential': 4,
        }
        
        score = property_scores.get(lead.property_type, 0)
        
        if score > 0:
            property_display = dict(lead.PROPERTY_TYPE_CHOICES).get(lead.property_type, lead.property_type)
            reasoning = f"Property type: {property_display}"
            return score, reasoning
        
        return 0, ""
    
    def _score_interaction_frequency(self, lead: Lead) -> Tuple[int, str]:
        """Score based on interaction frequency."""
        try:
            # Count interactions in the last 30 days
            thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
            recent_interactions = LeadInteraction.objects.filter(
                lead=lead,
                interaction_date__gte=thirty_days_ago
            ).count()
            
            if recent_interactions == 0:
                return 0, ""
            
            score = 0
            reasoning_parts = []
            
            if recent_interactions >= 5:
                score = 10
                reasoning_parts.append("very active (5+ interactions)")
            elif recent_interactions >= 3:
                score = 7
                reasoning_parts.append("active (3-4 interactions)")
            elif recent_interactions >= 2:
                score = 5
                reasoning_parts.append("moderate activity (2 interactions)")
            else:
                score = 2
                reasoning_parts.append("some activity (1 interaction)")
            
            reasoning = f"Recent activity: {', '.join(reasoning_parts)}"
            return score, reasoning
            
        except Exception as e:
            logger.error(f"Error scoring interaction frequency for lead {lead.id}: {e}")
            return 0, ""
    
    def _generate_reasoning(self, lead: Lead, score: int, reasoning_parts: List[str]) -> str:
        """Generate human-readable reasoning for the score."""
        if not reasoning_parts:
            return f"Lead scored {score}/100 based on basic information only."
        
        priority_level = self._get_priority_level(score)
        
        reasoning = f"Lead scored {score}/100 ({priority_level} priority) based on: "
        reasoning += "; ".join(reasoning_parts)
        reasoning += "."
        
        return reasoning
    
    def _get_priority_level(self, score: int) -> str:
        """Determine priority level based on score."""
        if score >= 80:
            return 'critical'
        elif score >= 60:
            return 'high'
        elif score >= 40:
            return 'medium'
        else:
            return 'low'
    
    def update_lead_priority(self, lead: Lead, save: bool = True) -> LeadScore:
        """
        Update lead priority and create score record.
        """
        try:
            # Calculate new score
            score, factors, reasoning = self.calculate_lead_score(lead)
            priority_level = self._get_priority_level(score)
            
            # Update lead
            lead.score = score
            lead.priority_level = priority_level
            
            if save:
                lead.save(update_fields=['score', 'priority_level', 'updated_at'])
            
            # Create score record
            lead_score = LeadScore.objects.create(
                lead=lead,
                score=score,
                priority_level=priority_level,
                scoring_factors=factors,
                applied_rules=[],  # Will be populated when rule-based system is implemented
                reasoning=reasoning,
                calculator_data_used='calculator_data' in factors and factors['calculator_data'] > 0,
                chatbot_data_used='chatbot_engagement' in factors and factors['chatbot_engagement'] > 0,
                interaction_data_used='interaction_frequency' in factors and factors['interaction_frequency'] > 0,
            )
            
            logger.info(f"Updated lead {lead.id} priority to {priority_level} with score {score}")
            
            return lead_score
            
        except Exception as e:
            logger.error(f"Error updating lead priority for lead {lead.id}: {e}")
            raise
    
    def bulk_update_priorities(self, lead_ids: Optional[List[int]] = None) -> int:
        """
        Update priorities for multiple leads.
        
        Args:
            lead_ids: List of lead IDs to update. If None, updates all leads.
            
        Returns:
            Number of leads updated.
        """
        try:
            if lead_ids:
                leads = Lead.objects.filter(id__in=lead_ids, status__in=['new', 'contacted', 'qualified'])
            else:
                leads = Lead.objects.filter(status__in=['new', 'contacted', 'qualified'])
            
            updated_count = 0
            
            for lead in leads:
                try:
                    self.update_lead_priority(lead)
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Error updating priority for lead {lead.id}: {e}")
                    continue
            
            logger.info(f"Bulk updated priorities for {updated_count} leads")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in bulk priority update: {e}")
            return 0
    
    def get_priority_explanation(self, lead: Lead) -> Dict:
        """
        Get detailed explanation of lead priority calculation.
        """
        try:
            latest_score = LeadScore.objects.filter(lead=lead).order_by('-calculated_at').first()
            
            if not latest_score:
                # Calculate on-the-fly if no score record exists
                score, factors, reasoning = self.calculate_lead_score(lead)
                return {
                    'score': score,
                    'priority_level': self._get_priority_level(score),
                    'factors': factors,
                    'reasoning': reasoning,
                    'calculated_at': timezone.now(),
                    'is_current': False,
                }
            
            return {
                'score': latest_score.score,
                'priority_level': latest_score.priority_level,
                'factors': latest_score.scoring_factors,
                'reasoning': latest_score.reasoning,
                'calculated_at': latest_score.calculated_at,
                'is_current': True,
                'data_sources': {
                    'calculator': latest_score.calculator_data_used,
                    'chatbot': latest_score.chatbot_data_used,
                    'interactions': latest_score.interaction_data_used,
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting priority explanation for lead {lead.id}: {e}")
            return {
                'score': lead.score,
                'priority_level': lead.priority_level,
                'factors': {},
                'reasoning': 'Error calculating priority explanation',
                'calculated_at': timezone.now(),
                'is_current': False,
            }


# Convenience function for easy access
def update_lead_priority(lead: Lead) -> LeadScore:
    """Update priority for a single lead."""
    service = LeadPrioritizationService()
    return service.update_lead_priority(lead)


def bulk_update_lead_priorities(lead_ids: Optional[List[int]] = None) -> int:
    """Update priorities for multiple leads."""
    service = LeadPrioritizationService()
    return service.bulk_update_priorities(lead_ids)


def get_lead_priority_explanation(lead: Lead) -> Dict:
    """Get priority explanation for a lead."""
    service = LeadPrioritizationService()
    return service.get_priority_explanation(lead)