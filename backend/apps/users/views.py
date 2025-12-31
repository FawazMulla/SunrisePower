"""
Views for users app.
"""
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView

from .serializers import (
    UserSerializer, UserProfileSerializer, 
    LoginSerializer, ChangePasswordSerializer
)
from .models import User, UserProfile


# API Views
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_login(request):
    """
    API endpoint for user login.
    """
    serializer = LoginSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def api_logout(request):
    """
    API endpoint for user logout.
    """
    try:
        # Delete the user's token
        request.user.auth_token.delete()
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
    except:
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_user_profile(request):
    """
    API endpoint to get current user profile.
    """
    try:
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = UserProfile.objects.create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def api_update_profile(request):
    """
    API endpoint to update user profile.
    """
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    serializer = UserProfileSerializer(profile, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def api_change_password(request):
    """
    API endpoint to change user password.
    """
    serializer = ChangePasswordSerializer(
        data=request.data, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Update token
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        
        return Response({
            'message': 'Password changed successfully',
            'token': token.key
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Web Views (for admin interface)
def login_view(request):
    """
    Web login view for admin interface.
    """
    if request.method == 'POST':
        serializer = LoginSerializer(data=request.POST, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            messages.success(request, f'Welcome back, {user.full_name}!')
            return redirect('admin:index')
        else:
            for error in serializer.errors.values():
                messages.error(request, error[0])
    
    return render(request, 'users/login.html')


@login_required
def logout_view(request):
    """
    Web logout view for admin interface.
    """
    user_name = request.user.full_name
    logout(request)
    messages.success(request, f'Goodbye, {user_name}!')
    return redirect('login')


class UserPermissionMixin:
    """
    Mixin to check user permissions based on roles.
    """
    
    def check_owner_permission(self, user):
        """Check if user is owner."""
        return user.has_role('owner')
    
    def check_manager_permission(self, user):
        """Check if user is owner or manager."""
        return user.role in ['owner', 'sales_manager']
    
    def check_staff_permission(self, user):
        """Check if user has any staff role."""
        return user.role in ['owner', 'sales_manager', 'sales_staff', 'support_staff']