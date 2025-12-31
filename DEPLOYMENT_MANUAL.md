# Solar CRM Platform - Deployment & Usage Manual

## 🚀 Quick Start Guide

### System Requirements
- Python 3.8+ 
- PostgreSQL 12+ (or SQLite for development)
- Node.js 16+ (optional, for frontend development)
- Git

### Project Structure
```
solar-crm-platform/
├── frontend/                 # Original website files (HTML/CSS/JS)
├── backend/                  # Django CRM application
│   ├── venv/                # Python virtual environment
│   ├── solar_crm/           # Django project settings
│   ├── apps/                # Django applications
│   ├── templates/           # Admin interface templates
│   ├── static/              # Admin interface static files
│   └── manage.py            # Django management script
└── DEPLOYMENT_MANUAL.md     # This file
```

---

## 🔧 Installation & Setup

### Step 1: Clone and Navigate
```bash
# If not already cloned
git clone <repository-url>
cd solar-crm-platform
```

### Step 2: Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Database Setup
```bash
# Run database migrations
python manage.py migrate

# Create superuser account (IMPORTANT!)
python manage.py createsuperuser
# Follow prompts to create admin account
```

### Step 4: Collect Static Files
```bash
# Collect static files for admin interface
python manage.py collectstatic --noinput
```

---

## 🏃‍♂️ Running the Application

### Development Mode (Recommended for Testing)

**Single Command (Serves Both Frontend & Backend):**
```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Start Django development server
python manage.py runserver 8000
```

**The server will start on:** `http://localhost:8000`

