"""
URL configuration for solar_crm project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('apps.users.urls')),
    path('api/', include('apps.leads.urls')),
    path('api/', include('apps.customers.urls')),
    path('api/', include('apps.services.urls')),
    path('api/', include('apps.analytics.urls')),
    path('api/', include('apps.integrations.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # Frontend routes (serve existing website)
    path('', TemplateView.as_view(template_name='Index.html'), name='home'),
    path('services/', TemplateView.as_view(template_name='services.html'), name='services'),
    path('products/', TemplateView.as_view(template_name='Products.html'), name='products'),
    path('projects/', TemplateView.as_view(template_name='Projects.html'), name='projects'),
    path('about/', TemplateView.as_view(template_name='About.html'), name='about'),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns