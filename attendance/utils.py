from geopy.distance import geodesic

def is_within_allowed_location(lat, lon, session, radius_meters=100):
    """
    Checks whether student's location is within the allowed radius of the session's allowed location.
    """
    try:
        if not (lat and lon):
            print("⚠️ Missing latitude or longitude.")
            return False

        if not session.allowed_latitude or not session.allowed_longitude:
            print("⚠️ Session has no allowed location defined.")
            return True  # Skip restriction if location not set

        session_location = (session.allowed_latitude, session.allowed_longitude)
        student_location = (lat, lon)
        distance = geodesic(session_location, student_location).meters
        print(f"📏 Distance from allowed location: {distance:.2f} meters")

        return distance <= radius_meters
    except Exception as e:
        print(f"❌ Error in is_within_allowed_location: {e}")
        return False


# attendance/utils.py

from django.utils import timezone
from .models import AttendanceSession, Attendance
from courses.models import BatchEnrollment
import logging

logger = logging.getLogger(__name__)


def mark_absent_for_ended_sessions():
    """
    Automatically mark absent for students who didn't attend ended sessions
    """
    
    current_time = timezone.now()
    
    # Get sessions that ended but still active
    ended_sessions = AttendanceSession.objects.filter(
        is_active=True,
        end_time__lt=current_time
    )
    
    if ended_sessions.count() == 0:
        print("✅ No ended sessions to process")
        return 0
    
    print("=" * 60)
    print(f"🔍 AUTO-ABSENT CHECKER")
    print(f"⏰ Time: {timezone.localtime(current_time).strftime('%d/%m/%Y %I:%M %p')}")
    print(f"📊 Ended Sessions: {ended_sessions.count()}")
    print("=" * 60)
    
    total_marked = 0
    
    for session in ended_sessions:
        print(f"\n✅ Processing: {session.batch.name}")
        print(f"   Session: {session.start_time.strftime('%d/%m/%Y %I:%M %p')}")
        
        # Get enrolled students
        enrolled = BatchEnrollment.objects.filter(
            batch=session.batch,
            is_active=True
        ).values_list('student_id', flat=True)
        
        # Get who marked
        marked = Attendance.objects.filter(
            session=session
        ).values_list('student_id', flat=True)
        
        # Find who didn't mark
        unmarked_ids = set(enrolled) - set(marked)
        
        print(f"   👥 Total: {len(enrolled)} | ✅ Marked: {len(marked)} | ❌ Unmarked: {len(unmarked_ids)}")
        
        # Mark absent
        for student_id in unmarked_ids:
            try:
                from userss.models import CustomUser
                student = CustomUser.objects.get(id=student_id)
                
                Attendance.objects.create(
                    session=session,
                    student=student,
                    is_present=False,
                    is_late=False,
                    marking_method='manual',
                    notes='Auto-marked absent: Session ended without attendance'
                )
                total_marked += 1
                print(f"      ❌ Marked absent: {student.get_full_name()}")
                
            except Exception as e:
                logger.error(f"Error marking absent for student {student_id}: {str(e)}")
                print(f"      ⚠️ Error: {str(e)}")
        
        # Deactivate session
        session.is_active = False
        session.save()
        print(f"   🔒 Session deactivated")
    
    print("=" * 60)
    print(f"✅ COMPLETED: Marked {total_marked} students as absent")
    print("=" * 60)
    
    return total_marked