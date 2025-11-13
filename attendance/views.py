# attendance/views.py - COMPLETE WITH SUPERADMIN ACCESS

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Q, Count, Avg
import json
from .models import AttendanceSession, Attendance, ManualAttendanceRequest
from courses.models import BatchEnrollment, Batch

# Helper function for role-based redirects
def get_dashboard_url(user):
    """Return appropriate dashboard URL based on user role"""
    if user.role == 'superadmin':
        return 'admin_dashboard'
    elif user.role == 'instructor':
        return 'instructor_dashboard'
    elif user.role == 'student':
        return 'student_dashboard'
    return 'user_login'

# ==================== INSTRUCTOR/SUPERADMIN - CREATE SESSION ====================
from django.utils import timezone
from datetime import datetime

@login_required
def create_session(request):
    """Instructor/Superadmin creates attendance session with Google Maps"""
    
    if request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'Only instructors/admins can create sessions!')
        return redirect(get_dashboard_url(request.user))
    
    # Get batches based on role
    if request.user.role == 'superadmin':
        instructor_batches = Batch.objects.filter(is_active=True)
    else:
        instructor_batches = Batch.objects.filter(
            instructor=request.user,
            is_active=True
        )
    
    # Get sessions based on role and set base template
    if request.user.role == 'superadmin':
        base_template = 'base.html'
        page_title = 'All Attendance Sessions'
    else:
        base_template = 'instructor_base.html'
        page_title = 'My Attendance Sessions'

    if request.method == 'POST':
        try:
            batch_id = request.POST.get('batch')
            date = request.POST.get('date')  # Format: YYYY-MM-DD
            start_time = request.POST.get('start_time')  # Format: HH:MM
            end_time = request.POST.get('end_time')  # Format: HH:MM
            classroom_location = request.POST.get('classroom_location')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            radius = request.POST.get('allowed_radius_meters', 50)
            
            # ✅ COMBINE DATE + TIME INTO DATETIME
            try:
                # Parse date string (YYYY-MM-DD)
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                
                # Parse time strings (HH:MM)
                start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                end_time_obj = datetime.strptime(end_time, '%H:%M').time()
                
                # Combine date + time
                start_datetime = datetime.combine(date_obj, start_time_obj)
                end_datetime = datetime.combine(date_obj, end_time_obj)
                
                # Make timezone aware (Asia/Kolkata)
                start_datetime = timezone.make_aware(start_datetime)
                end_datetime = timezone.make_aware(end_datetime)
                
                print(f"Start DateTime: {start_datetime}")
                print(f"End DateTime: {end_datetime}")
                
            except ValueError as e:
                messages.error(request, f'Invalid date/time format: {str(e)}')
                return render(request, 'attendance/create_session.html', {
                    'batches': instructor_batches,
                    'page_title': 'Create Attendance Session',
                    'today': timezone.now().date(),
                    'base_template': base_template
                })
            
            # Validate times
            if start_datetime >= end_datetime:
                messages.error(request, 'End time must be after start time!')
                return render(request, 'attendance/create_session.html', {
                    'batches': instructor_batches,
                    'page_title': 'Create Attendance Session',
                    'today': timezone.now().date(),
                    'base_template': base_template
                })
            
            # Get batch and instructor
            batch = Batch.objects.get(id=batch_id)
            instructor = batch.instructor if request.user.role == 'superadmin' else request.user
            
            # Validate location data
            if not latitude or not longitude:
                messages.error(request, 'Classroom location (lat/long) is required!')
                return render(request, 'attendance/create_session.html', {
                    'batches': instructor_batches,
                    'page_title': 'Create Attendance Session',
                    'today': timezone.now().date(),
                    'base_template': base_template
                })
            
            # Create session with DateTime fields
            session = AttendanceSession.objects.create(
                batch=batch,
                instructor=instructor,
                start_time=start_datetime,  # ✅ DateTime object
                end_time=end_datetime,      # ✅ DateTime object
                classroom_location=classroom_location,
                latitude=latitude,
                longitude=longitude,
                allowed_radius_meters=radius
            )
            
            messages.success(request, f'Attendance session created! QR Code generated.')
            return redirect('attendance:session_detail', session_id=session.id)
            
        except Batch.DoesNotExist:
            messages.error(request, 'Batch not found!')
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"ERROR: {error_trace}")
            messages.error(request, f'Error: {str(e)}')
    
    context = {
        'batches': instructor_batches,
        'page_title': 'Create Attendance Session',
        'today': timezone.now().date(),
        'base_template': base_template
    }
    
    return render(request, 'attendance/create_session.html', context)

# ==================== INSTRUCTOR/SUPERADMIN - SESSION LIST ====================
# attendance/views.py - instructor_sessions with DEBUGGING

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Q
from datetime import datetime

from .models import AttendanceSession, Attendance
from courses.models import Batch, BatchEnrollment

User = get_user_model()


