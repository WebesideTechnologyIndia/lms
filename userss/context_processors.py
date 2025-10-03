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