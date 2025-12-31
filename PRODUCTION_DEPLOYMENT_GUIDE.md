# Solar CRM Platform - Production Deployment Guide

This guide covers deploying the Solar CRM Platform to production environments, specifically **Render** and **PythonAnywhere**.

## 📋 Pre-Deployment Checklist

### 1. Project Preparation
- [ ] All code committed to Git repository
- [ ] Environment variables documented
- [ ] Database migrations tested
- [ ] Static files configuration verified
- [ ] Production settings configured

### 2. Required Files for Production
- [ ] `requirements.txt` (already exists)
- [ ] `runtime.txt` (Python version specification)
- [ ] `build.sh` (for Render deployment)
- [ ] Production settings file
- [ ] Environment variables configuration   

---

## 🚀 Deployment Option 1: Render

Render is a modern cloud platform that offers easy deployment with automatic builds and SSL certificates.

### Step 1: Prepare Production Files

Create the following files in your project root:

#### `runtime.txt`
```
python-3.11.0
```

#### `build.sh`
```bash
#!/usr/bin/env bash
# Exit on error
set -o errexit

# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate
```

#### Update `backend/requirements.txt`
Add production-specific dependencies:
```txt
# Core Django Framework
Django==4.2.7
djangorestframework==3.14.0

psycopg2-binary==2.9.9

# Environment and Configuration
python-decouple==3.8
django-environ==0.11.2

# CORS handling for API
django-cors-headers==4.3.1

# Authentication and Security
PyJWT==2.8.0
cryptography>=41.0.0
    
# Production Server
gunicorn==21.2.0

# Static Files (Production)
whitenoise==6.6.0

# Development Tools (optional in production)
django-extensions==3.2.3

# Image processing
Pillow>=10.0.0

# API Documentation
drf-spectacular==0.27.0
```

### Step 2: Create Production Settings

Create `backend/solar_crm/settings/production.py`:
```python
from .base import *
import dj_database_url

# Security Settings
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Database Configuration
DATABASES = {
    'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
}

# Static Files Configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security Headers
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Session Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}
```

### Step 3: Update Django Settings

Update `backend/manage.py` to use production settings:
```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Use production settings by default, override with environment variable
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "solar_crm.settings.production")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

### Step 4: Deploy to Render

1. **Create Render Account**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub account

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure the service:

3. **Render Configuration**
   ```
   Name: solar-crm-platform
   Environment: Python 3
   Build Command: ./build.sh
   Start Command: cd backend && gunicorn solar_crm.wsgi:application
   ```

4. **Environment Variables**
   Add these in Render dashboard:
   ```
   SECRET_KEY=your-super-secret-key-here
   DATABASE_URL=postgresql://user:pass@host:port/dbname
   ALLOWED_HOSTS=your-app-name.onrender.com
   DJANGO_SETTINGS_MODULE=solar_crm.settings.production
   ```

5. **Database Setup**
   - Create PostgreSQL database in Render
   - Copy the DATABASE_URL to your environment variables

### Step 5: Post-Deployment Setup

1. **Create Superuser**
   ```bash
   # In Render console
   python backend/manage.py createsuperuser
   ```

2. **Test Deployment**
   - Visit your Render URL
   - Check admin panel: `https://your-app.onrender.com/admin/`
   - Verify API endpoints work

---

## 🐍 Deployment Option 2: PythonAnywhere

PythonAnywhere is a Python-focused hosting platform with excellent Django support.

### Step 1: Prepare for PythonAnywhere

#### Update `backend/requirements.txt` for PythonAnywhere
```txt
# Core Django Framework
Django==4.2.7
djangorestframework==3.14.0

# Database (MySQL for PythonAnywhere)
mysqlclient==2.2.0

# Environment and Configuration
python-decouple==3.8
django-environ==0.11.2

# CORS handling for API
django-cors-headers==4.3.1

# Authentication and Security
PyJWT==2.8.0
cryptography>=41.0.0

# Static Files
whitenoise==6.6.0

# Image processing
Pillow>=10.0.0

# API Documentation
drf-spectacular==0.27.0
```

### Step 2: Create PythonAnywhere Settings