@login_required
def instructor_sessions(request):
    """
    View all attendance sessions
    - Superadmin: ALL sessions
    - Instructor: Only their sessions
    """
    
    # ✅ Debug: Print user info
    print(f"\n=== USER INFO ===")
    print(f"Username: {request.user.username}")
    print(f"Role: {request.user.role}")
    print(f"Is Superadmin: {request.user.role == 'superadmin'}")
    print(f"Is Instructor: {request.user.role == 'instructor'}")
    
    # ✅ Check role and get sessions
    if request.user.role == 'superadmin':
        sessions = AttendanceSession.objects.all()
        page_title = 'All Attendance Sessions (Superadmin View)'
        is_superadmin = True
        base_template = 'base.html'
        
        # Debug: Count sessions
        print(f"\n✅ SUPERADMIN MODE")
        print(f"Total Sessions in DB: {AttendanceSession.objects.count()}")
        print(f"Active Sessions: {AttendanceSession.objects.filter(is_active=True).count()}")
        
    elif request.user.role == 'instructor':
        sessions = AttendanceSession.objects.filter(
            batch__instructor=request.user
        )
        page_title = 'My Attendance Sessions'
        is_superadmin = False
        base_template = 'instructor_base.html'
        
        # Debug: Count instructor sessions
        print(f"\n✅ INSTRUCTOR MODE")
        print(f"My Sessions: {sessions.count()}")
        
    else:
        messages.error(request, 'Access denied - Invalid role')
        return redirect('dashboard')
    
    # ✅ Optimize query
    sessions = sessions.select_related(
        'batch', 
        'batch__instructor',
        'batch__course'
    ).prefetch_related(
        'attendances'
    ).order_by('-start_time')
    
    # Debug: Print sessions
    print(f"\n=== SESSIONS LIST ===")
    for idx, session in enumerate(sessions[:5], 1):  # First 5 only
        print(f"{idx}. {session.batch.name} | {session.start_time} | Instructor: {session.batch.instructor.username}")
    
    # ✅ Filters
    date_filter = request.GET.get('date')
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            sessions = sessions.filter(start_time__date=filter_date)
            print(f"\n📅 Date Filter Applied: {filter_date}")
        except:
            pass
    
    search = request.GET.get('search')
    if search:
        sessions = sessions.filter(
            Q(batch__name__icontains=search) |
            Q(batch__course__title__icontains=search) |
            Q(classroom_location__icontains=search)
        )
        print(f"\n🔍 Search Applied: {search}")
    
    # ✅ Calculate stats
    sessions_data = []
    for session in sessions:
        # Get students from BatchEnrollment
        total_students = BatchEnrollment.objects.filter(
            batch=session.batch,
            is_active=True
        ).count()
        
        present_count = session.attendances.filter(is_present=True).count()
        late_count = session.attendances.filter(is_late=True).count()
        
        percentage = round((present_count / total_students) * 100, 2) if total_students > 0 else 0
        
        sessions_data.append({
            'session': session,
            'total_students': total_students,
            'present_count': present_count,
            'absent_count': total_students - present_count,
            'late_count': late_count,
            'percentage': percentage,
            'is_ongoing': session.is_open_now(),
        })
    
    print(f"\n✅ Total sessions to display: {len(sessions_data)}")
    
    # ✅ Filters for superadmin
    all_batches = None
    all_instructors = None
    
    if is_superadmin:
        all_batches = Batch.objects.all().select_related('instructor', 'course')
        all_instructors = User.objects.filter(role='instructor').order_by('first_name')
        
        print(f"\n📊 Superadmin Filters:")
        print(f"Total Batches: {all_batches.count()}")
        print(f"Total Instructors: {all_instructors.count()}")
    
    context = {
        'sessions_data': sessions_data,
        'all_batches': all_batches,
        'all_instructors': all_instructors,
        'page_title': page_title,
        'base_template': base_template,
        'is_superadmin': is_superadmin,
        'search': search,
        'date_filter': date_filter,
    }
    
    return render(request, 'attendance/instructor_sessions.html', context)




@login_required
def session_detail(request, session_id):
    """View session details and attendance list"""
    
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    # Check permission
    if request.user.role == 'instructor' and session.instructor != request.user:
        messages.error(request, 'Access denied!')
        return redirect('attendance:instructor_sessions')
    
    # Get all enrolled students
    enrolled_students = BatchEnrollment.objects.filter(
        batch=session.batch,
        is_active=True
    ).select_related('student')
    
    # Get attendance records
    attendances = session.attendances.select_related('student').order_by('-marked_at')
    attendance_dict = {a.student_id: a for a in attendances}
    
    # Get pending manual requests
    pending_requests = ManualAttendanceRequest.objects.filter(
        session=session,
        status='pending'
    ).select_related('student')
     # Get sessions based on role and set base template
    if request.user.role == 'superadmin':
        # sessions = AttendanceSession.objects.all()
        base_template = 'base.html'  # ✅ ADD THIS
        page_title = 'All Attendance Sessions'
    else:
        # sessions = AttendanceSession.objects.filter(instructor=request.user)
        base_template = 'instructor_base.html'  # ✅ ADD THIS
        page_title = 'My Attendance Sessions'
    # Prepare student list with attendance status
    student_list = []
    for enrollment in enrolled_students:
        student = enrollment.student
        attendance = attendance_dict.get(student.id)
        
        student_list.append({
            'student': student,
            'attendance': attendance,
            'has_attendance': attendance is not None,
            'status': 'Present' if attendance and attendance.is_present else 'Absent',
            'is_late': attendance.is_late if attendance else False,
            'distance': attendance.distance_from_classroom if attendance else None,
            'marked_at': attendance.marked_at if attendance else None,
            'method': attendance.get_marking_method_display() if attendance else None
        })
    
    stats = session.get_stats()
    
    context = {
        'session': session,
        'student_list': student_list,
        'pending_requests': pending_requests,
        'stats': stats,
        'page_title': f'Session - {session.batch.name}',
        'is_instructor': request.user == session.instructor or request.user.role == 'superadmin',
        'base_template': base_template
    }
    
    return render(request, 'attendance/session_detail.html', context)


# ==================== STUDENT - QR SCANNER ====================

@login_required
def student_scanner(request):
    """QR code scanner page for students"""
    
    if request.user.role != 'student':
        messages.error(request, 'Only students can scan QR codes!')
        return redirect(get_dashboard_url(request.user))
    
    context = {
        'page_title': 'Scan QR Code for Attendance'
    }
    
    return render(request, 'attendance/student_scanner.html', context)



