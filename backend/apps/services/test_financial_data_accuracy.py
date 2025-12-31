"""
Property-based tests for financial data accuracy.
"""

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase as HypothesisTestCase

from .models import (
    PaymentMilestone, Invoice, Payment, FinancialSummary,
    InstallationProject, AMCContract, ServiceRequest
)
from ..customers.models import Customer
from ..leads.models import Lead, LeadSource

User = get_user_model()


class FinancialDataAccuracyPropertyTest(HypothesisTestCase):
    """Property-based tests for financial data accuracy."""
    
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
        
        # Create test installation project
        self.project = InstallationProject.objects.create(
            customer=self.customer,
            system_capacity=Decimal('10.5'),
            panel_brand='Test Solar',
            panel_model='TS-400W',
            panel_quantity=26,
            inverter_brand='Test Inverter',
            inverter_model='TI-10K',
            inverter_quantity=1,
            installation_type='rooftop',
            status='approved',
            progress_percentage=0,
            project_value=Decimal('525000.00'),
            amount_paid=Decimal('0.00'),
            warranty_years=25,
            project_manager=self.user,
            sales_person=self.user
        )
    
    @given(
        # Payment milestone data
        milestone_amounts=st.lists(
            st.decimals(min_value=1000, max_value=500000, places=2),
            min_size=1, max_size=6
        ),
        milestone_types=st.lists(
            st.sampled_from(['advance', 'material_delivery', 'installation_start', 'installation_complete', 'commissioning', 'final_payment']),
            min_size=1, max_size=6
        ),
        
        # Invoice data
        invoice_subtotals=st.lists(
            st.decimals(min_value=1000, max_value=500000, places=2),
            min_size=1, max_size=5
        ),
        tax_rates=st.lists(
            st.decimals(min_value=0, max_value=28, places=2),
            min_size=1, max_size=5
        ),
        invoice_types=st.lists(
            st.sampled_from(['project', 'amc', 'service', 'maintenance']),
            min_size=1, max_size=5
        ),
        
        # Payment data
        payment_amounts=st.lists(
            st.decimals(min_value=100, max_value=100000, places=2),
            min_size=0, max_size=10
        ),
        payment_methods=st.lists(
            st.sampled_from(['cash', 'cheque', 'bank_transfer', 'upi', 'card', 'online']),
            min_size=0, max_size=10
        ),
        payment_statuses=st.lists(
            st.sampled_from(['pending', 'processing', 'completed', 'failed']),
            min_size=0, max_size=10
        ),
        
        # Date ranges
        days_offset_start=st.integers(min_value=-30, max_value=0),
        days_offset_end=st.integers(min_value=1, max_value=90),
        
        # Financial operations
        perform_partial_payments=st.booleans(),
        create_overpayments=st.booleans(),
        update_payment_statuses=st.booleans()
    )
    @settings(max_examples=5, deadline=None)
    def test_financial_data_accuracy_property(self, milestone_amounts, milestone_types, 
                                            invoice_subtotals, tax_rates, invoice_types,
                                            payment_amounts, payment_methods, payment_statuses,
                                            days_offset_start, days_offset_end,
                                            perform_partial_payments, create_overpayments,
                                            update_payment_statuses):
        """
        **Feature: solar-crm-platform, Property 10: Financial Data Accuracy**
        
        Property: For any payment or invoice operation, the system should maintain accurate 
        real-time balances, payment status, and complete audit trails.
        
        **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
        """
        try:
            created_milestones = []
            created_invoices = []
            created_payments = []
            
            # Ensure we have matching lengths for milestone data
            min_milestone_count = min(len(milestone_amounts), len(milestone_types))
            milestone_amounts = milestone_amounts[:min_milestone_count]
            milestone_types = milestone_types[:min_milestone_count]
            
            # Ensure we have matching lengths for invoice data
            min_invoice_count = min(len(invoice_subtotals), len(tax_rates), len(invoice_types))
            invoice_subtotals = invoice_subtotals[:min_invoice_count]
            tax_rates = tax_rates[:min_invoice_count]
            invoice_types = invoice_types[:min_invoice_count]
            
            # Ensure we have matching lengths for payment data
            min_payment_count = min(len(payment_amounts), len(payment_methods), len(payment_statuses))
            payment_amounts = payment_amounts[:min_payment_count]
            payment_methods = payment_methods[:min_payment_count]
            payment_statuses = payment_statuses[:min_payment_count]
            
            # Property 1: Payment milestones should maintain accurate financial calculations (Requirements 9.1)
            total_milestone_amount = Decimal('0.00')
            for i, (amount, milestone_type) in enumerate(zip(milestone_amounts, milestone_types)):
                milestone = PaymentMilestone.objects.create(
                    installation_project=self.project,
                    milestone_type=milestone_type,
                    name=f"Test Milestone {i+1}",
                    amount=amount,
                    due_date=timezone.now().date() + timedelta(days=30 + i*10)
                )
                created_milestones.append(milestone)
                total_milestone_amount += amount
                
                # Verify milestone amount is stored correctly
                self.assertEqual(milestone.amount, amount, 
                               f"Milestone amount should be stored accurately: expected {amount}, got {milestone.amount}")
                
                # Verify initial outstanding amount equals milestone amount
                self.assertEqual(milestone.outstanding_amount, amount,
                               f"Initial outstanding amount should equal milestone amount: expected {amount}, got {milestone.outstanding_amount}")
                
                # Verify initial amount paid is zero
                self.assertEqual(milestone.amount_paid, Decimal('0.00'),
                               "Initial amount paid should be zero")
            
            # Property 2: Invoices should calculate tax and totals accurately (Requirements 9.2)
            total_invoice_amount = Decimal('0.00')
            for i, (subtotal, tax_rate, invoice_type) in enumerate(zip(invoice_subtotals, tax_rates, invoice_types)):
                # Calculate expected tax amount and total
                expected_tax_amount = (subtotal * tax_rate) / 100
                expected_total_amount = subtotal + expected_tax_amount
                
                invoice = Invoice.objects.create(
                    customer=self.customer,
                    invoice_type=invoice_type,
                    installation_project=self.project if invoice_type == 'project' else None,
                    subtotal=subtotal,
                    tax_rate=tax_rate,
                    invoice_date=timezone.now().date(),
                    due_date=timezone.now().date() + timedelta(days=30),
                    line_items=[{
                        'description': f'Test Item {i+1}',
                        'quantity': 1,
                        'rate': float(subtotal),
                        'amount': float(subtotal)
                    }]
                )
                created_invoices.append(invoice)
                total_invoice_amount += expected_total_amount
                
                # Verify tax calculation accuracy
                self.assertEqual(invoice.tax_amount, expected_tax_amount,
                               f"Tax amount calculation should be accurate: expected {expected_tax_amount}, got {invoice.tax_amount}")
                
                # Verify total calculation accuracy
                self.assertEqual(invoice.total_amount, expected_total_amount,
                               f"Total amount calculation should be accurate: expected {expected_total_amount}, got {invoice.total_amount}")
                
                # Verify initial outstanding amount equals total amount
                self.assertEqual(invoice.outstanding_amount, expected_total_amount,
                               f"Initial outstanding amount should equal total amount: expected {expected_total_amount}, got {invoice.outstanding_amount}")
                
                # Verify invoice number generation
                self.assertIsNotNone(invoice.invoice_number, "Invoice should have a generated invoice number")
                self.assertTrue(invoice.invoice_number.startswith('INV'), "Invoice number should start with 'INV'")
            
            # Property 3: Payments should update balances accurately (Requirements 9.1, 9.3)
            total_payments_made = Decimal('0.00')
            
            # Create payments for invoices and milestones
            payment_targets = []
            
            # Add invoices as payment targets
            for invoice in created_invoices:
                payment_targets.append(('invoice', invoice))
            
            # Add milestones as payment targets
            for milestone in created_milestones:
                payment_targets.append(('milestone', milestone))
            
            # Create payments
            for i, (amount, method, status) in enumerate(zip(payment_amounts, payment_methods, payment_statuses)):
                if i < len(payment_targets):
                    target_type, target_object = payment_targets[i]
                    
                    # Limit payment amount to not exceed target amount
                    if target_type == 'invoice':
                        max_amount = target_object.total_amount
                    else:  # milestone
                        max_amount = target_object.amount
                    
                    if create_overpayments and i % 3 == 0:
                        # Occasionally test overpayments
                        payment_amount = min(amount, max_amount * Decimal('1.5'))
                    else:
                        payment_amount = min(amount, max_amount)
                    
                    payment_kwargs = {
                        'customer': self.customer,
                        'amount': payment_amount,
                        'payment_method': method,
                        'payment_date': timezone.now().date(),
                        'status': status,
                        'processed_by': self.user if status == 'completed' else None
                    }
                    
                    if target_type == 'invoice':
                        payment_kwargs['invoice'] = target_object
                        payment_kwargs['installation_project'] = target_object.installation_project
                    else:  # milestone
                        payment_kwargs['payment_milestone'] = target_object
                        payment_kwargs['installation_project'] = target_object.installation_project
                    
                    payment = Payment.objects.create(**payment_kwargs)
                    created_payments.append(payment)
                    
                    if status == 'completed':
                        total_payments_made += payment_amount
                    
                    # Verify payment number generation
                    self.assertIsNotNone(payment.payment_number, "Payment should have a generated payment number")
                    self.assertTrue(payment.payment_number.startswith('PAY'), "Payment number should start with 'PAY'")
                    
                    # Verify payment amount is stored correctly
                    self.assertEqual(payment.amount, payment_amount,
                                   f"Payment amount should be stored accurately: expected {payment_amount}, got {payment.amount}")
            
            # Property 4: Outstanding amounts should be calculated correctly after payments (Requirements 9.3)
            for invoice in created_invoices:
                # Refresh from database to get updated calculations
                invoice.refresh_from_db()
                
                # Calculate expected amounts
                completed_payments = invoice.payments.filter(status='completed')
                expected_amount_paid = sum(p.amount for p in completed_payments)
                expected_outstanding = invoice.total_amount - expected_amount_paid
                
                # Verify amount paid calculation
                self.assertEqual(invoice.amount_paid, expected_amount_paid,
                               f"Invoice amount paid should be calculated correctly: expected {expected_amount_paid}, got {invoice.amount_paid}")
                
                # Verify outstanding amount calculation
                self.assertEqual(invoice.outstanding_amount, expected_outstanding,
                               f"Invoice outstanding amount should be calculated correctly: expected {expected_outstanding}, got {invoice.outstanding_amount}")
                
                # Verify status updates based on payments
                if expected_amount_paid >= invoice.total_amount:
                    expected_status = 'paid'
                elif expected_amount_paid > 0:
                    expected_status = 'partial'
                elif invoice.is_overdue:
                    expected_status = 'overdue'
                elif invoice.sent_at:
                    expected_status = 'sent'
                else:
                    expected_status = 'draft'
                
                # Update status to verify automatic status calculation
                invoice.update_status_based_on_payments()
                self.assertEqual(invoice.status, expected_status,
                               f"Invoice status should be updated correctly based on payments: expected {expected_status}, got {invoice.status}")
            
            # Property 5: Payment milestone balances should be accurate (Requirements 9.1)
            for milestone in created_milestones:
                # Refresh from database to get updated calculations
                milestone.refresh_from_db()
                
                # Calculate expected amounts
                completed_payments = milestone.payments.filter(status='completed')
                expected_amount_paid = sum(p.amount for p in completed_payments)
                expected_outstanding = milestone.amount - expected_amount_paid
                
                # Verify amount paid calculation
                self.assertEqual(milestone.amount_paid, expected_amount_paid,
                               f"Milestone amount paid should be calculated correctly: expected {expected_amount_paid}, got {milestone.amount_paid}")
                
                # Verify outstanding amount calculation
                self.assertEqual(milestone.outstanding_amount, expected_outstanding,
                               f"Milestone outstanding amount should be calculated correctly: expected {expected_outstanding}, got {milestone.outstanding_amount}")
                
                # Verify status updates based on payments
                if expected_amount_paid >= milestone.amount:
                    expected_status = 'paid'
                elif expected_amount_paid > 0:
                    expected_status = 'partial'
                elif milestone.is_overdue:
                    expected_status = 'overdue'
                else:
                    expected_status = 'pending'
                
                # Update status to verify automatic status calculation
                milestone.update_status_based_on_payments()
                self.assertEqual(milestone.status, expected_status,
                               f"Milestone status should be updated correctly based on payments: expected {expected_status}, got {milestone.status}")
            
            # Property 6: Payment status updates should maintain data integrity (Requirements 9.3, 9.4)
            if update_payment_statuses and created_payments:
                for payment in created_payments[:min(3, len(created_payments))]:
                    original_amount = payment.amount
                    original_customer = payment.customer
                    original_date = payment.payment_date
                    
                    # Test status transitions
                    if payment.status == 'pending':
                        payment.status = 'processing'
                        payment.save()
                        
                        # Verify data integrity maintained
                        self.assertEqual(payment.amount, original_amount, "Payment amount should not change during status update")
                        self.assertEqual(payment.customer, original_customer, "Payment customer should not change during status update")
                        self.assertEqual(payment.payment_date, original_date, "Payment date should not change during status update")
                    
                    if payment.status in ['processing', 'pending']:
                        payment.mark_as_completed(self.user, "Test completion")
                        
                        # Verify completion updates
                        self.assertEqual(payment.status, 'completed', "Payment should be marked as completed")
                        self.assertEqual(payment.processed_by, self.user, "Payment should record who processed it")
                        
                        # Verify related objects are updated
                        if payment.invoice:
                            payment.invoice.refresh_from_db()
                            # Invoice status should be recalculated
                            self.assertIsNotNone(payment.invoice.status, "Invoice status should be updated after payment completion")
                        
                        if payment.payment_milestone:
                            payment.payment_milestone.refresh_from_db()
                            # Milestone status should be recalculated
                            self.assertIsNotNone(payment.payment_milestone.status, "Milestone status should be updated after payment completion")
            
            # Property 7: Financial summary calculations should be accurate (Requirements 9.4)
            if created_invoices or created_payments:
                # Create financial summary for the period
                period_start = timezone.now().date() + timedelta(days=days_offset_start)
                period_end = timezone.now().date() + timedelta(days=days_offset_end)
                
                # Calculate expected values
                period_invoices = [inv for inv in created_invoices if period_start <= inv.invoice_date <= period_end]
                period_payments = [pay for pay in created_payments if period_start <= pay.payment_date <= period_end and pay.status == 'completed']
                
                expected_total_invoiced = sum(inv.total_amount for inv in period_invoices)
                expected_total_collected = sum(pay.amount for pay in period_payments)
                expected_total_outstanding = sum(inv.outstanding_amount for inv in period_invoices)
                
                financial_summary = FinancialSummary.objects.create(
                    summary_type='daily',
                    period_start=period_start,
                    period_end=period_end,
                    total_invoiced=expected_total_invoiced,
                    total_collected=expected_total_collected,
                    total_outstanding=expected_total_outstanding,
                    projects_invoiced=len([inv for inv in period_invoices if inv.invoice_type == 'project']),
                    payments_received=len(period_payments)
                )
                
                # Verify financial summary accuracy
                self.assertEqual(financial_summary.total_invoiced, expected_total_invoiced,
                               f"Financial summary total invoiced should be accurate: expected {expected_total_invoiced}, got {financial_summary.total_invoiced}")
                
                self.assertEqual(financial_summary.total_collected, expected_total_collected,
                               f"Financial summary total collected should be accurate: expected {expected_total_collected}, got {financial_summary.total_collected}")
                
                self.assertEqual(financial_summary.total_outstanding, expected_total_outstanding,
                               f"Financial summary total outstanding should be accurate: expected {expected_total_outstanding}, got {financial_summary.total_outstanding}")
            
            # Property 8: Audit trail should be maintained for all financial operations (Requirements 9.4)
            # Verify all financial records have proper timestamps
            for milestone in created_milestones:
                self.assertIsNotNone(milestone.created_at, "Payment milestone should have creation timestamp")
                self.assertIsNotNone(milestone.updated_at, "Payment milestone should have update timestamp")
                self.assertLessEqual(milestone.created_at, milestone.updated_at, "Update timestamp should be >= creation timestamp")
            
            for invoice in created_invoices:
                self.assertIsNotNone(invoice.created_at, "Invoice should have creation timestamp")
                self.assertIsNotNone(invoice.updated_at, "Invoice should have update timestamp")
                self.assertLessEqual(invoice.created_at, invoice.updated_at, "Update timestamp should be >= creation timestamp")
                
                # Verify invoice date constraints
                self.assertLessEqual(invoice.invoice_date, invoice.due_date, "Due date should be >= invoice date")
            
            for payment in created_payments:
                self.assertIsNotNone(payment.created_at, "Payment should have creation timestamp")
                self.assertIsNotNone(payment.updated_at, "Payment should have update timestamp")
                self.assertLessEqual(payment.created_at, payment.updated_at, "Update timestamp should be >= creation timestamp")
            
            # Property 9: Data constraints should be enforced (Requirements 9.1, 9.2, 9.3)
            # Verify all amounts are non-negative
            for milestone in created_milestones:
                self.assertGreaterEqual(milestone.amount, 0, "Milestone amount should be non-negative")
                self.assertGreaterEqual(milestone.amount_paid, 0, "Milestone amount paid should be non-negative")
                self.assertGreaterEqual(milestone.outstanding_amount, 0, "Milestone outstanding amount should be non-negative")
            
            for invoice in created_invoices:
                self.assertGreaterEqual(invoice.subtotal, 0, "Invoice subtotal should be non-negative")
                self.assertGreaterEqual(invoice.tax_amount, 0, "Invoice tax amount should be non-negative")
                self.assertGreaterEqual(invoice.total_amount, 0, "Invoice total amount should be non-negative")
                self.assertGreaterEqual(invoice.amount_paid, 0, "Invoice amount paid should be non-negative")
                self.assertGreaterEqual(invoice.outstanding_amount, 0, "Invoice outstanding amount should be non-negative")
            
            for payment in created_payments:
                self.assertGreater(payment.amount, 0, "Payment amount should be positive")
            
            # Property 10: Real-time balance calculations should be consistent (Requirements 9.3, 9.4)
            # Verify that sum of all milestone amounts equals project financial tracking
            if created_milestones:
                total_milestone_amounts = sum(m.amount for m in created_milestones)
                total_milestone_paid = sum(m.amount_paid for m in created_milestones)
                total_milestone_outstanding = sum(m.outstanding_amount for m in created_milestones)
                
                # Verify mathematical consistency
                self.assertEqual(total_milestone_amounts, total_milestone_paid + total_milestone_outstanding,
                               "Total milestone amounts should equal paid + outstanding")
            
            # Verify that invoice totals are mathematically consistent
            for invoice in created_invoices:
                calculated_total = invoice.subtotal + invoice.tax_amount
                self.assertEqual(invoice.total_amount, calculated_total,
                               f"Invoice total should equal subtotal + tax: expected {calculated_total}, got {invoice.total_amount}")
                
                calculated_outstanding = invoice.total_amount - invoice.amount_paid
                self.assertEqual(invoice.outstanding_amount, calculated_outstanding,
                               f"Invoice outstanding should equal total - paid: expected {calculated_outstanding}, got {invoice.outstanding_amount}")
            
        except Exception as e:
            # Clean up any created objects on failure
            for payment in created_payments:
                payment.delete()
            for invoice in created_invoices:
                invoice.delete()
            for milestone in created_milestones:
                milestone.delete()
            raise e