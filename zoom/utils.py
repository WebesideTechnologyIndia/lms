# zoom/utils.py - Complete Zoom Utilities

import requests
from django.conf import settings
from django.utils import timezone
from .models import ZoomConfiguration, BatchSession, ZoomRecording
from .services import ZoomAPIService

def check_zoom_configuration():
    """Check if Zoom is properly configured"""
    try:
        config = ZoomConfiguration.get_active_config()
        if not config:
            return False, "No Zoom configuration found. Please configure Zoom in admin panel."
        
        if not config.is_configured:
            missing_fields = []
            if not config.client_id:
                missing_fields.append("Client ID")
            if not config.client_secret:
                missing_fields.append("Client Secret")
            
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Test API connection
        try:
            service = ZoomAPIService(config)
            token = service.get_access_token()
            if token:
                return True, "Zoom configuration is valid"
            else:
                return False, "Failed to generate access token"
        except Exception as e:
            return False, f"Configuration error: {str(e)}"
            
    except Exception as e:
        return False, f"Configuration check failed: {str(e)}"


def create_zoom_meeting_for_session(session):
    """Create Zoom meeting for a session using ZoomAPIService"""
    try:
        # Check if session already has a Zoom meeting
        if session.zoom_meeting_id:
            return True, f"Session already has Zoom meeting: {session.zoom_meeting_id}"
        
        # Initialize Zoom API service
        service = ZoomAPIService()
        
        # Create meeting
        success, result = service.create_meeting(session)
        
        if success:
            return True, f"Zoom meeting created successfully: {result['id']}"
        else:
            return False, result
            
    except Exception as e:
        return False, f"Failed to create Zoom meeting: {str(e)}"


def update_zoom_meeting(session):
    """Update existing Zoom meeting"""
    try:
        if not session.zoom_meeting_id:
            return False, "No Zoom meeting found for this session"
        
        service = ZoomAPIService()
        success, result = service.update_meeting(session)
        
        if success:
            return True, "Zoom meeting updated successfully"
        else:
            return False, result
            
    except Exception as e:
        return False, f"Failed to update Zoom meeting: {str(e)}"


def delete_zoom_meeting(meeting_id):
    """Delete Zoom meeting"""
    try:
        service = ZoomAPIService()
        success, result = service.delete_meeting(meeting_id)
        
        if success:
            return True, "Zoom meeting deleted successfully"
        else:
            return False, result
            
    except Exception as e:
        return False, f"Failed to delete Zoom meeting: {str(e)}"


def get_zoom_meeting_details(meeting_id):
    """Get Zoom meeting details"""
    try:
        service = ZoomAPIService()
        success, result = service.get_meeting_details(meeting_id)
        
        if success:
            return True, result
        else:
            return False, result
            
    except Exception as e:
        return False, f"Failed to get meeting details: {str(e)}"


def create_bulk_zoom_meetings(sessions):
    """Create Zoom meetings for multiple sessions (for recurring sessions)"""
    results = {
        'success_count': 0,
        'failure_count': 0,
        'errors': []
    }
    
    try:
        service = ZoomAPIService()
        
        for session in sessions:
            try:
                if session.zoom_meeting_id:
                    # Skip if already has meeting
                    continue
                
                success, result = service.create_meeting(session)
                
                if success:
                    results['success_count'] += 1
                else:
                    results['failure_count'] += 1
                    results['errors'].append(f"Session {session.id}: {result}")
                    
            except Exception as e:
                results['failure_count'] += 1
                results['errors'].append(f"Session {session.id}: {str(e)}")
        
        return True, results
        
    except Exception as e:
        return False, f"Bulk meeting creation failed: {str(e)}"


def sync_zoom_recordings():
    """Sync recordings from Zoom for completed sessions"""
    try:
        # Get completed sessions that might have recordings
        from datetime import date, timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=30)  # Last 30 days
        
        completed_sessions = BatchSession.objects.filter(
            status='completed',
            scheduled_date__range=[start_date, end_date],
            zoom_meeting_id__isnull=False
        )
        
        service = ZoomAPIService()
        sync_count = 0
        
        for session in completed_sessions:
            try:
                # Check if recording already exists
                if ZoomRecording.objects.filter(session=session).exists():
                    continue
                
                success, recordings = service.get_meeting_recordings(session.zoom_meeting_id)
                
                if success and recordings:
                    for recording_data in recordings:
                        ZoomRecording.objects.create(
                            session=session,
                            recording_id=recording_data.get('id'),
                            recording_url=recording_data.get('play_url'),
                            download_url=recording_data.get('download_url'),
                            file_size=recording_data.get('file_size', 0),
                            recording_type=recording_data.get('recording_type', 'shared_screen_with_speaker_view'),
                            start_time=recording_data.get('recording_start'),
                            end_time=recording_data.get('recording_end')
                        )
                    sync_count += 1
                    
            except Exception as e:
                print(f"Error syncing recording for session {session.id}: {e}")
                continue
        
        return True, f"Synced recordings for {sync_count} sessions"
        
    except Exception as e:
        return False, f"Recording sync failed: {str(e)}"