@login_required
@require_POST
def mark_attendance_qr(request):
    """Mark attendance via QR code scan with location verification"""
    
    if request.user.role != 'student':
        return JsonResponse({
            'success': False,
            'message': 'Only students can mark attendance!'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        qr_data = data.get('qr_data', '')
        student_lat = data.get('latitude')
        student_lon = data.get('longitude')
        
        # Validate QR data
        if not qr_data.startswith('ATTENDANCE:'):
            return JsonResponse({
                'success': False,
                'message': 'Invalid QR code!'
            })
        
        # Parse QR data
        try:
            _, session_id, qr_secret = qr_data.split(':')
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid QR code format!'
            })
        
        # Get session
        try:
            session = AttendanceSession.objects.get(
                id=session_id,
                qr_secret=qr_secret,
                is_active=True
            )
        except AttendanceSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid or expired QR code!'
            })
        
        # ===== DEBUGGING START =====
        from django.utils import timezone
        import logging
        
        logger = logging.getLogger(__name__)
        current_time = timezone.now()
        
        debug_info = {
            'current_datetime': str(current_time),
            'current_timezone': str(timezone.get_current_timezone()),
            'session_start_time': str(session.start_time),
            'session_end_time': str(session.end_time),
            'session_start_type': type(session.start_time).__name__,
            'session_end_type': type(session.end_time).__name__,
        }
        
        logger.info(f"DEBUG ATTENDANCE: {debug_info}")
        print("="*60)
        print("DEBUGGING ATTENDANCE SESSION CHECK")
        print("="*60)
        print(f"Current DateTime: {current_time}")
        print(f"Current Timezone: {timezone.get_current_timezone()}")
        print(f"Session Start: {session.start_time} (Type: {type(session.start_time).__name__})")
        print(f"Session End: {session.end_time} (Type: {type(session.end_time).__name__})")
        print(f"Session is_active: {session.is_active}")
        print("="*60)
        
        # Check if session is open
        is_open = session.is_open_now()
        print(f"is_open_now() result: {is_open}")
        
        if hasattr(session, 'start_time') and hasattr(session, 'end_time'):
            # Manual time check
            current_time_only = current_time.time()
            start_time_only = session.start_time.time() if hasattr(session.start_time, 'time') else session.start_time
            end_time_only = session.end_time.time() if hasattr(session.end_time, 'time') else session.end_time
            
            print(f"\nManual Check (Time Only):")
            print(f"  Current Time: {current_time_only}")
            print(f"  Start Time: {start_time_only}")
            print(f"  End Time: {end_time_only}")
            print(f"  Between? {start_time_only <= current_time_only <= end_time_only}")
        
        print("="*60)
        # ===== DEBUGGING END =====
        
        if not is_open:
            return JsonResponse({
                'success': False,
                'message': f'Session closed! Time: {session.start_time.strftime("%I:%M %p")} - {session.end_time.strftime("%I:%M %p")}',
                'debug': debug_info  # Frontend mein dekh sakta hai
            })
        
        # Check enrollment
        if not BatchEnrollment.objects.filter(
            student=request.user,
            batch=session.batch,
            is_active=True
        ).exists():
            return JsonResponse({
                'success': False,
                'message': 'You are not enrolled in this batch!'
            })
        
        # Check if already marked
        if Attendance.objects.filter(session=session, student=request.user).exists():
            return JsonResponse({
                'success': False,
                'message': 'Attendance already marked!'
            })
        
        # Validate location
        if not student_lat or not student_lon:
            return JsonResponse({
                'success': False,
                'message': 'Location permission required!'
            })
        
        # Create attendance
        attendance = Attendance.objects.create(
            session=session,
            student=request.user,
            marking_method='qr_scan',
            student_latitude=student_lat,
            student_longitude=student_lon
        )
        
        # Verify location
        is_valid = attendance.verify_location()
        
        if not is_valid:
            # Mark as absent - outside radius
            attendance.is_present = False
            attendance.save()
            
            return JsonResponse({
                'success': False,
                'message': f'Too far! You are {attendance.distance_from_classroom}m away. Max: {session.allowed_radius_meters}m',
                'can_request': True  # Allow manual request
            })
        
        # Check if late (compare datetime with datetime, not time with datetime!)
        current_datetime = timezone.now()
        if current_datetime > session.start_time:
            attendance.is_late = True
            attendance.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Attendance marked!' + (' (Late)' if attendance.is_late else ''),
            'data': {
                'distance': attendance.distance_from_classroom,
                'marked_at': attendance.marked_at.strftime('%I:%M %p'),
                'is_late': attendance.is_late
            }
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"ATTENDANCE ERROR: {error_trace}")
        print("ERROR TRACE:")
        print(error_trace)
        
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}',
            'error_trace': error_trace  # Development mein hi dekh
        }, status=500)
