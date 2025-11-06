# userss/context_processors.py
def instructor_navigation(request):
    if request.user.is_authenticated and request.user.role == 'instructor':
        return {
            'instructor_nav_items': [
                {'name': 'Dashboard', 'url': 'instructor_dashboard', 'icon': 'bi-speedometer2'},
                {'name': 'Courses', 'url': 'instructor_course_management', 'icon': 'bi-book'},
                {'name': 'Batches', 'url': 'courses:batch_overview', 'icon': 'bi-people'},
            ]
        }
    return {}


def student_context(request):
    """Global context for student sidebar counts"""
    if request.user.is_authenticated and request.user.role == 'student':
        from courses.models import Enrollment, BatchEnrollment
        
        enrolled_courses_count = Enrollment.objects.filter(
            student=request.user,
            is_active=True
        ).count()
        
        return {
            'enrolled_courses_count': enrolled_courses_count,
        }
    
    return {'enrolled_courses_count': 0}


# lms/context_processors.py

def instructor_permissions(request):
    """
    Add instructor permissions to all templates
    """
    if not request.user.is_authenticated:
        return {}
    
    if request.user.role != 'instructor':
        return {}
    
    # Permission mapping - database codes to template variables
    permission_mapping = {
        'course_management': 'has_course_permission',
        'batch_management': 'has_batch_permission',
        'content_management': 'has_content_permission',
        'exam_dashboard': 'has_exam_permission',
        'create_exam': 'has_create_exam_permission',
        'my_exams': 'has_my_exams_permission',
        'assign_exam': 'has_assign_exam_permission',
        'attendance_dashboard': 'has_attendance_dashboard_permission',
        'createsession': 'has_createsession_permission',
        'all_sessions': 'has_all_sessions_permission',
        'attendance_pending': 'has_attendance_pending_permission',
        'attendance_reports': 'has_attendance_reports_permission',
        'student_management': 'has_student_permission',
        'email_marketing': 'has_email_permission',
        'profile_setting': 'has_profile_setting_permission',
    }
    
    # Generate permission flags
    permission_flags = {}
    for perm_code, template_var in permission_mapping.items():
        permission_flags[template_var] = request.user.has_instructor_permission(perm_code)
    
    return permission_flags