def validate_zoom_meeting_url(url):
    """Validate Zoom meeting URL format"""
    if not url:
        return False, "URL is required"
    
    zoom_url_patterns = [
        'https://zoom.us/j/',
        'https://us02web.zoom.us/j/',
        'https://us04web.zoom.us/j/',
        'https://us05web.zoom.us/j/',
    ]
    
    if not any(url.startswith(pattern) for pattern in zoom_url_patterns):
        return False, "Invalid Zoom meeting URL format"
    
    return True, "Valid Zoom URL"


def extract_meeting_id_from_url(url):
    """Extract meeting ID from Zoom URL"""
    try:
        if '/j/' in url:
            meeting_id = url.split('/j/')[1].split('?')[0]
            return meeting_id
        return None
    except:
        return None


def format_meeting_time_for_zoom(session):
    """Format session time for Zoom API"""
    from datetime import datetime
    meeting_datetime = datetime.combine(session.scheduled_date, session.start_time)
    return meeting_datetime.strftime("%Y-%m-%dT%H:%M:%S")


def get_session_attendees(session):
    """Get list of users who can attend the session"""
    attendees = []
    
    # Get enrolled students
    enrollments = session.batch.enrollments.filter(is_active=True).select_related('student')
    for enrollment in enrollments:
        attendees.append({
            'email': enrollment.student.email,
            'name': enrollment.student.get_full_name() or enrollment.student.username,
            'role': 'student'
        })
    
    # Add instructor
    instructor = session.batch.instructor
    attendees.append({
        'email': instructor.email,
        'name': instructor.get_full_name() or instructor.username,
        'role': 'instructor'
    })
    
    # Add co-instructors if any
    for co_instructor in session.batch.course.co_instructors.all():
        attendees.append({
            'email': co_instructor.email,
            'name': co_instructor.get_full_name() or co_instructor.username,
            'role': 'co_instructor'
        })
    
    return attendees


def send_meeting_invitations(session):
    """Send meeting invitations to all attendees"""
    try:
        if not session.zoom_join_url:
            return False, "No Zoom meeting URL found"
        
        attendees = get_session_attendees(session)
        
        # Import here to avoid circular import
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        
        subject = f"Zoom Meeting Invitation: {session.title}"
        
        sent_count = 0
        failed_count = 0
        
        for attendee in attendees:
            try:
                # Render email template
                message = render_to_string('zoom/emails/meeting_invitation.html', {
                    'session': session,
                    'attendee': attendee,
                    'zoom_url': session.zoom_join_url,
                    'meeting_id': session.zoom_meeting_id,
                    'password': session.zoom_meeting_password
                })
                
                send_mail(
                    subject=subject,
                    message="", 
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[attendee['email']],
                    html_message=message,
                    fail_silently=False
                )
                
                sent_count += 1
                
            except Exception as e:
                print(f"Failed to send invitation to {attendee['email']}: {e}")
                failed_count += 1
                continue
        
        return True, f"Invitations sent: {sent_count}, Failed: {failed_count}"
        
    except Exception as e:
        return False, f"Failed to send invitations: {str(e)}"


def get_zoom_api_usage():
    """Get Zoom API usage statistics"""
    try:
        service = ZoomAPIService()
        
        # This would need to be implemented in ZoomAPIService
        # success, usage_data = service.get_api_usage()
        
        # For now, return basic stats from our database
        total_meetings = BatchSession.objects.filter(
            zoom_meeting_id__isnull=False
        ).count()
        
        active_meetings = BatchSession.objects.filter(
            status='live',
            zoom_meeting_id__isnull=False
        ).count()
        
        completed_meetings = BatchSession.objects.filter(
            status='completed',
            zoom_meeting_id__isnull=False
        ).count()
        
        usage_stats = {
            'total_meetings_created': total_meetings,
            'active_meetings': active_meetings,
            'completed_meetings': completed_meetings,
            'recordings_available': ZoomRecording.objects.count()
        }
        
        return True, usage_stats
        
    except Exception as e:
        return False, f"Failed to get usage stats: {str(e)}"


