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
    


import hashlib
from django.utils import timezone
from courses.models import StudentSubscription, DeviceSession

class DeviceTrackingMiddleware:
    """Track student devices automatically"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process before view
        if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'student':
            self.track_student_device(request)
        
        response = self.get_response(request)
        return response
    
    def track_student_device(self, request):
        """Track student device sessions"""
        
        # Skip AJAX/API requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return
        
        # Skip static/media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return
        
        try:
            # Generate unique device ID
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            ip_address = self.get_client_ip(request)
            device_id = hashlib.md5(f"{user_agent}{ip_address}".encode()).hexdigest()
            
            # Get device name
            device_name = self.parse_device_name(user_agent)
            
            # Get student's active subscriptions
            subscriptions = StudentSubscription.objects.filter(
                student=request.user,
                is_active=True
            )
            
            for subscription in subscriptions:
                # Get or create device session
                device_session, created = DeviceSession.objects.get_or_create(
                    subscription=subscription,
                    device_id=device_id,
                    defaults={
                        'device_name': device_name,
                        'is_active': True
                    }
                )
                
                if created:
                    print(f"🆕 New device added for {request.user.username}: {device_name}")
                    # Update current_devices count
                    subscription.current_devices = subscription.devices.filter(is_active=True).count()
                    subscription.save()
                else:
                    # Update last login time
                    device_session.last_login = timezone.now()
                    device_session.save()
        
        except Exception as e:
            print(f"❌ Device tracking error: {e}")
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')
        return ip
    
    def parse_device_name(self, user_agent):
        """Parse device name from user agent"""
        user_agent_lower = user_agent.lower()
        
        if 'mobile' in user_agent_lower or 'android' in user_agent_lower:
            if 'android' in user_agent_lower:
                return 'Android Mobile'
            elif 'iphone' in user_agent_lower:
                return 'iPhone'
            else:
                return 'Mobile Device'
        elif 'ipad' in user_agent_lower:
            return 'iPad'
        elif 'tablet' in user_agent_lower:
            return 'Tablet'
        elif 'windows' in user_agent_lower:
            return 'Windows PC'
        elif 'mac' in user_agent_lower:
            return 'Mac Computer'
        elif 'linux' in user_agent_lower:
            return 'Linux Computer'
        else:
            return 'Desktop Computer'