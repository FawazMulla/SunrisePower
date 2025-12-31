"""
Property-based tests for contract and project tracking system.
"""

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase as HypothesisTestCase

from .models import (
    AMCContract, InstallationProject, ProjectStatusHistory, 
    ProjectMilestone, ProjectNotification, AMCRenewalAlert
)
from ..customers.models import Customer
from ..leads.models import Lead, LeadSource

User = get_user_model()


class ContractProjectTrackingPropertyTest(HypothesisTestCase):
    """Property-based tests for contract and project tracking system."""
    
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
        # Project data
        system_capacity=st.decimals(min_value=1, max_value=100, places=2),
        panel_brand=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        panel_model=st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        panel_quantity=st.integers(min_value=1, max_value=1000),
        inverter_brand=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        inverter_model=st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
        inverter_quantity=st.integers(min_value=1, max_value=10),
        installation_type=st.sampled_from(['rooftop', 'ground_mount', 'carport', 'floating', 'agri_solar']),
        project_status=st.sampled_from(['quotation', 'approved', 'design', 'permits', 'procurement', 'installation', 'testing', 'completed', 'on_hold', 'cancelled']),
        progress_percentage=st.integers(min_value=0, max_value=100),
        project_value=st.decimals(min_value=10000, max_value=10000000, places=2),
        amount_paid=st.decimals(min_value=0, max_value=10000000, places=2),
        warranty_years=st.integers(min_value=1, max_value=50),
        
        # AMC Contract data
        contract_start_days_offset=st.integers(min_value=-365, max_value=365),
        contract_duration_days=st.integers(min_value=365, max_value=1825),  # 1-5 years
        annual_value=st.decimals(min_value=1000, max_value=100000, places=2),
        maintenance_frequency=st.sampled_from(['monthly', 'quarterly', 'bi-annual', 'annual']),
        contract_status=st.sampled_from(['active', 'expired', 'cancelled', 'suspended', 'renewal_pending']),
        auto_renewal=st.booleans(),
        
        # Status changes
        status_changes=st.lists(
            st.sampled_from(['quotation', 'approved', 'design', 'permits', 'procurement', 'installation', 'testing', 'completed']),
            min_size=0, max_size=5
        ),
        
        # Milestone data
        milestone_count=st.integers(min_value=0, max_value=8),
        
        # Alert data
        alert_days_before=st.lists(
            st.integers(min_value=1, max_value=90),
            min_size=0, max_size=4
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_contract_and_project_tracking_property(self, system_capacity, panel_brand, panel_model, 
                                                  panel_quantity, inverter_brand, inverter_model, 
                                                  inverter_quantity, installation_type, project_status, 
                                                  progress_percentage, project_value, amount_paid, 
                                                  warranty_years, contract_start_days_offset, 
                                                  contract_duration_days, annual_value, maintenance_frequency, 
                                                  contract_status, auto_renewal, status_changes, 
                                                  milestone_count, alert_days_before):
        """
        **Feature: solar-crm-platform, Property 9: Contract and Project Tracking**
        
        Property: For any AMC contract or installation project, the system should track all stages, 
        dates, milestones, and generate appropriate alerts and notifications.
        
        **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
        """
        try:
            # Ensure amount_paid doesn't exceed project_value
            if amount_paid > project_value:
                amount_paid = project_value
            
            # Create installation project
            project = InstallationProject.objects.create(
                customer=self.customer,
                system_capacity=system_capacity,
                panel_brand=panel_brand,
                panel_model=panel_model,
                panel_quantity=panel_quantity,
                inverter_brand=inverter_brand,
                inverter_model=inverter_model,
                inverter_quantity=inverter_quantity,
                installation_type=installation_type,
                status=project_status,
                progress_percentage=progress_percentage,
                project_value=project_value,
                amount_paid=amount_paid,
                warranty_years=warranty_years,
                project_manager=self.user,
                sales_person=self.user
            )
            
            # Property 1: Project should have unique project number (Requirements 8.3)
            self.assertIsNotNone(project.project_number, "Project should have a project number")
            self.assertTrue(project.project_number.startswith('PRJ'), "Project number should start with 'PRJ'")
            self.assertEqual(len(project.project_number), 14, "Project number should be 14 characters long")
            
            # Property 2: Project status should be tracked correctly (Requirements 8.3)
            self.assertEqual(project.status, project_status, "Project status should be set correctly")
            self.assertIn(project.status, [choice[0] for choice in InstallationProject.PROJECT_STATUS_CHOICES], 
                         "Project status should be valid")
            
            # Property 3: Progress percentage should be within valid range (Requirements 8.3)
            self.assertGreaterEqual(project.progress_percentage, 0, "Progress percentage should be >= 0")
            self.assertLessEqual(project.progress_percentage, 100, "Progress percentage should be <= 100")
            
            # Property 4: Financial calculations should be accurate (Requirements 8.3)
            expected_outstanding = project_value - amount_paid
            self.assertEqual(project.outstanding_amount, expected_outstanding, 
                           "Outstanding amount should be calculated correctly")
            
            if project_value > 0:
                expected_payment_percentage = (amount_paid / project_value) * 100
                self.assertEqual(project.payment_percentage, expected_payment_percentage, 
                               "Payment percentage should be calculated correctly")
            
            # Property 5: Status changes should be tracked with history (Requirements 8.4)
            original_status = project.status
            for new_status in status_changes:
                if new_status != project.status:
                    project.update_status_with_notification(new_status, self.user, f"Status changed to {new_status}")
                    
                    # Check that status history was created
                    history_records = ProjectStatusHistory.objects.filter(
                        installation_project=project,
                        new_status=new_status
                    )
                    self.assertGreater(history_records.count(), 0, 
                                     f"Status history should be created for status change to {new_status}")
                    
                    # Check that notification was created
                    notifications = ProjectNotification.objects.filter(
                        installation_project=project,
                        notification_type='status_change'
                    )
                    self.assertGreater(notifications.count(), 0, 
                                     "Status change notification should be created")
            
            # Property 6: Project milestones should be manageable (Requirements 8.4)
            milestones = []
            milestone_types = ['quotation', 'approval', 'design', 'permits', 'procurement', 
                             'installation_start', 'installation_complete', 'testing']
            
            for i in range(min(milestone_count, len(milestone_types))):
                milestone = ProjectMilestone.objects.create(
                    installation_project=project,
                    milestone_type=milestone_types[i],
                    name=f"Test Milestone {i+1}",
                    planned_date=timezone.now().date() + timedelta(days=i*10),
                    assigned_to=self.user
                )
                milestones.append(milestone)
            
            # Verify milestones are linked to project
            project_milestones = project.milestones.all()
            self.assertEqual(project_milestones.count(), len(milestones), 
                           "All milestones should be linked to project")
            
            # Property 7: Milestone completion should be tracked (Requirements 8.4)
            for milestone in milestones[:min(2, len(milestones))]:  # Complete first 2 milestones
                milestone.mark_as_completed(self.user, "Milestone completed successfully")
                
                self.assertEqual(milestone.status, 'completed', "Milestone should be marked as completed")
                self.assertIsNotNone(milestone.actual_date, "Milestone should have actual completion date")
                
                # Check that milestone completion notification was created
                milestone_notifications = ProjectNotification.objects.filter(
                    installation_project=project,
                    notification_type='milestone_completed'
                )
                self.assertGreater(milestone_notifications.count(), 0, 
                                 "Milestone completion notification should be created")
            
            # Property 8: AMC contract should be created and tracked (Requirements 8.1, 8.2)
            contract_start_date = timezone.now().date() + timedelta(days=contract_start_days_offset)
            contract_end_date = contract_start_date + timedelta(days=contract_duration_days)
            
            amc_contract = AMCContract.objects.create(
                customer=self.customer,
                installation_project=project,
                start_date=contract_start_date,
                end_date=contract_end_date,
                annual_value=annual_value,
                maintenance_frequency=maintenance_frequency,
                status=contract_status,
                auto_renewal=auto_renewal,
                contact_person=self.user,
                services_included=['cleaning', 'inspection', 'maintenance']
            )
            
            # Property 9: AMC contract should have unique contract number (Requirements 8.1)
            self.assertIsNotNone(amc_contract.contract_number, "AMC contract should have a contract number")
            self.assertTrue(amc_contract.contract_number.startswith('AMC'), "Contract number should start with 'AMC'")
            self.assertEqual(len(amc_contract.contract_number), 14, "Contract number should be 14 characters long")
            
            # Property 10: AMC contract validity should be calculated correctly (Requirements 8.1, 8.2)
            today = timezone.now().date()
            expected_is_active = (
                contract_status == 'active' and 
                contract_start_date <= today <= contract_end_date
            )
            self.assertEqual(amc_contract.is_active, expected_is_active, 
                           "AMC contract active status should be calculated correctly")
            
            # Property 11: Contract expiry calculations should be accurate (Requirements 8.2)
            if contract_end_date > today:
                expected_days_until_expiry = (contract_end_date - today).days
                self.assertEqual(amc_contract.days_until_expiry, expected_days_until_expiry, 
                               "Days until expiry should be calculated correctly")
            else:
                self.assertEqual(amc_contract.days_until_expiry, 0, 
                               "Expired contracts should have 0 days until expiry")
            
            # Property 12: Renewal alerts should be created and managed (Requirements 8.2)
            if contract_end_date > today:  # Only create alerts for future contracts
                alerts_created = AMCRenewalAlert.create_alerts_for_contract(amc_contract)
                
                # Verify alerts were created for future dates
                all_alerts = AMCRenewalAlert.objects.filter(amc_contract=amc_contract)
                self.assertGreater(all_alerts.count(), 0, "Renewal alerts should be created for future contracts")
                
                # Check alert types
                alert_types = list(all_alerts.values_list('alert_type', flat=True))
                expected_alert_types = ['30_days', '15_days', '7_days', 'expired']
                for alert_type in alert_types:
                    self.assertIn(alert_type, expected_alert_types, f"Alert type '{alert_type}' should be valid")
            
            # Property 13: Contract renewal should work correctly (Requirements 8.2)
            if contract_status == 'active' and contract_end_date > today:
                new_end_date = contract_end_date + timedelta(days=365)
                new_annual_value = annual_value * Decimal('1.1')  # 10% increase
                
                original_start_date = amc_contract.start_date
                amc_contract.renew_contract(new_end_date, new_annual_value)
                
                # Verify renewal
                self.assertEqual(amc_contract.end_date, new_end_date, "Contract end date should be updated")
                self.assertEqual(amc_contract.annual_value, new_annual_value, "Annual value should be updated")
                self.assertEqual(amc_contract.status, 'active', "Renewed contract should be active")
                self.assertFalse(amc_contract.renewal_reminder_sent, "Renewal reminder flag should be reset")
            
            # Property 14: Project completion should update all related data (Requirements 8.3, 8.4)
            if project_status not in ['completed', 'cancelled']:
                project.mark_as_completed()
                
                self.assertEqual(project.status, 'completed', "Project should be marked as completed")
                self.assertEqual(project.progress_percentage, 100, "Completed project should have 100% progress")
                self.assertIsNotNone(project.completion_date, "Completed project should have completion date")
            
            # Property 15: Overdue detection should work correctly (Requirements 8.3, 8.4)
            # Test project overdue detection
            if project.approval_date:
                expected_overdue = (
                    project.status not in ['completed', 'cancelled'] and
                    timezone.now().date() > (project.approval_date + timedelta(days=90))
                )
                self.assertEqual(project.is_overdue, expected_overdue, 
                               "Project overdue status should be calculated correctly")
            
            # Test milestone overdue detection
            for milestone in milestones:
                if milestone.planned_date and milestone.status != 'completed':
                    expected_milestone_overdue = timezone.now().date() > milestone.planned_date
                    self.assertEqual(milestone.is_overdue, expected_milestone_overdue, 
                                   "Milestone overdue status should be calculated correctly")
            
            # Property 16: Stakeholder notifications should contain required information (Requirements 8.4)
            notifications = ProjectNotification.objects.filter(installation_project=project)
            for notification in notifications:
                self.assertIsNotNone(notification.title, "Notification should have a title")
                self.assertIsNotNone(notification.message, "Notification should have a message")
                self.assertIsInstance(notification.recipients, list, "Notification recipients should be a list")
                self.assertIn(notification.status, ['pending', 'sent', 'failed', 'acknowledged'], 
                             "Notification status should be valid")
                
                # Check that notification contains project information
                self.assertIn(project.project_number, notification.message, 
                             "Notification should contain project number")
            
            # Property 17: Data integrity should be maintained across all operations (Requirements 8.1, 8.2, 8.3, 8.4)
            # Verify project-contract relationship
            self.assertEqual(amc_contract.installation_project, project, 
                           "AMC contract should be linked to correct project")
            self.assertEqual(amc_contract.customer, project.customer, 
                           "AMC contract and project should have same customer")
            
            # Verify all timestamps are set
            self.assertIsNotNone(project.created_at, "Project should have creation timestamp")
            self.assertIsNotNone(project.updated_at, "Project should have update timestamp")
            self.assertIsNotNone(amc_contract.created_at, "Contract should have creation timestamp")
            self.assertIsNotNone(amc_contract.updated_at, "Contract should have update timestamp")
            
            # Verify data constraints are enforced
            self.assertGreaterEqual(project.project_value, 0, "Project value should be non-negative")
            self.assertGreaterEqual(project.amount_paid, 0, "Amount paid should be non-negative")
            self.assertLessEqual(project.amount_paid, project.project_value, 
                               "Amount paid should not exceed project value")
            self.assertGreaterEqual(amc_contract.annual_value, 0, "Annual value should be non-negative")
            self.assertGreater(amc_contract.end_date, amc_contract.start_date, 
                             "Contract end date should be after start date")
            
        except Exception as e:
            # Clean up any created objects on failure
            if 'project' in locals():
                project.delete()
            if 'amc_contract' in locals():
                amc_contract.delete()
            raise e