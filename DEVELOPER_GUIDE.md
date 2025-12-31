# Solar CRM Platform - Developer Guide

This guide explains where and how to make changes to the Solar CRM Platform, covering both frontend and backend modifications.

## 📋 Table of Contents

1. [Quick Reference](#quick-reference)
2. [Frontend Changes](#frontend-changes)
3. [Backend Changes](#backend-changes)
4. [Database Changes](#database-changes)
5. [API Changes](#api-changes)
6. [Integration Changes](#integration-changes)
7. [Deployment Changes](#deployment-changes)
8. [Testing Changes](#testing-changes)

---

## 🚀 Quick Reference


| What to Change | File Location | Type |
|----------------|---------------|------|
| Website content | `frontend/*.html` | HTML |
| Website styling | `frontend/styles.css` | CSS |
| Chatbot behavior | `frontend/chat.js` | JavaScript |
| Form handling | `frontend/sendemail.js` | JavaScript |
| Admin interface | `backend/templates/admin/` | HTML/Django |
| Database models | `backend/apps/*/models.py` | Python |
| API endpoints | `backend/apps/*/views.py` | Python |
| URL routing | `backend/apps/*/urls.py` | Python |
| Business logic | `backend/apps/*/services.py` | Python |
| Settings | `backend/solar_crm/settings/` | Python |

### Development Workflow

```bash
# 1. Make changes to code
# 2. Test locally
cd backend
python manage.py runserver 8000

# 3. Run tests
python manage.py test

# 4. Collect static files (if needed)
python manage.py collectstatic

# 5. Apply database migrations (if needed)
python manage.py makemigrations
python manage.py migrate

# 6. Commit changes
git add .
git commit -m "Description of changes"
git push
```

---

## 🌐 Frontend Changes

### 1. Website Content Changes

#### Updating Text Content
**File:** `frontend/Index.html`, `frontend/About.html`, etc.

```html
<!-- Example: Changing hero section text -->
<section class="hero">
  <div class="hero-content">
    <h1>With Sunrise Power, your home leads the change.</h1>
    <p>To make power smarter, greener, more affordable, more convenient, and more friendly.</p>
    <!-- Change text above as needed -->
  </div>
</section>
```

#### Adding New Pages
1. **Create new HTML file** in `frontend/` directory
2. **Copy structure** from existing page
3. **Update navigation** in all HTML files
4. **Add to Django URL routing** (see backend section)

```html
<!-- Add to navigation in all HTML files -->
<ul class="nav-links">
  <li><a href="index.html">Home</a></li>
  <li><a href="about.html">About Us</a></li>
  <li><a href="services.html">Services</a></li>
  <li><a href="projects.html">Projects</a></li>
  <li><a href="products.html">Products</a></li>
  <li><a href="new-page.html">New Page</a></li> <!-- Add this -->
</ul>
```

### 2. Styling Changes

#### Main Stylesheet
**File:** `frontend/styles.css`

```css
/* Example: Changing primary color */
:root {
  --primary-color: #fdd835;    /* Change this */
  --secondary-color: #3D2B1F;
  --accent-color: #f7931e;
}

/* Example: Updating hero section */
.hero {
  background-image: linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0.3)), 
                    url('Assets/Home Page.png'); /* Change background image */
}

/* Example: Adding new component styles */
.new-component {
  background: var(--primary-color);
  padding: 20px;
  border-radius: 10px;
  margin: 20px 0;
}
```

#### Chatbot Styling
**File:** `frontend/chat.css`

```css
/* Example: Changing chatbot colors */
.chat-modal {
  background: #ffffff;         /* Change modal background */
}

.chat-header {
  background: var(--primary-color); /* Change header color */
}

.message.bot {
  background: #f0f0f0;         /* Change bot message background */
}
```

### 3. JavaScript Functionality Changes

#### Chatbot Modifications
**File:** `frontend/chat.js`

```javascript
// Example: Changing chatbot configuration
class ChatBot {
    constructor() {
        this.config = {
            apiKey: "",
            apiUrl: "https://api.cohere.ai/v2/chat",
            model: "command-a-03-2025",
            
            // Modify system prompt
            systemPrompt: `You are a helpful solar energy assistant for Sunrise Power.
            
            Updated instructions:
            - Focus on solar panel benefits
            - Provide technical specifications
            - Guide users to contact forms
            
            Response style:
            - Professional and knowledgeable
            - Include relevant solar facts
            - Suggest next steps`,
            
            // Modify welcome message
            welcomeMessage: {
                title: "👋 Welcome to Sunrise Power!",
                message: "Hi! I'm your solar energy consultant. How can I help you save money with solar today?",
                autoSend: true
            }
        };
    }
}
```

#### Form Handling Changes
**File:** `frontend/sendemail.js`

```javascript
// Example: Adding new form fields
document.getElementById("service-form").addEventListener("submit", function(event) {
  event.preventDefault();
  
  const form = document.getElementById("service-form");
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());
  
  // Add custom processing
  data.custom_field = processCustomData(data);
  data.priority = determinePriority(data.service);
  
  // Send to CRM
  sendFormDataToCRM(data);
  
  // Send via EmailJS
  emailjs.sendForm("service_tyc0213", "template_32q43sm", form, "Prx0yDnr-5MlTe-vB");
});

// Add custom processing functions
function processCustomData(data) {
  // Custom logic here
  return processedData;
}

function determinePriority(serviceType) {
  const highPriorityServices = ['emergency', 'maintenance'];
  return highPriorityServices.includes(serviceType) ? 'high' : 'normal';
}
```
#### Solar Calculator Changes
**File:** `frontend/Index.html` (Calculator section)

```javascript
// Example: Modifying calculation logic
class SolarCalculator {
    calculateSavings() {
        const monthlyBill = parseFloat(document.getElementById('monthly-bill').value);
        const propertyType = document.getElementById('property-type').value;
        const roofArea = parseFloat(document.getElementById('roof-area').value);
        const location = document.getElementById('location').value;
        
        // Updated calculation logic
        const annualBill = monthlyBill * 12;
        const unitsPerMonth = monthlyBill / 8; // Update rate if needed
        const annualUnits = unitsPerMonth * 12;
        
        // Improved system sizing based on location
        const locationMultiplier = this.getLocationMultiplier(location);
        const systemCapacity = Math.round((annualUnits / (1500 * locationMultiplier)) * 10) / 10;
        
        // Updated cost estimation
        const costPerKW = this.getCostPerKW(propertyType);
        const systemCost = Math.round(systemCapacity * costPerKW);
        
        // Enhanced savings calculation
        const savingsPercentage = this.getSavingsPercentage(propertyType);
        const annualSavings = Math.round(annualBill * savingsPercentage);
        
        this.calculationResults = {
            system_capacity_kw: systemCapacity,
            total_system_cost: systemCost,
            annual_savings: annualSavings,
            payback_period_years: Math.round((systemCost / annualSavings) * 10) / 10,
            monthly_bill: monthlyBill,
            annual_units: annualUnits
        };
        
        this.displayResults();
    }
    
    // Add helper methods
    getLocationMultiplier(location) {
        const locationMultipliers = {
            'mumbai': 1.1,
            'pune': 1.2,
            'nanded': 1.3,
            'default': 1.0
        };
        
        const key = location.toLowerCase();
        return locationMultipliers[key] || locationMultipliers['default'];
    }
    
    getCostPerKW(propertyType) {
        const costs = {
            'residential': 60000,
            'commercial': 55000,
            'industrial': 50000
        };
        return costs[propertyType] || costs['residential'];
    }
    
    getSavingsPercentage(propertyType) {
        const percentages = {
            'residential': 0.8,
            'commercial': 0.85,
            'industrial': 0.9
        };
        return percentages[propertyType] || percentages['residential'];
    }
}
```

### 4. Adding New Frontend Features

#### Adding a New Form
1. **Create HTML form** in appropriate page
2. **Add styling** in `styles.css`
3. **Add JavaScript handler** in separate file or inline
4. **Connect to backend** via API call

```html
<!-- Example: New consultation form -->
<form id="consultation-form" class="consultation-form">
    <h3>Free Solar Consultation</h3>
    
    <div class="form-group">
        <label for="consultation-name">Full Name</label>
        <input type="text" id="consultation-name" name="name" required>
    </div>
    
    <div class="form-group">
        <label for="consultation-email">Email</label>
        <input type="email" id="consultation-email" name="email" required>
    </div>
    
    <div class="form-group">
        <label for="consultation-phone">Phone</label>
        <input type="tel" id="consultation-phone" name="phone" required>
    </div>
    
    <div class="form-group">
        <label for="preferred-time">Preferred Consultation Time</label>
        <select id="preferred-time" name="preferred_time">
            <option value="morning">Morning (9 AM - 12 PM)</option>
            <option value="afternoon">Afternoon (12 PM - 5 PM)</option>
            <option value="evening">Evening (5 PM - 8 PM)</option>
        </select>
    </div>
    
    <button type="submit">Schedule Consultation</button>
</form>

<script>
document.getElementById('consultation-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    
    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());
    
    try {
        const response = await fetch('/api/integrations/webhooks/consultation/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                form_type: 'consultation_request',
                ...data,
                timestamp: new Date().toISOString()
            })
        });
        
        if (response.ok) {
            alert('Consultation scheduled successfully! We will contact you soon.');
            this.reset();
        } else {
            throw new Error('Failed to schedule consultation');
        }
    } catch (error) {
        alert('Error scheduling consultation. Please try again or call us directly.');
        console.error('Consultation form error:', error);
    }
});
</script>
```

---

## ⚙️ Backend Changes

### 1. Database Model Changes

#### Adding New Fields to Existing Models
**File:** `backend/apps/leads/models.py`

```python
class Lead(models.Model):
    # Existing fields...
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    
    # Add new fields
    preferred_contact_time = models.CharField(
        max_length=20,
        choices=[
            ('morning', 'Morning (9 AM - 12 PM)'),
            ('afternoon', 'Afternoon (12 PM - 5 PM)'),
            ('evening', 'Evening (5 PM - 8 PM)'),
        ],
        blank=True
    )
    
    consultation_scheduled = models.BooleanField(default=False)
    consultation_date = models.DateTimeField(null=True, blank=True)
    
    # Add custom methods
    def schedule_consultation(self, date_time):
        self.consultation_scheduled = True
        self.consultation_date = date_time
        self.save()
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    class Meta:
        db_table = 'leads'
        ordering = ['-created_at']
```
#### Creating New Models
**File:** `backend/apps/services/models.py`

```python
# Example: Adding a new Consultation model
class Consultation(models.Model):
    CONSULTATION_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    CONSULTATION_TYPE_CHOICES = [
        ('initial', 'Initial Consultation'),
        ('technical', 'Technical Assessment'),
        ('financial', 'Financial Planning'),
        ('follow_up', 'Follow-up Meeting'),
    ]
    
    # Basic Information
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='consultations')
    lead = models.ForeignKey('leads.Lead', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Consultation Details
    consultation_type = models.CharField(max_length=20, choices=CONSULTATION_TYPE_CHOICES, default='initial')
    status = models.CharField(max_length=20, choices=CONSULTATION_STATUS_CHOICES, default='scheduled')
    
    # Scheduling
    scheduled_date = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    location = models.CharField(max_length=200, blank=True)  # 'online', 'customer_site', 'office'
    
    # Assignment
    assigned_consultant = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Notes and Outcomes
    preparation_notes = models.TextField(blank=True)
    consultation_notes = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Consultation - {self.customer.get_full_name()} - {self.scheduled_date.strftime('%Y-%m-%d')}"
    
    def is_upcoming(self):
        return self.scheduled_date > timezone.now() and self.status == 'scheduled'
    
    def mark_completed(self, notes="", outcome=""):
        self.status = 'completed'
        if notes:
            self.consultation_notes = notes
        if outcome:
            self.outcome = outcome
        self.save()
    
    class Meta:
        db_table = 'consultations'
        ordering = ['-scheduled_date']
```

#### Applying Database Changes
```bash
# After making model changes
cd backend

# Create migration files
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# If you need to add data to new fields
python manage.py shell
>>> from apps.leads.models import Lead
>>> Lead.objects.filter(preferred_contact_time='').update(preferred_contact_time='morning')
```

### 2. API Endpoint Changes

#### Adding New API Endpoints
**File:** `backend/apps/services/views.py`

```python
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Consultation
from .serializers import ConsultationSerializer

class ConsultationViewSet(viewsets.ModelViewSet):
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(
                scheduled_date__date__range=[start_date, end_date]
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark consultation as completed"""
        consultation = self.get_object()
        notes = request.data.get('notes', '')
        outcome = request.data.get('outcome', '')
        
        consultation.mark_completed(notes=notes, outcome=outcome)
        
        return Response({
            'message': 'Consultation marked as completed',
            'consultation_id': consultation.id
        })
    
    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        """Reschedule consultation"""
        consultation = self.get_object()
        new_date = request.data.get('new_date')
        
        if not new_date:
            return Response(
                {'error': 'new_date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        consultation.scheduled_date = new_date
        consultation.status = 'rescheduled'
        consultation.save()
        
        return Response({
            'message': 'Consultation rescheduled successfully',
            'new_date': new_date
        })
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming consultations"""
        upcoming_consultations = self.get_queryset().filter(
            scheduled_date__gt=timezone.now(),
            status='scheduled'
        )
        
        serializer = self.get_serializer(upcoming_consultations, many=True)
        return Response(serializer.data)
```
#### Creating Serializers
**File:** `backend/apps/services/serializers.py`

```python
from rest_framework import serializers
from .models import Consultation

class ConsultationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    consultant_name = serializers.CharField(source='assigned_consultant.get_full_name', read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Consultation
        fields = [
            'id', 'customer', 'customer_name', 'lead',
            'consultation_type', 'status', 'scheduled_date',
            'duration_minutes', 'location', 'assigned_consultant',
            'consultant_name', 'preparation_notes', 'consultation_notes',
            'outcome', 'follow_up_required', 'follow_up_date',
            'is_upcoming', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_scheduled_date(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Scheduled date must be in the future")
        return value
```

#### Updating URL Configuration
**File:** `backend/apps/services/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'requests', views.ServiceRequestViewSet)
router.register(r'projects', views.InstallationProjectViewSet)
router.register(r'amc', views.AMCContractViewSet)
router.register(r'consultations', views.ConsultationViewSet)  # Add this

urlpatterns = [
    path('', include(router.urls)),
    
    # Custom endpoints
    path('dashboard/', views.ServiceDashboardView.as_view(), name='service_dashboard'),
    path('reports/', views.ServiceReportsView.as_view(), name='service_reports'),
]
```

### 3. Admin Interface Changes

#### Updating Admin Templates
**File:** `backend/templates/admin/dashboard.html`

```html
<!-- Add new consultation metrics -->
<div class="metrics-grid">
    <!-- Existing metrics -->
    <div class="metric-card">
        <h3>Total Leads</h3>
        <div class="metric-value">{{ total_leads }}</div>
    </div>
    
    <!-- Add new consultation metrics -->
    <div class="metric-card">
        <h3>Scheduled Consultations</h3>
        <div class="metric-value">{{ scheduled_consultations }}</div>
        <div class="metric-change">{{ consultation_change }}% from last month</div>
    </div>
    
    <div class="metric-card">
        <h3>Consultation Conversion Rate</h3>
        <div class="metric-value">{{ consultation_conversion_rate }}%</div>
    </div>
</div>

<!-- Add consultation calendar -->
<div class="dashboard-section">
    <h2>Upcoming Consultations</h2>
    <div class="consultation-calendar">
        {% for consultation in upcoming_consultations %}
        <div class="consultation-item">
            <div class="consultation-time">
                {{ consultation.scheduled_date|date:"M d, Y H:i" }}
            </div>
            <div class="consultation-details">
                <strong>{{ consultation.customer.get_full_name }}</strong>
                <span class="consultation-type">{{ consultation.get_consultation_type_display }}</span>
            </div>
            <div class="consultation-consultant">
                {{ consultation.assigned_consultant.get_full_name }}
            </div>
        </div>
        {% endfor %}
    </div>
</div>
```

#### Adding New Admin Views
**File:** `backend/apps/admin_interface/views.py`

```python
class ConsultationListView(AdminRequiredMixin, ListView):
    """List view for consultations management"""
    model = Consultation
    template_name = 'admin/consultations/list.html'
    context_object_name = 'consultations'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Consultation.objects.select_related(
            'customer', 'assigned_consultant'
        ).order_by('-scheduled_date')
        
        # Apply filters
        status = self.request.GET.get('status')
        consultant = self.request.GET.get('consultant')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if status:
            queryset = queryset.filter(status=status)
        if consultant:
            queryset = queryset.filter(assigned_consultant_id=consultant)
        if date_from:
            queryset = queryset.filter(scheduled_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(scheduled_date__date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'consultants': User.objects.filter(role__in=['consultant', 'admin']),
            'status_choices': Consultation.CONSULTATION_STATUS_CHOICES,
            'current_filters': {
                'status': self.request.GET.get('status', ''),
                'consultant': self.request.GET.get('consultant', ''),
                'date_from': self.request.GET.get('date_from', ''),
                'date_to': self.request.GET.get('date_to', ''),
            }
        })
        return context

class ConsultationCreateView(AdminRequiredMixin, CreateView):
    """Create new consultation"""
    model = Consultation
    template_name = 'admin/consultations/form.html'
    fields = [
        'customer', 'consultation_type', 'scheduled_date',
        'duration_minutes', 'location', 'assigned_consultant',
        'preparation_notes'
    ]
    success_url = reverse_lazy('admin_interface:consultations')
    
    def form_valid(self, form):
        messages.success(self.request, 'Consultation scheduled successfully!')
        return super().form_valid(form)
```

---

## 🗄️ Database Changes

### 1. Schema Migrations

#### Creating Migrations
```bash
# After making model changes
cd backend

# Create migration for specific app
python manage.py makemigrations leads

# Create migration for all apps
python manage.py makemigrations

# Name your migration
python manage.py makemigrations --name add_consultation_fields leads

# Check migration SQL (before applying)
python manage.py sqlmigrate leads 0002
```

#### Custom Migrations
**File:** `backend/apps/leads/migrations/0003_add_consultation_fields.py`

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('leads', '0002_initial_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='preferred_contact_time',
            field=models.CharField(
                blank=True,
                choices=[
                    ('morning', 'Morning (9 AM - 12 PM)'),
                    ('afternoon', 'Afternoon (12 PM - 5 PM)'),
                    ('evening', 'Evening (5 PM - 8 PM)')
                ],
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='lead',
            name='consultation_scheduled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='lead',
            name='consultation_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
```
### 2. Integration Changes

#### Adding New Webhook Endpoints
**File:** `backend/apps/integrations/views.py`

```python
@csrf_exempt
@require_http_methods(["POST"])
def consultation_webhook(request):
    """
    Webhook endpoint for consultation requests from frontend.
    """
    try:
        data = json.loads(request.body)
        
        # Log the consultation request
        logger.info(f"Received consultation request: {data}")
        
        # Enqueue task to process consultation request
        task_id = TaskManager.enqueue_task(
            task_name='process_consultation_request',
            kwargs={'consultation_data': data},
            priority=2  # High priority for consultation requests
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Consultation request received and queued for processing',
            'task_id': task_id
        })
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in consultation request")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error processing consultation request: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

# Register consultation processing task
@TaskRegistry.register('process_consultation_request')
def process_consultation_request(consultation_data):
    """
    Process consultation request and create consultation record.
    """
    logger.info(f"Processing consultation request: {consultation_data}")
    
    try:
        from apps.leads.models import Lead, LeadSource
        from apps.customers.models import Customer
        from apps.services.models import Consultation
        
        # Extract data
        name = consultation_data.get('name', '')
        email = consultation_data.get('email', '')
        phone = consultation_data.get('phone', '')
        preferred_time = consultation_data.get('preferred_time', 'morning')
        
        # Find or create lead
        lead = None
        if email:
            lead = Lead.objects.filter(email=email).first()
        
        if not lead and (email or phone):
            # Create new lead
            consultation_source, _ = LeadSource.objects.get_or_create(
                name='Consultation Request',
                defaults={'description': 'Lead from consultation request form'}
            )
            
            name_parts = name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            lead = Lead.objects.create(
                source=consultation_source,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                interest_level='high',  # Consultation requests indicate high interest
                preferred_contact_time=preferred_time,
                original_data=consultation_data
            )
        
        # Schedule consultation if lead exists
        if lead:
            # Calculate consultation date based on preferred time
            consultation_date = calculate_next_available_slot(preferred_time)
            
            # Create consultation record
            consultation = Consultation.objects.create(
                lead=lead,
                consultation_type='initial',
                scheduled_date=consultation_date,
                location='to_be_determined',
                preparation_notes=f"Consultation requested via website. Preferred time: {preferred_time}"
            )
            
            # Update lead
            lead.schedule_consultation(consultation_date)
            
            logger.info(f"Created consultation {consultation.id} for lead {lead.id}")
            
            return {
                'processed': True,
                'lead_id': lead.id,
                'consultation_id': consultation.id,
                'scheduled_date': consultation_date.isoformat()
            }
        
        return {'processed': False, 'error': 'Insufficient contact information'}
        
    except Exception as e:
        logger.error(f"Error processing consultation request: {str(e)}")
        return {'processed': False, 'error': str(e)}

def calculate_next_available_slot(preferred_time):
    """Calculate next available consultation slot based on preferred time."""
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    
    # Time slots based on preference
    time_slots = {
        'morning': 10,    # 10 AM
        'afternoon': 14,  # 2 PM
        'evening': 17     # 5 PM
    }
    
    preferred_hour = time_slots.get(preferred_time, 10)
    
    # Find next available weekday
    next_date = now + timedelta(days=1)
    while next_date.weekday() >= 5:  # Skip weekends
        next_date += timedelta(days=1)
    
    # Set to preferred time
    consultation_datetime = next_date.replace(
        hour=preferred_hour,
        minute=0,
        second=0,
        microsecond=0
    )
    
    return consultation_datetime
```

---

## 🧪 Testing Changes

### 1. Writing Tests

#### Model Tests
**File:** `backend/apps/services/tests/test_models.py`

```python
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.services.models import Consultation
from apps.customers.models import Customer
from apps.leads.models import Lead, LeadSource
from apps.users.models import User

class ConsultationModelTest(TestCase):
    def setUp(self):
        # Create test data
        self.lead_source = LeadSource.objects.create(
            name='Test Source',
            description='Test lead source'
        )
        
        self.lead = Lead.objects.create(
            source=self.lead_source,
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='1234567890'
        )
        
        self.customer = Customer.objects.create(
            lead=self.lead,
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='1234567890'
        )
        
        self.consultant = User.objects.create_user(
            username='consultant',
            email='consultant@example.com',
            role='consultant'
        )
    
    def test_consultation_creation(self):
        """Test consultation model creation"""
        future_date = timezone.now() + timedelta(days=1)
        
        consultation = Consultation.objects.create(
            customer=self.customer,
            lead=self.lead,
            consultation_type='initial',
            scheduled_date=future_date,
            assigned_consultant=self.consultant
        )
        
        self.assertEqual(consultation.customer, self.customer)
        self.assertEqual(consultation.lead, self.lead)
        self.assertEqual(consultation.consultation_type, 'initial')
        self.assertEqual(consultation.status, 'scheduled')  # Default status
        self.assertTrue(consultation.is_upcoming())
    
    def test_consultation_completion(self):
        """Test marking consultation as completed"""
        future_date = timezone.now() + timedelta(days=1)
        
        consultation = Consultation.objects.create(
            customer=self.customer,
            scheduled_date=future_date,
            assigned_consultant=self.consultant
        )
        
        notes = "Customer interested in 5kW system"
        outcome = "Quote to be prepared"
        
        consultation.mark_completed(notes=notes, outcome=outcome)
        
        self.assertEqual(consultation.status, 'completed')
        self.assertEqual(consultation.consultation_notes, notes)
        self.assertEqual(consultation.outcome, outcome)
    
    def test_consultation_str_representation(self):
        """Test string representation of consultation"""
        future_date = timezone.now() + timedelta(days=1)
        
        consultation = Consultation.objects.create(
            customer=self.customer,
            scheduled_date=future_date
        )
        
        expected_str = f"Consultation - John Doe - {future_date.strftime('%Y-%m-%d')}"
        self.assertEqual(str(consultation), expected_str)
```

#### API Tests
**File:** `backend/apps/services/tests/test_views.py`

```python
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.services.models import Consultation
from apps.customers.models import Customer
from apps.leads.models import Lead, LeadSource

User = get_user_model()

class ConsultationAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='admin'
        )
        
        # Create test data
        self.lead_source = LeadSource.objects.create(name='Test Source')
        self.lead = Lead.objects.create(
            source=self.lead_source,
            first_name='John',
            last_name='Doe',
            email='john@example.com'
        )
        self.customer = Customer.objects.create(
            lead=self.lead,
            first_name='John',
            last_name='Doe',
            email='john@example.com'
        )
        
        # Authenticate client
        self.client.force_authenticate(user=self.user)
    
    def test_create_consultation(self):
        """Test creating a consultation via API"""
        url = reverse('consultation-list')
        data = {
            'customer': self.customer.id,
            'consultation_type': 'initial',
            'scheduled_date': '2025-02-01T10:00:00Z',
            'duration_minutes': 60,
            'location': 'customer_site'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Consultation.objects.count(), 1)
        
        consultation = Consultation.objects.first()
        self.assertEqual(consultation.customer, self.customer)
        self.assertEqual(consultation.consultation_type, 'initial')
    
    def test_list_consultations(self):
        """Test listing consultations"""
        # Create test consultations
        Consultation.objects.create(
            customer=self.customer,
            scheduled_date='2025-02-01T10:00:00Z'
        )
        Consultation.objects.create(
            customer=self.customer,
            scheduled_date='2025-02-02T14:00:00Z'
        )
        
        url = reverse('consultation-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_complete_consultation(self):
        """Test marking consultation as completed"""
        consultation = Consultation.objects.create(
            customer=self.customer,
            scheduled_date='2025-02-01T10:00:00Z'
        )
        
        url = reverse('consultation-complete', kwargs={'pk': consultation.id})
        data = {
            'notes': 'Customer interested in solar',
            'outcome': 'Quote requested'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        consultation.refresh_from_db()
        self.assertEqual(consultation.status, 'completed')
        self.assertEqual(consultation.consultation_notes, 'Customer interested in solar')
        self.assertEqual(consultation.outcome, 'Quote requested')
```

#### Integration Tests
**File:** `backend/apps/integrations/tests/test_webhooks.py`

```python
from django.test import TestCase, Client
from django.urls import reverse
import json
from apps.leads.models import Lead, LeadSource
from apps.services.models import Consultation

class ConsultationWebhookTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse('integrations:consultation_webhook')
    
    def test_consultation_webhook_creates_lead(self):
        """Test that consultation webhook creates a lead"""
        data = {
            'form_type': 'consultation_request',
            'name': 'Jane Smith',
            'email': 'jane@example.com',
            'phone': '9876543210',
            'preferred_time': 'afternoon',
            'timestamp': '2025-01-01T12:00:00Z'
        }
        
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that lead was created
        self.assertEqual(Lead.objects.count(), 1)
        
        lead = Lead.objects.first()
        self.assertEqual(lead.first_name, 'Jane')
        self.assertEqual(lead.last_name, 'Smith')
        self.assertEqual(lead.email, 'jane@example.com')
        self.assertEqual(lead.phone, '9876543210')
        self.assertEqual(lead.preferred_contact_time, 'afternoon')
        self.assertEqual(lead.interest_level, 'high')
    
    def test_consultation_webhook_invalid_json(self):
        """Test webhook with invalid JSON"""
        response = self.client.post(
            self.webhook_url,
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)
```

### 2. Running Tests

```bash
# Run all tests
cd backend
python manage.py test

# Run tests for specific app
python manage.py test apps.services

# Run specific test class
python manage.py test apps.services.tests.test_models.ConsultationModelTest

# Run specific test method
python manage.py test apps.services.tests.test_models.ConsultationModelTest.test_consultation_creation

# Run tests with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

### 3. Test Configuration

#### Test Settings
**File:** `backend/solar_crm/settings/test.py`

```python
from .base import *

# Test database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Test-specific settings
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',  # Faster for tests
]

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
```

---

## 🚀 Deployment Changes

### 1. Environment Configuration

#### Production Settings Updates
**File:** `backend/solar_crm/settings/production.py`

```python
# Add new environment variables
CONSULTATION_BOOKING_ENABLED = os.environ.get('CONSULTATION_BOOKING_ENABLED', 'True').lower() == 'true'
DEFAULT_CONSULTATION_DURATION = int(os.environ.get('DEFAULT_CONSULTATION_DURATION', '60'))
CONSULTATION_BUFFER_HOURS = int(os.environ.get('CONSULTATION_BUFFER_HOURS', '24'))

# Email settings for consultation notifications
CONSULTATION_EMAIL_TEMPLATE = os.environ.get('CONSULTATION_EMAIL_TEMPLATE', 'consultation_confirmation')
CONSULTATION_FROM_EMAIL = os.environ.get('CONSULTATION_FROM_EMAIL', DEFAULT_FROM_EMAIL)

# Calendar integration (if needed)
GOOGLE_CALENDAR_ENABLED = os.environ.get('GOOGLE_CALENDAR_ENABLED', 'False').lower() == 'true'
GOOGLE_CALENDAR_CREDENTIALS = os.environ.get('GOOGLE_CALENDAR_CREDENTIALS', '')
```

#### Environment Variables
**File:** `backend/.env.example`

```env
# Existing variables...

# Consultation Settings
CONSULTATION_BOOKING_ENABLED=True
DEFAULT_CONSULTATION_DURATION=60
CONSULTATION_BUFFER_HOURS=24
CONSULTATION_EMAIL_TEMPLATE=consultation_confirmation
CONSULTATION_FROM_EMAIL=consultations@sunrisepower.com

# Calendar Integration
GOOGLE_CALENDAR_ENABLED=False
GOOGLE_CALENDAR_CREDENTIALS=path/to/credentials.json
```

### 2. Static Files and Media

#### Collecting Static Files
```bash
# After making frontend changes
cd backend
python manage.py collectstatic --noinput

# For production deployment
python manage.py collectstatic --noinput --clear
```

#### Media Files Configuration
**File:** `backend/solar_crm/settings/production.py`

```python
# Media files for consultation documents
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Allowed file types for consultation documents
ALLOWED_CONSULTATION_FILE_TYPES = [
    'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'
]
```

---

**🎉 This comprehensive developer guide provides everything you need to modify and extend the Solar CRM Platform!**

The guide covers all aspects of development from simple content changes to complex feature additions, ensuring developers can efficiently work with both the frontend website and backend CRM system.