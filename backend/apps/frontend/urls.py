"""
URL configuration for frontend app.
"""
from django.urls import path, re_path
from django.conf import settings
from django.views.static import serve
import os
from . import views

app_name = 'frontend'

urlpatterns = [
    # Main frontend routes
    path('', views.serve_frontend_file, {'file_path': ''}, name='home'),
    path('index.html', views.serve_frontend_file, {'file_path': 'index.html'}, name='index'),
    path('Index.html', views.serve_frontend_file, {'file_path': 'Index.html'}, name='index_cap'),
    
    # Services
    path('services/', views.serve_frontend_file, {'file_path': 'services/'}, name='services'),
    path('services.html', views.serve_frontend_file, {'file_path': 'services.html'}, name='services_html'),
    
    # Products
    path('products/', views.serve_frontend_file, {'file_path': 'products/'}, name='products'),
    path('products.html', views.serve_frontend_file, {'file_path': 'products.html'}, name='products_html'),
    path('Products.html', views.serve_frontend_file, {'file_path': 'Products.html'}, name='products_cap'),
    
    # Projects
    path('projects/', views.serve_frontend_file, {'file_path': 'projects/'}, name='projects'),
    path('projects.html', views.serve_frontend_file, {'file_path': 'projects.html'}, name='projects_html'),
    path('Projects.html', views.serve_frontend_file, {'file_path': 'Projects.html'}, name='projects_cap'),
    
    # About
    path('about/', views.serve_frontend_file, {'file_path': 'about/'}, name='about'),
    path('about.html', views.serve_frontend_file, {'file_path': 'about.html'}, name='about_html'),
    path('About.html', views.serve_frontend_file, {'file_path': 'About.html'}, name='about_cap'),
]

# Serve Assets folder directly (for development)
if settings.DEBUG:
    # Get the correct path to the frontend directory
    base_dir = settings.BASE_DIR  # This is backend/
    frontend_dir = base_dir.parent / 'frontend'  # Go up one level to get to frontend/
    assets_path = frontend_dir / 'Assets'
    
    urlpatterns += [
        re_path(r'^Assets/(?P<path>.*)$', serve, {
            'document_root': str(assets_path),
        }),
    ]