# ==================== STUDENT - MANUAL REQUEST ====================
from django.views.decorators.http import require_http_methods

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from attendance.models import AttendanceSession, Attendance, ManualAttendanceRequest
from .utils import is_within_allowed_location


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_manual_attendance(request, session_id):
    print("=" * 60)
    print("🔍 DEBUG MANUAL REQUEST STARTED")
    print(f"Session ID: {session_id}")
    print(f"User: {request.user.username} ({getattr(request.user, 'role', 'N/A')})")
    print("=" * 60)

    data = request.data
    reason = data.get("reason", "")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    print(f"📍 Location Data:")
    print(f"  Reason: {reason}")
    print(f"  Latitude: {latitude}")
    print(f"  Longitude: {longitude}")

    try:
        session = AttendanceSession.objects.get(id=session_id)
    except AttendanceSession.DoesNotExist:
        print("❌ Invalid Session ID")
        return Response({"error": "Invalid session"}, status=404)

    print(f"✅ Session: {session.batch.name} | Instructor: {session.instructor}")

    # Check enrollment
    from courses.models import BatchEnrollment
    if not BatchEnrollment.objects.filter(
        student=request.user,
        batch=session.batch,
        is_active=True
    ).exists():
        print("❌ Student not enrolled!")
        return Response({"error": "You are not enrolled in this batch!"}, status=403)

    # Check if attendance already exists and is PRESENT
    existing_attendance = Attendance.objects.filter(
        session=session, 
        student=request.user
    ).first()
    
    if existing_attendance and existing_attendance.is_present:
        print("✅ Attendance already marked as PRESENT")
        return Response({
            "error": "Attendance already marked as present!"
        }, status=400)

    # ✅ Check for existing requests
    existing_request = ManualAttendanceRequest.objects.filter(
        session=session,
        student=request.user
    ).first()
    
    if existing_request:
        print(f"⚠️ Existing request found - Status: {existing_request.status}")
        
        # If approved, don't allow new request
        if existing_request.status == 'approved':
            return Response({
                "error": "Your request has already been approved!"
            }, status=400)
        
        # If pending, inform user
        if existing_request.status == 'pending':
            return Response({
                "error": "You already have a pending request. Please wait for instructor approval.",
                "request_id": existing_request.id
            }, status=400)
        
        # ✅ If rejected, allow resubmission by updating existing request
        if existing_request.status == 'rejected':
            print(f"🔄 Updating rejected request (ID: {existing_request.id})")
            existing_request.reason = reason
            existing_request.request_latitude = latitude
            existing_request.request_longitude = longitude
            existing_request.status = 'pending'  # ✅ Reset to pending
            existing_request.approved_by = None
            existing_request.approved_at = None
            existing_request.admin_notes = ''
            existing_request.save()
            
            print(f"✅ Request updated and resubmitted (ID: {existing_request.id})")
            return Response({
                "success": "Your request has been resubmitted successfully!",
                "request_id": existing_request.id,
                "message": "Your previous request was rejected. This is a new submission."
            }, status=200)

    # ✅ CREATE NEW REQUEST
    manual_request = ManualAttendanceRequest.objects.create(
        session=session,
        student=request.user,
        reason=reason,
        request_latitude=latitude,
        request_longitude=longitude,
        status='pending'
    )

    print(f"✅ New Manual Request Created (ID: {manual_request.id})")
    print(f"   Location: ({latitude}, {longitude})")
    print("=" * 60)
    
    return Response({
        "success": "Manual attendance request submitted successfully!",
        "request_id": manual_request.id,
        "message": "Your request has been sent to the instructor for approval."
    }, status=200)
#
# 
# 
@login_required
def pending_requests(request):
    """Instructor/Superadmin views pending manual attendance requests"""
    
    if request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'Access denied!')
        return redirect(get_dashboard_url(request.user))
    
    # Get requests based on role
    if request.user.role == 'superadmin':
        requests_list = ManualAttendanceRequest.objects.filter(status='pending')
        base_template = 'base.html'  # ✅ Superadmin ke liye
    else:
        requests_list = ManualAttendanceRequest.objects.filter(
            session__instructor=request.user,
            status='pending'
        )
        base_template = 'instructor_base.html'  # ✅ Instructor ke liye
    
    requests_list = requests_list.select_related(
        'session', 'student', 'session__batch', 'session__instructor'
    ).order_by('-created_at')
    
    context = {
        'requests': requests_list,
        'page_title': 'Pending Attendance Requests',
        'base_template': base_template  # ✅ Template ko bhejo
    }
    
    return render(request, 'attendance/pending_requests.html', context)

@login_required
def approve_manual_request(request, request_id):
    """Approve a manual attendance request"""
    
    if request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'Access denied!')
        return redirect(get_dashboard_url(request.user))
    
    try:
        # Get request based on role
        if request.user.role == 'superadmin':
            manual_req = ManualAttendanceRequest.objects.select_related(
                'session', 'student'
            ).get(id=request_id, status='pending')
        else:
            manual_req = ManualAttendanceRequest.objects.select_related(
                'session', 'student'
            ).get(id=request_id, session__instructor=request.user, status='pending')
        
        print("="*60)
        print(f"🔍 APPROVING REQUEST {request_id}")
        print(f"   Student: {manual_req.student.get_full_name()}")
        print(f"   Session: {manual_req.session.batch.name}")
        print(f"   Location: ({manual_req.request_latitude}, {manual_req.request_longitude})")
        print("="*60)
        
        # Check if attendance already exists
        existing = Attendance.objects.filter(
            session=manual_req.session,
            student=manual_req.student
        ).first()
        
        if existing:
            print(f"⚠️ Attendance EXISTS - Present: {existing.is_present}")
            
            # ✅ UPDATE existing attendance to PRESENT
            existing.is_present = True
            existing.is_late = False
            existing.marking_method = 'manual'
            existing.marked_by_instructor = request.user
            existing.notes = f"Manual request approved. Reason: {manual_req.reason[:100]}"
            existing.save()
            
            print(f"✅ Updated existing attendance to PRESENT")
        else:
            # ✅ CREATE new attendance record
            admin_notes = request.POST.get('admin_notes', '').strip()
            notes_text = f"Manual request approved. Reason: {manual_req.reason[:100]}"
            if admin_notes:
                notes_text += f"\nAdmin Notes: {admin_notes}"
            
            attendance = Attendance.objects.create(
                session=manual_req.session,
                student=manual_req.student,
                is_present=True,  # ✅ PRESENT
                is_late=False,
                marking_method='manual',
                marked_by_instructor=request.user,
                student_latitude=manual_req.request_latitude,   # ✅ Use saved location
                student_longitude=manual_req.request_longitude, # ✅ Use saved location
                notes=notes_text,
                is_within_radius=True  # ✅ Manual approval = within radius
            )
            
            print(f"✅ Created NEW attendance - Present: {attendance.is_present}")
        
        # ✅ UPDATE request status
        admin_notes = request.POST.get('admin_notes', '').strip()
        manual_req.status = 'approved'
        manual_req.approved_by = request.user
        manual_req.approved_at = timezone.now()
        manual_req.admin_notes = admin_notes
        manual_req.save()
        
        print(f"✅ Request status updated to APPROVED")
        print("="*60)
        
        messages.success(
            request, 
            f'✅ Approved manual attendance for {manual_req.student.get_full_name()}'
        )
        
        return redirect('attendance:pending_requests')
        
    except ManualAttendanceRequest.DoesNotExist:
        messages.error(request, '❌ Request not found or already processed!')
        return redirect('attendance:pending_requests')
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("="*60)
        print("❌ ERROR IN APPROVE_MANUAL_REQUEST:")
        print(error_trace)
        print("="*60)
        messages.error(request, f'Error: {str(e)}')
        return redirect('attendance:pending_requests')