### What Gets Served:
- **Frontend Website:** `http://localhost:8000/` (original website with full styling)
- **Admin Panel:** `http://localhost:8000/admin/` (CRM dashboard)
- **API Endpoints:** `http://localhost:8000/api/` (REST APIs)
- **Django Admin:** `http://localhost:8000/django-admin/` (Django's built-in admin)

### ✅ Frontend Integration Fixed:
- Django now properly serves the original website files from `frontend/` folder
- All CSS, JavaScript, images, and styling are correctly loaded
- Website appears exactly as designed with full functionality
- Chatbot, forms, and calculator work with CRM integration

---

## 🔐 Admin Panel Access

### Default Admin Credentials
**⚠️ IMPORTANT: You need to create these during setup!**

When you run `python manage.py createsuperuser`, create:
- **Username:** `admin`
- **Email:** `admin@sunrisepower.com`
- **Password:** `SunrisePower2024!`

### Admin Panel URLs:
1. **Custom CRM Admin:** `http://localhost:8000/admin/`
   - Modern interface matching website design
   - Dashboard, leads, customers, services, analytics

2. **Django Built-in Admin:** `http://localhost:8000/django-admin/`
   - Standard Django admin interface
   - Direct database access and management

---

## 🌐 Frontend Website Access

### Website Pages:
- **Home:** `http://localhost:8000/` or `http://localhost:8000/Index.html`
- **Services:** `http://localhost:8000/services.html`
- **Products:** `http://localhost:8000/Products.html`
- **Projects:** `http://localhost:8000/Projects.html`
- **About:** `http://localhost:8000/About.html`

### Features Working:
- ✅ **Chatbot Integration** - Conversations automatically saved to CRM
- ✅ **Contact Forms** - Form submissions create leads/service requests
- ✅ **Solar Calculator** - Results saved as high-priority leads
- ✅ **EmailJS Integration** - Emails processed and stored in CRM

---

## 🔧 Configuration

### Environment Variables (.env file)
Create `.env` file in `backend/` directory:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
EMAILJS_WEBHOOK_SECRET=your-webhook-secret
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_DIR=../frontend
```

### Database Configuration
**Development (SQLite - Default):**
```python
# Already configured in settings/development.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

**Production (PostgreSQL):**
```env
DATABASE_URL=postgresql://username:password@localhost:5432/solar_crm
```

---

## 📊 Using the Admin Panel

### 1. Dashboard
- **URL:** `http://localhost:8000/admin/`
- **Features:** Real-time metrics, recent activity, quick actions
- **Metrics:** Total leads, customers, revenue, active services

### 2. Lead Management
- **URL:** `http://localhost:8000/admin/leads/`
- **Features:** View, create, edit leads; lead prioritization; conversion tracking
- **Actions:** Convert leads to customers, update priority, view interaction history

### 3. Customer Management
- **URL:** `http://localhost:8000/admin/customers/`
- **Features:** Customer profiles, service history, project tracking
- **Actions:** Create customers, manage projects, track payments

### 4. Service Requests
- **URL:** `http://localhost:8000/admin/services/`
- **Features:** Ticket management, status tracking, customer communication
- **Actions:** Create tickets, update status, assign technicians

### 5. Analytics
- **URL:** `http://localhost:8000/admin/analytics/`
- **Features:** Performance metrics, conversion rates, revenue tracking
- **Reports:** Lead sources, conversion funnel, financial summaries

---

## 🔌 API Endpoints

### Public Endpoints (No Authentication)
```
POST /api/integrations/webhooks/emailjs/     # EmailJS form submissions
POST /api/integrations/webhooks/chatbot/     # Chatbot interactions
POST /api/integrations/webhooks/calculator/  # Solar calculator data
GET  /health/                                # Health check
```

### Authenticated Endpoints
```
GET  /api/leads/                    # List leads
POST /api/leads/                    # Create lead
GET  /api/customers/                # List customers
POST /api/customers/                # Create customer
GET  /api/services/requests/        # List service requests
POST /api/services/requests/        # Create service request
GET  /api/analytics/dashboard/      # Dashboard metrics
```

### API Documentation
- **Swagger UI:** `http://localhost:8000/api/docs/`
- **API Schema:** `http://localhost:8000/api/schema/`

---

## 🧪 Testing

### Run All Tests
```bash
cd backend
python manage.py test
```

### Run Specific Test Categories
```bash
# Property-based tests
python manage.py test apps.services.test_contract_project_tracking
python manage.py test apps.services.test_financial_data_accuracy
python manage.py test apps.leads.test_prioritization

# Integration tests
python manage.py test apps.integrations

# Unit tests
python manage.py test apps.leads.tests
python manage.py test apps.customers.tests
```

---

## 🚨 Troubleshooting

### Common Issues

**1. Frontend not displaying correctly (showing basic HTML without styling)**
```bash
# The issue is that Django needs to serve frontend files properly
# Make sure the frontend app is installed and configured

# Check that frontend files exist
ls ../frontend/
# Should show: Index.html, styles.css, chat.js, etc.

# Restart the server after configuration changes
python manage.py runserver 8000
```

**2. "ModuleNotFoundError" when starting server**
```bash
# Ensure virtual environment is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Reinstall dependencies
pip install -r requirements.txt
```

**3. "Database doesn't exist" error**
```bash
# Run migrations
python manage.py migrate
```

**4. "Static files not found" error**
```bash
# Collect static files
python manage.py collectstatic --noinput
```

**5. "Permission denied" on admin panel**
```bash
# Create superuser
python manage.py createsuperuser
```

**6. CSS/JavaScript not loading on frontend**
```bash
# Check static files configuration
# Ensure STATICFILES_DIRS includes frontend directory
# Restart server after changes
python manage.py runserver 8000
```

### Logs and Debugging
```bash
# Check Django logs
tail -f backend/logs/django.log

# Enable debug mode
# Set DEBUG=True in .env file
```

---

## 🌍 Production Deployment

### Environment Setup
```env
DEBUG=False
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:pass@host:5432/solar_crm
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECURE_SSL_REDIRECT=True
```

### Production Commands
```bash
# Install production dependencies
pip install gunicorn whitenoise

# Collect static files
python manage.py collectstatic --noinput

# Run with Gunicorn
gunicorn solar_crm.wsgi:application --bind 0.0.0.0:8000
```

### Nginx Configuration (Optional)
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location /static/ {
        alias /path/to/backend/staticfiles/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📞 Support & Maintenance

### Regular Maintenance Tasks
```bash
# Backup database
python manage.py dumpdata > backup.json

# Clear old logs
python manage.py clearlogs

# Update lead priorities
python manage.py update_lead_priorities

# Generate analytics reports
python manage.py generate_monthly_report
```

### Monitoring
- **Health Check:** `http://localhost:8000/health/`
- **System Metrics:** Available in admin panel under Analytics
- **Error Logs:** `backend/logs/django.log`

---

## 🎯 Key Features Summary

### ✅ What's Working
- **Dual Interface:** Original website + CRM admin panel
- **Data Capture:** Chatbot, forms, calculator → automatic lead creation
- **Lead Management:** Prioritization, conversion tracking, duplicate detection
- **Service Management:** Ticket system, AMC tracking, project management
- **Financial Tracking:** Payment milestones, invoicing, revenue analytics
- **UI Consistency:** Admin panel matches website design perfectly

### 🔄 Integration Flow
1. **Website Visitor** interacts with chatbot/forms/calculator
2. **Frontend JavaScript** sends data to CRM APIs (invisible to user)
3. **CRM Backend** processes data, creates leads/service requests
4. **Admin Users** manage leads/customers through admin panel
5. **Analytics Engine** provides insights and reporting

---

## 📋 Quick Reference

### Essential Commands
```bash
# Start development server
cd backend && venv\Scripts\activate && python manage.py runserver

# Create admin user
python manage.py createsuperuser

# Run migrations
python manage.py migrate

# Run tests
python manage.py test

# Collect static files
python manage.py collectstatic
```

### Important URLs
- **Website:** http://localhost:8000/
- **Admin Panel:** http://localhost:8000/admin/
- **API Docs:** http://localhost:8000/api/docs/
- **Django Admin:** http://localhost:8000/django-admin/

### Default Credentials
- **Username:** admin
- **Password:** (set during `createsuperuser` command)
- **Recommended:** `SunrisePower2024!`

---

**🎉 Your Solar CRM Platform is ready to use!**

For additional support or questions, refer to the technical documentation in the `docs/` directory or contact the development team.

---

# ✅ FRONTEND STYLING ISSUE - FINAL FIX

## 🔧 The Problem:
The website HTML was loading but CSS/JavaScript files were not being served correctly by Django.

## 🛠️ Complete Fix Applied:

### 1. Updated Frontend View (`backend/apps/frontend/views.py`)
- Fixed static file path references in HTML files
- Added proper URL rewriting for CSS, JS, and image files
- Ensured absolute URLs for all static assets

### 2. Updated URL Configuration (`backend/solar_crm/urls.py`)
- Added `staticfiles_urlpatterns()` for proper static file serving
- Configured Django to serve static files during development

### 3. Verified Static Files Configuration
- Confirmed `STATICFILES_DIRS` includes frontend directory
- Verified Django can find all frontend files (`styles.css`, `chat.css`, etc.)

## 🚀 How to Apply the Fix:

```bash
# 1. Navigate to backend
cd backend

# 2. Activate virtual environment
venv\Scripts\activate

# 3. Collect static files (important!)
python manage.py collectstatic --noinput

# 4. Start server
python manage.py runserver 8000
```

## 🌐 Test the Fix:

Visit these URLs to verify the styling is working:

- **Home:** `http://localhost:8000/` - Should show full styling
- **Services:** `http://localhost:8000/services.html` - Complete design
- **Products:** `http://localhost:8000/Products.html` - All styling
- **Admin:** `http://localhost:8000/admin/` - CRM dashboard

## ✅ What Should Work Now:

- **✅ Full CSS Styling** - Colors, fonts, layouts, animations
- **✅ JavaScript Functionality** - Chatbot, forms, calculator
- **✅ All Images/Assets** - Logo, backgrounds, icons
- **✅ Responsive Design** - Mobile and desktop layouts
- **✅ CRM Integration** - Data capture still works seamlessly

## 🔍 If Still Not Working:

1. **Clear Browser Cache** - Hard refresh (Ctrl+F5)
2. **Check Console** - Open browser dev tools for errors
3. **Verify Static Files** - Run `python manage.py findstatic styles.css`
4. **Restart Server** - Stop and start Django server again

**🎉 The website should now display with complete styling matching the original frontend design!**