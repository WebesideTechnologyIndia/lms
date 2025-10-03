# context_processors.py (अपने main app में बनाएं)
def sidebar_context(request):
    context = {}
    
    if request.user.is_authenticated:
        from courses.models import Course
        
        # Check if user is admin (either superuser or superadmin role)
        is_admin = request.user.is_superuser or getattr(request.user, 'role', None) == 'superadmin'
        
        if is_admin:
            sidebar_courses = Course.objects.filter(is_active=True).order_by('course_code')[:15]
        elif getattr(request.user, 'role', None) == 'instructor':
            sidebar_courses = Course.objects.filter(
                instructor=request.user, 
                is_active=True
            ).order_by('course_code')[:15]
        else:
            sidebar_courses = []
            
        context['sidebar_courses'] = sidebar_courses
        context['is_admin_user'] = is_admin  # Template में use करने के लिए
    
    return context



# context_processors.py (update existing file)
from courses.models import Course

def instructor_permissions(request):
    """
    Make instructor permissions available in all templates
    """
    context = {
        'instructor_permissions': [],
        'has_content_permission': False,
        'has_email_permission': False,
        'has_course_permission': False,
        'has_batch_permission': False,
        'has_student_permission': False,
        'has_analytics_permission': False,
    }
    
    if request.user.is_authenticated and request.user.role == 'instructor':
        try:
            # Get instructor's permissions
            permissions = request.user.get_instructor_permissions()
            permission_codes = [p.permission.code for p in permissions]
            
            context.update({
                'instructor_permissions': permission_codes,
                'has_content_permission': 'content_management' in permission_codes,
                'has_email_permission': 'email_marketing' in permission_codes,
                'has_course_permission': 'course_management' in permission_codes,
                'has_batch_permission': 'batch_management' in permission_codes,
                'has_student_permission': 'student_management' in permission_codes,
                'has_analytics_permission': 'analytics_view' in permission_codes,
            })
        except:
            pass
    
    return context

def sidebar_courses(request):
    """
    Make courses available in sidebar for all users
    """
    sidebar_courses = []
    
    if request.user.is_authenticated:
        if request.user.role == 'superadmin':
            # Admin can see all courses
            sidebar_courses = Course.objects.filter(is_active=True).order_by('-created_at')[:10]
        elif request.user.role == 'instructor':
            # Instructor can see their courses
            from django.db.models import Q
            sidebar_courses = Course.objects.filter(
                Q(instructor=request.user) | Q(co_instructors=request.user),
                is_active=True
            ).distinct().order_by('-created_at')[:10]
    
    return {
        'sidebar_courses': sidebar_courses
    }


# instructor/context_processors.py - Navigation context for instructor

def instructor_navigation(request):
    """Add instructor navigation context"""
    if request.user.is_authenticated and request.user.role == 'instructor':
        # Get instructor courses for dropdown
        instructor_courses = request.user.instructor_courses.filter(
            is_active=True
        ).order_by('title')[:10]  # Limit to 10 for dropdown
        
        return {
            'instructor_courses': instructor_courses,
            'instructor_nav_items': [
                {
                    'name': 'Dashboard',
                    'url': 'instructor:dashboard',
                    'icon': 'bi-speedometer2'
                },
                {
                    'name': 'My Courses',
                    'url': 'instructor:manage_courses',
                    'icon': 'bi-book'
                },
                {
                    'name': 'Batch Overview',
                    'url': 'instructor:batch_overview',
                    'icon': 'bi-people'
                },
                {
                    'name': 'Content Management',
                    'url': 'instructor:content_overview',
                    'icon': 'bi-file-earmark-text'
                },
                {
                    'name': 'Reports',
                    'url': 'instructor:reports',
                    'icon': 'bi-graph-up'
                },
            ]
        }
    return {}

# settings.py mein add karna:
# TEMPLATES = [
#     {
#         'OPTIONS': {
#             'context_processors': [
#                 ...
#                 'instructor.context_processors.instructor_navigation',
#             ],
#         },
#     },
# ]