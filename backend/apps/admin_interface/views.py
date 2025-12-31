"""
Views for Solar CRM Admin Interface
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, 
    UpdateView, DeleteView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
import csv

from apps.leads.models import Lead, LeadSource
from apps.customers.models import Customer
from apps.services.models import ServiceRequest, AMCContract, InstallationProject
from apps.analytics.models import AnalyticsMetric, ConversionFunnel, RevenueTracking, ServiceWorkload, PerformanceIndicator


class AdminRequiredMixin(LoginRequiredMixin):
    """Mixin to ensure user is authenticated and has admin access"""
    login_url = reverse_lazy('admin_interface:login')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        # Add role-based access control here if needed
        return super().dispatch(request, *args, **kwargs)


class DashboardView(AdminRequiredMixin, TemplateView):
    """Main admin dashboard with metrics and overview"""
    template_name = 'admin/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate date ranges
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        last_month_start = today.replace(day=1) - timedelta(days=1)
        last_month_start = last_month_start.replace(day=1)
        
        # Basic metrics
        context.update({
            'total_leads': Lead.objects.count(),
            'total_customers': Customer.objects.count(),
            'active_services': ServiceRequest.objects.filter(
                status__in=['open', 'in_progress']
            ).count(),
            'monthly_revenue': self.get_monthly_revenue(),
            
            # Recent activity
            'recent_leads': Lead.objects.select_related('source').order_by('-created_at')[:5],
            'recent_services': ServiceRequest.objects.select_related('customer').order_by('-created_at')[:5],
            
            # Conversion metrics
            'conversion_rate': self.get_conversion_rate(),
            'leads_this_month': Lead.objects.filter(created_at__gte=last_month_start).count(),
            'services_this_month': ServiceRequest.objects.filter(created_at__gte=last_month_start).count(),
        })
        
        return context
    
    def get_monthly_revenue(self):
        """Calculate monthly revenue from completed projects"""
        current_month = timezone.now().replace(day=1)
        revenue = InstallationProject.objects.filter(
            completion_date__gte=current_month,
            status='completed'
        ).aggregate(total=Sum('project_value'))['total'] or 0
        return revenue
    
    def get_conversion_rate(self):
        """Calculate lead to customer conversion rate"""
        total_leads = Lead.objects.count()
        converted_leads = Lead.objects.filter(converted_at__isnull=False).count()
        if total_leads > 0:
            return round((converted_leads / total_leads) * 100, 1)
        return 0


class LeadsListView(AdminRequiredMixin, ListView):
    """List view for leads management"""
    model = Lead
    template_name = 'admin/leads/list.html'
    context_object_name = 'leads'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Lead.objects.select_related('source').order_by('-created_at')
        
        # Apply filters
        status = self.request.GET.get('status')
        source = self.request.GET.get('source')
        search = self.request.GET.get('search')
        
        if status:
            queryset = queryset.filter(status=status)
        if source:
            queryset = queryset.filter(source_id=source)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'lead_sources': LeadSource.objects.all(),
            'status_choices': Lead.LEAD_STATUS_CHOICES,
            'current_filters': {
                'status': self.request.GET.get('status', ''),
                'source': self.request.GET.get('source', ''),
                'search': self.request.GET.get('search', ''),
            }
        })
        return context


class LeadDetailView(AdminRequiredMixin, DetailView):
    """Detail view for individual lead"""
    model = Lead
    template_name = 'admin/leads/detail.html'
    context_object_name = 'lead'
    
    def get_queryset(self):
        return Lead.objects.select_related('source')


class LeadCreateView(AdminRequiredMixin, CreateView):
    """Create new lead"""
    model = Lead
    template_name = 'admin/leads/form.html'
    fields = [
        'first_name', 'last_name', 'email', 'phone', 'source',
        'property_type', 'estimated_capacity', 'budget_range',
        'interest_level', 'status'
    ]
    success_url = reverse_lazy('admin_interface:leads')
    
    def form_valid(self, form):
        messages.success(self.request, 'Lead created successfully!')
        return super().form_valid(form)


class LeadUpdateView(AdminRequiredMixin, UpdateView):
    """Update existing lead"""
    model = Lead
    template_name = 'admin/leads/form.html'
    fields = [
        'first_name', 'last_name', 'email', 'phone', 'source',
        'property_type', 'estimated_capacity', 'budget_range',
        'interest_level', 'status'
    ]
    success_url = reverse_lazy('admin_interface:leads')
    
    def form_valid(self, form):
        messages.success(self.request, 'Lead updated successfully!')
        return super().form_valid(form)


class LeadConvertView(AdminRequiredMixin, View):
    """Convert lead to customer"""
    
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        
        if lead.converted_at:
            messages.warning(request, 'Lead has already been converted!')
            return redirect('admin_interface:lead_detail', pk=pk)
        
        # Create customer from lead
        customer = Customer.objects.create(
            lead=lead,
            # Copy basic information
            # Additional customer fields can be filled later
        )
        
        # Mark lead as converted
        lead.status = 'converted'
        lead.converted_at = timezone.now()
        lead.save()
        
        messages.success(request, f'Lead converted to customer successfully!')
        return redirect('admin_interface:customer_detail', pk=customer.pk)


class LeadDeleteView(AdminRequiredMixin, DeleteView):
    """Delete lead"""
    model = Lead
    template_name = 'admin/leads/delete.html'
    success_url = reverse_lazy('admin_interface:leads')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Lead deleted successfully!')
        return super().delete(request, *args, **kwargs)


class CustomersListView(AdminRequiredMixin, ListView):
    """List view for customers management"""
    model = Customer
    template_name = 'admin/customers/list.html'
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Customer.objects.select_related('lead').order_by('-created_at')
        
        # Apply filters
        status = self.request.GET.get('status')
        search = self.request.GET.get('search')
        
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                Q(lead__first_name__icontains=search) |
                Q(lead__last_name__icontains=search) |
                Q(lead__email__icontains=search) |
                Q(company_name__icontains=search)
            )
        
        return queryset


class CustomerDetailView(AdminRequiredMixin, DetailView):
    """Detail view for individual customer"""
    model = Customer
    template_name = 'admin/customers/detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        
        context.update({
            'service_requests': ServiceRequest.objects.filter(customer=customer).order_by('-created_at'),
            'installation_projects': InstallationProject.objects.filter(customer=customer).order_by('-created_at'),
            'amc_contracts': AMCContract.objects.filter(customer=customer).order_by('-created_at'),
        })
        
        return context


class CustomerCreateView(AdminRequiredMixin, CreateView):
    """Create new customer"""
    model = Customer
    template_name = 'admin/customers/form.html'
    fields = [
        'first_name', 'last_name', 'email', 'phone',
        'company_name', 'address', 'city', 'state', 'pincode',
        'customer_type', 'status'
    ]
    success_url = reverse_lazy('admin_interface:customers')
    
    def form_valid(self, form):
        messages.success(self.request, 'Customer created successfully!')
        return super().form_valid(form)


class CustomerUpdateView(AdminRequiredMixin, UpdateView):
    """Update existing customer"""
    model = Customer
    template_name = 'admin/customers/form.html'
    fields = [
        'first_name', 'last_name', 'email', 'phone',
        'company_name', 'address', 'city', 'state', 'pincode',
        'customer_type', 'status'
    ]
    success_url = reverse_lazy('admin_interface:customers')
    
    def form_valid(self, form):
        messages.success(self.request, 'Customer updated successfully!')
        return super().form_valid(form)


class CustomerDeleteView(AdminRequiredMixin, DeleteView):
    """Delete customer"""
    model = Customer
    template_name = 'admin/customers/delete.html'
    success_url = reverse_lazy('admin_interface:customers')


class ServiceRequestsListView(AdminRequiredMixin, ListView):
    """List view for service requests management"""
    model = ServiceRequest
    template_name = 'admin/services/list.html'
    context_object_name = 'service_requests'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ServiceRequest.objects.select_related('customer').order_by('-created_at')
        
        # Apply filters
        status = self.request.GET.get('status')
        priority = self.request.GET.get('priority')
        search = self.request.GET.get('search')
        
        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        if search:
            queryset = queryset.filter(
                Q(ticket_number__icontains=search) |
                Q(subject__icontains=search) |
                Q(customer__lead__first_name__icontains=search) |
                Q(customer__lead__last_name__icontains=search)
            )
        
        return queryset


class ServiceRequestDetailView(AdminRequiredMixin, DetailView):
    """Detail view for individual service request"""
    model = ServiceRequest
    template_name = 'admin/services/detail.html'
    context_object_name = 'service_request'


class ServiceRequestCreateView(AdminRequiredMixin, CreateView):
    """Create new service request"""
    model = ServiceRequest
    template_name = 'admin/services/form.html'
    fields = [
        'customer', 'request_type', 'priority', 'subject',
        'description', 'status', 'assigned_to'
    ]
    success_url = reverse_lazy('admin_interface:services')


class ServiceRequestUpdateView(AdminRequiredMixin, UpdateView):
    """Update existing service request"""
    model = ServiceRequest
    template_name = 'admin/services/form.html'
    fields = [
        'request_type', 'priority', 'subject', 'description',
        'status', 'assigned_to'
    ]
    success_url = reverse_lazy('admin_interface:services')


class ServiceRequestDeleteView(AdminRequiredMixin, DeleteView):
    """Delete service request"""
    model = ServiceRequest
    template_name = 'admin/services/delete.html'
    success_url = reverse_lazy('admin_interface:services')


class AnalyticsView(AdminRequiredMixin, TemplateView):
    """Analytics dashboard with charts and reports"""
    template_name = 'admin/analytics/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Performance metrics
        context.update({
            'lead_conversion_rate': self.get_conversion_rate(),
            'average_response_time': self.get_average_response_time(),
            'customer_satisfaction': self.get_customer_satisfaction(),
            'revenue_growth': self.get_revenue_growth(),
        })
        
        return context
    
    def get_conversion_rate(self):
        """Calculate lead conversion rate"""
        total_leads = Lead.objects.count()
        converted = Lead.objects.filter(converted_at__isnull=False).count()
        return round((converted / total_leads * 100), 1) if total_leads > 0 else 0
    
    def get_average_response_time(self):
        """Calculate average service response time"""
        # Placeholder - implement based on service request timestamps
        return "2.5 hours"
    
    def get_customer_satisfaction(self):
        """Calculate customer satisfaction score"""
        # Placeholder - implement based on feedback data
        return "4.2/5"
    
    def get_revenue_growth(self):
        """Calculate revenue growth percentage"""
        # Placeholder - implement based on project completion data
        return "+15%"


class ReportsView(AdminRequiredMixin, TemplateView):
    """Reports and detailed analytics"""
    template_name = 'admin/analytics/reports.html'


class DashboardMetricsAPIView(AdminRequiredMixin, View):
    """API endpoint for dashboard metrics (AJAX)"""
    
    def get(self, request):
        data = {
            'total_leads': Lead.objects.count(),
            'total_customers': Customer.objects.count(),
            'active_services': ServiceRequest.objects.filter(
                status__in=['open', 'in_progress']
            ).count(),
            'monthly_revenue': float(self.get_monthly_revenue()),
        }
        return JsonResponse(data)
    
    def get_monthly_revenue(self):
        """Calculate monthly revenue"""
        current_month = timezone.now().replace(day=1)
        revenue = InstallationProject.objects.filter(
            completion_date__gte=current_month,
            status='completed'
        ).aggregate(total=Sum('project_value'))['total'] or 0
        return revenue


class ChartDataAPIView(AdminRequiredMixin, View):
    """API endpoint for chart data (AJAX)"""
    
    def get(self, request, chart_type):
        if chart_type == 'leads_by_month':
            data = self.get_leads_by_month()
        elif chart_type == 'conversion_funnel':
            data = self.get_conversion_funnel()
        elif chart_type == 'service_status':
            data = self.get_service_status()
        else:
            data = {'error': 'Invalid chart type'}
        
        return JsonResponse(data)
    
    def get_leads_by_month(self):
        """Get leads data by month for chart"""
        # Placeholder implementation
        return {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'data': [12, 19, 8, 15, 22, 18]
        }
    
    def get_conversion_funnel(self):
        """Get conversion funnel data"""
        return {
            'labels': ['Leads', 'Qualified', 'Quoted', 'Converted'],
            'data': [100, 75, 45, 25]
        }
    
    def get_service_status(self):
        """Get service request status distribution"""
        return {
            'labels': ['Open', 'In Progress', 'Resolved', 'Closed'],
            'data': [15, 8, 12, 25]
        }


# Export Views
class ExportLeadsView(AdminRequiredMixin, View):
    """Export leads to CSV"""
    
    def get(self, request):
        # Create the HttpResponse object with CSV header
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="leads_export.csv"'
        
        writer = csv.writer(response)
        
        # Write CSV header
        writer.writerow([
            'ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Source',
            'Status', 'Interest Level', 'Property Type', 'Estimated Capacity (kW)',
            'Budget Range', 'Score', 'Priority Level', 'Address', 'City', 'State',
            'Pincode', 'Assigned To', 'Created At', 'Last Contacted', 'Notes'
        ])
        
        # Get filtered leads based on request parameters
        leads = Lead.objects.select_related('source', 'assigned_to').all()
        
        # Apply filters if provided
        status = request.GET.get('status')
        source = request.GET.get('source')
        if status:
            leads = leads.filter(status=status)
        if source:
            leads = leads.filter(source_id=source)
        
        # Write data rows
        for lead in leads:
            writer.writerow([
                lead.id,
                lead.first_name,
                lead.last_name,
                lead.email,
                lead.phone,
                lead.source.name,
                lead.get_status_display(),
                lead.get_interest_level_display(),
                lead.get_property_type_display(),
                lead.estimated_capacity or '',
                lead.get_budget_range_display(),
                lead.score,
                lead.get_priority_level_display(),
                lead.address,
                lead.city,
                lead.state,
                lead.pincode,
                lead.assigned_to.get_full_name() if lead.assigned_to else '',
                lead.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                lead.last_contacted_at.strftime('%Y-%m-%d %H:%M:%S') if lead.last_contacted_at else '',
                lead.notes
            ])
        
        return response


class ExportCustomersView(AdminRequiredMixin, View):
    """Export customers to CSV"""
    
    def get(self, request):
        # Create the HttpResponse object with CSV header
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="customers_export.csv"'
        
        writer = csv.writer(response)
        
        # Write CSV header
        writer.writerow([
            'ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Company Name',
            'Customer Type', 'Status', 'Address', 'City', 'State', 'Pincode',
            'Lead Source', 'Created At', 'Total Projects', 'Total Revenue'
        ])
        
        # Get filtered customers
        customers = Customer.objects.select_related('lead__source').prefetch_related('service_requests').all()
        
        # Apply filters if provided
        status = request.GET.get('status')
        customer_type = request.GET.get('customer_type')
        if status:
            customers = customers.filter(status=status)
        if customer_type:
            customers = customers.filter(customer_type=customer_type)
        
        # Write data rows
        for customer in customers:
            # Calculate total projects and revenue
            service_requests = customer.service_requests.all()
            total_projects = service_requests.count()
            total_revenue = sum(sr.total_amount or 0 for sr in service_requests)
            
            writer.writerow([
                customer.id,
                customer.first_name,
                customer.last_name,
                customer.email,
                customer.phone,
                customer.company_name or '',
                customer.get_customer_type_display(),
                customer.get_status_display(),
                customer.address,
                customer.city,
                customer.state,
                customer.pincode,
                customer.lead.source.name if customer.lead and customer.lead.source else 'Direct',
                customer.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                total_projects,
                f"₹{total_revenue:,.2f}"
            ])
        
        return response


class ExportServiceRequestsView(AdminRequiredMixin, View):
    """Export service requests to CSV"""
    
    def get(self, request):
        # Create the HttpResponse object with CSV header
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="service_requests_export.csv"'
        
        writer = csv.writer(response)
        
        # Write CSV header
        writer.writerow([
            'ID', 'Customer Name', 'Customer Email', 'Service Type', 'Status',
            'Priority', 'Description', 'Estimated Cost', 'Total Amount',
            'Installation Date', 'Completion Date', 'Assigned To',
            'Created At', 'Updated At'
        ])
        
        # Get filtered service requests
        service_requests = ServiceRequest.objects.select_related(
            'customer', 'assigned_to'
        ).all()
        
        # Apply filters if provided
        status = request.GET.get('status')
        service_type = request.GET.get('service_type')
        if status:
            service_requests = service_requests.filter(status=status)
        if service_type:
            service_requests = service_requests.filter(service_type=service_type)
        
        # Write data rows
        for sr in service_requests:
            writer.writerow([
                sr.id,
                sr.customer.full_name,
                sr.customer.email,
                sr.get_service_type_display(),
                sr.get_status_display(),
                sr.get_priority_display(),
                sr.description,
                f"₹{sr.estimated_cost:,.2f}" if sr.estimated_cost else '',
                f"₹{sr.total_amount:,.2f}" if sr.total_amount else '',
                sr.installation_date.strftime('%Y-%m-%d') if sr.installation_date else '',
                sr.completion_date.strftime('%Y-%m-%d') if sr.completion_date else '',
                sr.assigned_to.get_full_name() if sr.assigned_to else '',
                sr.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                sr.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response