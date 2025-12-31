# Solar CRM Platform - Complete Architecture Guide

This comprehensive guide explains how the entire Solar CRM Platform works, covering both frontend and backend architecture, data flow, and integration points.

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Frontend Architecture](#frontend-architecture)
3. [Backend Architecture](#backend-architecture)
4. [Data Flow & Integration](#data-flow--integration)
5. [Database Schema](#database-schema)
6. [API Architecture](#api-architecture)
7. [Security & Authentication](#security--authentication)
8. [Deployment Architecture](#deployment-architecture)

---

## 🏗️ System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SOLAR CRM PLATFORM                      │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Static Website)     │  Backend (Django CRM)      │
│  ├── HTML/CSS/JavaScript       │  ├── Django Framework      │
│  ├── Chatbot Integration       │  ├── REST APIs             │
│  ├── Forms & Calculator        │  ├── Admin Interface       │
│  └── EmailJS Integration       │  └── Database Models       │
├─────────────────────────────────────────────────────────────┤
│                    Integration Layer                        │
│  ├── Webhook Endpoints         │  ├── Background Tasks      │
│  ├── Data Processing           │  └── Error Handling        │
├─────────────────────────────────────────────────────────────┤
│                      Data Layer                             │
│  ├── SQLite/PostgreSQL         │  ├── Static Files          │
│  ├── User Data                 │  └── Media Files           │
│  └── CRM Records               │                             │
└─────────────────────────────────────────────────────────────┘
```

### Core Principles

1. **Invisible Integration** - Frontend remains unchanged, CRM operates behind the scenes
2. **Dual Interface** - Public website + Private admin dashboard
3. **Automatic Data Capture** - Forms, chatbot, and calculator feed CRM automatically
4. **Consistent Styling** - Admin interface matches website design
5. **Scalable Architecture** - Modular Django apps for easy expansion

---

## 🌐 Frontend Architecture

### File Structure
```
frontend/
├── Index.html              # Homepage
├── About.html              # About page
├── services.html           # Services page
├── Products.html           # Products page
├── Projects.html           # Projects page
├── styles.css              # Main stylesheet
├── chat.css                # Chatbot styles
├── chat.js                 # Chatbot functionality
├── sendemail.js            # Form submission handling
└── Assets/                 # Images, logos, documents
    ├── sunrise power logo.png
    ├── Home Page.png
    ├── Ashok Rao.jpg
    ├── Ashok Rao2.jpg
    ├── ShankarRao.png
    └── Sunrise Power.pdf
```

### Key Frontend Components

#### 1. Static Website
- **Pure HTML/CSS/JavaScript** - No framework dependencies
- **Responsive Design** - Mobile-first approach
- **SEO Optimized** - Proper meta tags and structure
- **Fast Loading** - Optimized images and minimal dependencies

#### 2. Chatbot System (`chat.js`)
```javascript
class ChatBot {
    constructor() {
        this.config = {
            apiKey: "",                    // Loaded from backend
            apiUrl: "https://api.cohere.ai/v2/chat",
            model: "command-a-03-2025",
            systemPrompt: "..."            // AI assistant instructions
        };
        this.sessionId = this.generateSessionId();
        this.conversationHistory = [];
    }
    
    // Key Methods:
    // - sendMessage() - Handles user input
    // - callCohere() - Communicates with AI API
    // - sendConversationToCRM() - Sends data to backend
    // - extractUserInfo() - Captures contact details
}
```

**Chatbot Features:**
- **AI-Powered** - Uses Cohere API for intelligent responses
- **Context Aware** - Maintains conversation history
- **Data Extraction** - Automatically captures user contact information
- **CRM Integration** - Sends conversation data to backend for lead creation
- **Session Management** - Tracks individual chat sessions

#### 3. Solar Calculator
```javascript
class SolarCalculator {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.calculationResults = {};
        this.userInputs = {};
    }
    
    // Key Methods:
    // - calculateSavings() - Performs solar calculations
    // - submitCalculatorData() - Sends results to CRM
    // - displayResults() - Shows calculation results
}
```

**Calculator Features:**
- **Real-time Calculations** - Instant solar savings estimates
- **Lead Generation** - High-intent users automatically become leads
- **Data Capture** - Collects property details and contact information
- **CRM Integration** - Sends calculation data to backend

#### 4. Form Integration (`sendemail.js`)
```javascript
// EmailJS Integration
document.getElementById("service-form").addEventListener("submit", function(event) {
    event.preventDefault();
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Send to CRM first (invisible to user)
    sendFormDataToCRM(data);
    
    // Send via EmailJS (existing functionality)
    emailjs.sendForm("service_tyc0213", "template_32q43sm", form, "Prx0yDnr-5MlTe-vB");
});
```

**Form Features:**
- **Dual Submission** - EmailJS for notifications + CRM for data storage
- **Error Handling** - Graceful degradation if CRM is unavailable
- **Data Validation** - Client-side and server-side validation
- **CSRF Protection** - Secure form submissions

### Frontend Data Flow

```
User Interaction → JavaScript Handler → Data Processing → CRM API Call
     ↓                    ↓                   ↓              ↓
1. User fills form    2. Extract data    3. Format for API  4. Send to backend
2. User chats         2. Parse messages  3. Create payload  4. Create lead/service
3. User calculates    2. Get results     3. Add contact     4. High-priority lead
```

---

## ⚙️ Backend Architecture

### Django Project Structure
```
backend/
├── manage.py                   # Django management script
├── requirements.txt            # Python dependencies
├── db.sqlite3                 # Database file
├── solar_crm/                 # Main Django project
│   ├── __init__.py
│   ├── settings/              # Environment-specific settings
│   │   ├── __init__.py
│   │   ├── base.py           # Base settings
│   │   ├── development.py    # Development settings
│   │   └── production.py     # Production settings
│   ├── urls.py               # Main URL configuration
│   └── wsgi.py               # WSGI application
├── apps/                      # Django applications
│   ├── __init__.py
│   ├── users/                # User management
│   ├── leads/                # Lead management
│   ├── customers/            # Customer management
│   ├── services/             # Service requests & projects
│   ├── analytics/            # Analytics & reporting
│   ├── integrations/         # External integrations
│   ├── admin_interface/      # Custom admin interface
│   └── frontend/             # Frontend file serving
├── templates/                 # Django templates
│   ├── base/
│   │   └── admin_base.html   # Base admin template
│   └── admin/                # Admin interface templates
├── static/                   # Static files
│   └── admin/               # Admin interface assets
└── logs/                    # Application logs
    └── django.log
```

### Django Applications

#### 1. Users App (`apps/users/`)
```python
# Models
class User(AbstractUser):
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15, blank=True)
    department = models.CharField(max_length=50, blank=True)
    
# Features:
# - Custom user model with roles
# - Authentication & authorization
# - User profile management
```

#### 2. Leads App (`apps/leads/`)
```python
# Models
class Lead(models.Model):
    # Contact Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    
    # Lead Details
    source = models.ForeignKey(LeadSource, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES)
    interest_level = models.CharField(max_length=10, choices=INTEREST_CHOICES)
    priority_level = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    
    # Solar-Specific Fields
    property_type = models.CharField(max_length=20, choices=PROPERTY_CHOICES)
    estimated_capacity = models.DecimalField(max_digits=8, decimal_places=2)
    budget_range = models.CharField(max_length=20, choices=BUDGET_CHOICES)
    
    # Scoring & Assignment
    score = models.IntegerField(default=0)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    original_data = models.JSONField(default=dict)

class LeadSource(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2)
```

**Lead Features:**
- **Automatic Scoring** - AI-based lead prioritization
- **Source Tracking** - Track where leads come from
- **Conversion Tracking** - Monitor lead-to-customer conversion
- **Duplicate Detection** - Prevent duplicate lead creation
- **Assignment Rules** - Automatic lead assignment to sales team

#### 3. Customers App (`apps/customers/`)
```python
# Models
class Customer(models.Model):
    # Link to original lead
    lead = models.OneToOneField(Lead, on_delete=models.CASCADE)
    
    # Contact Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    
    # Business Information
    company_name = models.CharField(max_length=200, blank=True)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES)
    
    # Address Information
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    
    # Status & Tracking
    status = models.CharField(max_length=20, choices=CUSTOMER_STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    lifetime_value = models.DecimalField(max_digits=12, decimal_places=2)
```

**Customer Features:**
- **Lead Conversion** - Seamless lead-to-customer conversion
- **Lifetime Value Tracking** - Monitor customer profitability
- **Service History** - Complete service request history
- **Project Management** - Track installation projects
- **Communication Log** - Record all customer interactions

#### 4. Services App (`apps/services/`)
```python
# Models
class ServiceRequest(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    ticket_number = models.CharField(max_length=20, unique=True)
    
    # Request Details
    request_type = models.CharField(max_length=30, choices=REQUEST_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Description & Resolution
    subject = models.CharField(max_length=200)
    description = models.TextField()
    resolution = models.TextField(blank=True)
    
    # Assignment & Tracking
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

class InstallationProject(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    project_name = models.CharField(max_length=200)
    
    # Project Details
    system_capacity = models.DecimalField(max_digits=8, decimal_places=2)
    project_value = models.DecimalField(max_digits=12, decimal_places=2)
    installation_address = models.TextField()
    
    # Timeline
    start_date = models.DateField()
    expected_completion = models.DateField()
    completion_date = models.DateField(null=True, blank=True)
    
    # Status & Progress
    status = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES)
    progress_percentage = models.IntegerField(default=0)

class AMCContract(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    contract_number = models.CharField(max_length=20, unique=True)
    
    # Contract Details
    start_date = models.DateField()
    end_date = models.DateField()
    annual_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status & Renewal
    status = models.CharField(max_length=20, choices=CONTRACT_STATUS_CHOICES)
    auto_renewal = models.BooleanField(default=False)
    renewal_date = models.DateField(null=True, blank=True)
```

**Service Features:**
- **Ticket Management** - Complete service request lifecycle
- **Project Tracking** - Installation project management
- **AMC Management** - Annual maintenance contract tracking
- **SLA Monitoring** - Service level agreement compliance
- **Resource Planning** - Technician assignment and scheduling

#### 5. Integrations App (`apps/integrations/`)
```python
# Models
class EmailLog(models.Model):
    email_id = models.CharField(max_length=100, unique=True)
    sender_email = models.EmailField()
    sender_name = models.CharField(max_length=200)
    subject = models.CharField(max_length=500)
    
    # Processing
    email_type = models.CharField(max_length=30, choices=EMAIL_TYPE_CHOICES)
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS_CHOICES)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Data
    raw_content = models.TextField()
    parsed_data = models.JSONField(default=dict)
    processing_notes = models.TextField(blank=True)

class ChatbotInteraction(models.Model):
    session_id = models.CharField(max_length=100)
    user_messages = models.JSONField(default=list)
    bot_responses = models.JSONField(default=list)
    user_info = models.JSONField(default=dict)
    conversation_context = models.JSONField(default=dict)
    
    # Links
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class CalculatorData(models.Model):
    session_id = models.CharField(max_length=100)
    calculation_results = models.JSONField(default=dict)
    user_inputs = models.JSONField(default=dict)
    user_info = models.JSONField(default=dict)
    
    # Links
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Integration Features:**
- **Email Processing** - Automatic email parsing and lead creation
- **Chatbot Data** - Conversation analysis and lead generation
- **Calculator Integration** - High-intent lead capture
- **Background Tasks** - Asynchronous data processing
- **Error Handling** - Comprehensive error tracking and recovery

#### 6. Analytics App (`apps/analytics/`)
```python
# Models
class AnalyticsMetric(models.Model):
    metric_name = models.CharField(max_length=100)
    metric_value = models.DecimalField(max_digits=15, decimal_places=2)
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPE_CHOICES)
    date_recorded = models.DateField()
    metadata = models.JSONField(default=dict)

class ConversionFunnel(models.Model):
    funnel_stage = models.CharField(max_length=50)
    stage_order = models.IntegerField()
    entry_count = models.IntegerField()
    exit_count = models.IntegerField()
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2)
    date_recorded = models.DateField()

class RevenueTracking(models.Model):
    revenue_source = models.CharField(max_length=100)
    revenue_amount = models.DecimalField(max_digits=12, decimal_places=2)
    revenue_date = models.DateField()
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    project = models.ForeignKey(InstallationProject, on_delete=models.CASCADE)
```

**Analytics Features:**
- **Performance Metrics** - KPI tracking and monitoring
- **Conversion Analysis** - Lead-to-customer conversion tracking
- **Revenue Analytics** - Financial performance monitoring
- **Trend Analysis** - Historical data analysis
- **Custom Reports** - Flexible reporting system

### Backend Data Flow

```
API Request → View → Model → Database → Response
     ↓          ↓      ↓        ↓         ↓
1. Webhook    2. Parse  3. Validate  4. Store  5. Return status
2. Admin UI   2. Process 3. Update   4. Save   5. Redirect/JSON
3. API Call   2. Query   3. Filter   4. Fetch  5. Serialize
```

---

## 🔄 Data Flow & Integration

### Complete Integration Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Integration   │    │    Backend      │
│   Interaction   │───▶│     Layer       │───▶│   Processing    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • Form Submit   │    │ • Webhook       │    │ • Create Lead   │
│ • Chat Message  │    │ • Data Parse    │    │ • Update CRM    │
│ • Calculator    │    │ • Validation    │    │ • Send Alerts   │
│ • User Action   │    │ • Queue Task    │    │ • Generate ID   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 1. Form Submission Flow

```
User fills form → sendemail.js → EmailJS + CRM API → Email sent + Lead created
     ↓                ↓              ↓                    ↓
1. Service form   2. Extract data  3. Dual submission  4. Confirmation
2. Contact form   2. Validate      3. Error handling   4. Follow-up
3. Quote request  2. Format        3. Background task  4. Assignment
```

**Implementation:**
```javascript
// Frontend (sendemail.js)
async function sendFormDataToCRM(formData) {
    const crmData = {
        form_type: 'service_inquiry',
        service_type: formData.service || '',
        contact_info: {
            name: formData.name || '',
            email: formData.email || '',
            phone: formData.phone || ''
        },
        form_data: formData,
        timestamp: new Date().toISOString(),
        source: 'website_form'
    };

    const response = await fetch('/api/integrations/webhooks/emailjs/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(crmData)
    });
}
```

```python
# Backend (integrations/views.py)
@csrf_exempt
@require_http_methods(["POST"])
def emailjs_webhook(request):
    data = json.loads(request.body)
    
    # Process the email with error handling
    result = safe_external_api_call(
        process_emailjs_webhook,
        data,
        service_name='emailjs_processing'
    )
    
    return JsonResponse({'status': 'success', 'result': result})
```

### 2. Chatbot Integration Flow

```
User message → chat.js → Cohere API → Response + CRM data → Lead creation
     ↓            ↓          ↓            ↓                    ↓
1. Type message  2. Send    3. AI reply  4. Extract info     5. High-intent lead
2. Conversation  2. Context 3. Generate  4. Session data     5. Follow-up task
3. Contact info  2. History 3. Response  4. User details     5. Assignment
```

**Implementation:**
```javascript
// Frontend (chat.js)
async sendConversationToCRM() {
    const conversationData = {
        session_id: this.sessionId,
        user_messages: this.conversationHistory
            .filter(msg => msg.role === 'user')
            .map(msg => msg.text),
        bot_responses: this.conversationHistory
            .filter(msg => msg.role === 'assistant')
            .map(msg => msg.text),
        user_info: this.userInfo,
        conversation_context: {
            total_messages: this.conversationHistory.length,
            session_duration: Date.now() - parseInt(this.sessionId.split('_')[1]),
            timestamp: new Date().toISOString()
        }
    };

    await fetch('/api/integrations/webhooks/chatbot/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(conversationData)
    });
}
```

```python
# Backend (integrations/views.py)
@TaskRegistry.register('process_chatbot_interaction')
def process_chatbot_interaction(interaction_data):
    # Create chatbot interaction record
    chatbot_interaction = ChatbotInteraction.objects.create(
        session_id=interaction_data.get('session_id', ''),
        user_messages=interaction_data.get('user_messages', []),
        bot_responses=interaction_data.get('bot_responses', []),
        user_info=interaction_data.get('user_info', {}),
        conversation_context=interaction_data.get('conversation_context', {})
    )
    
    # Analyze for lead creation
    should_create_lead = _analyze_chatbot_interaction_for_lead(interaction_data)
    
    if should_create_lead:
        # Create high-intent lead
        lead = Lead.objects.create(
            source=LeadSource.objects.get(name='Chatbot'),
            interest_level='high',
            # ... other fields
        )
        chatbot_interaction.lead = lead
        chatbot_interaction.save()
```

### 3. Solar Calculator Flow

```
User calculation → Calculator → Results + Contact → CRM API → High-priority lead
       ↓              ↓           ↓                  ↓              ↓
1. Input details   2. Calculate  3. Show savings   4. Process     5. Sales follow-up
2. Property info   2. Estimate   3. Contact form   4. Create      5. Quote generation
3. Contact data    2. Pricing    3. Submit         4. Prioritize  5. Assignment
```

**Implementation:**
```javascript
// Frontend (Index.html - Calculator)
async submitCalculatorData() {
    const calculatorData = {
        session_id: this.sessionId,
        calculation_results: this.calculationResults,
        user_inputs: this.userInputs,
        user_info: {
            first_name: name.split(' ')[0],
            last_name: name.split(' ').slice(1).join(' '),
            email: email,
            phone: phone
        },
        timestamp: new Date().toISOString()
    };

    const response = await fetch('/api/integrations/webhooks/calculator/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(calculatorData)
    });
}
```

```python
# Backend (integrations/views.py)
@TaskRegistry.register('process_calculator_data')
def process_calculator_data(calculator_data):
    # Create calculator data record
    calculator_record = CalculatorData.objects.create(
        session_id=calculator_data.get('session_id', ''),
        calculation_results=calculator_data.get('calculation_results', {}),
        user_inputs=calculator_data.get('user_inputs', {}),
        user_info=calculator_data.get('user_info', {})
    )
    
    # Create high-priority lead (calculator usage indicates strong intent)
    if calculator_data.get('user_info'):
        lead = Lead.objects.create(
            source=LeadSource.objects.get(name='Solar Calculator'),
            interest_level='high',
            priority_level='high',
            estimated_capacity=calculator_data['calculation_results'].get('system_capacity_kw', 0),
            # ... other fields
        )
        calculator_record.lead = lead
        calculator_record.save()
```

---

## 🗄️ Database Schema

### Entity Relationship Diagram

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    User     │    │    Lead     │    │  Customer   │
│             │    │             │    │             │
│ • id        │    │ • id        │    │ • id        │
│ • username  │◄──┤ • assigned_to│    │ • lead_id   │
│ • email     │    │ • first_name│───▶│ • first_name│
│ • role      │    │ • email     │    │ • email     │
│ • phone     │    │ • source_id │    │ • status    │
└─────────────┘    │ • status    │    └─────────────┘
                   │ • score     │           │
┌─────────────┐    │ • created_at│           │
│ LeadSource  │    └─────────────┘           │
│             │           ▲                  │
│ • id        │           │                  │
│ • name      │───────────┘                  │
│ • conv_rate │                              │
└─────────────┘                              │
                                             ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│EmailLog     │    │ServiceReq   │    │Installation │
│             │    │             │    │Project      │
│ • email_id  │    │ • id        │    │             │
│ • sender    │    │ • customer  │◄───│ • customer  │
│ • subject   │    │ • type      │    │ • capacity  │
│ • status    │    │ • priority  │    │ • value     │
│ • parsed    │    │ • status    │    │ • status    │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ChatbotInt   │    │AMCContract  │    │Analytics    │
│             │    │             │    │Metric       │
│ • session_id│    │ • customer  │    │             │
│ • messages  │    │ • start_date│    │ • name      │
│ • user_info │    │ • end_date  │    │ • value     │
│ • lead_id   │    │ • value     │    │ • date      │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Key Relationships

1. **User → Lead** (One-to-Many): Users can be assigned multiple leads
2. **Lead → Customer** (One-to-One): Each lead can convert to one customer
3. **Customer → ServiceRequest** (One-to-Many): Customers can have multiple service requests
4. **Customer → InstallationProject** (One-to-Many): Customers can have multiple projects
5. **Customer → AMCContract** (One-to-Many): Customers can have multiple AMC contracts
6. **Lead → ChatbotInteraction** (One-to-Many): Leads can be created from multiple chat sessions
7. **Lead → CalculatorData** (One-to-Many): Leads can be created from calculator usage

---

## 🔌 API Architecture

### REST API Endpoints

#### Authentication Endpoints
```
POST /api/auth/login/          # User login
POST /api/auth/logout/         # User logout
POST /api/auth/refresh/        # Token refresh
GET  /api/auth/user/           # Current user info
```

#### Lead Management
```
GET    /api/leads/             # List leads
POST   /api/leads/             # Create lead
GET    /api/leads/{id}/        # Get lead details
PUT    /api/leads/{id}/        # Update lead
DELETE /api/leads/{id}/        # Delete lead
POST   /api/leads/{id}/convert/ # Convert to customer
```

#### Customer Management
```
GET    /api/customers/         # List customers
POST   /api/customers/         # Create customer
GET    /api/customers/{id}/    # Get customer details
PUT    /api/customers/{id}/    # Update customer
DELETE /api/customers/{id}/    # Delete customer
```

#### Service Management
```
GET    /api/services/requests/           # List service requests
POST   /api/services/requests/           # Create service request
GET    /api/services/requests/{id}/      # Get service request
PUT    /api/services/requests/{id}/      # Update service request
POST   /api/services/requests/{id}/resolve/ # Resolve request

GET    /api/services/projects/           # List projects
POST   /api/services/projects/           # Create project
GET    /api/services/projects/{id}/      # Get project details
PUT    /api/services/projects/{id}/      # Update project

GET    /api/services/amc/                # List AMC contracts
POST   /api/services/amc/                # Create AMC contract
GET    /api/services/amc/{id}/           # Get AMC details
PUT    /api/services/amc/{id}/           # Update AMC
```

#### Integration Endpoints (Public)
```
POST /api/integrations/webhooks/emailjs/     # EmailJS webhook
POST /api/integrations/webhooks/chatbot/     # Chatbot data
POST /api/integrations/webhooks/calculator/  # Calculator data
GET  /api/integrations/config/cohere-key/    # Get Cohere API key
```

#### Analytics Endpoints
```
GET /api/analytics/dashboard/         # Dashboard metrics
GET /api/analytics/conversion-funnel/ # Conversion funnel data
GET /api/analytics/revenue/           # Revenue analytics
GET /api/analytics/performance/       # Performance metrics
```

#### System Endpoints
```
GET /health/                          # Health check
GET /api/system/health/               # Detailed system health
GET /api/system/metrics/              # System metrics
GET /api/system/errors/               # Error dashboard
```

### API Response Format

#### Success Response
```json
{
    "status": "success",
    "data": {
        "id": 123,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com"
    },
    "message": "Lead created successfully",
    "timestamp": "2025-01-01T12:00:00Z"
}
```

#### Error Response
```json
{
    "status": "error",
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Email is required",
        "details": {
            "field": "email",
            "value": null
        }
    },
    "timestamp": "2025-01-01T12:00:00Z"
}
```

#### Pagination Response
```json
{
    "status": "success",
    "data": {
        "results": [...],
        "count": 150,
        "next": "http://api.example.com/leads/?page=2",
        "previous": null,
        "page_size": 20,
        "total_pages": 8
    }
}
```

---

## 🔐 Security & Authentication

### Authentication System

#### JWT Token Authentication
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}
```

#### Role-Based Access Control
```python
# Custom permissions
class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == 'admin'

class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            obj.assigned_to == request.user or 
            request.user.role in ['admin', 'manager']
        )
```

### Security Measures

#### 1. CSRF Protection
```python
# For form submissions
@csrf_exempt  # Only for webhook endpoints
@require_http_methods(["POST"])
def webhook_endpoint(request):
    # Validate webhook signature
    if not validate_webhook_signature(request):
        return HttpResponseForbidden()
```

#### 2. Input Validation
```python
# Serializers with validation
class LeadSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)
    phone = serializers.RegexField(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be valid"
    )
    
    def validate_email(self, value):
        if value and Lead.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
```

#### 3. Rate Limiting
```python
# Rate limiting for API endpoints
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/h', method='POST')
def webhook_endpoint(request):
    pass
```

#### 4. SQL Injection Prevention
```python
# Using Django ORM (automatically prevents SQL injection)
leads = Lead.objects.filter(
    email__icontains=search_term,
    status__in=['new', 'contacted']
)

# For raw queries (if needed)
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT * FROM leads WHERE email = %s", [email])
```

#### 5. XSS Prevention
```html
<!-- Template auto-escaping -->
{{ user_input|escape }}

<!-- For trusted HTML -->
{{ trusted_html|safe }}

<!-- CSP Headers -->
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'
```

---

## 🚀 Deployment Architecture

### Development Environment
```
┌─────────────────────────────────────────────────────────────┐
│                    Development Setup                        │
├─────────────────────────────────────────────────────────────┤
│  Frontend: Static files served by Django                   │
│  Backend: Django development server (port 8000)            │
│  Database: SQLite (db.sqlite3)                             │
│  Static Files: Served by Django                            │
│  Media Files: Local filesystem                             │
└─────────────────────────────────────────────────────────────┘
```

### Production Environment
```
┌─────────────────────────────────────────────────────────────┐
│                    Production Setup                         │
├─────────────────────────────────────────────────────────────┤
│  Load Balancer (Nginx/Cloudflare)                          │
│  ├── Static Files (CDN/S3)                                 │
│  ├── Media Files (S3/Cloud Storage)                        │
│  └── Application Server                                     │
│      ├── Web Server (Gunicorn/uWSGI)                       │
│      ├── Django Application                                 │
│      └── Background Tasks (Celery/Redis)                   │
│  Database: PostgreSQL (RDS/Cloud SQL)                      │
│  Cache: Redis (ElastiCache/Cloud Memory)                   │
│  Monitoring: Sentry/New Relic                              │
└─────────────────────────────────────────────────────────────┘
```

### Scaling Considerations

#### Horizontal Scaling
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   App Server 1  │    │   App Server 2  │
│                 │───▶│                 │    │                 │
│ • Route Traffic │    │ • Django App    │    │ • Django App    │
│ • SSL Term      │    │ • Gunicorn      │    │ • Gunicorn      │
│ • Health Check  │    │ • Static Files  │    │ • Static Files  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │    │   Cache Layer   │    │  File Storage   │
│                 │    │                 │    │                 │
│ • PostgreSQL    │    │ • Redis         │    │ • S3/Cloud      │
│ • Read Replicas │    │ • Session Store │    │ • CDN           │
│ • Backup        │    │ • Query Cache   │    │ • Media Files   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### Performance Optimization
1. **Database Optimization**
   - Query optimization
   - Database indexing
   - Connection pooling
   - Read replicas

2. **Caching Strategy**
   - Redis for session storage
   - Query result caching
   - Template fragment caching
   - CDN for static files

3. **Background Processing**
   - Celery for async tasks
   - Redis as message broker
   - Task queues for heavy operations
   - Scheduled tasks for maintenance

---

## 📊 Monitoring & Observability

### Application Monitoring
```python
# Sentry integration
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)
```

### Health Checks
```python
# Health check endpoint
def health_check(request):
    try:
        # Database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Cache connectivity
        cache.set('health_check', 'ok', 30)
        
        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now(),
            'version': '1.0.0'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)
```

### Logging Strategy
```python
# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

---

**🎉 This comprehensive architecture guide provides a complete understanding of how the Solar CRM Platform works!**

The system seamlessly integrates a static frontend website with a powerful Django backend, providing invisible CRM functionality while maintaining the original user experience. The modular architecture ensures scalability, maintainability, and easy feature expansion.