def cleanup_expired_meetings():
    """Clean up expired Zoom meetings"""
    try:
        from datetime import date, timedelta
        
        # Get sessions older than 7 days that are completed or cancelled
        cutoff_date = date.today() - timedelta(days=7)
        
        expired_sessions = BatchSession.objects.filter(
            scheduled_date__lt=cutoff_date,
            status__in=['completed', 'cancelled'],
            zoom_meeting_id__isnull=False
        )
        
        service = ZoomAPIService()
        cleaned_count = 0
        
        for session in expired_sessions:
            try:
                success, result = service.delete_meeting(session.zoom_meeting_id)
                if success:
                    # Clear Zoom data from session but keep the session
                    session.zoom_meeting_id = None
                    session.zoom_meeting_password = None
                    session.zoom_join_url = None
                    session.zoom_start_url = None
                    session.save()
                    cleaned_count += 1
                    
            except Exception as e:
                print(f"Error cleaning up meeting {session.zoom_meeting_id}: {e}")
                continue
        
        return True, f"Cleaned up {cleaned_count} expired meetings"
        
    except Exception as e:
        return False, f"Cleanup failed: {str(e)}"


def test_zoom_connection():
    """Test Zoom API connection"""
    try:
        service = ZoomAPIService()
        
        # Test by getting user information
        success, result = service.get_user_info()
        
        if success:
            return True, f"Connection successful. User: {result.get('email', 'Unknown')}"
        else:
            return False, result
            
    except Exception as e:
        return False, f"Connection test failed: {str(e)}"


# Recurring session specific utilities
def create_recurring_zoom_meetings(parent_session):
    """Create Zoom meetings for all sessions in a recurring series"""
    try:
        if not parent_session.is_recurring:
            return False, "Session is not part of a recurring series"
        
        # Get all sessions in the series
        all_sessions = parent_session.get_all_recurring_sessions()
        
        # Filter sessions that don't have Zoom meetings yet
        sessions_without_meetings = [s for s in all_sessions if not s.zoom_meeting_id]
        
        if not sessions_without_meetings:
            return True, "All sessions already have Zoom meetings"
        
        # Create meetings in bulk
        success, results = create_bulk_zoom_meetings(sessions_without_meetings)
        
        if success:
            return True, f"Created {results['success_count']} meetings, {results['failure_count']} failed"
        else:
            return False, results
            
    except Exception as e:
        return False, f"Failed to create recurring meetings: {str(e)}"


def update_recurring_zoom_meetings(parent_session, update_data):
    """Update all Zoom meetings in a recurring series"""
    try:
        if not parent_session.is_recurring:
            return False, "Session is not part of a recurring series"
        
        all_sessions = parent_session.get_all_recurring_sessions()
        sessions_with_meetings = [s for s in all_sessions if s.zoom_meeting_id]
        
        service = ZoomAPIService()
        updated_count = 0
        failed_count = 0
        
        for session in sessions_with_meetings:
            try:
                # Apply updates to session (if needed)
                for field, value in update_data.items():
                    if hasattr(session, field):
                        setattr(session, field, value)
                session.save()
                
                # Update Zoom meeting
                success, result = service.update_meeting(session)
                if success:
                    updated_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                continue
        
        return True, f"Updated {updated_count} meetings, {failed_count} failed"
        
    except Exception as e:
        return False, f"Failed to update recurring meetings: {str(e)}"


def delete_recurring_zoom_meetings(parent_session):
    """Delete all Zoom meetings in a recurring series"""
    try:
        if not parent_session.is_recurring:
            return False, "Session is not part of a recurring series"
        
        all_sessions = parent_session.get_all_recurring_sessions()
        sessions_with_meetings = [s for s in all_sessions if s.zoom_meeting_id]
        
        service = ZoomAPIService()
        deleted_count = 0
        failed_count = 0
        
        for session in sessions_with_meetings:
            try:
                success, result = service.delete_meeting(session.zoom_meeting_id)
                if success:
                    # Clear Zoom data
                    session.zoom_meeting_id = None
                    session.zoom_meeting_password = None
                    session.zoom_join_url = None
                    session.zoom_start_url = None
                    session.save()
                    deleted_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                continue
        
        return True, f"Deleted {deleted_count} meetings, {failed_count} failed"
        
    except Exception as e:
        return False, f"Failed to delete recurring meetings: {str(e)}"