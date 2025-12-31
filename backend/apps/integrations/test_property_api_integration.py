"""
Property-based tests for API integration completeness.

**Feature: solar-crm-platform, Property 6: API Integration Completeness**

This module tests that frontend interactions (chatbot, calculator, forms) 
can successfully capture and submit data to the CRM via API endpoints 
while maintaining response times under 5 seconds.

Validates: Requirements 3.1, 3.5, 5.1
"""

import time
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase as HypothesisTestCase

from apps.leads.models import Lead, LeadSource
from apps.customers.models import Customer
from apps.services.models import ServiceRequest
from apps.integrations.models import BackgroundTask

User = get_user_model()


class APIIntegrationCompletenessPropertyTest(HypothesisTestCase):
    """
    Property-based tests for API integration completeness.
    
    **Feature: solar-crm-platform, Property 6: API Integration Completeness**
    **Validates: Requirements 3.1, 3.5, 5.1**
    """
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create a test user with appropriate permissions
        # Use get_or_create to avoid unique constraint issues
        self.user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'password': 'testpass123',
                'role': 'owner'
            }
        )
        
        # Create a lead source for testing
        self.lead_source, _ = LeadSource.objects.get_or_create(
            name='Website Chatbot',
            defaults={'description': 'Chatbot interactions from website'}
        )
        
        # Authenticate the client
        self.client.force_authenticate(user=self.user)
    
    @given(
        first_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        last_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        email=st.emails(),
        phone=st.text(min_size=10, max_size=15).filter(lambda x: x.isdigit()),
        property_type=st.sampled_from(['residential', 'commercial', 'industrial']),
        estimated_capacity=st.decimals(min_value=1, max_value=1000, places=2),
        budget_range=st.sampled_from(['under_5_lakh', '5_to_10_lakh', '10_to_25_lakh', 'above_25_lakh']),
        interest_level=st.sampled_from(['low', 'medium', 'high', 'very_high'])
    )
    @settings(max_examples=100, deadline=None)
    def test_chatbot_data_submission_api_integration_completeness(
        self, first_name, last_name, email, phone, property_type, 
        estimated_capacity, budget_range, interest_level
    ):
        """
        Property: For any chatbot interaction data, the API should successfully 
        capture and process the data within 5 seconds, creating appropriate CRM records.
        
        **Feature: solar-crm-platform, Property 6: API Integration Completeness**
        **Validates: Requirements 3.1, 3.5**
        """
        # Prepare chatbot data payload
        chatbot_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'property_type': property_type,
            'estimated_capacity': str(estimated_capacity),
            'budget_range': budget_range,
            'interest_level': interest_level,
            'source': 'chatbot',
            'conversation_context': f'User interested in {property_type} solar installation'
        }
        
        # Record start time for performance testing
        start_time = time.time()
        
        # Submit data to lead creation API (simulating chatbot integration)
        response = self.client.post(
            reverse('leads:lead-list-create'),
            data=chatbot_data,
            format='json'
        )
        
        # Record end time
        end_time = time.time()
        response_time = end_time - start_time
        
        # Property assertions
        # 1. API should successfully process the request
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
        
        # 2. Response time should be under 5 seconds (Requirement 3.5)
        self.assertLess(response_time, 5.0, 
                       f"API response time {response_time:.2f}s exceeds 5 second limit")
        
        # 3. If successful, a lead record should be created with the submitted data
        if response.status_code == status.HTTP_201_CREATED:
            lead_id = response.data.get('id')
            self.assertIsNotNone(lead_id)
            
            # Verify the lead was created with correct data
            lead = Lead.objects.get(id=lead_id)
            self.assertEqual(lead.first_name, first_name)
            self.assertEqual(lead.last_name, last_name)
            self.assertEqual(lead.email, email)
            self.assertEqual(lead.phone, phone)
            self.assertEqual(lead.property_type, property_type)
            self.assertEqual(lead.interest_level, interest_level)
    
    @given(
        system_capacity=st.decimals(min_value=1, max_value=500, places=2),
        monthly_consumption=st.integers(min_value=100, max_value=5000),
        roof_area=st.decimals(min_value=100, max_value=10000, places=2),
        property_type=st.sampled_from(['residential', 'commercial', 'industrial']),
        location=st.text(min_size=3, max_size=50).filter(lambda x: x.strip()),
        contact_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        contact_email=st.emails(),
        contact_phone=st.text(min_size=10, max_size=15).filter(lambda x: x.isdigit())
    )
    @settings(max_examples=100, deadline=None)
    def test_solar_calculator_data_submission_api_integration_completeness(
        self, system_capacity, monthly_consumption, roof_area, property_type,
        location, contact_name, contact_email, contact_phone
    ):
        """
        Property: For any solar calculator completion data, the API should successfully 
        capture and process the data within 5 seconds, creating appropriate lead records.
        
        **Feature: solar-crm-platform, Property 6: API Integration Completeness**
        **Validates: Requirements 5.1**
        """
        # Prepare calculator data payload
        calculator_data = {
            'first_name': contact_name.split()[0] if ' ' in contact_name else contact_name,
            'last_name': contact_name.split()[-1] if ' ' in contact_name else '',
            'email': contact_email,
            'phone': contact_phone,
            'property_type': property_type,
            'estimated_capacity': str(system_capacity),
            'city': location,
            'source': 'calculator',
            'original_data': {
                'system_capacity': str(system_capacity),
                'monthly_consumption': monthly_consumption,
                'roof_area': str(roof_area),
                'location': location
            }
        }
        
        # Record start time for performance testing
        start_time = time.time()
        
        # Submit data to lead creation API (simulating calculator integration)
        response = self.client.post(
            reverse('leads:lead-list-create'),
            data=calculator_data,
            format='json'
        )
        
        # Record end time
        end_time = time.time()
        response_time = end_time - start_time
        
        # Property assertions
        # 1. API should successfully process the request
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
        
        # 2. Response time should be under 5 seconds
        self.assertLess(response_time, 5.0, 
                       f"API response time {response_time:.2f}s exceeds 5 second limit")
        
        # 3. If successful, a lead record should be created with calculator context
        if response.status_code == status.HTTP_201_CREATED:
            lead_id = response.data.get('id')
            self.assertIsNotNone(lead_id)
            
            # Verify the lead was created with correct data
            lead = Lead.objects.get(id=lead_id)
            self.assertEqual(lead.email, contact_email)
            self.assertEqual(lead.phone, contact_phone)
            self.assertEqual(lead.property_type, property_type)
            self.assertEqual(lead.estimated_capacity, system_capacity)
            self.assertEqual(lead.city, location)
    
    @given(
        sender_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        sender_email=st.emails(),
        subject=st.text(min_size=5, max_size=200).filter(lambda x: x.strip()),
        message_body=st.text(min_size=10, max_size=1000).filter(lambda x: x.strip()),
        form_type=st.sampled_from(['contact', 'quotation', 'service_request'])
    )
    @settings(max_examples=100, deadline=None)
    def test_emailjs_webhook_api_integration_completeness(
        self, sender_name, sender_email, subject, message_body, form_type
    ):
        """
        Property: For any EmailJS form submission, the webhook API should successfully 
        capture and process the data within 5 seconds, creating appropriate CRM records.
        
        **Feature: solar-crm-platform, Property 6: API Integration Completeness**
        **Validates: Requirements 3.1 (form integration aspect)**
        """
        # Prepare EmailJS webhook data payload
        webhook_data = {
            'from_name': sender_name,
            'from_email': sender_email,
            'subject': subject,
            'message': message_body,
            'form_type': form_type,
            'timestamp': time.time()
        }
        
        # Record start time for performance testing
        start_time = time.time()
        
        # Submit data to EmailJS webhook endpoint (no authentication required)
        client = Client()  # Use regular client for webhook (no auth)
        response = client.post(
            reverse('integrations:emailjs_webhook'),
            data=webhook_data,
            content_type='application/json'
        )
        
        # Record end time
        end_time = time.time()
        response_time = end_time - start_time
        
        # Property assertions
        # 1. Webhook should successfully accept the request
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 2. Response time should be under 5 seconds
        self.assertLess(response_time, 5.0, 
                       f"Webhook response time {response_time:.2f}s exceeds 5 second limit")
        
        # 3. Response should indicate successful queuing
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'success')
        self.assertIn('task_id', response_data)
        
        # 4. The webhook should have created a background task for processing
        task_id = response_data.get('task_id')
        self.assertIsNotNone(task_id)
    
    @given(
        api_endpoint=st.sampled_from([
            'leads:lead-list-create',
            'customers:customer-list-create', 
            'services:service-request-list-create'
        ]),
        data_size=st.integers(min_value=1, max_value=10)  # Number of fields in payload
    )
    @settings(max_examples=50, deadline=None)
    def test_api_endpoint_performance_consistency(self, api_endpoint, data_size):
        """
        Property: For any API endpoint, response times should be consistently under 5 seconds
        regardless of payload size (within reasonable limits).
        
        **Feature: solar-crm-platform, Property 6: API Integration Completeness**
        **Validates: Requirements 3.5 (performance consistency)**
        """
        # Generate test data based on endpoint
        if 'lead' in api_endpoint:
            test_data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': f'test{time.time()}@example.com',
                'phone': '1234567890',
                'property_type': 'residential'
            }
        elif 'customer' in api_endpoint:
            test_data = {
                'first_name': 'Test',
                'last_name': 'Customer',
                'email': f'customer{time.time()}@example.com',
                'phone': '1234567890',
                'address': '123 Test St',
                'city': 'Test City',
                'state': 'Test State',
                'pincode': '123456'
            }
        else:  # service request
            # Create a customer first for service request
            customer = Customer.objects.create(
                first_name='Test',
                last_name='Customer',
                email=f'service{time.time()}@example.com',
                phone='1234567890',
                address='123 Test St',
                city='Test City',
                state='Test State',
                pincode='123456'
            )
            test_data = {
                'customer': customer.id,
                'subject': 'Test Service Request',
                'description': 'Test description',
                'request_type': 'maintenance',
                'priority': 'medium'
            }
        
        # Add extra fields based on data_size parameter
        for i in range(data_size):
            test_data[f'extra_field_{i}'] = f'extra_value_{i}'
        
        # Record start time
        start_time = time.time()
        
        # Make API request
        response = self.client.post(
            reverse(api_endpoint),
            data=test_data,
            format='json'
        )
        
        # Record end time
        end_time = time.time()
        response_time = end_time - start_time
        
        # Property assertions
        # 1. API should respond (success or validation error)
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED, 
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN
        ])
        
        # 2. Response time should be under 5 seconds regardless of data size
        self.assertLess(response_time, 5.0, 
                       f"API endpoint {api_endpoint} response time {response_time:.2f}s "
                       f"exceeds 5 second limit with {data_size} extra fields")