# Solar CRM Platform - Production Setup Guide (SQLite3)

## 🚀 Quick Production Deployment with SQLite3

### Step 1: Generate Secret Key
```bash
python generate_secret_key.py
```
Copy the generated SECRET_KEY for use in environment variables.

### Step 2: Choose Deployment Platform

#### Option A: Render (Recommended)
1. **Create Render Account**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub
2. **Create Web Service** (No separate database needed - SQLite3 is included)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     ```
     Name: solar-crm-platform
     Environment: Python 3
     Build Command: ./build.sh
     Start Command: cd backend && gunicorn solar_crm.wsgi:application
     ```

3. **Environment Variables**
   Add these in Render dashboard:
   ```
   SECRET_KEY=your-generated-secret-key-from-step-1
   ALLOWED_HOSTS=your-app-name.onrender.com
   DJANGO_SETTINGS_MODULE=solar_crm.settings.production
   COHERE_API_KEY=your-cohere-api-key
   EMAILJS_WEBHOOK_SECRET=your-emailjs-webhook-secret
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for build to complete
   - Your app will be available at `https://your-app-name.onrender.com`

#### Option B: PythonAnywhere

1. **Create Account**
   - Go to [pythonanywhere.com](https://pythonanywhere.com)
   - Choose Hacker plan or higher

2. **Upload Code**
   ```bash
   # In PythonAnywhere console
   git clone https://github.com/yourusername/solar-crm-platform.git
   cd solar-crm-platform/backend
   ```

3. **Setup Environment**
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 solar-crm
   workon solar-crm
   pip install -r requirements.txt
   ```

4. **Setup Database & Static Files**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

5. **Setup WSGI**
   Edit `/var/www/yourusername_pythonanywhere_com_wsgi.py`:
   ```python
   import os
   import sys
   
   path = '/home/yourusername/solar-crm-platform/backend'
   if path not in sys.path:
       sys.path.insert(0, path)
   
   os.environ['DJANGO_SETTINGS_MODULE'] = 'solar_crm.settings.production'
   
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

### Step 3: Post-Deployment Setup

1. **Create Superuser**
   ```bash
   # For Render (in console)
   python backend/manage.py createsuperuser
   
   # For PythonAnywhere
   cd ~/solar-crm-platform/backend
   python manage.py createsuperuser
   ```

2. **Test Deployment**
   - Visit your website URL
   - Check favicon appears in browser tab
   - Test admin login: `https://your-domain.com/admin/`
   - Verify API endpoints work
   - Test contact forms and chatbot

## 🔧 Configuration Files Summary

### Files Created/Updated:
- ✅ `runtime.txt` - Python version specification
- ✅ `build.sh` - Build script for Render
- ✅ `backend/requirements.txt` - Updated with production dependencies
- ✅ `backend/solar_crm/settings/production.py` - Production settings
- ✅ `backend/.env.production` - Environment variables template
- ✅ `backend/manage.py` - Updated to use production settings
- ✅ Favicon files added to all HTML pages
- ✅ Admin favicon configuration
- ✅ Web manifest for PWA support

### Favicon Implementation:
- ✅ Frontend HTML files updated with favicon links
- ✅ Admin interface favicon configured
- ✅ Django admin favicon setup
- ✅ Web manifest created for mobile support
- ✅ Theme colors configured

## 🔐 Security Features Implemented

### Production Security:
- ✅ DEBUG=False in production
- ✅ Secure secret key generation
- ✅ HTTPS enforcement
- ✅ Security headers configured
- ✅ CSRF protection enabled
- ✅ Session security hardened
- ✅ SQL injection protection
- ✅ XSS protection enabled

### Content Security Policy:
- ✅ External resources whitelisted
- ✅ Script sources controlled
- ✅ Style sources managed
- ✅ Font sources specified
- ✅ Connection sources limited

## 📊 Performance Optimizations

### Static Files:
- ✅ WhiteNoise compression enabled
- ✅ Static file caching configured
- ✅ Favicon optimization
- ✅ CSS/JS compression ready

### Database:
- ✅ Connection pooling configured
- ✅ Query optimization ready
- ✅ Migration management
- ✅ Backup procedures documented

## 🚨 Monitoring & Maintenance

### Health Checks:
- ✅ Health check endpoint available
- ✅ Error logging configured
- ✅ Performance monitoring ready
- ✅ Sentry integration prepared

### Backup Strategy:
```bash
# Database backup
python manage.py dumpdata > backup_$(date +%Y%m%d).json

# Media files backup
tar -czf media_backup_$(date +%Y%m%d).tar.gz media/
```

## 📞 Support & Troubleshooting

### Common Issues:

1. **Favicon Not Showing**
   - Clear browser cache (Ctrl+F5)
   - Check static files are collected
   - Verify favicon paths in HTML

2. **Static Files 404**
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Database Connection Error**
   - Verify DATABASE_URL format
   - Check database credentials
   - Ensure database is running

4. **CSRF Token Error**
   - Add domain to CSRF_TRUSTED_ORIGINS
   - Check HTTPS configuration

### Emergency Contacts:
- Development Team: [your-email]
- Hosting Support: [platform-support]
- Database Issues: [db-admin]

## ✅ Deployment Verification

### Frontend Checklist:
- [ ] Website loads with favicon
- [ ] All pages accessible
- [ ] Contact forms working
- [ ] Chatbot functional
- [ ] Calculator operational
- [ ] Mobile responsive

### Backend Checklist:
- [ ] Admin panel accessible with favicon
- [ ] User authentication working
- [ ] CRUD operations functional
- [ ] API endpoints responding
- [ ] Export features working
- [ ] Analytics dashboard active

### Security Checklist:
- [ ] HTTPS enabled
- [ ] Admin panel secured
- [ ] API authentication working
- [ ] Error pages configured
- [ ] Monitoring active

---

## 🎉 Production Ready!

Your Solar CRM Platform is now production-ready with:

### ✅ Professional Features:
- Favicons across all interfaces
- Mobile-optimized design
- PWA capabilities
- Professional admin interface

### ✅ Security & Performance:
- Production-grade security
- Optimized static file serving
- Database optimization
- Error monitoring ready

### ✅ Deployment Options:
- Render deployment configured
- PythonAnywhere setup ready
- Environment variables documented
- Build scripts prepared

**Your platform is ready to serve customers and manage your solar business efficiently!**

For ongoing support and updates, refer to the deployment checklist and troubleshooting guides.