@login_required
def reject_manual_request(request, request_id):
    """Reject a manual attendance request"""
    
    if request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'Access denied!')
        return redirect(get_dashboard_url(request.user))
    
    try:
        # Get request based on role
        if request.user.role == 'superadmin':
            manual_req = ManualAttendanceRequest.objects.get(
                id=request_id, 
                status='pending'
            )
        else:
            manual_req = ManualAttendanceRequest.objects.get(
                id=request_id, 
                session__instructor=request.user,
                status='pending'
            )
        
        # Get rejection reason from POST
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        
        manual_req.status = 'rejected'
        manual_req.approved_by = request.user
        manual_req.approved_at = timezone.now()
        manual_req.admin_notes = rejection_reason  # Save rejection reason
        manual_req.save()
        
        messages.success(
            request, 
            f'❌ Rejected request from {manual_req.student.get_full_name()}'
        )
        
        return redirect('attendance:pending_requests')
        
    except ManualAttendanceRequest.DoesNotExist:
        messages.error(request, 'Request not found or already processed!')
        return redirect('attendance:pending_requests')
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("="*60)
        print("ERROR IN REJECT_MANUAL_REQUEST:")
        print(error_trace)
        print("="*60)
        messages.error(request, f'Error: {str(e)}')
        return redirect('attendance:pending_requests')
# ==================== MANUAL MARK ATTENDANCE ====================


@login_required
def manual_mark_attendance(request, session_id, student_id):
    """Instructor/Superadmin manually marks attendance for individual student"""
    
    if request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'Only instructors/admins can mark attendance!')
        return redirect(get_dashboard_url(request.user))
    
    from userss.models import CustomUser  # ✅ Correct import
    from courses.models import BatchEnrollment
    
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    # Check permission
    if request.user.role == 'instructor' and session.instructor != request.user:
        messages.error(request, 'Access denied!')
        return redirect('attendance:instructor_sessions')
    
    # ✅ Use CustomUser instead of User
    student = get_object_or_404(CustomUser, id=student_id, role='student')
    
    # Check enrollment
    if not BatchEnrollment.objects.filter(
        student=student,
        batch=session.batch,
        is_active=True
    ).exists():
        messages.error(request, 'Student not enrolled in this batch!')
        return redirect('attendance:session_detail', session_id=session_id)
    
    # Get existing attendance
    existing_attendance = Attendance.objects.filter(
        session=session,
        student=student
    ).first()
    
    if request.method == 'POST':
        status = request.POST.get('status')
        is_late = request.POST.get('is_late', 'no') == 'yes'
        notes = request.POST.get('notes', '').strip()
        
        if status not in ['present', 'absent']:
            messages.error(request, 'Invalid status!')
            return redirect(request.path)
        
        is_present = (status == 'present')
        
        if existing_attendance:
            # Update existing
            existing_attendance.is_present = is_present
            existing_attendance.is_late = is_late if is_present else False
            existing_attendance.notes = notes
            existing_attendance.marked_by_instructor = request.user
            existing_attendance.marking_method = 'manual'
            existing_attendance.save()
            messages.success(request, 'Attendance updated successfully!')
        else:
            # Create new
            Attendance.objects.create(
                session=session,
                student=student,
                is_present=is_present,
                is_late=is_late if is_present else False,
                marking_method='manual',
                marked_by_instructor=request.user,
                notes=notes
            )
            messages.success(request, 'Attendance marked successfully!')
        
        return redirect('attendance:session_detail', session_id=session_id)
    
    stats = session.get_stats()
    
    context = {
        'session': session,
        'student': student,
        'existing_attendance': existing_attendance,
        'stats': stats,
        'page_title': f'Mark Attendance - {student.get_full_name()}'
    }
    
    return render(request, 'attendance/manual_mark.html', context)


# ==================== MARK ATTENDANCE PAGE ====================