Create `backend/solar_crm/settings/pythonanywhere.py`:
```python
from .base import *

# Security Settings
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# PythonAnywhere specific hosts
ALLOWED_HOSTS = [
    'yourusername.pythonanywhere.com',
    'www.yourdomain.com',  # if using custom domain
    'yourdomain.com'
]

# Database Configuration for MySQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'yourusername$solar_crm',
        'USER': 'yourusername',
        'PASSWORD': 'your-mysql-password',
        'HOST': 'yourusername.mysql.pythonanywhere-services.com',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Static Files Configuration
STATIC_URL = '/static/'
STATIC_ROOT = '/home/yourusername/solar-crm-platform/backend/static'

# Media Files
MEDIA_URL = '/media/'
MEDIA_ROOT = '/home/yourusername/solar-crm-platform/backend/media'

# Security Headers (optional for PythonAnywhere)
SECURE_SSL_REDIRECT = False  # PythonAnywhere handles SSL
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

### Step 3: Deploy to PythonAnywhere

1. **Create PythonAnywhere Account**
   - Go to [pythonanywhere.com](https://pythonanywhere.com)
   - Choose appropriate plan (Hacker plan minimum for Django)

2. **Upload Code**
   ```bash
   # In PythonAnywhere console
   cd ~
   git clone https://github.com/yourusername/solar-crm-platform.git
   cd solar-crm-platform/backend
   ```

3. **Create Virtual Environment**
   ```bash
   # In PythonAnywhere console
   mkvirtualenv --python=/usr/bin/python3.10 solar-crm
   workon solar-crm
   pip install -r requirements.txt
   ```

4. **Setup Database**
   ```bash
   # Create MySQL database in PythonAnywhere dashboard
   # Then run migrations
   python manage.py migrate --settings=solar_crm.settings.pythonanywhere
   python manage.py collectstatic --settings=solar_crm.settings.pythonanywhere
   python manage.py createsuperuser --settings=solar_crm.settings.pythonanywhere
   ```

### Step 4: Configure WSGI

Create/edit `/var/www/yourusername_pythonanywhere_com_wsgi.py`:
```python
import os
import sys

# Add your project directory to the sys.path
path = '/home/yourusername/solar-crm-platform/backend'
if path not in sys.path:
    sys.path.insert(0, path)

# Set Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'solar_crm.settings.pythonanywhere'

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Step 5: Configure Static Files

In PythonAnywhere Web tab:
```
Static files:
URL: /static/
Directory: /home/yourusername/solar-crm-platform/backend/static

URL: /media/
Directory: /home/yourusername/solar-crm-platform/backend/media
```

### Step 6: Environment Variables

Create `.env` file in `/home/yourusername/solar-crm-platform/backend/`:
```env
SECRET_KEY=your-super-secret-key-here
DEBUG=False
DATABASE_NAME=yourusername$solar_crm
DATABASE_USER=yourusername
DATABASE_PASSWORD=your-mysql-password
DATABASE_HOST=yourusername.mysql.pythonanywhere-services.com
```

---

## 🔧 Post-Deployment Configuration

### 1. SSL Certificate Setup

#### Render
- SSL is automatic and free
- Custom domains supported with DNS configuration

#### PythonAnywhere
- Free SSL on pythonanywhere.com subdomain
- Custom domain SSL available on paid plans

### 2. Environment Variables Security

#### Critical Environment Variables
```env
SECRET_KEY=generate-a-new-secret-key-for-production
DATABASE_URL=your-database-connection-string
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
EMAILJS_WEBHOOK_SECRET=your-webhook-secret
SENTRY_DSN=your-sentry-dsn-for-error-tracking
```

#### Generate Secret Key
```python
# Run in Python console
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

### 3. Database Backup Strategy

#### Automated Backups
```bash
# Create backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
python manage.py dumpdata > backup_$DATE.json

# Schedule with cron (Linux/Mac) or Task Scheduler (Windows)
0 2 * * * /path/to/backup_script.sh
```

### 4. Monitoring and Logging

#### Error Tracking with Sentry
```python
# Add to production settings
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)
```

#### Health Check Endpoint
```python
# Add to urls.py
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'healthy', 'timestamp': timezone.now()})

