# courses/middleware.py - COMPLETE REPLACEMENT

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from courses.models import StudentLoginLog
import logging

logger = logging.getLogger(__name__)

class AttendanceTrackingMiddleware(MiddlewareMixin):
    """
    Track each login/logout session separately
    Creates NEW session on each login
    """
    
    def process_request(self, request):
        """Track student login automatically"""
        
        # Skip if not authenticated
        if not request.user.is_authenticated:
            return None
        
        # Only track students
        if request.user.role != 'student':
            return None
        
        # Skip AJAX/API requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return None
        
        # Skip static/media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
        
        try:
            # Get session ID from session storage
            log_id = request.session.get('attendance_log_id')
            
            if log_id:
                # Check if this session still exists and is active
                try:
                    active_log = StudentLoginLog.objects.get(
                        id=log_id,
                        student=request.user,
                        logout_time__isnull=True
                    )
                    # Session exists and is active - continue using it
                    return None
                    
                except StudentLoginLog.DoesNotExist:
                    # Session doesn't exist or was logged out
                    # Create new session
                    pass
            
            # No active session found - create new one
            new_log = StudentLoginLog.objects.create(
                student=request.user,
                course=None,
                ip_address=self.get_client_ip(request),
                device_info=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            # Store new session ID
            request.session['attendance_log_id'] = new_log.id
            logger.info(f"✅ New session created: {request.user.username} (ID: {new_log.id})")
            
        except Exception as e:
            logger.error(f"❌ Attendance tracking error: {e}")
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    


# courses/middleware.py

from django.utils import timezone
from courses.models import StudentDeviceLimit, DeviceSession

class DeviceTrackingMiddleware:
    """Track student devices using fingerprint"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process before view
        if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'student':
            self.track_student_device(request)
        
        response = self.get_response(request)
        return response
    
    def track_student_device(self, request):
        """Track student device sessions using fingerprint"""
        
        # Skip AJAX/API requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return
        
        # Skip static/media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return
        
        # Skip login/logout URLs
        skip_paths = ['/login/', '/logout/', '/admin/']
        if any(request.path.startswith(path) for path in skip_paths):
            return
        
        try:
            # Get device fingerprint from session
            device_fingerprint = request.session.get('device_fingerprint')
            
            if not device_fingerprint:
                # No fingerprint in session - might be old session
                # Don't track, let login handle it
                return
            
            # Get or create device limit
            device_limit, created = StudentDeviceLimit.objects.get_or_create(
                student=request.user,
                defaults={'max_devices': 2, 'is_active': True}
            )
            
            if not device_limit.is_active:
                # Account disabled - don't track
                return
            
            # Check if device exists
            try:
                device_session = DeviceSession.objects.get(
                    device_id=device_fingerprint,
                    student_limit=device_limit
                )
                
                # Update last login time (only once per minute to avoid too many writes)
                now = timezone.now()
                if (now - device_session.last_login).total_seconds() > 60:
                    device_session.last_login = now
                    device_session.is_active = True
                    device_session.save(update_fields=['last_login', 'is_active'])
                
            except DeviceSession.DoesNotExist:
                # Device not found - this shouldn't happen if login was successful
                # But if it does, log user out for security
                print(f"⚠️ Unknown device detected for {request.user.username}")
                from django.contrib.auth import logout
                logout(request)
                from django.shortcuts import redirect
                from django.contrib import messages
                messages.error(request, 'Device session expired. Please login again.')
                return redirect('user_login')
        
        except Exception as e:
            print(f"❌ Device tracking error: {e}")
            import traceback
            traceback.print_exc()
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')
        return ip