@login_required
def mark_attendance(request, session_id):
    """Instructor/Superadmin marks attendance for multiple students"""
    
    if request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'Only instructors/admins can mark attendance!')
        return redirect(get_dashboard_url(request.user))
    
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    # Check permission
    if request.user.role == 'instructor' and session.instructor != request.user:
        messages.error(request, 'Access denied!')
        return redirect('attendance:instructor_sessions')
    
    enrolled_students = BatchEnrollment.objects.filter(
        batch=session.batch,
        is_active=True
    ).select_related('student')
    
    attendances = Attendance.objects.filter(session=session).select_related('student')
    attendance_dict = {a.student_id: a for a in attendances}
    
    students = []
    for enrollment in enrolled_students:
        student = enrollment.student
        attendance = attendance_dict.get(student.id)
        students.append({
            'student': student,
            'attendance': attendance
        })
    
    stats = session.get_stats()
    
    context = {
        'session': session,
        'students': students,
        'stats': stats,
        'page_title': f'Mark Attendance - {session.batch.name}'
    }
    
    return render(request, 'attendance/mark_attendance.html', context)


@login_required
def mark_attendance_instructor(request, session_id):
    """Instructor/Superadmin marks attendance for multiple students"""
    
    if request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'Only instructors/admins can mark attendance!')
        return redirect(get_dashboard_url(request.user))
    
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    # Check permission
    if request.user.role == 'instructor' and session.instructor != request.user:
        messages.error(request, 'Access denied!')
        return redirect('attendance:instructor_sessions')
    
    enrolled_students = BatchEnrollment.objects.filter(
        batch=session.batch,
        is_active=True
    ).select_related('student')
    
    attendances = Attendance.objects.filter(session=session).select_related('student')
    attendance_dict = {a.student_id: a for a in attendances}
    
    students = []
    for enrollment in enrolled_students:
        student = enrollment.student
        attendance = attendance_dict.get(student.id)
        students.append({
            'student': student,
            'attendance': attendance
        })
    
    stats = session.get_stats()
    
    context = {
        'session': session,
        'students': students,
        'stats': stats,
        'page_title': f'Mark Attendance - {session.batch.name}'
    }
    
    return render(request, 'attendance/mark_attendance_instructor.html', context)


# ==================== MARK SELECTED ====================

@login_required
@require_POST
def mark_selected_attendance(request, session_id):
    """Mark selected students (AJAX)"""
    
    if request.user.role not in ['instructor', 'superadmin']:
        return JsonResponse({'success': False, 'message': 'Access denied!'}, status=403)
    
    try:
        session = get_object_or_404(AttendanceSession, id=session_id)
        
        # Check permission
        if request.user.role == 'instructor' and session.instructor != request.user:
            return JsonResponse({'success': False, 'message': 'Access denied!'}, status=403)
        
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        status = data.get('status', 'present')
        is_late = data.get('is_late', False)
        
        if not student_ids:
            return JsonResponse({'success': False, 'message': 'No students selected!'})
        
        is_present = (status == 'present')
        marked_count = 0
        
        from userss.models import AbstractUser
        students = User.objects.filter(id__in=student_ids, role='student')
        
        for student in students:
            if not BatchEnrollment.objects.filter(
                student=student,
                batch=session.batch,
                is_active=True
            ).exists():
                continue
            
            attendance, created = Attendance.objects.update_or_create(
                session=session,
                student=student,
                defaults={
                    'is_present': is_present,
                    'is_late': is_late if is_present else False,
                    'marking_method': 'manual',
                    'marked_by_instructor': request.user
                }
            )
            marked_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Marked {marked_count} student(s) as {status}!'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ==================== BULK MARK ====================

@login_required
@require_POST
def bulk_mark_attendance(request, session_id):
    """Mark all unmarked students"""
    
    if request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'Access denied!')
        return redirect(get_dashboard_url(request.user))
    
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    # Check permission
    if request.user.role == 'instructor' and session.instructor != request.user:
        messages.error(request, 'Access denied!')
        return redirect('attendance:session_detail', session_id=session_id)
    
    status = request.POST.get('status')
    
    if status not in ['present', 'absent']:
        messages.error(request, 'Invalid status!')
        return redirect('attendance:session_detail', session_id=session_id)
    
    is_present = (status == 'present')
    
    enrolled_students = BatchEnrollment.objects.filter(
        batch=session.batch,
        is_active=True
    ).values_list('student_id', flat=True)
    
    marked_students = Attendance.objects.filter(
        session=session
    ).values_list('student_id', flat=True)
    
    unmarked_student_ids = set(enrolled_students) - set(marked_students)
    
    marked_count = 0
    from users.models import User
    for student_id in unmarked_student_ids:
        student = User.objects.get(id=student_id)
        Attendance.objects.create(
            session=session,
            student=student,
            is_present=is_present,
            marking_method='manual',
            marked_by_instructor=request.user,
            notes=f'Bulk marked as {status}'
        )
        marked_count += 1
    
    messages.success(request, f'Marked {marked_count} unmarked student(s) as {status}!')
    return redirect('attendance:session_detail', session_id=session_id)


# ==================== STUDENT VIEWS ====================