urlpatterns = [
    path('health/', health_check, name='health_check'),
    # ... other patterns
]
```

---

## 🚨 Troubleshooting Production Issues

### Common Deployment Problems

#### 1. Static Files Not Loading
```bash
# Ensure static files are collected
python manage.py collectstatic --noinput

# Check STATIC_ROOT and STATIC_URL settings
# Verify web server static file configuration
```

#### 2. Database Connection Issues
```bash
# Test database connection
python manage.py dbshell

# Check DATABASE_URL format
# Verify database credentials and permissions
```

#### 3. 500 Internal Server Error
```bash
# Check application logs
# Enable DEBUG temporarily to see detailed errors
# Verify all environment variables are set
```

#### 4. CSRF Token Issues
```python
# Add to production settings
CSRF_TRUSTED_ORIGINS = [
    'https://your-domain.com',
    'https://www.your-domain.com',
]
```

### Performance Optimization

#### 1. Database Optimization
```python
# Add database connection pooling
DATABASES = {
    'default': {
        # ... existing config
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'MAX_CONNS': 20,
        }
    }
}
```

#### 2. Caching Configuration
```python
# Redis caching (if available)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

#### 3. Static File Compression
```python
# Enable gzip compression
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Add compression middleware
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    # ... other middleware
]
```

---

## 📊 Monitoring and Maintenance

### 1. Application Monitoring

#### Key Metrics to Monitor
- Response times
- Error rates
- Database query performance
- Memory usage
- Disk space

#### Monitoring Tools
- **Render**: Built-in metrics dashboard
- **PythonAnywhere**: CPU seconds and error logs
- **External**: New Relic, DataDog, or Sentry

### 2. Regular Maintenance Tasks

#### Weekly Tasks
```bash
# Check application logs
tail -f /var/log/your-app.log

# Monitor database size
python manage.py dbshell -c "SELECT pg_size_pretty(pg_database_size('your_db'));"

# Update dependencies (test first!)
pip list --outdated
```

#### Monthly Tasks
```bash
# Database backup
python manage.py dumpdata > monthly_backup.json

# Clean old log files
find /var/log -name "*.log" -mtime +30 -delete

# Review security updates
pip audit
```

### 3. Scaling Considerations

#### Horizontal Scaling
- Load balancer configuration
- Database read replicas
- CDN for static files
- Redis for session storage

#### Vertical Scaling
- Increase server resources
- Optimize database queries
- Implement caching strategies
- Use async task queues (Celery)

---

## 🔐 Security Best Practices

### 1. Environment Security
```env
# Use strong, unique passwords
SECRET_KEY=use-django-secret-key-generator
DATABASE_PASSWORD=use-strong-database-password

# Restrict access
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DEBUG=False
```

### 2. Application Security
```python
# Security middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

### 3. Database Security
- Use connection encryption
- Implement proper user permissions
- Regular security updates
- Monitor for suspicious activity

---

## 📞 Support and Resources

### Documentation Links
- **Django Deployment**: https://docs.djangoproject.com/en/4.2/howto/deployment/
- **Render Django Guide**: https://render.com/docs/deploy-django
- **PythonAnywhere Django**: https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/

### Emergency Contacts
- Platform support channels
- Database administrator
- Development team lead

### Rollback Procedures
1. Revert to previous Git commit
2. Restore database from backup
3. Clear application cache
4. Restart application servers

---

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] Code tested in staging environment
- [ ] Database migrations tested
- [ ] Static files configuration verified
- [ ] Environment variables documented
- [ ] Backup procedures tested

### During Deployment
- [ ] Deploy to staging first
- [ ] Run database migrations
- [ ] Collect static files
- [ ] Create superuser account
- [ ] Test critical functionality

### Post-Deployment
- [ ] Verify website loads correctly
- [ ] Test admin panel access
- [ ] Check API endpoints
- [ ] Monitor error logs
- [ ] Set up monitoring alerts

---

**🎉 Your Solar CRM Platform is now ready for production!**

Choose the deployment option that best fits your needs:
- **Render**: Modern, automatic deployments with great developer experience
- **PythonAnywhere**: Python-focused hosting with excellent Django support

Both platforms provide reliable hosting for your Solar CRM Platform with proper configuration and monitoring.