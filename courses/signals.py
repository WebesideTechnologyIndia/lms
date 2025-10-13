# ==================== FILE 1: courses/signals.py ====================
# COMPLETE REPLACEMENT

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models import StudentLoginLog
import logging

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def track_student_login(sender, request, user, **kwargs):
    """Track when student logs in - Create NEW session"""
    
    print(f"🔥 LOGIN SIGNAL FIRED for {user.username}")
    
    # Only track students
    if not hasattr(user, 'role') or user.role != 'student':
        print(f"⚠️ Not a student, skipping (role: {getattr(user, 'role', 'N/A')})")
        return
    
    try:
        # Close any existing active sessions (user logged in from another place)
        active_sessions = StudentLoginLog.objects.filter(
            student=user,
            logout_time__isnull=True
        )
        
        if active_sessions.exists():
            print(f"🔒 Closing {active_sessions.count()} old active sessions...")
            for old_session in active_sessions:
                old_session.logout_time = timezone.now()
                old_session.calculate_duration()
                print(f"   Closed session {old_session.id} (duration: {old_session.session_duration} min)")
        
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')
        
        # Get device info
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        # Create NEW session
        new_log = StudentLoginLog.objects.create(
            student=user,
            ip_address=ip,
            device_info=user_agent
        )
        
        # Store in session
        request.session['attendance_log_id'] = new_log.id
        
        print(f"✅ Login tracked: {user.username} - Session ID: {new_log.id}, IP: {ip}")
        logger.info(f"Login: {user.username} - Session {new_log.id}")
        
    except Exception as e:
        print(f"❌ Login tracking error: {e}")
        logger.error(f"Login tracking error for {user.username}: {e}")
        import traceback
        traceback.print_exc()


@receiver(user_logged_out)
def track_student_logout(sender, request, user, **kwargs):
    """Track when student logs out - Close current session"""
    
    print(f"🔥 LOGOUT SIGNAL FIRED for {user.username if user else 'Unknown'}")
    
    # Check if user object exists
    if not user:
        print("⚠️ No user object in logout signal")
        return
    
    # Check if user has role attribute
    if not hasattr(user, 'role'):
        print("⚠️ User has no role attribute")
        return
    
    # Only track students
    if user.role != 'student':
        print(f"⚠️ Not a student, skipping (role: {user.role})")
        return
    
    try:
        # Method 1: Try to get from session
        closed_from_session = False
        
        if hasattr(request, 'session'):
            log_id = request.session.get('attendance_log_id')
            
            if log_id:
                try:
                    log = StudentLoginLog.objects.get(id=log_id, student=user)
                    
                    if not log.logout_time:
                        log.logout_time = timezone.now()
                        log.calculate_duration()
                        print(f"✅ Logout from session: User {user.username} - Session {log.id} - Duration: {log.session_duration} min")
                        logger.info(f"Logout: {user.username} - Session {log.id} - Duration: {log.session_duration} min")
                        closed_from_session = True
                    
                except StudentLoginLog.DoesNotExist:
                    print(f"⚠️ Session log {log_id} not found")
        
        # Method 2: Close all active sessions (fallback)
        active_sessions = StudentLoginLog.objects.filter(
            student=user,
            logout_time__isnull=True
        )
        
        if active_sessions.exists():
            print(f"🔒 Found {active_sessions.count()} active sessions to close...")
            
            for session in active_sessions:
                session.logout_time = timezone.now()
                session.calculate_duration()
                print(f"   ✅ Closed session {session.id} (duration: {session.session_duration} min)")
                logger.info(f"Auto-logout: {user.username} - Session {session.id} - Duration: {session.session_duration} min")
        elif not closed_from_session:
            print(f"⚠️ No active sessions found for {user.username}")
        
    except Exception as e:
        print(f"❌ Logout tracking error: {e}")
        logger.error(f"Logout tracking error for {user.username}: {e}")
        import traceback
        traceback.print_exc()


print("✅ Attendance signals loaded and connected!")