@login_required
def student_my_attendance(request):
    """Student views their own attendance records + ALL sessions (past + upcoming)"""
    
    if request.user.role != 'student':
        messages.error(request, 'Only students can access this!')
        return redirect('home')
    
    from django.utils import timezone
    from datetime import datetime, timedelta
    from django.db.models import Count, Q
    from courses.models import BatchEnrollment
    
    # Get all attendance records for this student
    attendances = Attendance.objects.filter(
        student=request.user
    ).select_related(
        'session', 
        'session__batch'
    ).order_by('-session__created_at', '-session__start_time')
    
    # Calculate overall stats
    total_sessions = attendances.count()
    present_count = attendances.filter(is_present=True).count()
    absent_count = attendances.filter(is_present=False).count()
    late_count = attendances.filter(is_late=True, is_present=True).count()
    
    # Calculate percentage
    attendance_percentage = 0
    if total_sessions > 0:
        attendance_percentage = (present_count / total_sessions) * 100
    
    # 📅 Get ALL sessions for enrolled batches
    enrolled_batches = BatchEnrollment.objects.filter(
        student=request.user,
        is_active=True
    ).values_list('batch_id', flat=True)
    
    # ✅ Get ALL active sessions
    all_sessions = AttendanceSession.objects.filter(
        batch_id__in=enrolled_batches,
        is_active=True
    ).select_related('batch').order_by('-start_time')
    
    # Get current time
    current_time = timezone.now()
    
    # ✅ CREATE DICT - session_id → attendance object
    attendance_dict = {
        att.session_id: att for att in Attendance.objects.filter(
            student=request.user,
            session__in=all_sessions
        ).select_related('session')
    }
    
    # 🎯 Add status + attendance info to each session
    sessions_with_status = []
    for session in all_sessions:
        is_upcoming = session.start_time > current_time
        is_running = session.start_time <= current_time <= session.end_time if session.end_time else False
        is_past = session.end_time < current_time if session.end_time else session.start_time < current_time
        
        # ✅ CHECK if attendance exists for this session
        attendance_record = attendance_dict.get(session.id)
        
        # ✅ CHECK if manual request exists
        has_pending_request = ManualAttendanceRequest.objects.filter(
            session=session,
            student=request.user,
            status='pending'
        ).exists()
        
        sessions_with_status.append({
            'session': session,
            'is_upcoming': is_upcoming,
            'is_running': is_running,
            'is_past': is_past,
            'status': 'upcoming' if is_upcoming else ('running' if is_running else 'past'),
            # ✅ NEW FIELDS
            'attendance': attendance_record,
            'has_attendance': attendance_record is not None,
            'is_present': attendance_record.is_present if attendance_record else False,
            'is_late': attendance_record.is_late if attendance_record else False,
            'has_pending_request': has_pending_request,
        })
    
    # Optional: Filter by batch
    batch_id = request.GET.get('batch')
    if batch_id:
        attendances = attendances.filter(session__batch_id=batch_id)
    
    # Optional: Filter by date range
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    if from_date:
        try:
            from_datetime = timezone.make_aware(
                datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            )
            attendances = attendances.filter(session__created_at__gte=from_datetime)
        except ValueError:
            messages.warning(request, 'Invalid from_date format. Use YYYY-MM-DD')
    
    if to_date:
        try:
            to_datetime = timezone.make_aware(
                datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            )
            attendances = attendances.filter(session__created_at__lte=to_datetime)
        except ValueError:
            messages.warning(request, 'Invalid to_date format. Use YYYY-MM-DD')
    
    # ✅ Calculate batch-wise stats
    batch_stats = {}
    all_batches = Attendance.objects.filter(
        student=request.user
    ).values('session__batch__id', 'session__batch__name').distinct()
    
    for batch in all_batches:
        batch_id_val = batch['session__batch__id']
        batch_name = batch['session__batch__name']
        
        batch_attendances = Attendance.objects.filter(
            student=request.user,
            session__batch_id=batch_id_val
        )
        
        batch_total = batch_attendances.count()
        batch_present = batch_attendances.filter(is_present=True).count()
        batch_absent = batch_attendances.filter(is_present=False).count()
        batch_late = batch_attendances.filter(is_late=True, is_present=True).count()
        
        batch_stats[batch_name] = {
            'total': batch_total,
            'present': batch_present,
            'absent': batch_absent,
            'late': batch_late,
            'percentage': (batch_present / batch_total * 100) if batch_total > 0 else 0
        }
    
    # Pagination - Show recent 8 records
    from django.core.paginator import Paginator
    paginator = Paginator(attendances, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get enrolled batches for filter
    enrolled_batches_list = BatchEnrollment.objects.filter(
        student=request.user,
        is_active=True
    ).select_related('batch')
    
    context = {
        'page_obj': page_obj,
        'attendances': page_obj.object_list,
        'total_sessions': total_sessions,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'attendance_percentage': round(attendance_percentage, 2),
        'batch_stats': batch_stats,
        'sessions_with_status': sessions_with_status,
        'current_time': current_time,
        'enrolled_batches': enrolled_batches_list,
        'selected_batch': batch_id,
        'from_date': from_date,
        'to_date': to_date,
    }
    
    return render(request, 'attendance/student_my_attendance.html', context)

@login_required
def student_attendance_history(request):
    """Student attendance history"""
    
    if request.user.role != 'student':
        messages.error(request, 'Access denied!')
        return redirect(get_dashboard_url(request.user))
    
    batch_id = request.GET.get('batch')
    status = request.GET.get('status')
    
    attendances = Attendance.objects.filter(
        student=request.user
    ).select_related('session', 'session__batch')
    
    if batch_id:
        attendances = attendances.filter(session__batch_id=batch_id)
    
    if status == 'present':
        attendances = attendances.filter(is_present=True)
    elif status == 'absent':
        attendances = attendances.filter(is_present=False)
    elif status == 'late':
        attendances = attendances.filter(is_late=True)
    
    attendances = attendances.order_by('-session__date', '-marked_at')
    
    # ✅ SAHI - NAYA CODE
    batches = Batch.objects.filter(
    enrollments__student=request.user,
    enrollments__is_active=True
).distinct()
    
    context = {
        'attendances': attendances,
        'batches': batches,
        'selected_batch': batch_id,
        'selected_status': status,
        'page_title': 'Attendance History'
    }
    
    return render(request, 'attendance/student_attendance_history.html', context)


# ==================== COMMON VIEWS ====================
@login_required
def session_list(request):
    """List all attendance sessions"""
    
    # Check if user is instructor or superadmin
    if request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'Only instructors/admins can view sessions!')
        return redirect('home')
    
    # Get sessions based on role
    if request.user.role == 'superadmin':
        sessions = AttendanceSession.objects.all()
        base_template = 'base.html'
        page_title = 'All Attendance Sessions'
    else:
        # Get batches where user is instructor
        instructor_batches = Batch.objects.filter(instructor=request.user)
        sessions = AttendanceSession.objects.filter(batch__in=instructor_batches)
        base_template = 'instructor_base.html'
        page_title = 'My Attendance Sessions'
    
    # ✅ FIXED - Use start_time instead of date
    # ✅ FIXED - Don't select_related 'instructor' (doesn't exist)
    sessions = sessions.select_related('batch').order_by('-start_time')
    
    # Filter by batch if provided
    batch_id = request.GET.get('batch')
    if batch_id:
        sessions = sessions.filter(batch_id=batch_id)
    
    # Filter by date range if provided
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    if from_date:
        from django.utils import timezone
        from datetime import datetime
        try:
            from_datetime = timezone.make_aware(
                datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            )
            # ✅ Use __gte with start_time
            sessions = sessions.filter(start_time__gte=from_datetime)
        except ValueError:
            messages.warning(request, 'Invalid from_date format')
    
    if to_date:
        from django.utils import timezone
        from datetime import datetime
        try:
            to_datetime = timezone.make_aware(
                datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            )
            # ✅ Use __lte with start_time
            sessions = sessions.filter(start_time__lte=to_datetime)
        except ValueError:
            messages.warning(request, 'Invalid to_date format')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(sessions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get batches for filter dropdown
    if request.user.role == 'superadmin':
        available_batches = Batch.objects.filter(is_active=True)
    else:
        available_batches = Batch.objects.filter(
            instructor=request.user,
            is_active=True
        )
    
    context = {
        'page_obj': page_obj,
        'sessions': page_obj.object_list,
        'available_batches': available_batches,
        'selected_batch': batch_id,
        'from_date': from_date,
        'to_date': to_date,
        'page_title': page_title,
        'base_template': base_template,
    }
    
    return render(request, 'attendance/session_list.html', context)
    
# ==================== REPORTS & ANALYTICS ====================
@login_required
def attendance_reports(request):
    """Generate attendance reports"""
    
    if request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'Access denied!')
        return redirect(get_dashboard_url(request.user))
    
    batch_id = request.GET.get('batch')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # ✅ Dynamic base template
    if request.user.role == 'superadmin':
        sessions = AttendanceSession.objects.all()
        batches = Batch.objects.filter(is_active=True)
        base_template = 'base.html'
    else:
        sessions = AttendanceSession.objects.filter(batch__instructor=request.user)
        batches = Batch.objects.filter(instructor=request.user, is_active=True)
        base_template = 'instructor_base.html'
    
    # ✅ Filters - Use start_time instead of date
    if batch_id:
        sessions = sessions.filter(batch_id=batch_id)
    if date_from:
        # ✅ Filter by start_time date
        sessions = sessions.filter(start_time__date__gte=date_from)
    if date_to:
        # ✅ Filter by start_time date
        sessions = sessions.filter(start_time__date__lte=date_to)
    
    # ✅ Order by start_time instead of date
    sessions = sessions.select_related('batch').order_by('-start_time')
    
    total_sessions = sessions.count()
    total_attendances = Attendance.objects.filter(session__in=sessions).count()
    present_count = Attendance.objects.filter(session__in=sessions, is_present=True).count()
    
    overall_percentage = round((present_count / total_attendances * 100), 2) if total_attendances > 0 else 0
    
    context = {
        'sessions': sessions,
        'batches': batches,
        'total_sessions': total_sessions,
        'total_attendances': total_attendances,
        'present_count': present_count,
        'overall_percentage': overall_percentage,
        'selected_batch': batch_id,
        'date_from': date_from,
        'date_to': date_to,
        'page_title': 'Attendance Reports',
        'base_template': base_template  # ✅ Add this
    }
    
    return render(request, 'attendance/attendance_reports.html', context)


