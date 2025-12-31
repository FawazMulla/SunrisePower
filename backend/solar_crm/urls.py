"""
URL configuration for solar_crm project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Django Admin interface
    path('django-admin/', admin.site.urls),
    
    # Custom Admin Interface
    path('admin/', include('apps.admin_interface.urls')),
    
    # API endpoints
    path('api/', include('apps.users.urls')),
    path('api/', include('apps.leads.urls')),
    path('api/', include('apps.customers.urls')),
    path('api/', include('apps.services.urls')),
    path('api/', include('apps.analytics.urls')),
    path('api/integrations/', include('apps.integrations.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # Frontend routes (serve existing website files directly)
    path('', include('apps.frontend.urls')),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()
    
    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns