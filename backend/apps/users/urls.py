"""
URL configuration for users app.
"""
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # API endpoints
    path('auth/login/', views.api_login, name='api_login'),
    path('auth/logout/', views.api_logout, name='api_logout'),
    path('auth/profile/', views.api_user_profile, name='api_user_profile'),
    path('auth/profile/update/', views.api_update_profile, name='api_update_profile'),
    path('auth/change-password/', views.api_change_password, name='api_change_password'),
    
    # Web views
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]