@login_required
def attendance_analytics(request):
    """View attendance analytics"""
    
    if request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'Access denied!')
        return redirect(get_dashboard_url(request.user))
    
    # ✅ Dynamic base template
    if request.user.role == 'superadmin':
        sessions = AttendanceSession.objects.all()
        base_template = 'base.html'
    else:
        sessions = AttendanceSession.objects.filter(batch__instructor=request.user)
        base_template = 'instructor_base.html'
    
    total_sessions = sessions.count()
    active_sessions = sessions.filter(is_active=True).count()
    
    all_attendances = Attendance.objects.filter(session__in=sessions)
    total_marks = all_attendances.count()
    present_marks = all_attendances.filter(is_present=True).count()
    late_marks = all_attendances.filter(is_late=True).count()
    
    avg_attendance = round((present_marks / total_marks * 100), 2) if total_marks > 0 else 0
    
    batch_stats = sessions.values('batch__name').annotate(
        session_count=Count('id'),
        avg_attendance=Avg('attendances__is_present')
    ).order_by('-session_count')[:10]
    
    recent_sessions = sessions.select_related('batch').order_by('-start_time')[:10]
    for session in recent_sessions:
        session.stats = session.get_stats()
    
    context = {
        'total_sessions': total_sessions,
        'active_sessions': active_sessions,
        'total_marks': total_marks,
        'present_marks': present_marks,
        'late_marks': late_marks,
        'avg_attendance': avg_attendance,
        'batch_stats': batch_stats,
        'recent_sessions': recent_sessions,
        'page_title': 'Attendance Analytics',
        'base_template': base_template,
    }
    
    return render(request, 'attendance/attendance_analytics.html', context)



