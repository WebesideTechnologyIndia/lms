# views.py - Updated with admin user management

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login ,logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser, UserActivityLog
from .forms import UserCreationForm, UserUpdateForm
from django.db.models import Q
from courses.models import BatchEnrollment

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from courses.models import StudentSubscription, DeviceSession
import hashlib

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        print(username)
        print(password)
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            
            # ========== DEVICE LIMIT CHECK FOR STUDENTS ==========
            if user.role == "student":
                # Generate device ID for this login attempt
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                ip_address = get_client_ip(request)
                device_id = hashlib.md5(f"{user_agent}{ip_address}".encode()).hexdigest()
                
                print(f"🔍 Checking device limit for {username}")
                print(f"   Device ID: {device_id[:16]}...")
                
                # Check all active subscriptions
                subscriptions = StudentSubscription.objects.filter(
                    student=user,
                    is_active=True
                )
                
                if subscriptions.exists():
                    device_blocked = False
                    blocked_course = None
                    max_allowed = 0
                    
                    for subscription in subscriptions:
                        # Check if this device is already registered
                        existing_device = DeviceSession.objects.filter(
                            subscription=subscription,
                            device_id=device_id,
                            is_active=True
                        ).exists()
                        
                        if existing_device:
                            # Device already registered - ALLOW
                            print(f"   ✅ Device already registered for {subscription.course.title}")
                            continue
                        
                        # NEW DEVICE - Check if limit reached
                        active_devices_count = subscription.devices.filter(is_active=True).count()
                        
                        print(f"   📱 {subscription.course.title}: {active_devices_count}/{subscription.max_devices} devices")
                        
                        if active_devices_count >= subscription.max_devices:
                            # LIMIT REACHED - BLOCK LOGIN
                            device_blocked = True
                            blocked_course = subscription.course.title
                            max_allowed = subscription.max_devices
                            print(f"   ❌ Device limit reached for {blocked_course}!")
                            break
                    
                    if device_blocked:
                        # BLOCK LOGIN
                        error_msg = (
                            f'❌ Device Limit Reached!\n\n'
                            f'Course: {blocked_course}\n'
                            f'Maximum devices allowed: {max_allowed}\n\n'
                            f'Please remove an existing device from your account or contact admin.'
                        )
                        print(f"🚫 LOGIN BLOCKED: {error_msg}")
                        return render(request, "login.html", {
                            "error": error_msg,
                            "username": username
                        })
            # ========== END DEVICE CHECK ==========
            
            # ALL CHECKS PASSED - LOGIN ALLOWED
            login(request, user)
            
            # Log the login activity
            UserActivityLog.objects.create(
                user=user,
                action='login',
                description=f'User logged in successfully',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            print(f"✅ LOGIN SUCCESS: {username}")
            
            # Redirect based on role
            if user.role == "superadmin":
                return redirect("admin_dashboard")
            elif user.role == "instructor":
                return redirect("instructor_dashboard")
            elif user.role == "student":
                return redirect("student_dashboard")
            elif user.role == "webinar_user":
                return redirect("webinars:webinar_landing")
            else:
                return render(request, "login.html", {"error": "Role not match please login again"})
        else:
            print(f"❌ LOGIN FAILED: Invalid credentials for {username}")
            return render(request, "login.html", {"error": "Invalid Credentials"})
    
    return render(request, 'login.html')

# userss/views.py - ADD THIS AT TOP
from courses.models import StudentLoginLog
from django.utils import timezone

# THEN FIND AND REPLACE user_logout function:

@login_required
def user_logout(request):
    """Enhanced logout with attendance tracking"""
    
    print(f"🚪 Logout request from: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    
    # CRITICAL: Track attendance BEFORE logout
    if request.user.is_authenticated:
        # Store username before logout clears it
        username = request.user.username
        user_role = request.user.role
        
        print(f"User: {username}, Role: {user_role}")
        
        if user_role == 'student':
            try:
                # Method 1: Try from session
                log_id = request.session.get('attendance_log_id')
                print(f"Session log_id: {log_id}")
                
                if log_id:
                    log = StudentLoginLog.objects.get(id=log_id)
                    if not log.logout_time:
                        log.logout_time = timezone.now()
                        log.calculate_duration()
                        print(f"✅ Session Logout: {username} - Session {log.id} - Duration: {log.session_duration} min")
                
                # Method 2: Close any other active sessions
                active_sessions = StudentLoginLog.objects.filter(
                    student=request.user,
                    logout_time__isnull=True
                )
                
                if active_sessions.exists():
                    print(f"Found {active_sessions.count()} active sessions to close")
                    
                    for session in active_sessions:
                        session.logout_time = timezone.now()
                        session.calculate_duration()
                        session.save()
                        print(f"✅ Auto Logout: {username} - Session {session.id} - Duration: {session.session_duration} min")
                
            except StudentLoginLog.DoesNotExist:
                print(f"⚠️ No active session found")
            except Exception as e:
                print(f"❌ Logout tracking error: {e}")
                import traceback
                traceback.print_exc()
    
    # Now perform Django logout
    logout(request)
    print(f"🔓 Django logout completed")
    
    return redirect('user_login')



def check_device_limit(user, course):
    """Check if student has reached device limit for course"""
    
    try:
        subscription = StudentSubscription.objects.get(
            student=user,
            course=course,
            is_active=True
        )
        
        # Count active devices
        active_devices = subscription.devices.filter(is_active=True).count()
        
        if active_devices >= subscription.max_devices:
            return False, f"Device limit reached ({subscription.max_devices} devices max)"
        
        return True, "OK"
        
    except StudentSubscription.DoesNotExist:
        return True, "No subscription found"



# Admin Dashboard
@login_required
def admin_dashboard(request):
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    # Get user statistics
    total_users = CustomUser.objects.count()
    total_students = CustomUser.objects.filter(role='student').count()
    total_instructors = CustomUser.objects.filter(role='instructor').count()
    total_admins = CustomUser.objects.filter(role='superadmin').count()
    
    # Add courses data for sidebar dropdown
    from courses.models import Course
    sidebar_courses = Course.objects.filter(is_active=True).order_by('course_code')[:15]
    
    context = {
        'total_users': total_users,
        'total_students': total_students,
        'total_instructors': total_instructors,
        'total_admins': total_admins,
        'sidebar_courses': sidebar_courses,
    }
    return render(request, 'admin_dashboard.html', context)

# User Management Views
@login_required
def manage_users(request):
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    course_filter = request.GET.get('course', '')
    batch_type_filter = request.GET.get('batch_type', '')
    
    users = CustomUser.objects.all()
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Course filter for students
    if course_filter and role_filter == 'student':
        users = users.filter(enrollments__course_id=course_filter, enrollments__is_active=True).distinct()
    
    # Batch type filter for students
    if batch_type_filter and role_filter == 'student':
        users = users.filter(batch_enrollments__batch__batch_type=batch_type_filter, batch_enrollments__is_active=True).distinct()
    
    users = users.order_by('-date_joined')
    
    # Get student details with courses and batches
    students_data = []
    if role_filter == 'student' or not role_filter:
        for user in users:
            if user.role == 'student':
                # Get enrollments
                enrollments = Enrollment.objects.filter(
                    student=user, 
                    is_active=True
                ).select_related('course', 'course__category')
                
                # Get batch enrollments
                batch_enrollments = BatchEnrollment.objects.filter(
                    student=user,
                    is_active=True
                ).select_related('batch', 'batch__course', 'batch__instructor')
                
                students_data.append({
                    'user': user,
                    'enrollments': enrollments,
                    'batch_enrollments': batch_enrollments,
                })
    
    # Get all courses for filter dropdown
    all_courses = Course.objects.filter(is_active=True).order_by('title')
    
    context = {
        'users': users,
        'students_data': students_data,
        'search_query': search_query,
        'role_filter': role_filter,
        'course_filter': course_filter,
        'batch_type_filter': batch_type_filter,
        'role_choices': CustomUser.ROLE_CHOICES,
        'all_courses': all_courses,
        'batch_type_choices': [
            ('online', 'Online'),
            ('offline', 'Offline'),
            ('hybrid', 'Hybrid'),
        ],
    }
    return render(request, 'manage_users.html', context)

    
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserCreationForm

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserCreationForm

@login_required
def create_user(request):
    if request.user.role != 'superadmin':
        messages.error(request, 'You do not have permission to create users.')
        return redirect('user_login')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('manage_users')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    
    return render(request, 'create_user.html', {'form': form})






@login_required
def edit_user(request, user_id):
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('manage_users')
    else:
        form = UserUpdateForm(instance=user)
    
    return render(request, 'edit_user.html', {'form': form, 'user': user})

@login_required
def delete_user(request, user_id):
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent self-deletion
    if user == request.user:
        messages.error(request, "You cannot delete your own account!")
        return redirect('manage_users')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User {username} deleted successfully!')
        return redirect('manage_users')
    
    return render(request, 'delete_user.html', {'user': user})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from datetime import date, timedelta
from userss.models import CustomUser, EmailLog, EmailLimitSet
from courses.models import Course, Batch, Enrollment, BatchEnrollment
from exams.models import Exam, ExamAttempt
from zoom.models import BatchSession

@login_required
def user_details(request, user_id):
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Common data for all users
    context = {
        'user': user,
    }
    
    # Email Statistics (for all users)
    today = date.today()
    email_limit = EmailLimitSet.objects.filter(is_active=True).first()
    daily_limit = email_limit.email_limit_per_day if email_limit else 50
    
    # Emails sent TO this user
    today_emails = EmailLog.objects.filter(
        recipient_user=user,
        sent_date=today
    ).count()
    
    total_emails = EmailLog.objects.filter(
        recipient_user=user
    ).count()
    
    remaining_emails = max(0, daily_limit - today_emails)
    can_receive_email = remaining_emails > 0
    
    # Recent emails
    recent_emails = EmailLog.objects.filter(
        recipient_user=user
    ).select_related('sent_by', 'template_used').order_by('-sent_time')[:10]
    
    # Add email data to context
    context.update({
        'today_emails': today_emails,
        'total_emails': total_emails,
        'remaining_emails': remaining_emails,
        'can_receive_email': can_receive_email,
        'daily_limit': daily_limit,
        'recent_emails': recent_emails,
    })
    
    # Role-specific data
    if user.role == 'instructor':
        # Instructor Statistics
        instructor_data = get_instructor_statistics(user)
        context.update(instructor_data)
        
    elif user.role == 'student':
        # Student Statistics
        student_data = get_student_statistics(user)
        context.update(student_data)
    
    # Emails SENT by this user (if instructor or admin)
    if user.role in ['instructor', 'superadmin']:
        emails_sent_by_user = EmailLog.objects.filter(
            sent_by=user
        ).count()
        
        emails_sent_today = EmailLog.objects.filter(
            sent_by=user,
            sent_date=today
        ).count()
        
        context.update({
            'emails_sent_by_user': emails_sent_by_user,
            'emails_sent_today': emails_sent_today,
        })
    
    return render(request, 'user_details.html', context)


def get_instructor_statistics(user):
    """Get comprehensive statistics for instructor"""
    
    # Courses
    total_courses = Course.objects.filter(
        Q(instructor=user) | Q(co_instructors=user),
        is_active=True
    ).distinct().count()
    
    active_courses = Course.objects.filter(
        Q(instructor=user) | Q(co_instructors=user),
        status='published',
        is_active=True
    ).distinct().count()
    
    # Get all courses (main + co-instructor)
    all_courses = Course.objects.filter(
        Q(instructor=user) | Q(co_instructors=user),
        is_active=True
    ).distinct().select_related('category')[:5]  # Recent 5
    
    # Batches
    total_batches = Batch.objects.filter(
        instructor=user,
        is_active=True
    ).count()
    
    active_batches = Batch.objects.filter(
        instructor=user,
        status='active',
        is_active=True
    ).count()
    
    recent_batches = Batch.objects.filter(
        instructor=user,
        is_active=True
    ).select_related('course').order_by('-created_at')[:5]
    
    # Students (enrolled in instructor's courses)
    total_students = Enrollment.objects.filter(
        course__instructor=user,
        is_active=True
    ).values('student').distinct().count()
    
    # Get recent students
    recent_students = Enrollment.objects.filter(
        course__instructor=user,
        is_active=True
    ).select_related('student', 'course').order_by('-enrolled_at')[:10]
    
    # Sessions (from batches) - DETAILED
    total_sessions = BatchSession.objects.filter(
        batch__instructor=user
    ).count()
    
    upcoming_sessions = BatchSession.objects.filter(
        batch__instructor=user,
        status='scheduled',
        scheduled_date__gte=date.today()
    ).count()
    
    completed_sessions = BatchSession.objects.filter(
        batch__instructor=user,
        status='completed'
    ).count()
    
    live_sessions = BatchSession.objects.filter(
        batch__instructor=user,
        status='live'
    ).count()
    
    # ALL Sessions with details
    all_sessions = BatchSession.objects.filter(
        batch__instructor=user
    ).select_related('batch', 'batch__course').order_by('-scheduled_date', '-start_time')[:20]
    
    # Session stats by status
    session_stats = BatchSession.objects.filter(
        batch__instructor=user
    ).values('status').annotate(count=Count('id'))
    
    recent_sessions = BatchSession.objects.filter(
        batch__instructor=user
    ).select_related('batch').order_by('-scheduled_date', '-start_time')[:5]
    
    # Exams
    total_exams = Exam.objects.filter(
        created_by=user,
        is_active=True
    ).count()
    
    active_exams = Exam.objects.filter(
        created_by=user,
        status='published',
        is_active=True
    ).count()
    
    recent_exams = Exam.objects.filter(
        created_by=user,
        is_active=True
    ).order_by('-created_at')[:5]
    
    # Exam attempts on instructor's exams
    total_attempts = ExamAttempt.objects.filter(
        exam__created_by=user
    ).count()
    
    # Permissions (if applicable)
    instructor_permissions = []
    if hasattr(user, 'instructor_profile'):
        instructor_permissions = user.get_instructor_permissions()
    
    return {
        'total_courses': total_courses,
        'active_courses': active_courses,
        'all_courses': all_courses,
        
        'total_batches': total_batches,
        'active_batches': active_batches,
        'recent_batches': recent_batches,
        
        'total_students': total_students,
        'recent_students': recent_students,
        
        'total_sessions': total_sessions,
        'upcoming_sessions': upcoming_sessions,
        'completed_sessions': completed_sessions,
        'live_sessions': live_sessions,
        'all_sessions': all_sessions,
        'session_stats': session_stats,
        'recent_sessions': recent_sessions,
        
        'total_exams': total_exams,
        'active_exams': active_exams,
        'recent_exams': recent_exams,
        'total_attempts': total_attempts,
        
        'instructor_permissions': instructor_permissions,
    }


def get_student_statistics(user):
    """Get comprehensive statistics for student"""
    
    # Enrollments
    total_enrollments = Enrollment.objects.filter(
        student=user,
        is_active=True
    ).count()
    
    active_enrollments = Enrollment.objects.filter(
        student=user,
        status='enrolled',
        is_active=True
    ).count()
    
    completed_enrollments = Enrollment.objects.filter(
        student=user,
        status='completed',
        is_active=True
    ).count()
    
    # Get enrolled courses
    enrolled_courses = Enrollment.objects.filter(
        student=user,
        is_active=True
    ).select_related('course', 'course__instructor').order_by('-enrolled_at')
    
    # Batch Enrollments
    total_batch_enrollments = BatchEnrollment.objects.filter(
        student=user,
        is_active=True
    ).count()
    
    active_batch_enrollments = BatchEnrollment.objects.filter(
        student=user,
        status='enrolled',
        is_active=True
    ).count()
    
    enrolled_batches = BatchEnrollment.objects.filter(
        student=user,
        is_active=True
    ).select_related('batch', 'batch__course', 'batch__instructor').order_by('-enrolled_at')
    
    # Exam Attempts
    total_exam_attempts = ExamAttempt.objects.filter(
        student=user
    ).count()
    
    completed_exams = ExamAttempt.objects.filter(
        student=user,
        status__in=['submitted', 'auto_submitted']
    ).count()
    
    passed_exams = ExamAttempt.objects.filter(
        student=user,
        is_passed=True
    ).count()
    
    # Average percentage
    avg_percentage = ExamAttempt.objects.filter(
        student=user,
        status__in=['submitted', 'auto_submitted']
    ).aggregate(avg=Sum('percentage'))['avg'] or 0
    
    recent_exam_attempts = ExamAttempt.objects.filter(
        student=user
    ).select_related('exam').order_by('-started_at')[:5]
    
    # Session Attendance
    from zoom.models import SessionAttendance
    
    total_sessions_attended = SessionAttendance.objects.filter(
        student=user,
        is_present=True
    ).count()
    
    total_sessions_assigned = SessionAttendance.objects.filter(
        student=user
    ).count()
    
    attendance_percentage = 0
    if total_sessions_assigned > 0:
        attendance_percentage = round((total_sessions_attended / total_sessions_assigned) * 100, 2)
    
    recent_attendance = SessionAttendance.objects.filter(
        student=user
    ).select_related('session', 'session__batch').order_by('-created_at')[:5]
    
    return {
        'total_enrollments': total_enrollments,
        'active_enrollments': active_enrollments,
        'completed_enrollments': completed_enrollments,
        'enrolled_courses': enrolled_courses,
        
        'total_batch_enrollments': total_batch_enrollments,
        'active_batch_enrollments': active_batch_enrollments,
        'enrolled_batches': enrolled_batches,
        
        'total_exam_attempts': total_exam_attempts,
        'completed_exams': completed_exams,
        'passed_exams': passed_exams,
        'avg_percentage': round(avg_percentage, 2) if avg_percentage else 0,
        'recent_exam_attempts': recent_exam_attempts,
        
        'total_sessions_attended': total_sessions_attended,
        'total_sessions_assigned': total_sessions_assigned,
        'attendance_percentage': attendance_percentage,
        'recent_attendance': recent_attendance,
    }


# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 


# students/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta

from userss.models import CustomUser, UserProfile, UserActivityLog
from courses.models import (
    Course, Enrollment, CourseCategory, 
    BatchEnrollment, LessonProgress
)
from .forms import StudentProfileForm ,UserProfileForm # You'll need to create this


# students/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta



@login_required
def student_dashboard(request):
    """Enhanced student dashboard with profile completion check"""
    
    # Check if user is student
    if request.user.role != 'student':
        messages.error(request, "Access denied. Students only.")
        return redirect('user_login')
    
    # Profile completion check
    profile_complete = check_profile_completion(request.user)
    
    if not profile_complete:
        messages.warning(request, "Please complete your profile to access all features.")
        return redirect('student_profile')
    
    # Dashboard data
    user = request.user
    today = timezone.now().date()
    
    # Get user enrollments
    active_enrollments = Enrollment.objects.filter(
        student=user, 
        is_active=True
    ).select_related('course', 'course__instructor')
    
    # Get batch enrollments
    batch_enrollments = BatchEnrollment.objects.filter(
        student=user,
        is_active=True
    ).select_related('batch', 'batch__course')
    
    # Calculate stats
    total_courses = active_enrollments.count()
    total_batches = batch_enrollments.count()
    completed_courses = active_enrollments.filter(status='completed').count()
    
    # Overall progress calculation
    overall_progress = active_enrollments.aggregate(
        avg_progress=Avg('progress_percentage')
    )['avg_progress'] or 0
    
    # Recent activity
    recent_activities = UserActivityLog.objects.filter(
        user=user
    ).order_by('-timestamp')[:5]
    
    # Get some active courses for display
    active_courses = active_enrollments.order_by('-enrolled_at')[:3]
    
    # Performance data
    average_grade = active_enrollments.exclude(grade='').aggregate(
        avg=Avg('progress_percentage')
    )['avg'] or 0
    
    total_hours = active_enrollments.aggregate(
        total=Sum('total_time_spent_minutes')
    )['total'] or 0
    total_hours = round(total_hours / 60, 1)  # Convert to hours
    
    completion_rate = (completed_courses / total_courses * 100) if total_courses > 0 else 0
    
    # Upcoming deadlines (placeholder - you can extend this)
    upcoming_deadlines = []
    
    context = {
        'user': user,
        'today': today,
        'total_courses': total_courses,
        'total_batches': total_batches,
        'completed_courses': completed_courses,
        'overall_progress': overall_progress,
        'active_courses': active_courses,
        'recent_activities': recent_activities,
        'upcoming_deadlines': upcoming_deadlines,
        'average_grade': average_grade,
        'total_hours': total_hours,
        'completion_rate': completion_rate,
    }
    
    return render(request, 'student_dashboard.html', context)


def check_profile_completion(user):
    """Check if student profile is complete"""
    try:
        profile = user.profile
        # Check required fields
        required_fields = [
            profile.student_id,
            user.first_name,
            user.last_name,
            user.email,
        ]
        return all(field for field in required_fields)
    except:
        return False


@login_required
def student_profile(request):
    """Student profile completion/update view"""
    
    if request.user.role != 'student':
        messages.error(request, "Access denied.")
        return redirect('user_login')
    
    # Get or create profile
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        # Import forms here to avoid circular import
        from .forms import StudentProfileForm, UserProfileForm
        
        form = StudentProfileForm(request.POST, request.FILES, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=profile)
        
        if form.is_valid() and profile_form.is_valid():
            # Save user data
            user = form.save()
            
            # Save profile data
            profile = profile_form.save(commit=False)
            profile.user = user
            
            # Auto-generate student ID if not provided
            if not profile.student_id:
                profile.student_id = generate_student_id()
            
            profile.save()
            
            # Log activity
            UserActivityLog.objects.create(
                user=user,
                action='update_user',
                description='Profile updated successfully'
            )
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('student_dashboard')
    else:
        # Import forms here to avoid circular import
        from .forms import StudentProfileForm, UserProfileForm
        
        form = StudentProfileForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile_form': profile_form,
        'profile': profile,
        'is_profile_complete': check_profile_completion(request.user),
        'enrolled_courses_count': 0,  # Default value
        'batch_enrollments_count': 0,  # Default value
    }
    
    return render(request, 'students/student_profile.html', context)


def generate_student_id():
    """Generate unique student ID"""
    import random
    import string
    
    while True:
        # Generate format: STU + year + 4 random digits
        year = timezone.now().year
        random_part = ''.join(random.choices(string.digits, k=4))
        student_id = f"STU{year}{random_part}"
        
        # Check if unique
        if not UserProfile.objects.filter(student_id=student_id).exists():
            return student_id


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from courses.models import Enrollment, Course
from fees.models import StudentFeeAssignment, EMISchedule, PaymentRecord
from django.utils import timezone
from datetime import date

@login_required
def student_courses(request):
    """Student's enrolled courses with lock status"""
    
    if request.user.role != 'student':
        return redirect('user_login')
    
    # Get enrollments with related data
    enrollments = Enrollment.objects.filter(
        student=request.user,
        is_active=True
    ).select_related(
        'course', 
        'course__instructor',
        'course__category'
    ).prefetch_related(
        'course__fee_assignments',
        'course__batches'
    ).order_by('-enrolled_at')
    
    # Filter by status if requested
    status = request.GET.get('status')
    if status:
        enrollments = enrollments.filter(status=status)
    
    # Search
    search = request.GET.get('search')
    if search:
        enrollments = enrollments.filter(
            Q(course__title__icontains=search) |
            Q(course__course_code__icontains=search)
        )
    
    # Enhanced enrollment data with lock status
    enhanced_enrollments = []
    
    for enrollment in enrollments:
        # Get fee assignment for this student and course
        try:
            fee_assignment = StudentFeeAssignment.objects.get(
                student=request.user,
                course=enrollment.course
            )
        except StudentFeeAssignment.DoesNotExist:
            fee_assignment = None
        
        # Calculate lock status and payment info
        lock_info = get_course_lock_info(enrollment.course, request.user, fee_assignment)
        
        # Get recent payments
        recent_payments = []
        if fee_assignment:
            recent_payments = PaymentRecord.objects.filter(
                fee_assignment=fee_assignment,
                status='completed'
            ).order_by('-payment_date')[:3]
        
        # Get next due payment
        next_due = None
        if fee_assignment and fee_assignment.fee_structure.payment_type == 'emi':
            next_due = EMISchedule.objects.filter(
                fee_assignment=fee_assignment,
                status__in=['pending', 'overdue']
            ).order_by('due_date').first()
        
        enhanced_enrollments.append({
            'enrollment': enrollment,
            'fee_assignment': fee_assignment,
            'lock_info': lock_info,
            'recent_payments': recent_payments,
            'next_due': next_due,
        })
    
    # Pagination
    paginator = Paginator(enhanced_enrollments, 12)
    page = request.GET.get('page')
    enhanced_enrollments = paginator.get_page(page)
    
    # Summary statistics
    total_courses = len(enhanced_enrollments.object_list) if hasattr(enhanced_enrollments, 'object_list') else len(enhanced_enrollments)
    locked_courses = sum(1 for item in (enhanced_enrollments.object_list if hasattr(enhanced_enrollments, 'object_list') else enhanced_enrollments) 
                        if item['lock_info']['is_locked'])
    
    context = {
        'enrollments': enhanced_enrollments,
        'status': status,
        'search': search,
        'total_courses': total_courses,
        'locked_courses': locked_courses,
        'active_courses': total_courses - locked_courses,
    }
    
    return render(request, 'students/student_courses.html', context)


def get_course_lock_info(course, student, fee_assignment=None):
    """
    Get comprehensive course lock information
    Returns dict with lock status, reason, and related info
    """
    lock_info = {
        'is_locked': False,
        'lock_reason': None,
        'can_unlock': False,
        'unlock_date': None,
        'payment_status': 'current',
        'overdue_amount': 0,
        'overdue_days': 0,
        'grace_period_remaining': 0,
        'warning_message': None,
        'action_required': None,
    }
    
    if not fee_assignment:
        # No fee assignment means course is accessible
        return lock_info
    
    # Check if course is manually locked
    if fee_assignment.is_course_locked:
        lock_info.update({
            'is_locked': True,
            'lock_reason': 'Payment overdue',
            'can_unlock': False,
        })
        
        # Check if admin set unlock date
        if fee_assignment.unlock_date:
            lock_info.update({
                'unlock_date': fee_assignment.unlock_date,
                'can_unlock': date.today() >= fee_assignment.unlock_date,
            })
    
    # Check payment status for EMI plans
    if fee_assignment.fee_structure.payment_type == 'emi':
        overdue_emis = EMISchedule.objects.filter(
            fee_assignment=fee_assignment,
            status__in=['pending', 'overdue'],
            due_date__lt=date.today()
        ).order_by('due_date')
        
        if overdue_emis.exists():
            oldest_overdue = overdue_emis.first()
            overdue_days = (date.today() - oldest_overdue.due_date).days
            overdue_amount = sum(emi.amount for emi in overdue_emis)
            
            lock_info.update({
                'payment_status': 'overdue',
                'overdue_amount': overdue_amount,
                'overdue_days': overdue_days,
            })
            
            # Check grace period
            grace_period = fee_assignment.fee_structure.grace_period_days
            if overdue_days <= grace_period:
                lock_info.update({
                    'grace_period_remaining': grace_period - overdue_days,
                    'warning_message': f'Payment overdue by {overdue_days} days. Grace period expires in {grace_period - overdue_days} days.',
                    'action_required': 'pay_now'
                })
            else:
                # Should be locked
                if not fee_assignment.is_course_locked:
                    # Auto-lock the course
                    fee_assignment.lock_course()
                
                lock_info.update({
                    'is_locked': True,
                    'lock_reason': f'Payment overdue by {overdue_days} days (grace period exceeded)',
                    'action_required': 'contact_admin'
                })
    
    # Check for upcoming due dates (warning)
    if not lock_info['is_locked'] and fee_assignment.fee_structure.payment_type == 'emi':
        upcoming_emi = EMISchedule.objects.filter(
            fee_assignment=fee_assignment,
            status='pending',
            due_date__gte=date.today(),
            due_date__lte=date.today() + timezone.timedelta(days=7)
        ).order_by('due_date').first()
        
        if upcoming_emi:
            days_until_due = (upcoming_emi.due_date - date.today()).days
            lock_info.update({
                'warning_message': f'Next payment of ${upcoming_emi.amount} due in {days_until_due} days',
                'action_required': 'payment_due_soon'
            })
    
    return lock_info


def get_payment_summary(student, course):
    """Get payment summary for a student's course"""
    try:
        fee_assignment = StudentFeeAssignment.objects.get(
            student=student,
            course=course
        )
        
        summary = {
            'total_amount': fee_assignment.total_amount,
            'amount_paid': fee_assignment.amount_paid,
            'amount_pending': fee_assignment.amount_pending,
            'completion_percentage': fee_assignment.get_completion_percentage(),
            'payment_type': fee_assignment.fee_structure.payment_type,
        }
        
        # EMI specific info
        if fee_assignment.fee_structure.payment_type == 'emi':
            total_emis = fee_assignment.emi_schedules.count()
            paid_emis = fee_assignment.emi_schedules.filter(status='paid').count()
            
            summary.update({
                'total_emis': total_emis,
                'paid_emis': paid_emis,
                'remaining_emis': total_emis - paid_emis,
            })
        
        return summary
        
    except StudentFeeAssignment.DoesNotExist:
        return None


# Helper view for AJAX requests to check lock status
@login_required
def check_course_lock_status(request, course_id):
    """AJAX endpoint to check course lock status"""
    
    if request.user.role != 'student':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        course = Course.objects.get(id=course_id)
        fee_assignment = StudentFeeAssignment.objects.get(
            student=request.user,
            course=course
        )
        
        lock_info = get_course_lock_info(course, request.user, fee_assignment)
        
        return JsonResponse({
            'success': True,
            'lock_info': lock_info
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)
    except StudentFeeAssignment.DoesNotExist:
        return JsonResponse({'error': 'Fee assignment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    


@login_required
def student_batches(request):
    """Student's batch enrollments - DEBUG VERSION"""
    
    if request.user.role != 'student':
        return redirect('user_login')
    
    from fees.models import StudentFeeAssignment
    from django.db.models import Q
    
    # Get ALL enrollments
    batch_enrollments = BatchEnrollment.objects.filter(
        student=request.user
    ).select_related('batch', 'batch__course', 'batch__instructor')
    
    print("\n" + "="*60)
    print(f"DEBUGGING FOR USER: {request.user.username}")
    print(f"Total enrollments found: {batch_enrollments.count()}")
    print("="*60)
    
    # Filters
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    sort = request.GET.get('sort', '-enrolled_at')
    
    if search:
        batch_enrollments = batch_enrollments.filter(
            Q(batch__name__icontains=search) |
            Q(batch__course__title__icontains=search) |
            Q(batch__code__icontains=search)
        )
    
    if sort:
        batch_enrollments = batch_enrollments.order_by(sort)
    
    # Stats
    active_batches_count = 0
    locked_batches_count = 0
    completed_batches_count = 0
    upcoming_batches_count = 0
    
    filtered_enrollments = []
    
    for enrollment in batch_enrollments:
        print(f"\n--- Enrollment ID: {enrollment.id} ---")
        print(f"Batch: {enrollment.batch.name}")
        print(f"Batch Status: {enrollment.batch.status}")
        print(f"Enrollment is_active: {enrollment.is_active}")
        
        # Fee assignment
        try:
            enrollment.fee_assignment = StudentFeeAssignment.objects.get(
                student=request.user,
                course=enrollment.batch.course
            )
            print(f"Fee Assignment found: {enrollment.fee_assignment}")
            print(f"Fee is_course_locked: {enrollment.fee_assignment.is_course_locked}")
        except StudentFeeAssignment.DoesNotExist:
            enrollment.fee_assignment = None
            print(f"Fee Assignment: None")
        
        # Check locked status
        print(f"enrollment.is_locked property: {enrollment.is_locked}")
        print(f"enrollment.get_lock_reason(): {enrollment.get_lock_reason()}")
        
        batch_status = enrollment.batch.status
        
        # Determine if locked
        is_enrollment_locked = enrollment.is_locked
        
        print(f"Final determination - is_enrollment_locked: {is_enrollment_locked}")
        
        if batch_status == 'completed':
            completed_batches_count += 1
            print(f"Categorized as: COMPLETED")
            if status_filter == '' or status_filter == 'completed':
                filtered_enrollments.append(enrollment)
                
        elif batch_status == 'draft':
            upcoming_batches_count += 1
            print(f"Categorized as: UPCOMING")
            if status_filter == '' or status_filter == 'upcoming':
                filtered_enrollments.append(enrollment)
                
        elif batch_status == 'active':
            if is_enrollment_locked:
                locked_batches_count += 1
                print(f"Categorized as: LOCKED ✓")
                if status_filter == '' or status_filter == 'locked':
                    filtered_enrollments.append(enrollment)
            else:
                active_batches_count += 1
                print(f"Categorized as: ACTIVE ✓")
                if status_filter == '' or status_filter == 'active':
                    filtered_enrollments.append(enrollment)
        else:
            print(f"Categorized as: OTHER")
            if status_filter == '':
                filtered_enrollments.append(enrollment)
    
    print("\n" + "="*60)
    print("FINAL COUNTS:")
    print(f"Active: {active_batches_count}")
    print(f"Locked: {locked_batches_count}")
    print(f"Completed: {completed_batches_count}")
    print(f"Upcoming: {upcoming_batches_count}")
    print(f"Filtered enrollments: {len(filtered_enrollments)}")
    print("="*60 + "\n")
    
    context = {
        'batch_enrollments': filtered_enrollments,
        'active_batches_count': active_batches_count,
        'locked_batches_count': locked_batches_count,
        'completed_batches_count': completed_batches_count,
        'upcoming_batches_count': upcoming_batches_count,
        'search': search,
        'status': status_filter,
        'sort': sort,
    }
    
    return render(request, 'students/student_batches.html', context)

@login_required
def browse_courses(request):
    """Browse available courses for enrollment with enrollment status"""
    
    if request.user.role != 'student':
        return redirect('user_login')
    
    from courses.models import BatchEnrollment, Enrollment
    from fees.models import StudentFeeAssignment
    
    # Debug current user enrollments
    print(f"=== DEBUG for User: {request.user.username} ===")
    
    # Check batch enrollments
    batch_enrollments = BatchEnrollment.objects.filter(student=request.user)
    print(f"Batch Enrollments: {batch_enrollments.count()}")
    for be in batch_enrollments:
        print(f"  - Batch: {be.batch.name} | Course: {be.batch.course.title} | Active: {be.is_active}")
    
    # Check course enrollments
    course_enrollments = Enrollment.objects.filter(student=request.user)
    print(f"Course Enrollments: {course_enrollments.count()}")
    for ce in course_enrollments:
        print(f"  - Course: {ce.course.title} | Active: {ce.is_active}")
    
    # Get courses
    courses = Course.objects.filter(
        is_active=True,
        status='published'
    ).select_related('instructor', 'category')
    
    # Rest of filtering code...
    category = request.GET.get('category')
    if category:
        courses = courses.filter(category__slug=category)
    
    difficulty = request.GET.get('difficulty')
    if difficulty:
        courses = courses.filter(difficulty_level=difficulty)
    
    course_type = request.GET.get('type')
    if course_type:
        courses = courses.filter(course_type=course_type)
    
    search = request.GET.get('search')
    if search:
        courses = courses.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(course_code__icontains=search)
        )
    
    sort = request.GET.get('sort', '-created_at')
    courses = courses.order_by(sort)
    
    # FIXED: Check enrollment for each course
    for course in courses:
        print(f"\n=== Checking Course: {course.title} ===")
        
        # Method 1: Check via BatchEnrollment
        batch_enrollment = BatchEnrollment.objects.filter(
            student=request.user,
            batch__course=course,
            is_active=True
        ).first()
        
        # Method 2: Check via direct Enrollment
        course_enrollment = Enrollment.objects.filter(
            student=request.user,
            course=course,
            is_active=True
        ).first()
        
        print(f"Batch Enrollment Found: {batch_enrollment is not None}")
        print(f"Course Enrollment Found: {course_enrollment is not None}")
        
        # Set enrollment status based on either method
        if batch_enrollment or course_enrollment:
            course.is_student_enrolled = True
            course.student_batch = batch_enrollment.batch if batch_enrollment else None
            
            # Check fee lock
            try:
                fee_assignment = StudentFeeAssignment.objects.get(
                    student=request.user,
                    course=course
                )
                course.is_course_locked = fee_assignment.is_course_locked
            except StudentFeeAssignment.DoesNotExist:
                course.is_course_locked = False
        else:
            course.is_student_enrolled = False
            course.student_batch = None
            course.is_course_locked = False
        
        print(f"Final Status - Enrolled: {course.is_student_enrolled}, Locked: {course.is_course_locked}")
    
    # ========== NEW ADDON: GROUP BY CATEGORY ==========
    from collections import OrderedDict
    category_courses = OrderedDict()
    
    for course in courses:
        cat = course.category
        if cat not in category_courses:
            category_courses[cat] = []
        category_courses[cat].append(course)
    # ========== END NEW ADDON ==========
    
    # Pagination
    paginator = Paginator(courses, 12)
    page = request.GET.get('page')
    courses = paginator.get_page(page)
    
    categories = CourseCategory.objects.filter(is_active=True)
    
    context = {
        'courses': courses,
        'categories': categories,
        'selected_category': category,
        'selected_difficulty': difficulty,
        'selected_type': course_type,
        'search': search,
        'sort': sort,
        'total_courses': Course.objects.count(),
        'category_courses': category_courses,  # NEW: Category-wise grouped
        'total_categories': len(category_courses),  # NEW: Total categories count
    }
    
    return render(request, 'students/browse_courses.html', context)

@login_required
def student_progress(request):
    """Student progress tracking"""
    
    if request.user.role != 'student':
        return redirect('user_login')
    
    # Get all enrollments with progress
    enrollments = Enrollment.objects.filter(
        student=request.user,
        is_active=True
    ).select_related('course')
    
    # Get detailed progress for each course
    progress_data = []
    for enrollment in enrollments:
        # Get lesson progress for this course
        lesson_progress = LessonProgress.objects.filter(
            student=request.user,
            lesson__module__course=enrollment.course
        )
        
        total_lessons = enrollment.course.modules.filter(
            is_active=True
        ).aggregate(
            total=Count('lessons', filter=Q(lessons__is_active=True))
        )['total'] or 0
        
        completed_lessons = lesson_progress.filter(
            status='completed'
        ).count()
        
        progress_data.append({
            'enrollment': enrollment,
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'completion_rate': (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        })
    
    context = {
        'progress_data': progress_data,
    }
    
    return render(request, 'students/student_progress.html', context)


@login_required
def student_assignments(request):
    """Student assignments (placeholder)"""
    
    if request.user.role != 'student':
        return redirect('user_login')
    
    # This is a placeholder - you can extend with actual assignment models
    context = {
        'assignments': [],
    }
    
    return render(request, 'students/student_assignments.html', context)


@login_required
def student_certificates(request):
    """Student certificates (placeholder)"""
    
    if request.user.role != 'student':
        return redirect('user_login')
    
    # Get completed courses
    completed_enrollments = Enrollment.objects.filter(
        student=request.user,
        status='completed',
        is_active=True
    ).select_related('course')
    
    context = {
        'completed_enrollments': completed_enrollments,
    }
    
    return render(request, 'students/student_certificates.html', context)


@login_required
def student_settings(request):
    """Student settings"""
    
    if request.user.role != 'student':
        return redirect('user_login')
    
    if request.method == 'POST':
        # Handle settings update
        pass
    
    context = {}
    
    return render(request, 'students/student_settings.html', context)



# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# student dashborad views 
# views.py - Add these views to your existing views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator


import logging
logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# Your existing views (keep as is, just add email sending functionality)

# Add these views to your existing views.py

from .models import EmailTemplate, EmailLog, DailyEmailSummary, EmailLimitSet
from django.db.models import Count
from datetime import date, timedelta



@login_required
def manage_email_templates(request):
    """Manage email templates"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    templates = EmailTemplate.objects.all().order_by('template_type')
    return render(request, 'email_management/templates.html', {'templates': templates})


@login_required
def edit_email_template(request, template_id):
    """Edit email template"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    template = get_object_or_404(EmailTemplate, id=template_id)
    
    if request.method == 'POST':
        template.name = request.POST.get('name')
        template.subject = request.POST.get('subject')
        template.email_body = request.POST.get('email_body')
        template.is_active = 'is_active' in request.POST
        template.save()
        
        messages.success(request, 'Email template updated successfully!')
        return redirect('manage_email_templates')
    
    return render(request, 'email_management/edit_template.html', {'template': template})


@login_required
def email_limit_settings(request):
    """Manage email limit settings"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    email_limit_setting = EmailLimitSet.objects.filter(is_active=True).first()
    
    if request.method == 'POST':
        new_limit = request.POST.get('email_limit_per_day')
        try:
            new_limit = int(new_limit)
            if new_limit > 0:
                # Deactivate old settings
                EmailLimitSet.objects.filter(is_active=True).update(is_active=False)
                
                # Create new setting
                EmailLimitSet.objects.create(
                    email_limit_per_day=new_limit,
                    is_active=True
                )
                
                messages.success(request, f'Daily email limit updated to {new_limit}!')
            else:
                messages.error(request, 'Email limit must be greater than 0!')
        except ValueError:
            messages.error(request, 'Please enter a valid number!')
        
        return redirect('email_limit_settings')
    
    return render(request, 'email_management/limit_settings.html', {
        'email_limit_setting': email_limit_setting
    })


@login_required
def email_logs(request):
    """View email logs with filtering"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    # Filters
    date_filter = request.GET.get('date', '')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    logs = EmailLog.objects.all()
    
    # Apply filters
    if date_filter:
        logs = logs.filter(sent_date=date_filter)
    if status_filter:
        if status_filter == 'success':
            logs = logs.filter(is_sent_successfully=True)
        elif status_filter == 'failed':
            logs = logs.filter(is_sent_successfully=False)
    if search_query:
        logs = logs.filter(
            Q(recipient_email__icontains=search_query) |
            Q(subject__icontains=search_query)
        )
    
    # Calculate statistics before pagination
    total_count = logs.count()
    successful_count = logs.filter(is_sent_successfully=True).count()
    failed_count = logs.filter(is_sent_successfully=False).count()
    success_rate = round((successful_count / total_count * 100), 1) if total_count > 0 else 0
    
    logs = logs.order_by('-sent_time')
    
    # Pagination
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    
    context = {
        'logs': logs,
        'date_filter': date_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        'successful_count': successful_count,
        'failed_count': failed_count,
        'success_rate': success_rate,
    }
    return render(request, 'email_management/logs.html', context)

# Add these views to your existing views.py

from django.core.mail import send_mass_mail
from django.db import transaction
from django.http import JsonResponse
import json

@login_required
def bulk_email(request):
    """Send bulk emails to selected users"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    if request.method == 'POST':
        # Get form data
        template_id = request.POST.get('template_id')
        recipient_type = request.POST.get('recipient_type')
        custom_subject = request.POST.get('custom_subject')
        custom_message = request.POST.get('custom_message')
        selected_users = request.POST.getlist('selected_users')
        role = request.POST.get('role')
        
        # Validate required fields
        if not custom_subject or not custom_message:
            messages.error(request, 'Subject and message are required!')
            return redirect('bulk_email')
        
        # Check daily email limit
        if check_daily_email_limit():
            messages.error(request, 'Daily email limit reached! Cannot send bulk emails.')
            return redirect('bulk_email')
        
        # Get recipients based on selection
        recipients = []
        if recipient_type == 'all':
            recipients = CustomUser.objects.filter(email__isnull=False).exclude(email='')
        elif recipient_type == 'role':
            if not role:
                messages.error(request, 'Please select a role!')
                return redirect('bulk_email')
            recipients = CustomUser.objects.filter(role=role, email__isnull=False).exclude(email='')
        elif recipient_type == 'selected':
            if not selected_users:
                messages.error(request, 'Please select at least one user!')
                return redirect('bulk_email')
            recipients = CustomUser.objects.filter(id__in=selected_users, email__isnull=False).exclude(email='')
        
        if not recipients.exists():
            messages.error(request, 'No valid recipients found!')
            return redirect('bulk_email')
        
        # Get email template if selected
        template = None
        if template_id:
            try:
                template = EmailTemplate.objects.get(id=template_id, is_active=True)
            except EmailTemplate.DoesNotExist:
                pass
        
        # Send emails one by one with proper error handling
        successful_count = 0
        failed_count = 0
        failed_emails = []
        
        for user in recipients:
            # Check individual email limit before each send
            if check_daily_email_limit():
                messages.warning(request, f'Daily email limit reached! Only {successful_count} emails were sent.')
                break
            
            try:
                # Use template or custom content
                if template:
                    subject = template.subject
                    message = template.email_body
                else:
                    subject = custom_subject
                    message = custom_message
                
                # Replace template variables with proper fallbacks
                context_vars = {
                    '{{username}}': user.username or user.email.split('@')[0],
                    '{{email}}': user.email or '',
                    '{{first_name}}': user.first_name or user.username or user.email.split('@')[0],
                    '{{last_name}}': user.last_name or ''
                }
                
                # Replace variables in subject and message
                for var, value in context_vars.items():
                    subject = subject.replace(var, str(value))
                    message = message.replace(var, str(value))
                
                # Send individual email
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )
                
                successful_count += 1
                
                # Log successful email
                EmailLog.objects.create(
                    recipient_email=user.email,
                    recipient_user=user,
                    template_used=template,
                    subject=subject,
                    email_body=message,
                    is_sent_successfully=True,
                    sent_by=request.user
                )
                
            except Exception as e:
                failed_count += 1
                failed_emails.append(f"{user.email}: {str(e)}")
                
                # Log failed email
                EmailLog.objects.create(
                    recipient_email=user.email,
                    recipient_user=user,
                    template_used=template,
                    subject=custom_subject,
                    email_body=custom_message,
                    is_sent_successfully=False,
                    error_message=str(e),
                    sent_by=request.user
                )
        
        # Update daily summary
        try:
            today = date.today()
            email_limit = 50  # Default
            if EmailLimitSet.objects.filter(is_active=True).exists():
                email_limit = EmailLimitSet.objects.filter(is_active=True).first().email_limit_per_day
            
            daily_summary, created = DailyEmailSummary.objects.get_or_create(
                date=today,
                defaults={'daily_limit': email_limit}
            )
            daily_summary.total_emails_sent += (successful_count + failed_count)
            daily_summary.successful_emails += successful_count
            daily_summary.failed_emails += failed_count
            daily_summary.save()
        except Exception as e:
            logger.error(f'Error updating daily summary: {e}')
        
        # Show results
        if successful_count > 0:
            messages.success(request, f'Bulk email sent successfully to {successful_count} recipients!')
        
        if failed_count > 0:
            messages.warning(request, f'{failed_count} emails failed to send. Check email logs for details.')
            # Optionally log failed emails for debugging
            logger.warning(f'Failed emails: {failed_emails}')
        
        if successful_count == 0 and failed_count == 0:
            messages.error(request, 'No emails were sent!')
        
        return redirect('email_dashboard')
    
    # GET request - show bulk email form
    users = CustomUser.objects.filter(
        email__isnull=False
    ).exclude(
        email=''
    ).order_by('first_name', 'username')
    
    templates = EmailTemplate.objects.filter(is_active=True).order_by('name')
    
    # Get role-wise counts for UI
    students_count = users.filter(role='student').count()
    instructors_count = users.filter(role='instructor').count()
    admins_count = users.filter(role='superadmin').count()
    
    # Add role choices that match your template
    role_choices = [
        ('student', 'Student'),
        ('instructor', 'Instructor'), 
        ('superadmin', 'Admin')
    ]
    
    context = {
        'users': users,
        'templates': templates,
        'role_choices': role_choices,
        'students_count': students_count,
        'instructors_count': instructors_count,
        'admins_count': admins_count,
        'total_users': users.count(),
    }
    
    return render(request, 'email_management/bulk_email.html', context)


@login_required
def create_email_template(request):
    """Create new email template"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        template_type = request.POST.get('template_type')
        subject = request.POST.get('subject')
        email_body = request.POST.get('email_body')
        is_active = 'is_active' in request.POST
        
        # Check if template type already exists
        if EmailTemplate.objects.filter(template_type=template_type).exists():
            messages.error(request, 'Template type already exists!')
            return redirect('create_email_template')
        
        EmailTemplate.objects.create(
            name=name,
            template_type=template_type,
            subject=subject,
            email_body=email_body,
            is_active=is_active
        )
        
        messages.success(request, 'Email template created successfully!')
        return redirect('manage_email_templates')
    
    return render(request, 'email_management/create_template.html', {
        'template_types': EmailTemplate.TEMPLATE_TYPES
    })

@login_required
def email_dashboard(request):
    """Enhanced email management dashboard"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    # Get email statistics
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    today_summary = DailyEmailSummary.objects.filter(date=today).first()
    yesterday_summary = DailyEmailSummary.objects.filter(date=yesterday).first()
    
    # Get current email limit
    email_limit_setting = EmailLimitSet.objects.filter(is_active=True).first()
    
    # Recent email logs
    recent_emails = EmailLog.objects.order_by('-sent_time')[:10]
    
    # Email statistics for last 7 days
    week_ago = today - timedelta(days=7)
    weekly_stats = DailyEmailSummary.objects.filter(
        date__gte=week_ago
    ).order_by('-date')
    
    # Get email templates
    email_templates = EmailTemplate.objects.filter(is_active=True)[:5]
    
    context = {
        'today_summary': today_summary,
        'yesterday_summary': yesterday_summary,
        'email_limit_setting': email_limit_setting,
        'recent_emails': recent_emails,
        'weekly_stats': weekly_stats,
        'email_templates': email_templates,
    }
    return render(request, 'email_management/dashboard.html', context)

@login_required
def email_analytics(request):
    """Email analytics and reports"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    # Monthly email statistics
    from django.db.models import Count, Sum
    from datetime import datetime
    
    # Get monthly data for current year
    current_year = datetime.now().year
    monthly_stats = DailyEmailSummary.objects.filter(
        date__year=current_year
    ).extra(
        {'month': "strftime('%m', date)"}
    ).values('month').annotate(
        total_emails=Sum('total_emails_sent'),
        successful_emails=Sum('successful_emails'),
        failed_emails=Sum('failed_emails')
    ).order_by('month')
    
    # Template usage statistics
    template_stats = EmailLog.objects.values(
        'template_used__name'
    ).annotate(
        usage_count=Count('id')
    ).order_by('-usage_count')[:10]
    
    # Success rate by template
    success_rates = EmailLog.objects.values(
        'template_used__name'
    ).annotate(
        total_sent=Count('id'),
        successful=Count('id', filter=Q(is_sent_successfully=True))
    ).order_by('-total_sent')
    
    context = {
        'monthly_stats': monthly_stats,
        'template_stats': template_stats,
        'success_rates': success_rates,
        'current_year': current_year,
    }
    return render(request, 'email_management/analytics.html', context)

@login_required
def test_email_template(request, template_id):
    """Test email template by sending to admin"""
    if request.user.role != 'superadmin':
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    template = get_object_or_404(EmailTemplate, id=template_id)
    
    # Check daily email limit
    if check_daily_email_limit():
        return JsonResponse({'success': False, 'message': 'Daily email limit reached'})
    
    try:
        # Replace template variables with admin data
        subject = template.subject
        message = template.email_body.replace(
            '{{username}}', request.user.username
        ).replace(
            '{{email}}', request.user.email
        ).replace(
            '{{first_name}}', request.user.first_name or request.user.username
        ).replace(
            '{{last_name}}', request.user.last_name or ''
        )
        
        # Send test email
        send_mail(
            subject=f"[TEST] {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
            fail_silently=False,
        )
        
        # Log test email
        EmailLog.objects.create(
            recipient_email=request.user.email,
            recipient_user=request.user,
            template_used=template,
            subject=f"[TEST] {subject}",
            email_body=message,
            is_sent_successfully=True,
            sent_by=request.user
        )
        
        return JsonResponse({'success': True, 'message': 'Test email sent successfully!'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Failed to send test email: {str(e)}'})

@login_required
def delete_email_template(request, template_id):
    """Delete email template"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    template = get_object_or_404(EmailTemplate, id=template_id)
    
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        messages.success(request, f'Email template "{template_name}" deleted successfully!')
        return redirect('manage_email_templates')
    
    return render(request, 'email_management/delete_template.html', {'template': template})


# Add this missing function to your views.py

def check_daily_email_limit():
    """Check if daily email limit is reached"""
    try:
        email_limit_setting = EmailLimitSet.objects.filter(is_active=True).first()
        if not email_limit_setting:
            return False  # No limit set, can send
        
        today = date.today()
        daily_summary, created = DailyEmailSummary.objects.get_or_create(
            date=today,
            defaults={'daily_limit': email_limit_setting.email_limit_per_day}
        )
        
        return daily_summary.total_emails_sent >= daily_summary.daily_limit
    except Exception:
        return False
    

# Add these views to your views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db import IntegrityError
from django.core.paginator import Paginator
from .models import EmailTemplateType, EmailTemplate

@login_required
@staff_member_required
def manage_template_types(request):
    """Display all template types with statistics"""
    template_types = EmailTemplateType.objects.all().order_by('-created_at')
    
    # Statistics
    total_types = template_types.count()
    active_types = template_types.filter(is_active=True).count()
    inactive_types = template_types.filter(is_active=False).count()
    templates_count = EmailTemplate.objects.count()
    
    # Add template count for each type
    for template_type in template_types:
        template_type.template_count = template_type.templates.count()
    
    context = {
        'template_types': template_types,
        'total_types': total_types,
        'active_types': active_types,
        'inactive_types': inactive_types,
        'templates_count': templates_count,
    }
    
    return render(request, 'email_management/manage_template_types.html', context)


@login_required
@staff_member_required
def create_template_type(request):
    """Create new template type"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().lower()
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # Validation
            if not name or not code:
                messages.error(request, 'Name and Code are required fields!')
                return redirect('manage_template_types')
            
            # Check if code contains only valid characters
            if not code.replace('_', '').replace('-', '').isalnum():
                messages.error(request, 'Code can only contain letters, numbers, underscores and hyphens!')
                return redirect('manage_template_types')
            
            # Create template type
            template_type = EmailTemplateType.objects.create(
                name=name,
                code=code,
                description=description,
                is_active=is_active,
                created_by=request.user
            )
            
            messages.success(
                request, 
                f'Template type "{template_type.name}" has been created successfully!'
            )
            
        except IntegrityError as e:
            if 'name' in str(e):
                messages.error(request, 'A template type with this name already exists!')
            elif 'code' in str(e):
                messages.error(request, 'A template type with this code already exists!')
            else:
                messages.error(request, 'An error occurred while creating the template type.')
        
        except Exception as e:
            messages.error(request, f'An unexpected error occurred: {str(e)}')
    
    return redirect('manage_template_types')


@login_required
@staff_member_required
def update_template_type(request, template_type_id):
    """Update existing template type"""
    template_type = get_object_or_404(EmailTemplateType, id=template_type_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().lower()
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # Validation
            if not name or not code:
                messages.error(request, 'Name and Code are required fields!')
                return redirect('manage_template_types')
            
            # Check for duplicate name (excluding current record)
            if EmailTemplateType.objects.filter(name=name).exclude(id=template_type_id).exists():
                messages.error(request, 'A template type with this name already exists!')
                return redirect('manage_template_types')
            
            # Check for duplicate code (excluding current record)
            if EmailTemplateType.objects.filter(code=code).exclude(id=template_type_id).exists():
                messages.error(request, 'A template type with this code already exists!')
                return redirect('manage_template_types')
            
            # Update template type
            template_type.name = name
            template_type.code = code
            template_type.description = description
            template_type.is_active = is_active
            template_type.save()
            
            messages.success(
                request, 
                f'Template type "{template_type.name}" has been updated successfully!'
            )
            
        except Exception as e:
            messages.error(request, f'An error occurred while updating: {str(e)}')
    
    return redirect('manage_template_types')


@login_required
@staff_member_required
def delete_template_type(request, template_type_id):
    """Delete template type and all associated templates"""
    template_type = get_object_or_404(EmailTemplateType, id=template_type_id)
    
    if request.method == 'POST':
        try:
            template_name = template_type.name
            templates_count = template_type.templates.count()
            
            # Delete the template type (this will also delete associated templates due to CASCADE)
            template_type.delete()
            
            if templates_count > 0:
                messages.success(
                    request, 
                    f'Template type "{template_name}" and {templates_count} associated template(s) have been deleted successfully!'
                )
            else:
                messages.success(
                    request, 
                    f'Template type "{template_name}" has been deleted successfully!'
                )
            
        except Exception as e:
            messages.error(request, f'An error occurred while deleting: {str(e)}')
    
    return redirect('manage_template_types')


@login_required
@staff_member_required
def toggle_template_type_status(request, template_type_id):
    """Toggle template type active/inactive status"""
    template_type = get_object_or_404(EmailTemplateType, id=template_type_id)
    
    if request.method == 'POST':
        try:
            template_type.is_active = not template_type.is_active
            template_type.save()
            
            status = "activated" if template_type.is_active else "deactivated"
            messages.success(
                request, 
                f'Template type "{template_type.name}" has been {status} successfully!'
            )
            
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('manage_template_types')


@login_required
def get_templates_by_type(request, template_type_id):
    """Get templates for a specific template type (AJAX endpoint)"""
    try:
        template_type = get_object_or_404(EmailTemplateType, id=template_type_id)
        templates = template_type.templates.all().order_by('-created_at')
        
        templates_data = []
        for template in templates:
            templates_data.append({
                'id': template.id,
                'name': template.name,
                'subject': template.subject,
                'is_active': template.is_active,
                'created_at': template.created_at.strftime('%b %d, %Y'),
            })
        
        return JsonResponse({
            'success': True,
            'templates': templates_data,
            'template_type': {
                'id': template_type.id,
                'name': template_type.name,
                'code': template_type.code,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# Update your existing create_email_template view
@login_required 
@staff_member_required
def create_email_template(request):
    """Create new email template with dynamic template types"""
    
    # Get active template types
    template_types = EmailTemplateType.objects.filter(is_active=True).values_list('id', 'name')
    
    # Check if template_type is passed in URL
    selected_template_type = request.GET.get('template_type')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            template_type_id = request.POST.get('template_type')
            subject = request.POST.get('subject', '').strip()
            email_body = request.POST.get('email_body', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # Validation
            if not all([name, template_type_id, subject, email_body]):
                messages.error(request, 'All fields are required!')
                return render(request, 'email_management/create_template.html', {
                    'template_types': template_types,
                    'selected_template_type': selected_template_type,
                })
            
            # Get template type
            template_type = get_object_or_404(EmailTemplateType, id=template_type_id)
            
            # Create email template
            email_template = EmailTemplate.objects.create(
                name=name,
                template_type=template_type,
                subject=subject,
                email_body=email_body,
                is_active=is_active,
                created_by=request.user
            )
            
            messages.success(
                request, 
                f'Email template "{email_template.name}" has been created successfully!'
            )
            
            return redirect('manage_email_templates')
            
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    context = {
        'template_types': template_types,
        'selected_template_type': selected_template_type,
    }
    
    return render(request, 'email_management/create_template.html', context)



# --------------------------- password reset ---------------------------------
# --------------------------- password reset ---------------------------------
# --------------------------- password reset ---------------------------------
# --------------------------- password reset ---------------------------------
# --------------------------- password reset ---------------------------------

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from .models import CustomUser, PasswordResetOTP, EmailLog, EmailTemplate, EmailTemplateType
import logging

logger = logging.getLogger(__name__)


@csrf_protect
@require_http_methods(["GET", "POST"])
def password_reset_request(request):
    """View to request password reset OTP"""
    error = None
    success = None
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            error = "Email address is required."
        else:
            try:
                user = CustomUser.objects.get(email=email)
                
                # Generate OTP
                otp_instance = PasswordResetOTP.generate_otp(user)
                
                # Send OTP email
                if send_otp_email(user, otp_instance.otp):
                    success = f"OTP has been sent to {email}. Please check your inbox."
                    # Store email in session for next step
                    request.session['reset_email'] = email
                else:
                    error = "Failed to send OTP. Please try again."
                    
            except CustomUser.DoesNotExist:
                error = "User with this email does not exist."
    
    return render(request, 'password_reset/request.html', {
        'error': error,
        'success': success
    })


@csrf_protect
@require_http_methods(["GET", "POST"])
def password_reset_verify(request):
    """View to verify OTP"""
    error = None
    success = None
    email = request.session.get('reset_email', '')
    
    if not email:
        messages.error(request, "Session expired. Please request OTP again.")
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        
        if not otp:
            error = "OTP is required."
        elif len(otp) != 6 or not otp.isdigit():
            error = "OTP must be 6 digits."
        else:
            try:
                user = CustomUser.objects.get(email=email)
                otp_instance = PasswordResetOTP.objects.get(
                    user=user, 
                    otp=otp, 
                    is_used=False
                )
                
                if otp_instance.is_valid():
                    success = "OTP verified successfully! You can now reset your password."
                    # Store OTP in session for final step
                    request.session['verified_otp'] = otp
                else:
                    error = "OTP has expired. Please request a new one."
                    
            except (CustomUser.DoesNotExist, PasswordResetOTP.DoesNotExist):
                error = "Invalid OTP. Please check and try again."
    
    return render(request, 'password_reset/verify.html', {
        'error': error,
        'success': success,
        'email': email
    })


@csrf_protect
@require_http_methods(["GET", "POST"])
def password_reset_confirm(request):
    """View to confirm new password"""
    error = None
    success = None
    email = request.session.get('reset_email', '')
    verified_otp = request.session.get('verified_otp', '')
    
    if not email or not verified_otp:
        messages.error(request, "Session expired. Please start the reset process again.")
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if not new_password or not confirm_password:
            error = "Both password fields are required."
        elif len(new_password) < 8:
            error = "Password must be at least 8 characters long."
        elif new_password != confirm_password:
            error = "Passwords do not match."
        else:
            try:
                user = CustomUser.objects.get(email=email)
                otp_instance = PasswordResetOTP.objects.get(
                    user=user, 
                    otp=verified_otp, 
                    is_used=False
                )
                
                if otp_instance.is_valid():
                    # Set new password
                    user.set_password(new_password)
                    user.save()
                    
                    # Mark OTP as used
                    otp_instance.is_used = True
                    otp_instance.save()
                    
                    # Send confirmation email
                    send_confirmation_email(user)
                    
                    # Clear session data
                    request.session.pop('reset_email', None)
                    request.session.pop('verified_otp', None)
                    
                    messages.success(request, "Password reset successfully! You can now login with your new password.")
                    return redirect('login')  # Redirect to login page
                else:
                    error = "OTP has expired. Please start the process again."
                    
            except (CustomUser.DoesNotExist, PasswordResetOTP.DoesNotExist):
                error = "Invalid session. Please start the process again."
    
    return render(request, 'password_reset/confirm.html', {
        'error': error,
        'success': success,
        'email': email
    })


def send_otp_email(user, otp):
    """Send OTP via email with proper display name"""
    try:
        # Try to get password reset template
        try:
            template_type = EmailTemplateType.objects.get(code='password_reset')
            email_template = EmailTemplate.objects.filter(
                template_type=template_type, 
                is_active=True
            ).first()
        except (EmailTemplateType.DoesNotExist, EmailTemplate.DoesNotExist):
            email_template = None
        
        if email_template:
            # Use dynamic template
            subject = email_template.subject.format(
                username=user.username,
                first_name=user.first_name or user.username,
                last_name=user.last_name or '',
                email=user.email,
                otp=otp
            )
            
            message = email_template.email_body.format(
                username=user.username,
                first_name=user.first_name or user.username,
                last_name=user.last_name or '',
                email=user.email,
                otp=otp
            )
        else:
            # Fallback to default template
            subject = f'Password Reset OTP - {otp}'
            message = f"""
Dear {user.first_name or user.username},

Your password reset OTP is: {otp}

This OTP is valid for 5 minutes only.

If you didn't request this password reset, please ignore this email.

Best regards,
LMS Support Team
"""
        
        # Create EmailMessage with proper display name
        from_email = f"LMS System <{settings.EMAIL_HOST_USER}>"
        
        email_msg = EmailMessage(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[user.email],
        )
        
        # Send email
        email_msg.send(fail_silently=False)
        
        # Log email
        EmailLog.objects.create(
            recipient_email=user.email,
            recipient_user=user,
            template_used=email_template,
            template_type_used=email_template.template_type if email_template else None,
            subject=subject,
            email_body=message,
            is_sent_successfully=True,
            sent_by=None  # System generated
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send OTP email to {user.email}: {str(e)}")
        
        # Log failed email
        EmailLog.objects.create(
            recipient_email=user.email,
            recipient_user=user,
            template_used=email_template if 'email_template' in locals() else None,
            template_type_used=email_template.template_type if 'email_template' in locals() and email_template else None,
            subject=subject if 'subject' in locals() else 'Password Reset OTP',
            email_body=message if 'message' in locals() else '',
            is_sent_successfully=False,
            error_message=str(e),
            sent_by=None
        )
        
        return False


def send_confirmation_email(user):
    """Send password reset confirmation email with proper display name"""
    try:
        # Try to get password reset confirmation template
        try:
            template_type = EmailTemplateType.objects.get(code='password_reset_confirmation')
            email_template = EmailTemplate.objects.filter(
                template_type=template_type, 
                is_active=True
            ).first()
        except (EmailTemplateType.DoesNotExist, EmailTemplate.DoesNotExist):
            email_template = None
        
        if email_template:
            # Use dynamic template
            subject = email_template.subject.format(
                username=user.username,
                first_name=user.first_name or user.username,
                last_name=user.last_name or '',
                email=user.email
            )
            
            message = email_template.email_body.format(
                username=user.username,
                first_name=user.first_name or user.username,
                last_name=user.last_name or '',
                email=user.email
            )
        else:
            # Fallback to default template
            subject = 'Password Reset Successful'
            message = f"""
Dear {user.first_name or user.username},

Your password has been successfully reset.

If you didn't make this change, please contact our support team immediately.

Best regards,
LMS Support Team
"""
        
        # Create EmailMessage with proper display name
        from_email = f"LMS System <{settings.EMAIL_HOST_USER}>"
        
        email_msg = EmailMessage(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[user.email],
        )
        
        # Send email
        email_msg.send(fail_silently=True)  # Don't fail if confirmation email fails
        
        # Log email
        EmailLog.objects.create(
            recipient_email=user.email,
            recipient_user=user,
            template_used=email_template,
            template_type_used=email_template.template_type if email_template else None,
            subject=subject,
            email_body=message,
            is_sent_successfully=True,
            sent_by=None
        )
        
    except Exception as e:
        logger.error(f"Failed to send confirmation email to {user.email}: {str(e)}")
        # Don't raise error as password reset was successful



# userss/views.py - Add these instructor views at the end of your existing views.py

# Add these imports at the top with your existing imports
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta

# Add these after your existing views

# ==================== INSTRUCTOR DASHBOARD VIEWS ====================




# permssion views for instructor
# userss/admin_views.py (ya views.py mein add karo)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from .models import CustomUser, InstructorPermission, InstructorPermissionAssignment, InstructorProfile
from .decorators import superadmin_required

@superadmin_required
def manage_instructor_permissions(request):
    """
    Admin view to manage all instructor permissions
    """
    # Get all instructors
    instructors = CustomUser.objects.filter(role='instructor').select_related('instructor_profile')
    
    # Get all available permissions
    all_permissions = InstructorPermission.objects.filter(is_active=True).order_by('category', 'name')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        instructors = instructors.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Filter by permission
    permission_filter = request.GET.get('permission', '')
    if permission_filter:
        instructors = instructors.filter(
            instructor_profile__permissions__permission__code=permission_filter,
            instructor_profile__permissions__is_active=True
        ).distinct()
    
    context = {
        'instructors': instructors,
        'all_permissions': all_permissions,
        'search_query': search_query,
        'permission_filter': permission_filter,
    }
    
    return render(request, 'admin/manage_instructor_permissions.html', context)



# views.py mein instructor_permission_detail function update karo:

@superadmin_required
def instructor_permission_detail(request, instructor_id):
    """
    Detailed view for managing single instructor's permissions
    """
    instructor = get_object_or_404(CustomUser, id=instructor_id, role='instructor')
    
    # Get or create instructor profile
    instructor_profile, created = InstructorProfile.objects.get_or_create(
        user=instructor,
        defaults={'created_by': request.user}
    )
    
    # Get all available permissions
    all_permissions = InstructorPermission.objects.filter(is_active=True).order_by('category', 'name')
    
    # Get instructor's current permissions
    current_permissions = InstructorPermissionAssignment.objects.filter(
        instructor=instructor_profile,
        is_active=True
    ).select_related('permission')
    
    # Create a dictionary for easy lookup WITH ASSIGNMENT DETAILS
    current_permission_data = {}
    for assignment in current_permissions:
        current_permission_data[assignment.permission.code] = {
            'assignment': assignment,
            'assigned_date': assignment.assigned_at
        }
    
    context = {
        'instructor': instructor,
        'instructor_profile': instructor_profile,
        'all_permissions': all_permissions,
        'current_permission_codes': [p.permission.code for p in current_permissions],
        'current_permission_data': current_permission_data,
    }
    
    return render(request, 'admin/instructor_permission_detail.html', context)


@superadmin_required
def update_instructor_permissions(request, instructor_id):
    """
    Update instructor permissions via POST request
    """
    if request.method != 'POST':
        return redirect('manage_instructor_permissions')
    
    instructor = get_object_or_404(CustomUser, id=instructor_id, role='instructor')
    instructor_profile, created = InstructorProfile.objects.get_or_create(
        user=instructor,
        defaults={'created_by': request.user}
    )
    
    # Get selected permissions from form
    selected_permissions = request.POST.getlist('permissions')
    
    # Get all available permissions
    all_permissions = InstructorPermission.objects.filter(is_active=True)
    
    # Deactivate all current permissions
    InstructorPermissionAssignment.objects.filter(
        instructor=instructor_profile
    ).update(is_active=False)
    
    # Add new permissions
    assigned_count = 0
    for permission in all_permissions:
        if permission.code in selected_permissions:
            assignment, created = InstructorPermissionAssignment.objects.get_or_create(
                instructor=instructor_profile,
                permission=permission,
                defaults={
                    'assigned_by': request.user,
                    'is_active': True
                }
            )
            if not created:
                assignment.is_active = True
                assignment.assigned_by = request.user
                assignment.save()
            assigned_count += 1
    
    messages.success(
        request, 
        f'Successfully updated permissions for {instructor.get_full_name()}. '
        f'{assigned_count} permissions assigned.'
    )
    
    return redirect('instructor_permission_detail', instructor_id=instructor_id)

@superadmin_required
def bulk_permission_update(request):
    """
    Bulk update permissions for multiple instructors
    """
    if request.method != 'POST':
        return redirect('manage_instructor_permissions')
    
    instructor_ids = request.POST.getlist('instructor_ids')
    permission_codes = request.POST.getlist('bulk_permissions')
    action = request.POST.get('bulk_action')  # 'add' or 'remove'
    
    if not instructor_ids or not permission_codes:
        messages.error(request, 'Please select instructors and permissions.')
        return redirect('manage_instructor_permissions')
    
    # Get instructors and permissions
    instructors = CustomUser.objects.filter(id__in=instructor_ids, role='instructor')
    permissions = InstructorPermission.objects.filter(code__in=permission_codes, is_active=True)
    
    updated_count = 0
    
    for instructor in instructors:
        instructor_profile, created = InstructorProfile.objects.get_or_create(
            user=instructor,
            defaults={'created_by': request.user}
        )
        
        for permission in permissions:
            if action == 'add':
                assignment, created = InstructorPermissionAssignment.objects.get_or_create(
                    instructor=instructor_profile,
                    permission=permission,
                    defaults={
                        'assigned_by': request.user,
                        'is_active': True
                    }
                )
                if not created and not assignment.is_active:
                    assignment.is_active = True
                    assignment.assigned_by = request.user
                    assignment.save()
                    
            elif action == 'remove':
                InstructorPermissionAssignment.objects.filter(
                    instructor=instructor_profile,
                    permission=permission
                ).update(is_active=False)
        
        updated_count += 1
    
    action_text = 'assigned' if action == 'add' else 'removed'
    messages.success(
        request,
        f'Successfully {action_text} permissions for {updated_count} instructors.'
    )
    
    return redirect('manage_instructor_permissions')

@superadmin_required
def create_instructor_permission(request):
    """
    Create new instructor permission
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        
        if not all([name, code, description, category]):
            messages.error(request, 'All fields are required.')
        elif InstructorPermission.objects.filter(code=code).exists():
            messages.error(request, 'Permission code already exists.')
        else:
            InstructorPermission.objects.create(
                name=name,
                code=code,
                description=description,
                category=category,
                created_by=request.user
            )
            messages.success(request, f'Permission "{name}" created successfully.')
            return redirect('manage_instructor_permissions')
    
    context = {
        'categories': InstructorPermission.objects.values_list('category', flat=True).distinct()
    }
    return render(request, 'admin/create_instructor_permission.html', context)







# views.py (instructor dashboard views)
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from .decorators import instructor_required, instructor_permission_required
from userss.models import CustomUser
from courses.models import Course, Enrollment, Batch

@instructor_required
def instructor_dashboard(request):
    """
    Main instructor dashboard
    """
    instructor = request.user
    
    # Get instructor's courses
    instructor_courses = Course.objects.filter(
        Q(instructor=instructor) | Q(co_instructors=instructor)
    ).distinct()
    
    # Get basic stats
    total_courses = instructor_courses.count()
    total_students = Enrollment.objects.filter(
        course__in=instructor_courses,
        is_active=True
    ).count()
    
    # Get recent enrollments
    recent_enrollments = Enrollment.objects.filter(
        course__in=instructor_courses,
        is_active=True
    ).select_related('student', 'course').order_by('-enrolled_at')[:5]
    
    # Get instructor permissions for display
    permissions = instructor.get_instructor_permissions()
    
    context = {
        'total_courses': total_courses,
        'total_students': total_students,
        'recent_enrollments': recent_enrollments,
        'instructor_courses': instructor_courses[:5],  # Show recent 5
        'permissions': permissions,
    }
    
    return render(request, 'instructor/instructor_dashboard.html', context)

@instructor_permission_required('course_management')
def instructor_courses(request):
    """
    View for managing instructor's courses
    """
    instructor = request.user
    
    courses = Course.objects.filter(
        Q(instructor=instructor) | Q(co_instructors=instructor)
    ).distinct().select_related('category').prefetch_related('enrollments')
    
    context = {
        'courses': courses,
    }
    
    return render(request, 'instructor/courses.html', context)

@instructor_permission_required('content_management')
def content_management(request):
    """
    View for managing course content
    """
    instructor = request.user
    
    courses = Course.objects.filter(
        Q(instructor=instructor) | Q(co_instructors=instructor)
    ).distinct()
    
    context = {
        'courses': courses,
    }
    
    return render(request, 'instructor/content_management.html', context)

@instructor_permission_required('batch_management')
def batch_management(request):
    """
    View for managing batches
    """
    instructor = request.user
    
    # Get instructor's courses
    instructor_courses = Course.objects.filter(
        Q(instructor=instructor) | Q(co_instructors=instructor)
    ).distinct()
    
    # Get batches for instructor's courses
    batches = Batch.objects.filter(
        course__in=instructor_courses
    ).select_related('course').order_by('-created_at')
    
    context = {
        'batches': batches,
        'instructor_courses': instructor_courses,
    }
    
    return render(request, 'instructor/batch_management.html', context)

@instructor_permission_required('student_management')
def student_management(request):
    """
    View for managing students
    """
    instructor = request.user
    
    # Get instructor's courses
    instructor_courses = Course.objects.filter(
        Q(instructor=instructor) | Q(co_instructors=instructor)
    ).distinct()
    
    # Get students enrolled in instructor's courses
    enrollments = Enrollment.objects.filter(
        course__in=instructor_courses,
        is_active=True
    ).select_related('student', 'course').order_by('-enrolled_at')
    
    context = {
        'enrollments': enrollments,
        'instructor_courses': instructor_courses,
    }
    
    return render(request, 'instructor/student_management.html', context)

@instructor_permission_required('email_marketing')
def email_marketing(request):
    """
    View for email marketing
    """
    instructor = request.user
    
    # Get instructor's courses for email targeting
    instructor_courses = Course.objects.filter(
        Q(instructor=instructor) | Q(co_instructors=instructor)
    ).distinct()
    
    context = {
        'instructor_courses': instructor_courses,
    }
    
    return render(request, 'instructor/email_marketing.html', context)

@instructor_permission_required('analytics_view')
def course_analytics(request):
    """
    View for course analytics
    """
    instructor = request.user
    
    # Get instructor's courses with analytics data
    courses_data = []
    instructor_courses = Course.objects.filter(
        Q(instructor=instructor) | Q(co_instructors=instructor)
    ).distinct()
    
    for course in instructor_courses:
        enrollments = course.enrollments.filter(is_active=True)
        courses_data.append({
            'course': course,
            'total_enrollments': enrollments.count(),
            'completed_enrollments': enrollments.filter(status='completed').count(),
            'active_enrollments': enrollments.filter(status='enrolled').count(),
        })
    
    context = {
        'courses_data': courses_data,
    }
    
    return render(request, 'instructor/analytics.html', context)

@instructor_required
def check_permission(request):
    """
    AJAX endpoint to check if instructor has specific permission
    """
    permission_code = request.GET.get('permission')
    if not permission_code:
        return JsonResponse({'error': 'Permission code required'}, status=400)
    
    has_permission = request.user.has_instructor_permission(permission_code)
    
    return JsonResponse({
        'has_permission': has_permission,
        'permission_code': permission_code
    })
from courses.models import *

def instructor_course_management(request):
    return render(request,'instructor/course_management.html')


# userss/views.py (ya jahan aapka instructor views hain)

@login_required
def instructor_content_management(request):
    """Content Management - Show only assigned courses to instructor"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    # Get only courses assigned to this instructor
    courses = Course.objects.filter(
        instructor=request.user,
        is_active=True
    ).prefetch_related('modules', 'batches', 'enrollments', 'category')
    
    # Calculate stats for instructor's assigned courses only
    total_batches = Batch.objects.filter(course__instructor=request.user).count()
    total_students = BatchEnrollment.objects.filter(
        batch__course__instructor=request.user,
        is_active=True
    ).count()
    
    # Categories for filter (optional)
    categories = CourseCategory.objects.filter(is_active=True)
    
    context = {
        'courses': courses,  # Yeh zaroori hai!
        'total_courses': courses.count(),
        'published_courses': courses.filter(status='published').count(),
        'total_batches': total_batches,
        'total_students': total_students,
        'categories': categories,
    }
    
    return render(request, 'instructor/content_management.html', context)

def instructor_batch_management(request):
    return render(request,'instructor/batch_management.html')

def instructor_student_management(request):
    return render(request,'instructor/student_management.html')



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from courses.models import Course, Batch, Enrollment, BatchEnrollment
from .models import CustomUser

@login_required
def instructor_student_management(request):
    """Enhanced student management with filtering, search, and pagination"""
    
    # Check if user is instructor
    if request.user.role != 'instructor':
        return redirect('dashboard')
    
    # Get instructor's courses
    instructor_courses = Course.objects.filter(
        instructor=request.user,
        is_active=True
    ).prefetch_related('batches')
    
    # Get all enrollments for instructor's courses
    enrollments = Enrollment.objects.filter(
        course__instructor=request.user
    ).select_related(
        'student', 'course'
    ).prefetch_related(
        'student__batch_enrollments__batch'
    ).order_by('-enrolled_at')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        enrollments = enrollments.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__email__icontains=search_query) |
            Q(student__username__icontains=search_query) |
            Q(course__title__icontains=search_query) |
            Q(course__course_code__icontains=search_query)
        )
    
    # Course filter
    course_filter = request.GET.get('course')
    if course_filter:
        enrollments = enrollments.filter(course_id=course_filter)
    
    # Batch filter
    batch_filter = request.GET.get('batch')
    available_batches = []
    if course_filter:
        available_batches = Batch.objects.filter(
            course_id=course_filter,
            instructor=request.user
        )
        if batch_filter:
            # Filter enrollments by batch
            batch_enrollment_students = BatchEnrollment.objects.filter(
                batch_id=batch_filter
            ).values_list('student_id', flat=True)
            enrollments = enrollments.filter(student_id__in=batch_enrollment_students)
    else:
        available_batches = Batch.objects.filter(
            instructor=request.user
        )
    
    # Status filter
    status_filter = request.GET.get('status')
    if status_filter:
        enrollments = enrollments.filter(status=status_filter)
    
    # Sorting
    sort_by = request.GET.get('sort_by', 'recent')
    if sort_by == 'name':
        enrollments = enrollments.order_by('student__first_name', 'student__last_name')
    elif sort_by == 'progress':
        enrollments = enrollments.order_by('-progress_percentage')
    elif sort_by == 'course':
        enrollments = enrollments.order_by('course__course_code')
    else:  # recent
        enrollments = enrollments.order_by('-enrolled_at')
    
    # Add batch enrollment info to each enrollment
    for enrollment in enrollments:
        # Get the batch enrollment for this student in this course
        batch_enrollment = BatchEnrollment.objects.filter(
            student=enrollment.student,
            batch__course=enrollment.course
        ).select_related('batch').first()
        enrollment.batch_enrollment = batch_enrollment
    
    # Statistics
    total_students = enrollments.values('student').distinct().count()
    active_students = enrollments.filter(is_active=True).values('student').distinct().count()
    total_courses = instructor_courses.count()
    total_batches = Batch.objects.filter(instructor=request.user, is_active=True).count()
    
    # Pagination
    paginator = Paginator(enrollments, 20)  # 20 students per page
    page_number = request.GET.get('page')
    page_enrollments = paginator.get_page(page_number)
    
    context = {
        'enrollments': page_enrollments,
        'my_courses': instructor_courses,
        'available_batches': available_batches,
        'total_students': total_students,
        'active_students': active_students,
        'total_courses': total_courses,
        'total_batches': total_batches,
        'search_query': search_query,
    }
    
    return render(request, 'instructor/student_management.html', context)


# API endpoints for AJAX functionality

@login_required
@require_http_methods(["GET"])
def get_course_batches_api(request, course_id):
    """API to get batches for a specific course"""
    if request.user.role != 'instructor':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        course = Course.objects.get(id=course_id, instructor=request.user)
        batches = course.batches.filter(is_active=True).values('id', 'name', 'code')
        return JsonResponse({'batches': list(batches)})
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def toggle_enrollment_status(request, enrollment_id):
    """Toggle enrollment active status"""
    if request.user.role != 'instructor':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        enrollment = Enrollment.objects.get(
            id=enrollment_id,
            course__instructor=request.user
        )
        enrollment.is_active = not enrollment.is_active
        enrollment.save()
        
        return JsonResponse({
            'success': True,
            'new_status': enrollment.is_active,
            'message': f'Student {"activated" if enrollment.is_active else "deactivated"} successfully'
        })
    except Enrollment.DoesNotExist:
        return JsonResponse({'error': 'Enrollment not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def change_enrollment_status(request, enrollment_id):
    """Change enrollment status (completed, suspended, etc.)"""
    if request.user.role != 'instructor':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in ['enrolled', 'completed', 'dropped', 'suspended']:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        enrollment = Enrollment.objects.get(
            id=enrollment_id,
            course__instructor=request.user
        )
        enrollment.status = new_status
        
        # Set completion date if marked as completed
        if new_status == 'completed' and not enrollment.completed_at:
            from django.utils import timezone
            enrollment.completed_at = timezone.now()
        
        enrollment.save()
        
        return JsonResponse({
            'success': True,
            'new_status': new_status,
            'message': f'Student status changed to {new_status} successfully'
        })
    except Enrollment.DoesNotExist:
        return JsonResponse({'error': 'Enrollment not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)


@login_required
@require_http_methods(["POST"])
def bulk_change_enrollment_status(request):
    """Bulk change status for multiple enrollments"""
    if request.user.role != 'instructor':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        enrollment_ids = data.get('enrollment_ids', [])
        new_status = data.get('status')
        
        if not enrollment_ids:
            return JsonResponse({'error': 'No enrollments selected'}, status=400)
        
        if new_status not in ['enrolled', 'completed', 'dropped', 'suspended']:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        # Update enrollments
        enrollments = Enrollment.objects.filter(
            id__in=enrollment_ids,
            course__instructor=request.user
        )
        
        updated_count = 0
        for enrollment in enrollments:
            enrollment.status = new_status
            if new_status == 'completed' and not enrollment.completed_at:
                from django.utils import timezone
                enrollment.completed_at = timezone.now()
            enrollment.save()
            updated_count += 1
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'message': f'{updated_count} students updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)


@login_required
@require_http_methods(["POST"])
def remove_student_enrollment(request, enrollment_id):
    """Remove student from course (soft delete)"""
    if request.user.role != 'instructor':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        enrollment = Enrollment.objects.get(
            id=enrollment_id,
            course__instructor=request.user
        )
        
        # Soft delete - mark as inactive and dropped
        enrollment.is_active = False
        enrollment.status = 'dropped'
        enrollment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Student removed successfully'
        })
    except Enrollment.DoesNotExist:
        return JsonResponse({'error': 'Enrollment not found'}, status=404)





# Add these views to your existing views.py for instructor email functionality

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.db.models import Q
from datetime import date
from .models import CustomUser, EmailTemplate, EmailTemplateType, EmailLog, DailyEmailSummary, EmailLimitSet
from courses.models import Batch, BatchEnrollment

@login_required
def instructor_email_management(request):
    """Main email management page for instructors"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied. Instructors only.')
        return redirect('user_login')
    
    # Get instructor's batches
    instructor_batches = Batch.objects.filter(
        instructor=request.user,
        is_active=True
    ).select_related('course')
    
    # Get active email templates
    email_templates = EmailTemplate.objects.filter(
        is_active=True
    ).select_related('template_type')
    
    # Get current email limit info
    email_limit_setting = EmailLimitSet.objects.filter(is_active=True).first()
    today_summary = DailyEmailSummary.objects.filter(date=date.today()).first()
    
    # Calculate remaining emails for today
    if email_limit_setting and today_summary:
        remaining_emails = email_limit_setting.email_limit_per_day - today_summary.total_emails_sent
        remaining_emails = max(0, remaining_emails)
    else:
        remaining_emails = email_limit_setting.email_limit_per_day if email_limit_setting else 50
    
    # Get recent email logs for this instructor
    recent_emails = EmailLog.objects.filter(
        sent_by=request.user
    ).order_by('-sent_time')[:5]
    
    context = {
        'instructor_batches': instructor_batches,
        'email_templates': email_templates,
        'email_limit_setting': email_limit_setting,
        'today_summary': today_summary,
        'remaining_emails': remaining_emails,
        'recent_emails': recent_emails,
    }
    
    return render(request, 'instructor/email_management.html', context)


@login_required
def instructor_send_batch_email(request):
    """Send email to batch students"""
    if request.user.role != 'instructor':
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    if request.method == 'POST':
        template_id = request.POST.get('template_id')
        batch_id = request.POST.get('batch_id')
        selected_students = request.POST.getlist('selected_students')
        custom_subject = request.POST.get('custom_subject', '').strip()
        custom_message = request.POST.get('custom_message', '').strip()
        
        # Validation
        if not template_id and (not custom_subject or not custom_message):
            messages.error(request, 'Please select a template or provide custom subject and message.')
            return redirect('instructor_email_management')
        
        if not batch_id:
            messages.error(request, 'Please select a batch.')
            return redirect('instructor_email_management')
        
        # Get batch and verify instructor owns it
        try:
            batch = Batch.objects.get(id=batch_id, instructor=request.user, is_active=True)
        except Batch.DoesNotExist:
            messages.error(request, 'Invalid batch selection.')
            return redirect('instructor_email_management')
        
        # Check daily email limit
        if check_daily_email_limit():
            messages.error(request, 'Daily email limit reached! Cannot send emails.')
            return redirect('instructor_email_management')
        
        # Get email template if selected
        template = None
        if template_id:
            try:
                template = EmailTemplate.objects.get(id=template_id, is_active=True)
            except EmailTemplate.DoesNotExist:
                messages.error(request, 'Invalid template selection.')
                return redirect('instructor_email_management')
        
        # Get recipients based on selection
        if selected_students:
            # Specific students selected
            recipients = CustomUser.objects.filter(
                id__in=selected_students,
                role='student',
                batch_enrollments__batch=batch,
                batch_enrollments__is_active=True,
                email__isnull=False
            ).exclude(email='').distinct()
        else:
            # All batch students
            recipients = CustomUser.objects.filter(
                role='student',
                batch_enrollments__batch=batch,
                batch_enrollments__is_active=True,
                email__isnull=False
            ).exclude(email='').distinct()
        
        if not recipients.exists():
            messages.error(request, 'No valid recipients found in the selected batch.')
            return redirect('instructor_email_management')
        
        # Send emails
        successful_count = 0
        failed_count = 0
        failed_emails = []
        
        for student in recipients:
            # Check individual email limit before each send
            if check_daily_email_limit():
                messages.warning(request, f'Daily email limit reached! Only {successful_count} emails were sent.')
                break
            
            try:
                # Use template or custom content
                if template:
                    subject = template.subject
                    message = template.email_body
                else:
                    subject = custom_subject
                    message = custom_message
                
                # Replace template variables
                context_vars = {
                    '{{username}}': student.username or student.email.split('@')[0],
                    '{{email}}': student.email or '',
                    '{{first_name}}': student.first_name or student.username or student.email.split('@')[0],
                    '{{last_name}}': student.last_name or '',
                    '{{batch_name}}': batch.name,
                    '{{course_name}}': batch.course.title,
                    '{{instructor_name}}': request.user.get_full_name() or request.user.username,
                }
                
                # Replace variables in subject and message
                for var, value in context_vars.items():
                    subject = subject.replace(var, str(value))
                    message = message.replace(var, str(value))
                
                # Send email
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[student.email],
                    fail_silently=False
                )
                
                successful_count += 1
                
                # Log successful email
                EmailLog.objects.create(
                    recipient_email=student.email,
                    recipient_user=student,
                    template_used=template,
                    template_type_used=template.template_type if template else None,
                    subject=subject,
                    email_body=message,
                    is_sent_successfully=True,
                    sent_by=request.user
                )
                
            except Exception as e:
                failed_count += 1
                failed_emails.append(f"{student.email}: {str(e)}")
                
                # Log failed email
                EmailLog.objects.create(
                    recipient_email=student.email,
                    recipient_user=student,
                    template_used=template,
                    template_type_used=template.template_type if template else None,
                    subject=custom_subject if not template else template.subject,
                    email_body=custom_message if not template else template.email_body,
                    is_sent_successfully=False,
                    error_message=str(e),
                    sent_by=request.user
                )
        
        # Update daily summary
        try:
            today = date.today()
            email_limit = 50  # Default
            if EmailLimitSet.objects.filter(is_active=True).exists():
                email_limit = EmailLimitSet.objects.filter(is_active=True).first().email_limit_per_day
            
            daily_summary, created = DailyEmailSummary.objects.get_or_create(
                date=today,
                defaults={'daily_limit': email_limit}
            )
            daily_summary.total_emails_sent += (successful_count + failed_count)
            daily_summary.successful_emails += successful_count
            daily_summary.failed_emails += failed_count
            daily_summary.save()
        except Exception as e:
            pass  # Don't break the flow for logging errors
        
        # Show results
        if successful_count > 0:
            messages.success(request, f'Email sent successfully to {successful_count} students in {batch.name}!')
        
        if failed_count > 0:
            messages.warning(request, f'{failed_count} emails failed to send.')
        
        if successful_count == 0 and failed_count == 0:
            messages.error(request, 'No emails were sent!')
        
        return redirect('instructor_email_management')
    
    return redirect('instructor_email_management')


@login_required
def get_batch_students(request, batch_id):
    """AJAX endpoint to get students in a specific batch"""
    if request.user.role != 'instructor':
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    try:
        # Verify instructor owns this batch
        batch = Batch.objects.get(id=batch_id, instructor=request.user, is_active=True)
        
        # Get enrolled students
        students = CustomUser.objects.filter(
            role='student',
            batch_enrollments__batch=batch,
            batch_enrollments__is_active=True,
            email__isnull=False
        ).exclude(email='').distinct().values(
            'id', 'username', 'first_name', 'last_name', 'email'
        )
        
        students_list = []
        for student in students:
            students_list.append({
                'id': student['id'],
                'name': f"{student['first_name']} {student['last_name']}".strip() or student['username'],
                'email': student['email']
            })
        
        return JsonResponse({
            'success': True,
            'students': students_list,
            'batch_name': batch.name,
            'total_count': len(students_list)
        })
        
    except Batch.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Batch not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def get_email_template_preview(request, template_id):
    """AJAX endpoint to preview email template"""
    if request.user.role != 'instructor':
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    try:
        template = EmailTemplate.objects.get(id=template_id, is_active=True)
        
        # Sample data for preview
        sample_subject = template.subject.replace('{{username}}', 'John Doe')
        sample_subject = sample_subject.replace('{{first_name}}', 'John')
        sample_subject = sample_subject.replace('{{last_name}}', 'Doe')
        sample_subject = sample_subject.replace('{{batch_name}}', 'Sample Batch')
        sample_subject = sample_subject.replace('{{course_name}}', 'Sample Course')
        sample_subject = sample_subject.replace('{{instructor_name}}', request.user.get_full_name() or request.user.username)
        
        sample_body = template.email_body.replace('{{username}}', 'John Doe')
        sample_body = sample_body.replace('{{first_name}}', 'John')
        sample_body = sample_body.replace('{{last_name}}', 'Doe')
        sample_body = sample_body.replace('{{batch_name}}', 'Sample Batch')
        sample_body = sample_body.replace('{{course_name}}', 'Sample Course')
        sample_body = sample_body.replace('{{instructor_name}}', request.user.get_full_name() or request.user.username)
        
        return JsonResponse({
            'success': True,
            'template': {
                'id': template.id,
                'name': template.name,
                'subject': sample_subject,
                'body': sample_body,
                'original_subject': template.subject,
                'original_body': template.email_body
            }
        })
        
    except EmailTemplate.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Template not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def instructor_email_history(request):
    """View instructor's email sending history"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied. Instructors only.')
        return redirect('user_login')
    
    # Get email logs for this instructor
    email_logs = EmailLog.objects.filter(
        sent_by=request.user
    ).select_related('template_used', 'template_type_used', 'recipient_user').order_by('-sent_time')
    
    # Filter by date if provided
    date_filter = request.GET.get('date')
    if date_filter:
        email_logs = email_logs.filter(sent_date=date_filter)
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter == 'success':
        email_logs = email_logs.filter(is_sent_successfully=True)
    elif status_filter == 'failed':
        email_logs = email_logs.filter(is_sent_successfully=False)
    
    # Statistics
    total_sent = email_logs.count()
    successful_sent = email_logs.filter(is_sent_successfully=True).count()
    failed_sent = email_logs.filter(is_sent_successfully=False).count()
    success_rate = round((successful_sent / total_sent * 100), 1) if total_sent > 0 else 0
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(email_logs, 20)
    page = request.GET.get('page')
    email_logs = paginator.get_page(page)
    
    context = {
        'email_logs': email_logs,
        'total_sent': total_sent,
        'successful_sent': successful_sent,
        'failed_sent': failed_sent,
        'success_rate': success_rate,
        'date_filter': date_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'instructor/email_history.html', context)





def instructor_profile_management(request):
    return render(request,'instructor/profile_management.html')



# courses/views.py - Add this simple view

@login_required
def instructor_course_management(request):
    """Simple view for instructor to see their courses - NO CREATE/EDIT options"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    # Get instructor's courses with basic stats
    courses = Course.objects.filter(
        Q(instructor=request.user) | Q(co_instructors=request.user)
    ).distinct().select_related('category').annotate(
        enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True)),
        module_count=Count('modules', filter=Q(modules__is_active=True))
    ).order_by('-created_at')
    
    # Basic search functionality (optional)
    search_query = request.GET.get('search', '')
    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query) |
            Q(course_code__icontains=search_query)
        )
    
    # Calculate basic stats
    total_courses = courses.count()
    published_courses = courses.filter(status='published').count()
    draft_courses = courses.filter(status='draft').count()
    total_students = sum([course.enrollment_count for course in courses])
    
    context = {
        'courses': courses,
        'search_query': search_query,
        'total_courses': total_courses,
        'published_courses': published_courses,
        'draft_courses': draft_courses,
        'total_students': total_students,
    }
    
    return render(request, 'instructor/course_management.html', context)


# courses/views.py - Add these views

@login_required
def instructor_view_students(request):
    """Instructor view to see all their students across courses and batches"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    # Get instructor's courses
    instructor_courses = Course.objects.filter(
        Q(instructor=request.user) | Q(co_instructors=request.user)
    ).distinct().prefetch_related('enrollments__student', 'batches__enrollments__student')
    
    # Get course enrollments
    course_enrollments = Enrollment.objects.filter(
        course__in=instructor_courses,
        is_active=True
    ).select_related('student', 'course').order_by('-enrolled_at')
    
    # Get batch enrollments  
    batch_enrollments = BatchEnrollment.objects.filter(
        batch__course__in=instructor_courses,
        is_active=True
    ).select_related('student', 'batch', 'batch__course').order_by('-enrolled_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        course_enrollments = course_enrollments.filter(
            Q(student__username__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__email__icontains=search_query)
        )
        batch_enrollments = batch_enrollments.filter(
            Q(student__username__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__email__icontains=search_query)
        )
    
    # Calculate stats
    total_course_students = course_enrollments.count()
    total_batch_students = batch_enrollments.count()
    total_courses = instructor_courses.count()
    total_batches = sum([course.batches.count() for course in instructor_courses])
    
    context = {
        'instructor_courses': instructor_courses,
        'course_enrollments': course_enrollments,
        'batch_enrollments': batch_enrollments,
        'search_query': search_query,
        'total_course_students': total_course_students,
        'total_batch_students': total_batch_students,
        'total_courses': total_courses,
        'total_batches': total_batches,
    }
    
    return render(request, 'instructor/view_students.html', context)


@login_required
def instructor_course_detail(request, course_id):
    """Detailed view of specific course with students and batches"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    # Get course and check permission
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != request.user and request.user not in course.co_instructors.all():
        messages.error(request, "You don't have permission to view this course!")
        return redirect('instructor_see_all_course')
    
    # Get course data
    modules = course.modules.filter(is_active=True).prefetch_related('lessons')
    enrollments = course.enrollments.filter(is_active=True).select_related('student')
    batches = course.batches.all().prefetch_related('enrollments__student')
    
    # Calculate stats
    total_modules = modules.count()
    total_lessons = sum([module.lessons.filter(is_active=True).count() for module in modules])
    total_students = enrollments.count()
    total_batch_students = sum([batch.enrollments.filter(is_active=True).count() for batch in batches])
    
    context = {
        'course': course,
        'modules': modules,
        'enrollments': enrollments,
        'batches': batches,
        'total_modules': total_modules,
        'total_lessons': total_lessons,
        'total_students': total_students,
        'total_batch_students': total_batch_students,
    }
    
    return render(request, 'instructor/course_detail.html', context)





# exam management
# exam management
# exam management
# exam management
# exam management
# exam management
# exam management

def createExam(request):
    return render(request,"exam/create_exam.html")

def assignExam(request):
    return render(request,"exam/assign_exam.html")

def exam_submission(request):
    return render(request,"exam/exam_submissions.html")

from django.core.mail import send_mail
from django.conf import settings

@login_required
def send_email_to_user(request, user_id):
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        email_type = request.POST.get('email_type', 'general')
        priority = request.POST.get('priority', 'normal')
        send_copy = request.POST.get('send_copy')
        
        # Check email limit
        today = date.today()
        email_limit = EmailLimitSet.objects.filter(is_active=True).first()
        daily_limit = email_limit.email_limit_per_day if email_limit else 50
        
        today_emails = EmailLog.objects.filter(
            recipient_user=user,
            sent_date=today
        ).count()
        
        if today_emails >= daily_limit:
            messages.warning(request, f'User has reached daily email limit ({daily_limit}). Email not sent.')
            return redirect('user_details', user_id=user_id)
        
        try:
            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            # Log email
            EmailLog.objects.create(
                recipient_user=user,
                sent_by=request.user,
                subject=subject,
                email_body=message,
                is_sent_successfully=True,
                sent_date=today,
            )
            
            # Send copy to self if requested
            if send_copy:
                send_mail(
                    subject=f"Copy: {subject}",
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],
                    fail_silently=True,
                )
            
            messages.success(request, f'Email sent successfully to {user.get_full_name()}!')
            return redirect('user_details', user_id=user_id)
            
        except Exception as e:
            # Log failed email
            EmailLog.objects.create(
                recipient_user=user,
                sent_by=request.user,
                subject=subject,
                email_body=message,
                is_sent_successfully=False,
                sent_date=today,
            )
            messages.error(request, f'Failed to send email: {str(e)}')
    
    return render(request, 'send_email_to_user.html', {'user': user})