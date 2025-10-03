# decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import Http404

def instructor_permission_required(permission_code):
    """
    Decorator to check if instructor has specific permission
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                messages.error(request, 'Please login to access this page.')
                return redirect('user_login')
            
            # Check if user is instructor
            if request.user.role != 'instructor':
                messages.error(request, 'Access denied. Only instructors can access this page.')
                return redirect('admin_dashboard')
            
            # Check if instructor has permission
            if not request.user.has_instructor_permission(permission_code):
                messages.error(request, f'You do not have permission to access this feature. Contact admin for "{permission_code}" permission.')
                return redirect('instructor_dashboard')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def instructor_required(view_func):
    """
    Decorator to check if user is instructor
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('user_login')
        
        if request.user.role != 'instructor':
            messages.error(request, 'Access denied. Only instructors can access this page.')
            return redirect('admin_dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def superadmin_required(view_func):
    """
    Decorator to check if user is superadmin
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('user_login')
        
        if request.user.role != 'superadmin':
            raise Http404("Page not found")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view