# courses/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from .forms import (
    CourseForm, CourseCategoryForm, CourseModuleForm,
    EnrollmentForm, CourseReviewForm, CourseFAQForm, CourseSearchForm,
    BatchForm, SimpleBatchModuleForm, SimpleBatchLessonForm, BatchEnrollForm  # <-- Yeh line add karo
)
# courses/views.py - Top mein imports section

from .models import (
    Course, CourseCategory, CourseModule, CourseLesson,
    Enrollment, CourseReview, CourseFAQ,
    # Yeh batch models add karo:
    Batch, BatchModule, BatchLesson, BatchEnrollment  # <-- Yeh line add karo
)

from .forms import (
    CourseForm, CourseCategoryForm, CourseModuleForm,
    EnrollmentForm, CourseReviewForm, CourseFAQForm, CourseSearchForm,
    # Yeh batch forms add karo:
    BatchForm, SimpleBatchModuleForm, SimpleBatchLessonForm, BatchEnrollForm  # <-- Yeh line add karo
)
from .models import (
    Course, CourseCategory, CourseModule, CourseLesson,
    Enrollment
)
from .forms import (
    CourseForm, CourseCategoryForm, CourseModuleForm,
    EnrollmentForm, CourseReviewForm, CourseFAQForm, CourseSearchForm,

)

User = get_user_model()


# ==================== COURSE MANAGEMENT VIEWS ====================

# views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from .models import Course, CourseCategory, Enrollment

@login_required
def course_dashboard(request):
    """Simple course dashboard - no permission checks"""
    
    # Basic stats for all logged-in users
    total_courses = Course.objects.count()
    active_courses = Course.objects.filter(is_active=True, status='published').count()
    draft_courses = Course.objects.filter(status='draft').count()
    total_enrollments = Enrollment.objects.count()
    recent_courses = Course.objects.all().order_by('-created_at')[:5]
    
    # Categories
    categories = CourseCategory.objects.filter(is_active=True)
    
    context = {
        'total_courses': total_courses,
        'active_courses': active_courses,
        'draft_courses': draft_courses,
        'total_enrollments': total_enrollments,
        'recent_courses': recent_courses,
        'categories': categories,
    }
    
    return render(request, 'courses/dashboard.html', context)

@login_required
def manage_courses(request):
    """List and manage all courses"""
    
    # Filter courses based on user role
    if request.user.role == 'superadmin':
        courses = Course.objects.all()
    else:
        courses = Course.objects.filter(instructor=request.user)
    
    # Search and filter
    search_form = CourseSearchForm(request.GET or None)
    
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        category = search_form.cleaned_data.get('category')
        difficulty = search_form.cleaned_data.get('difficulty')
        course_type = search_form.cleaned_data.get('course_type')
        price_range = search_form.cleaned_data.get('price_range')
        sort_by = search_form.cleaned_data.get('sort_by') or '-created_at'
        
        # Apply filters
        if search_query:
            courses = courses.filter(
                Q(title__icontains=search_query) |
                Q(course_code__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        if category:
            courses = courses.filter(category=category)
        
        if difficulty:
            courses = courses.filter(difficulty_level=difficulty)
        
        if course_type:
            courses = courses.filter(course_type=course_type)
        
        if price_range:
            if price_range == 'free':
                courses = courses.filter(is_free=True)
            elif price_range == '0-50':
                courses = courses.filter(price__lte=50, is_free=False)
            elif price_range == '50-100':
                courses = courses.filter(price__gt=50, price__lte=100)
            elif price_range == '100-200':
                courses = courses.filter(price__gt=100, price__lte=200)
            elif price_range == '200+':
                courses = courses.filter(price__gt=200)
        
        # Apply sorting
        courses = courses.order_by(sort_by)
    else:
        courses = courses.order_by('-created_at')
    
    # Add enrollment count annotation
    courses = courses.annotate(
        enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True))
    )
    
    # Pagination
    paginator = Paginator(courses, 10)
    page = request.GET.get('page')
    courses = paginator.get_page(page)
    
    context = {
        'courses': courses,
        'search_form': search_form,
    }
    
    return render(request, 'courses/manage_courses.html', context)



from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.text import slugify
import json

@login_required
def create_course(request):
    """Create a new course"""
    if request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.created_by = request.user
            
            # If instructor, set them as the instructor
            if request.user.role == 'instructor':
                course.instructor = request.user
            
            # Auto-generate slug
            if not course.slug:
                course.slug = slugify(f"{course.course_code}-{course.title}")
            
            course.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, f'Course "{course.title}" created successfully!')
            return redirect('courses:manage_courses')
    else:
        form = CourseForm()
    
    context = {
        'form': form,
        'title': 'Create New Course',
        'button_text': 'Create Course'
    }
    
    return render(request, 'courses/course_form.html', context)


@login_required
def edit_course(request, course_id):
    """Edit an existing course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You can only edit your own courses!")
        return redirect('courses:manage_courses')
    elif request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            course = form.save()
            messages.success(request, f'Course "{course.title}" updated successfully!')
            return redirect('courses:manage_courses')
    else:
        form = CourseForm(instance=course)
    
    context = {
        'form': form,
        'course': course,
        'title': f'Edit Course: {course.title}',
        'button_text': 'Update Course'
    }
    
    return render(request, 'courses/course_form.html', context)


@login_required
@require_POST
def toggle_course_status(request, course_id):
    """Toggle course status between published and draft"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        return JsonResponse({
            'success': False,
            'message': 'You can only modify your own courses!'
        }, status=403)
    elif request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to perform this action!'
        }, status=403)
    
    try:
        # Toggle status
        if course.status == 'published':
            course.status = 'draft'
            message = f'Course "{course.title}" has been set to Draft.'
        elif course.status == 'draft':
            course.status = 'published'
            message = f'Course "{course.title}" has been Published.'
        elif course.status == 'archived':
            course.status = 'published'
            message = f'Course "{course.title}" has been Reactivated.'
        else:
            # For suspended or other statuses, set to draft
            course.status = 'draft'
            message = f'Course "{course.title}" status updated to Draft.'
        
        course.save()
        
        return JsonResponse({
            'success': True,
            'message': message,
            'new_status': course.status,
            'status_display': course.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating status: {str(e)}'
        }, status=500)


@login_required
def change_course_status(request, course_id):
    """Change course status to any available status"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You can only modify your own courses!")
        return redirect('courses:manage_courses')
    elif request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        # Validate status
        valid_statuses = ['draft', 'published', 'archived', 'suspended']
        if new_status in valid_statuses:
            old_status = course.get_status_display()
            course.status = new_status
            course.save()
            
            messages.success(
                request, 
                f'Course "{course.title}" status changed from {old_status} to {course.get_status_display()}.'
            )
        else:
            messages.error(request, 'Invalid status selected.')
        
        return redirect('courses:manage_courses')
    
    # GET request - show status change form
    context = {
        'course': course,
        'status_choices': Course.STATUS_CHOICES
    }
    
    return render(request, 'courses/change_status.html', context)

@login_required
def course_detail(request, course_id):
    """View course details"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user can view this course
    can_view = False
    if request.user.role == 'superadmin':
        can_view = True
    elif request.user.role == 'instructor' and course.instructor == request.user:
        can_view = True
    elif request.user.role == 'student':
        # Students can view if enrolled or if course is published
        if course.status == 'published' or course.enrollments.filter(student=request.user, is_active=True).exists():
            can_view = True
    
    if not can_view:
        messages.error(request, "You don't have permission to view this course!")
        return redirect('courses:course_dashboard')
    
    # Get course modules and lessons
    modules = course.modules.filter(is_active=True).prefetch_related('lessons')
    
    # Get enrollment info for students
    user_enrollment = None
    if request.user.role == 'student':
        user_enrollment = course.enrollments.filter(student=request.user, is_active=True).first()
    
    # Get course reviews
    reviews = course.reviews.filter(is_approved=True).order_by('-created_at')[:5]
    
    # Get FAQs
    faqs = course.faqs.filter(is_active=True)
    
    context = {
        'course': course,
        'modules': modules,
        'user_enrollment': user_enrollment,
        'reviews': reviews,
        'faqs': faqs,
    }
    
    return render(request, 'courses/course_detail.html', context)


@login_required
def delete_course(request, course_id):
    """Delete a course (soft delete by setting inactive)"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You can only delete your own courses!")
        return redirect('manage_courses')
    elif request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    if request.method == 'POST':
        course_title = course.title
        course.is_active = False
        course.status = 'archived'
        course.save()
        
        messages.success(request, f'Course "{course_title}" has been archived!')
        return redirect('courses:manage_courses')
    
    context = {
        'course': course,
        'enrolled_count': course.get_enrolled_count()
    }
    
    return render(request, 'courses/delete_course.html', context)




# ==================== COURSE CATEGORY MANAGEMENT ====================

@login_required
def manage_categories(request):
    """Manage course categories"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    categories = CourseCategory.objects.all().annotate(
        course_count=Count('courses')
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(categories, 15)
    page = request.GET.get('page')
    categories = paginator.get_page(page)
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'courses/manage_categories.html', context)


@login_required
def create_category(request):
    """Create new course category"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    if request.method == 'POST':
        form = CourseCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            
            messages.success(request, f'Category "{category.name}" created successfully!')
            return redirect('courses:manage_categories')
    else:
        form = CourseCategoryForm()
    
    context = {
        'form': form,
        'title': 'Create New Category',
        'button_text': 'Create Category'
    }
    
    return render(request, 'courses/category_form.html', context)


@login_required
def edit_category(request, category_id):
    """Edit course category"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    category = get_object_or_404(CourseCategory, id=category_id)
    
    if request.method == 'POST':
        form = CourseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('courses:manage_categories')
    else:
        form = CourseCategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': f'Edit Category: {category.name}',
        'button_text': 'Update Category'
    }
    
    return render(request, 'courses/category_form.html', context)


@login_required
def delete_category(request, category_id):
    """Delete course category"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    category = get_object_or_404(CourseCategory, id=category_id)
    
    if request.method == 'POST':
        if category.courses.exists():
            messages.error(request, f'Cannot delete category "{category.name}" as it has associated courses!')
        else:
            category_name = category.name
            category.delete()
            messages.success(request, f'Category "{category_name}" deleted successfully!')
        return redirect('courses:manage_categories')
    
    context = {
        'category': category,
        'courses_count': category.courses.count()
    }
    
    return render(request, 'courses/delete_category.html', context)


# ==================== COURSE MODULES MANAGEMENT ====================

@login_required
def course_modules(request, course_id):
    """Manage course modules"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You can only manage your own course modules!")
        return redirect('manage_courses')
    elif request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    modules = course.modules.all().order_by('order')
    
    context = {
        'course': course,
        'modules': modules,
    }
    
    return render(request, 'courses/course_modules.html', context)


@login_required
def create_module(request, course_id):
    """Create new course module"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You can only create modules for your own courses!")
        return redirect('manage_courses')
    elif request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    if request.method == 'POST':
        form = CourseModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.save()
            
            messages.success(request, f'Module "{module.title}" created successfully!')
            return redirect('courses:course_modules', course_id=course.id)
    else:
        # Auto-suggest next order number
        next_order = course.modules.count() + 1
        form = CourseModuleForm(initial={'order': next_order})
    
    context = {
        'form': form,
        'course': course,
        'title': f'Create Module for {course.title}',
        'button_text': 'Create Module'
    }
    
    return render(request, 'courses/module_form.html', context)

@login_required
def create_module_instructor(request, course_id):
    """Create new course module"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You can only create modules for your own courses!")
        return redirect('manage_courses')
    elif request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    if request.method == 'POST':
        form = CourseModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.save()
            
            messages.success(request, f'Module "{module.title}" created successfully!')
            return redirect('courses:instructor_course_modules', course_id=course.id)
    else:
        # Auto-suggest next order number
        next_order = course.modules.count() + 1
        form = CourseModuleForm(initial={'order': next_order})
    
    context = {
        'form': form,
        'course': course,
        'title': f'Create Module for {course.title}',
        'button_text': 'Create Module'
    }
    
    return render(request, 'courses/create_module_instructor.html', context)


@login_required
def edit_module(request, course_id, module_id):
    """Edit course module"""
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You can only edit your own course modules!")
        return redirect('manage_courses')
    elif request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    if request.method == 'POST':
        form = CourseModuleForm(request.POST, instance=module)
        if form.is_valid():
            module = form.save()
            messages.success(request, f'Module "{module.title}" updated successfully!')
            return redirect('courses:course_modules', course_id=course.id)
    else:
        form = CourseModuleForm(instance=module)
    
    context = {
        'form': form,
        'course': course,
        'module': module,
        'title': f'Edit Module: {module.title}',
        'button_text': 'Update Module'
    }
    
    return render(request, 'courses/module_form.html', context)


@login_required
def delete_module(request, course_id, module_id):
    """Delete course module"""
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You can only delete your own course modules!")
        return redirect('manage_courses')
    elif request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    if request.method == 'POST':
        module_title = module.title
        lesson_count = module.lessons.count()
        module.delete()
        
        messages.success(request, f'Module "{module_title}" and {lesson_count} associated lessons deleted successfully!')
        return redirect('course_modules', course_id=course.id)
    
    context = {
        'course': course,
        'module': module,
        'lesson_count': module.lessons.count()
    }
    
    return render(request, 'courses/delete_module.html', context)


# ==================== COURSE LESSONS MANAGEMENT ====================



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction

# courses/views.py - Fixed create_lesson view
# courses/views.py - SIMPLE LESSON VIEWS

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import BasicLessonForm
from .models import Course, CourseModule, CourseLesson


# courses/views.py - Enhanced Lesson Views

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from .forms import EnhancedLessonForm, LessonAttachmentFormSet, QuickLessonForm
from .models import Course, CourseModule, CourseLesson, LessonAttachment
from .forms import EnhancedLessonForm, LessonAttachmentFormSet


# courses/views.py - REPLACE create_lesson view

@login_required
def create_lesson(request, course_id, module_id):
    """Create a new lesson with AUTO ORDER"""
    
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You don't have permission to edit this course")
        return redirect('courses:course_detail', course_id=course.id)
    
    if request.method == 'POST':
        form = EnhancedLessonForm(request.POST, request.FILES, module=module)
        
        attachment_formset = LessonAttachmentFormSet(
            request.POST, 
            request.FILES,
            prefix='attachments',
            queryset=LessonAttachment.objects.none()
        )
        
        if form.is_valid() and attachment_formset.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            
            # 🔥 AUTO-SET ORDER - THIS FIXES THE ERROR!
            from django.db.models import Max
            max_order = module.lessons.aggregate(Max('order'))['order__max'] or 0
            lesson.order = max_order + 1
            
            lesson.save()
            
            # Save attachments
            attachments = attachment_formset.save(commit=False)
            for attachment in attachments:
                attachment.lesson = lesson
                attachment.save()
            
            messages.success(request, f'Lesson "{lesson.title}" created successfully!')
            
            if 'save_and_continue' in request.POST:
                return redirect('courses:create_lesson', course_id=course.id, module_id=module.id)
            else:
                return redirect('courses:module_lessons', course_id=course.id, module_id=module.id)
        else:
            if not form.is_valid():
                messages.error(request, 'Please correct the errors in the lesson form.')
            if not attachment_formset.is_valid():
                messages.error(request, 'There was an issue with attachments.')
    else:
        form = EnhancedLessonForm(module=module)
        attachment_formset = LessonAttachmentFormSet(
            prefix='attachments',
            queryset=LessonAttachment.objects.none()
        )
    
    context = {
        'form': form,
        'attachment_formset': attachment_formset,
        'course': course,
        'module': module,
        'title': 'Create Lesson',
        'button_text': 'Create Lesson',
        'is_edit': False,
    }
    
    return render(request, 'courses/enhanced_lesson_form.html', context)

@login_required
def create_lesson_instructor(request, course_id, module_id):
    """Create a new lesson with AUTO ORDER"""
    
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You don't have permission to edit this course")
        return redirect('courses:course_detail', course_id=course.id)
    
    if request.method == 'POST':
        form = EnhancedLessonForm(request.POST, request.FILES, module=module)
        
        attachment_formset = LessonAttachmentFormSet(
            request.POST, 
            request.FILES,
            prefix='attachments',
            queryset=LessonAttachment.objects.none()
        )
        
        if form.is_valid() and attachment_formset.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            
            # 🔥 AUTO-SET ORDER - THIS FIXES THE ERROR!
            from django.db.models import Max
            max_order = module.lessons.aggregate(Max('order'))['order__max'] or 0
            lesson.order = max_order + 1
            
            lesson.save()
            
            # Save attachments
            attachments = attachment_formset.save(commit=False)
            for attachment in attachments:
                attachment.lesson = lesson
                attachment.save()
            
            messages.success(request, f'Lesson "{lesson.title}" created successfully!')
            
            if 'save_and_continue' in request.POST:
                return redirect('courses:create_lesson', course_id=course.id, module_id=module.id)
            else:
                return redirect('courses:module_lessons', course_id=course.id, module_id=module.id)
        else:
            if not form.is_valid():
                messages.error(request, 'Please correct the errors in the lesson form.')
            if not attachment_formset.is_valid():
                messages.error(request, 'There was an issue with attachments.')
    else:
        form = EnhancedLessonForm(module=module)
        attachment_formset = LessonAttachmentFormSet(
            prefix='attachments',
            queryset=LessonAttachment.objects.none()
        )
    
    context = {
        'form': form,
        'attachment_formset': attachment_formset,
        'course': course,
        'module': module,
        'title': 'Create Lesson',
        'button_text': 'Create Lesson',
        'is_edit': False,
    }
    
    return render(request, 'courses/lesson_instrtctor_create.html', context)



# Alternative: Simple debugging view


@login_required
def module_lessons(request, course_id, module_id):
    """View to list all lessons in a module"""
    
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course)
    
    # Check permissions
    can_edit = False
    if request.user.is_authenticated:
        if request.user.role == 'admin' or (request.user.role == 'instructor' and course.instructor == request.user):
            can_edit = True
    
    # Get all lessons ordered
    lessons = module.lessons.all().order_by('order')
    
    # Debug: Print lesson count
    print(f"Module: {module.title}")
    print(f"Total lessons: {lessons.count()}")
    for lesson in lessons:
        print(f"- {lesson.title} (Order: {lesson.order})")
    
    context = {
        'course': course,
        'module': module,
        'lessons': lessons,
        'can_edit': can_edit,
    }
    
    return render(request, 'courses/module_lessons.html', context)

@login_required
def edit_lesson(request, course_id, module_id, lesson_id):
    """Edit lesson with all content types"""
    
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course)
    lesson = get_object_or_404(CourseLesson, id=lesson_id, module=module)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You can only edit lessons from your own courses!")
        return redirect('courses:manage_courses')
    
    if request.method == 'POST':
        form = EnhancedLessonForm(request.POST, request.FILES, instance=lesson, module=module)
        attachment_formset = LessonAttachmentFormSet(
            request.POST, request.FILES, instance=lesson
        )
        
        if form.is_valid() and attachment_formset.is_valid():
            lesson = form.save()
            attachment_formset.save()
            
            messages.success(request, f'Lesson "{lesson.title}" updated successfully!')
            return redirect('courses:lesson_detail', 
                          course_id=course.id, module_id=module.id, lesson_id=lesson.id)
        else:
            messages.error(request, 'Please fix the errors below.')
    
    else:
        form = EnhancedLessonForm(instance=lesson, module=module)
        attachment_formset = LessonAttachmentFormSet(instance=lesson)
    
    context = {
        'course': course,
        'module': module,
        'lesson': lesson,
        'form': form,
        'attachment_formset': attachment_formset,
        'title': f'Edit: {lesson.title}',
        'button_text': 'Update Lesson',
        'is_edit': True
    }
    
    return render(request, 'courses/enhanced_lesson_form.html', context)


@login_required
def quick_create_lesson(request, course_id, module_id):
    """Quick lesson creation - minimal form"""
    
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('courses:manage_courses')
    
    if request.method == 'POST':
        form = QuickLessonForm(request.POST, module=module)
        
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            
            # Auto-set order
            last_lesson = module.lessons.order_by('-order').first()
            lesson.order = (last_lesson.order + 1) if last_lesson else 1
            
            lesson.save()
            
            messages.success(request, f'Quick lesson "{lesson.title}" created!')
            
            # Redirect to edit for adding content
            return redirect('courses:edit_lesson', 
                          course_id=course.id, module_id=module.id, lesson_id=lesson.id)
        else:
            messages.error(request, 'Please fix the errors below.')
    
    else:
        form = QuickLessonForm(module=module)
    
    context = {
        'course': course,
        'module': module,
        'form': form,
        'title': f'Quick Create - {module.title}',
        'button_text': 'Create & Add Content',
        'is_quick': True
    }
    
    return render(request, 'courses/quick_lesson_form.html', context)

# courses/views.py - UPDATE existing lesson_detail view

@login_required
def lesson_detail(request, course_id, module_id, lesson_id):
    """Detailed lesson view with progress tracking"""
    
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course)
    lesson = get_object_or_404(CourseLesson, id=lesson_id, module=module)
    
    # Check access permissions
    can_access = False
    is_enrolled = False
    
    if request.user.is_authenticated:
        if request.user.role == 'instructor' and course.instructor == request.user:
            can_access = True
        elif request.user.role == 'superadmin':
            can_access = True
        elif request.user.role == 'student':
            is_enrolled = course.enrollments.filter(
                student=request.user, is_active=True
            ).exists()
            if is_enrolled or lesson.is_free_preview:
                can_access = True
    
    if not can_access and not lesson.is_free_preview:
        messages.error(request, "You need to enroll in this course to access lessons.")
        return redirect('courses:course_detail', course_id=course.id)
    
    # 🔥 TRACK PROGRESS - THIS IS THE KEY PART
    lesson_progress = None
    if request.user.is_authenticated and request.user.role == 'student' and is_enrolled:
        lesson_progress, created = LessonProgress.objects.get_or_create(
            student=request.user,
            lesson=lesson
        )
        # Mark as started if first time
        if created or lesson_progress.status == 'not_started':
            lesson_progress.mark_as_started()
        
        # Update last accessed
        lesson_progress.last_accessed = timezone.now()
        lesson_progress.save(update_fields=['last_accessed'])
        
        # Also update enrollment last_accessed
        enrollment = course.enrollments.get(student=request.user, is_active=True)
        enrollment.last_accessed = timezone.now()
        enrollment.save(update_fields=['last_accessed'])
    
    # Get navigation lessons
    other_lessons = module.lessons.filter(is_active=True).exclude(id=lesson.id)
    prev_lesson = other_lessons.filter(order__lt=lesson.order).order_by('-order').first()
    next_lesson = other_lessons.filter(order__gt=lesson.order).order_by('order').first()
    
    context = {
        'course': course,
        'module': module,
        'lesson': lesson,
        'can_access': can_access,
        'is_enrolled': is_enrolled,
        'lesson_progress': lesson_progress,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'attachments': lesson.attachments.filter(is_active=True),
    }
    
    return render(request, 'courses/lesson_detail.html', context)

@login_required
def lesson_detail_instructor(request, course_id, module_id, lesson_id):
    """Detailed lesson view with progress tracking"""
    
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course)
    lesson = get_object_or_404(CourseLesson, id=lesson_id, module=module)
    
    # Check access permissions
    can_access = False
    is_enrolled = False
    
    if request.user.is_authenticated:
        if request.user.role == 'instructor' and course.instructor == request.user:
            can_access = True
        elif request.user.role == 'superadmin':
            can_access = True
        elif request.user.role == 'student':
            is_enrolled = course.enrollments.filter(
                student=request.user, is_active=True
            ).exists()
            if is_enrolled or lesson.is_free_preview:
                can_access = True
    
    if not can_access and not lesson.is_free_preview:
        messages.error(request, "You need to enroll in this course to access lessons.")
        return redirect('courses:course_detail', course_id=course.id)
    
    # 🔥 TRACK PROGRESS - THIS IS THE KEY PART
    lesson_progress = None
    if request.user.is_authenticated and request.user.role == 'student' and is_enrolled:
        lesson_progress, created = LessonProgress.objects.get_or_create(
            student=request.user,
            lesson=lesson
        )
        # Mark as started if first time
        if created or lesson_progress.status == 'not_started':
            lesson_progress.mark_as_started()
        
        # Update last accessed
        lesson_progress.last_accessed = timezone.now()
        lesson_progress.save(update_fields=['last_accessed'])
        
        # Also update enrollment last_accessed
        enrollment = course.enrollments.get(student=request.user, is_active=True)
        enrollment.last_accessed = timezone.now()
        enrollment.save(update_fields=['last_accessed'])
    
    # Get navigation lessons
    other_lessons = module.lessons.filter(is_active=True).exclude(id=lesson.id)
    prev_lesson = other_lessons.filter(order__lt=lesson.order).order_by('-order').first()
    next_lesson = other_lessons.filter(order__gt=lesson.order).order_by('order').first()
    
    context = {
        'course': course,
        'module': module,
        'lesson': lesson,
        'can_access': can_access,
        'is_enrolled': is_enrolled,
        'lesson_progress': lesson_progress,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'attachments': lesson.attachments.filter(is_active=True),
    }
    
    return render(request, 'courses/lesson_detail_instructor.html', context)




@login_required
def delete_lesson(request, course_id, module_id, lesson_id):
    """Delete lesson"""
    
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course)
    lesson = get_object_or_404(CourseLesson, id=lesson_id, module=module)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You can only delete lessons from your own courses!")
        return redirect('courses:manage_courses')
    
    if request.method == 'POST':
        lesson_title = lesson.title
        lesson.delete()
        messages.success(request, f'Lesson "{lesson_title}" deleted successfully!')
        return redirect('courses:module_lessons', course_id=course.id, module_id=module.id)
    
    context = {
        'course': course,
        'module': module,
        'lesson': lesson,
    }
    
    return render(request, 'courses/delete_lesson.html', context)




def lesson_content_type_help(request):
    """AJAX endpoint for content type help"""
    content_type = request.GET.get('type', '')
    
    help_text = {
        'text': 'Rich text content with formatting, images, and links.',
        'video': 'Upload video file or provide YouTube/Vimeo URL.',
        'pdf': 'Upload PDF documents for reading material.',
        'mixed': 'Combination of text, video, and PDF content.'
    }
    
    return JsonResponse({
        'help_text': help_text.get(content_type, 'Select a content type to see help.')
    })


# ==================== ENROLLMENT MANAGEMENT ====================

# courses/views.py - Add these to your existing views

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
import json
import logging

from userss.models import CustomUser
from courses.models import Course, Enrollment

logger = logging.getLogger(__name__)


@login_required
def manage_enrollments(request):
    """Manage course enrollments with enhanced filtering"""
    if request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    # Filter enrollments based on user role
    if request.user.role == 'superadmin':
        enrollments = Enrollment.objects.all()
        courses = Course.objects.filter(is_active=True)
    else:
        # Instructor can only see their own course enrollments
        enrollments = Enrollment.objects.filter(course__instructor=request.user)
        courses = Course.objects.filter(instructor=request.user, is_active=True)
    
    # Search and filter
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    course_filter = request.GET.get('course', '')
    
    if search_query:
        enrollments = enrollments.filter(
            Q(student__username__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__email__icontains=search_query) |
            Q(course__title__icontains=search_query) |
            Q(course__course_code__icontains=search_query)
        )
    
    if status_filter:
        enrollments = enrollments.filter(status=status_filter)
    
    if course_filter:
        enrollments = enrollments.filter(course_id=course_filter)
    
    # Sorting
    sort_by = request.GET.get('sort', '-enrolled_at')
    enrollments = enrollments.select_related('student', 'course').order_by(sort_by)
    
    # Calculate stats
    total_enrollments = enrollments.count()
    active_enrollments = enrollments.filter(status='enrolled').count()
    completed_enrollments = enrollments.filter(status='completed').count()
    pending_payments = enrollments.filter(payment_status='pending').count()
    
    # Pagination
    paginator = Paginator(enrollments, 20)
    page = request.GET.get('page')
    enrollments = paginator.get_page(page)
    
    context = {
        'enrollments': enrollments,
        'courses': courses,
        'search_query': search_query,
        'status_filter': status_filter,
        'course_filter': course_filter,
        'status_choices': Enrollment.STATUS_CHOICES,
        'total_enrollments': total_enrollments,
        'active_enrollments': active_enrollments,
        'completed_enrollments': completed_enrollments,
        'pending_payments': pending_payments,
    }
    
    return render(request, 'courses/manage_enrollments.html', context)


# ==================== API ENDPOINTS ====================

@require_http_methods(["GET"])
@login_required
def get_enrollment_api(request, enrollment_id):
    """GET enrollment data"""
    try:
        enrollment = Enrollment.objects.select_related('student', 'course').get(id=enrollment_id)
        
        # Check permission
        if request.user.role == 'instructor':
            if enrollment.course.instructor != request.user:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        
        return JsonResponse({
            'id': enrollment.id,
            'status': enrollment.status,
            'progress_percentage': float(enrollment.progress_percentage or 0),
            'grade': enrollment.grade or '',
            'payment_status': enrollment.payment_status,
            'student_name': enrollment.student.get_full_name(),
            'course_name': enrollment.course.title
        })
    except Enrollment.DoesNotExist:
        return JsonResponse({'error': 'Enrollment not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching enrollment {enrollment_id}: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt  # We'll handle CSRF in the view
@require_http_methods(["POST"])
@login_required
def update_enrollment_api(request, enrollment_id):
    """UPDATE enrollment"""
    try:
        enrollment = Enrollment.objects.select_related('course').get(id=enrollment_id)
        
        # Check permission
        if request.user.role == 'instructor':
            if enrollment.course.instructor != request.user:
                return JsonResponse({
                    'success': False,
                    'message': 'Permission denied'
                }, status=403)
        
        # Parse JSON data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        
        # Update fields
        if 'status' in data:
            valid_statuses = ['enrolled', 'completed', 'dropped', 'suspended']
            if data['status'] in valid_statuses:
                enrollment.status = data['status']
            else:
                return JsonResponse({
                    'success': False,
                    'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }, status=400)
        
        if 'progress_percentage' in data:
            try:
                progress = float(data['progress_percentage'])
                if 0 <= progress <= 100:
                    enrollment.progress_percentage = progress
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Progress must be between 0 and 100'
                    }, status=400)
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid progress value'
                }, status=400)
        
        if 'grade' in data:
            enrollment.grade = data['grade'] if data['grade'] else None
        
        if 'payment_status' in data:
            valid_payment_statuses = ['pending', 'completed', 'waived']
            if data['payment_status'] in valid_payment_statuses:
                enrollment.payment_status = data['payment_status']
            else:
                return JsonResponse({
                    'success': False,
                    'message': f'Invalid payment status. Must be one of: {", ".join(valid_payment_statuses)}'
                }, status=400)
        
        enrollment.save()
        
        logger.info(f"Enrollment {enrollment_id} updated by {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Enrollment updated successfully!'
        })
        
    except Enrollment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Enrollment not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error updating enrollment {enrollment_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST", "DELETE"])  # Support both methods
@login_required
def delete_enrollment_api(request, enrollment_id):
    """DELETE enrollment"""
    try:
        # Only superadmin can delete
        if request.user.role != 'superadmin':
            return JsonResponse({
                'success': False,
                'message': 'Only superadmin can delete enrollments'
            }, status=403)
        
        enrollment = Enrollment.objects.get(id=enrollment_id)
        course_name = enrollment.course.title
        student_name = enrollment.student.get_full_name()
        
        enrollment.delete()
        
        logger.info(f"Enrollment {enrollment_id} ({student_name} - {course_name}) deleted by {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Enrollment deleted successfully!'
        })
    except Enrollment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Enrollment not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error deleting enrollment {enrollment_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def bulk_update_status(request):
    """BULK UPDATE status"""
    try:
        data = json.loads(request.body)
        enrollment_ids = data.get('enrollment_ids', [])
        new_status = data.get('status')
        
        if not enrollment_ids:
            return JsonResponse({
                'success': False,
                'message': 'No enrollments selected'
            }, status=400)
        
        valid_statuses = ['enrolled', 'completed', 'dropped', 'suspended']
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }, status=400)
        
        # Filter by permission
        enrollments = Enrollment.objects.filter(id__in=enrollment_ids)
        if request.user.role == 'instructor':
            enrollments = enrollments.filter(course__instructor=request.user)
        
        updated = enrollments.update(status=new_status)
        
        logger.info(f"{updated} enrollments updated to {new_status} by {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'updated_count': updated,
            'message': f'{updated} enrollments updated to {new_status}'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in bulk update: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def bulk_delete_enrollments(request):
    """BULK DELETE enrollments"""
    try:
        # Only superadmin can bulk delete
        if request.user.role != 'superadmin':
            return JsonResponse({
                'success': False,
                'message': 'Only superadmin can delete enrollments'
            }, status=403)
        
        data = json.loads(request.body)
        enrollment_ids = data.get('enrollment_ids', [])
        
        if not enrollment_ids:
            return JsonResponse({
                'success': False,
                'message': 'No enrollments selected'
            }, status=400)
        
        deleted, _ = Enrollment.objects.filter(id__in=enrollment_ids).delete()
        
        logger.info(f"{deleted} enrollments deleted by {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted,
            'message': f'{deleted} enrollments deleted successfully'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in bulk delete: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def send_student_email(request):
    """Send email to student(s)"""
    try:
        data = json.loads(request.body)
        to_email = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        template = data.get('template')
        
        if not all([to_email, subject, body]):
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields'
            }, status=400)
        
        # Here you would implement actual email sending
        # For now, just log it
        logger.info(f"Email to {to_email}: {subject}")
        
        return JsonResponse({
            'success': True,
            'message': 'Email sent successfully!'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)
    
@login_required
def manual_enrollment(request):
    """Manually enroll a student with email notification"""
    if request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    # Get courses and students
    if request.user.role == 'superadmin':
        courses = Course.objects.filter(is_active=True).exclude(status='suspended')
        students = CustomUser.objects.filter(role='student', is_active=True).select_related('profile')
    else:
        courses = Course.objects.filter(
            instructor=request.user, 
            is_active=True
        ).exclude(status='suspended')
        students = CustomUser.objects.filter(role='student', is_active=True).select_related('profile')
    
    if request.method == 'POST':
        course_id = request.POST.get('course')
        student_id = request.POST.get('student')
        notes = request.POST.get('notes', '')
        send_welcome_email = request.POST.get('send_welcome_email') == 'on'
        send_instructor_notification = request.POST.get('send_instructor_notification') == 'on'
        
        try:
            course = Course.objects.get(id=course_id)
            student = CustomUser.objects.get(id=student_id, role='student')
            
            # Validate course status
            if course.status != 'published':
                status_messages = {
                    'draft': 'Cannot enroll students in draft courses. Please publish first.',
                    'archived': 'Cannot enroll students in archived courses. Please reactivate.',
                    'suspended': 'Cannot enroll students in suspended courses. Please unsuspend.',
                }
                messages.error(request, status_messages.get(course.status))
                return redirect('courses:manual_enrollment')
            
            # Check existing enrollment
            if Enrollment.objects.filter(student=student, course=course, is_active=True).exists():
                messages.error(request, f'Student "{student.get_full_name()}" is already enrolled in "{course.title}"')
                return redirect('courses:manual_enrollment')
            
            # Create enrollment
            enrollment = Enrollment.objects.create(
                student=student,
                course=course,
                status=request.POST.get('status', 'enrolled'),
                payment_status=request.POST.get('payment_status', 'pending'),
                amount_paid=float(request.POST.get('amount_paid', 0)),
                progress_percentage=float(request.POST.get('progress_percentage', 0)),
                is_active=True
            )
            
            # Update course enrollment count
            course.total_enrollments = course.get_enrolled_count()
            course.save(update_fields=['total_enrollments'])
            
            # SEND EMAILS - YEH MISSING THA!
            if send_welcome_email:
                email_sent = send_enrollment_welcome_email(enrollment, notes)
                if email_sent:
                    messages.success(request, 'Welcome email sent to student!')
                else:
                    messages.warning(request, 'Enrollment successful but email failed to send.')
            
            if send_instructor_notification and course.instructor != request.user:
                instructor_email_sent = send_instructor_notification_email(enrollment, request.user)
                if instructor_email_sent:
                    messages.success(request, 'Instructor notification sent!')
            
            messages.success(request, f'Student "{student.get_full_name()}" enrolled in "{course.title}" successfully!')
            return redirect('courses:manage_enrollments')
            
        except (Course.DoesNotExist, CustomUser.DoesNotExist):
            messages.error(request, 'Selected course or student not found.')
        except Exception as e:
            messages.error(request, f'Error creating enrollment: {str(e)}')
    
    context = {
        'students': students,
        'courses': courses,
    }
    
    return render(request, 'courses/manual_enrollment.html', context)

def send_enrollment_welcome_email(enrollment, notes=''):
    """Send welcome email to newly enrolled student"""
    try:
        student = enrollment.student
        course = enrollment.course
        
        # Try to get enrollment welcome template
        try:
            template_type = EmailTemplateType.objects.get(code='enrollment_welcome')
            email_template = EmailTemplate.objects.filter(
                template_type=template_type, 
                is_active=True
            ).first()
        except (EmailTemplateType.DoesNotExist, EmailTemplate.DoesNotExist):
            email_template = None
        
        if email_template:
            # Use dynamic template
            subject = email_template.subject.format(
                student_name=student.get_full_name() or student.username,
                course_name=course.title,
                instructor_name=course.instructor.get_full_name(),
                course_code=course.course_code,
                enrollment_date=enrollment.enrolled_at.strftime('%B %d, %Y')
            )
            
            message = email_template.email_body.format(
                student_name=student.get_full_name() or student.username,
                course_name=course.title,
                instructor_name=course.instructor.get_full_name(),
                course_code=course.course_code,
                enrollment_date=enrollment.enrolled_at.strftime('%B %d, %Y'),
                notes=notes
            )
        else:
            # Fallback to default template
            subject = f'Welcome to {course.title}!'
            message = f"""
Dear {student.get_full_name() or student.username},

Welcome to {course.title} ({course.course_code})!

We are excited to have you join this course. Your instructor {course.instructor.get_full_name()} will guide you through this learning journey.

Course Details:
- Course: {course.title}
- Instructor: {course.instructor.get_full_name()}
- Duration: {course.duration_weeks} weeks
- Start Date: {course.course_start_date.strftime('%B %d, %Y') if course.course_start_date else 'TBD'}

You can now access your course materials through the student portal.

{f"Special Notes: {notes}" if notes else ""}

Best regards,
{course.instructor.get_full_name()}
LMS Team
"""
        
        # Create and send email
        from_email = f"LMS System <{settings.EMAIL_HOST_USER}>"
        
        email_msg = EmailMessage(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[student.email],
        )
        
        email_msg.send(fail_silently=False)
        
        # Log email
        EmailLog.objects.create(
            recipient_email=student.email,
            recipient_user=student,
            template_used=email_template,
            template_type_used=email_template.template_type if email_template else None,
            subject=subject,
            email_body=message,
            is_sent_successfully=True,
            sent_by=None  # System generated
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {student.email}: {str(e)}")
        
        # Log failed email
        EmailLog.objects.create(
            recipient_email=student.email,
            recipient_user=student,
            subject=subject if 'subject' in locals() else 'Welcome Email',
            email_body=message if 'message' in locals() else '',
            is_sent_successfully=False,
            error_message=str(e),
            sent_by=None
        )
        
        return False


def send_instructor_notification_email(enrollment, enrolled_by):
    """Send notification to instructor about new enrollment"""
    try:
        instructor = enrollment.course.instructor
        student = enrollment.student
        course = enrollment.course
        
        subject = f'New Student Enrollment - {course.title}'
        message = f"""
Dear {instructor.get_full_name()},

A new student has been enrolled in your course:

Student Details:
- Name: {student.get_full_name() or student.username}
- Email: {student.email}
- Student ID: {student.profile.student_id if hasattr(student, 'profile') and student.profile.student_id else 'N/A'}

Course Details:
- Course: {course.title} ({course.course_code})
- Enrollment Date: {enrollment.enrolled_at.strftime('%B %d, %Y at %I:%M %p')}
- Enrolled by: {enrolled_by.get_full_name() or enrolled_by.username}

The student now has access to course materials and can begin their learning journey.

You can manage enrollments through the instructor panel.

Best regards,
LMS System
"""
        
        # Create and send email
        from_email = f"LMS System <{settings.EMAIL_HOST_USER}>"
        
        email_msg = EmailMessage(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[instructor.email],
        )
        
        email_msg.send(fail_silently=True)  # Don't fail if notification fails
        
        # Log email
        EmailLog.objects.create(
            recipient_email=instructor.email,
            recipient_user=instructor,
            subject=subject,
            email_body=message,
            is_sent_successfully=True,
            sent_by=enrolled_by
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send instructor notification to {instructor.email}: {str(e)}")
        return False


@csrf_exempt
@login_required
def send_student_email(request):
    """Send custom email to student via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    if request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    try:
        data = json.loads(request.body)
        to_email = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        template_code = data.get('template', '')
        
        if not to_email or not subject or not body:
            return JsonResponse({'success': False, 'message': 'Missing required fields'})
        
        # Get recipient user
        try:
            recipient = CustomUser.objects.get(email=to_email)
        except CustomUser.DoesNotExist:
            recipient = None
        
        # Replace template variables if recipient exists
        if recipient:
            # Get enrollment info for context
            enrollment = None
            if request.user.role == 'instructor':
                enrollment = Enrollment.objects.filter(
                    student=recipient,
                    course__instructor=request.user
                ).first()
            
            subject = subject.replace('{student_name}', recipient.get_full_name() or recipient.username)
            body = body.replace('{student_name}', recipient.get_full_name() or recipient.username)
            body = body.replace('{instructor_name}', request.user.get_full_name() or request.user.username)
            
            if enrollment:
                subject = subject.replace('{course_name}', enrollment.course.title)
                body = body.replace('{course_name}', enrollment.course.title)
                body = body.replace('{enrollment_date}', enrollment.enrolled_at.strftime('%B %d, %Y'))
        
        # Create and send email
        from_email = f"LMS System <{settings.EMAIL_HOST_USER}>"
        
        email_msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[to_email],
        )
        
        email_msg.send(fail_silently=False)
        
        # Log email
        EmailLog.objects.create(
            recipient_email=to_email,
            recipient_user=recipient,
            subject=subject,
            email_body=body,
            is_sent_successfully=True,
            sent_by=request.user
        )
        
        return JsonResponse({'success': True, 'message': 'Email sent successfully'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'})
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        
        # Log failed email
        if 'to_email' in locals():
            EmailLog.objects.create(
                recipient_email=to_email,
                recipient_user=recipient if 'recipient' in locals() else None,
                subject=subject if 'subject' in locals() else 'Custom Email',
                email_body=body if 'body' in locals() else '',
                is_sent_successfully=False,
                error_message=str(e),
                sent_by=request.user
            )
        
        return JsonResponse({'success': False, 'message': 'Failed to send email'})


@csrf_exempt
@login_required
def bulk_update_status(request):
    """Bulk update enrollment status"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    if request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    try:
        data = json.loads(request.body)
        enrollment_ids = data.get('enrollment_ids', [])
        new_status = data.get('status', '')
        
        if not enrollment_ids or not new_status:
            return JsonResponse({'success': False, 'message': 'Missing required data'})
        
        # Validate status
        valid_statuses = [choice[0] for choice in Enrollment.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'message': 'Invalid status'})
        
        # Filter enrollments based on user role
        if request.user.role == 'superadmin':
            enrollments = Enrollment.objects.filter(id__in=enrollment_ids)
        else:
            enrollments = Enrollment.objects.filter(
                id__in=enrollment_ids,
                course__instructor=request.user
            )
        
        # Update enrollments
        updated_count = enrollments.update(status=new_status)
        
        return JsonResponse({
            'success': True, 
            'message': f'Updated {updated_count} enrollments to {new_status}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'})
    except Exception as e:
        logger.error(f"Failed to bulk update status: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Failed to update enrollments'})


@csrf_exempt
@login_required
def bulk_delete_enrollments(request):
    """Bulk delete enrollments (superadmin only)"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    if request.user.role != 'superadmin':
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    try:
        data = json.loads(request.body)
        enrollment_ids = data.get('enrollment_ids', [])
        
        if not enrollment_ids:
            return JsonResponse({'success': False, 'message': 'No enrollments selected'})
        
        # Delete enrollments
        deleted_count, _ = Enrollment.objects.filter(id__in=enrollment_ids).delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'Removed {deleted_count} enrollments'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'})
    except Exception as e:
        logger.error(f"Failed to bulk delete enrollments: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Failed to remove enrollments'})


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@require_http_methods(["POST"])
def update_enrollment_api(request, enrollment_id):
    try:
        enrollment = Enrollment.objects.get(id=enrollment_id)
        
        # JSON data parse karo
        data = json.loads(request.body)
        
        # Status update karo
        if 'status' in data:
            enrollment.status = data['status']
        
        # Progress update karo
        if 'progress_percentage' in data:
            enrollment.progress_percentage = data['progress_percentage']
        
        # Grade update karo
        if 'grade' in data:
            enrollment.grade = data['grade'] if data['grade'] else None
        
        # Payment status update karo
        if 'payment_status' in data:
            enrollment.payment_status = data['payment_status']
        
        enrollment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Enrollment updated successfully!'
        })
        
    except Enrollment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Enrollment not found'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@csrf_exempt
@login_required
def delete_enrollment_api(request, enrollment_id):
    """Delete single enrollment via API"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    if request.user.role != 'superadmin':
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    try:
        enrollment = get_object_or_404(Enrollment, id=enrollment_id)
        student_name = enrollment.student.get_full_name()
        course_title = enrollment.course.title
        
        enrollment.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'Removed enrollment: {student_name} from {course_title}'
        })
        
    except Exception as e:
        logger.error(f"Failed to delete enrollment: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Failed to remove enrollment'})


@login_required
def get_enrollment_api(request, enrollment_id):
    """Get enrollment data via API"""
    if request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    try:
        # Get enrollment
        if request.user.role == 'superadmin':
            enrollment = get_object_or_404(Enrollment, id=enrollment_id)
        else:
            enrollment = get_object_or_404(
                Enrollment, 
                id=enrollment_id,
                course__instructor=request.user
            )
        
        data = {
            'id': enrollment.id,
            'status': enrollment.status,
            'progress_percentage': float(enrollment.progress_percentage),
            'grade': enrollment.grade or '',
            'payment_status': enrollment.payment_status,
            'amount_paid': float(enrollment.amount_paid),
            'student_name': enrollment.student.get_full_name(),
            'course_title': enrollment.course.title
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Failed to get enrollment data: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Failed to load enrollment data'})




@login_required
def update_enrollment_status(request, enrollment_id):
    """Update enrollment status"""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    
    # Check permissions
    if request.user.role == 'instructor' and enrollment.course.instructor != request.user:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    elif request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Enrollment.STATUS_CHOICES):
            enrollment.status = new_status
            if new_status == 'completed':
                enrollment.completed_at = timezone.now()
            enrollment.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Enrollment status updated to {new_status}',
                'new_status': new_status
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


# ==================== AJAX ENDPOINTS ====================

@login_required
def get_course_stats(request, course_id):
    """Get course statistics (AJAX)"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        return JsonResponse({'error': 'Permission denied'})
    elif request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({'error': 'Permission denied'})
    
    stats = {
        'total_modules': course.modules.count(),
        'total_lessons': CourseLesson.objects.filter(module__course=course).count(),
        'total_enrollments': course.get_enrolled_count(),
        'available_seats': course.get_available_seats(),
        'completion_rate': 0,  # Will be calculated when we add progress tracking
        'average_rating': float(course.average_rating),
    }
    
    return JsonResponse(stats)


@login_required
def course_analytics(request):
    """Course analytics dashboard"""
    if request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    # Filter courses based on user role
    if request.user.role == 'superadmin':
        courses = Course.objects.filter(is_active=True)
        enrollments = Enrollment.objects.filter(is_active=True)
    else:
        courses = Course.objects.filter(instructor=request.user, is_active=True)
        enrollments = Enrollment.objects.filter(course__instructor=request.user, is_active=True)
    
    # Get analytics data
    total_courses = courses.count()
    total_enrollments = enrollments.count()
    
    # Course by category
    courses_by_category = courses.values('category__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Enrollments by month
    from django.db.models.functions import TruncMonth
    enrollments_by_month = enrollments.annotate(
        month=TruncMonth('enrolled_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Top performing courses
    top_courses = courses.annotate(
        enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True))
    ).order_by('-enrollment_count')[:5]
    
    # Revenue by course (if not free)
    revenue_by_course = enrollments.exclude(
        course__is_free=True
    ).values('course__title').annotate(
        revenue=Sum('amount_paid')
    ).order_by('-revenue')[:5]
    
    context = {
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'courses_by_category': courses_by_category,
        'enrollments_by_month': enrollments_by_month,
        'top_courses': top_courses,
        'revenue_by_course': revenue_by_course,
    }
    
    return render(request, 'courses/analytics.html', context)


# ==================== STUDENT ENROLLMENT VIEWS ====================

def course_catalog(request):
    """Public course catalog for students"""
    courses = Course.objects.filter(
        is_active=True, 
        status='published'
    ).select_related('category', 'instructor')
    
    # Search and filter
    search_form = CourseSearchForm(request.GET or None)
    
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        category = search_form.cleaned_data.get('category')
        difficulty = search_form.cleaned_data.get('difficulty')
        course_type = search_form.cleaned_data.get('course_type')
        price_range = search_form.cleaned_data.get('price_range')
        sort_by = search_form.cleaned_data.get('sort_by') or '-created_at'
        
        # Apply filters (same logic as manage_courses)
        if search_query:
            courses = courses.filter(
                Q(title__icontains=search_query) |
                Q(course_code__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        if category:
            courses = courses.filter(category=category)
        
        if difficulty:
            courses = courses.filter(difficulty_level=difficulty)
        
        if course_type:
            courses = courses.filter(course_type=course_type)
        
        if price_range:
            if price_range == 'free':
                courses = courses.filter(is_free=True)
            elif price_range == '0-50':
                courses = courses.filter(price__lte=50, is_free=False)
            elif price_range == '50-100':
                courses = courses.filter(price__gt=50, price__lte=100)
            elif price_range == '100-200':
                courses = courses.filter(price__gt=100, price__lte=200)
            elif price_range == '200+':
                courses = courses.filter(price__gt=200)
        
        courses = courses.order_by(sort_by)
    else:
        courses = courses.order_by('-created_at')
    
    # Add enrollment count annotation
    courses = courses.annotate(
        enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True))
    )
    
    # Pagination
    paginator = Paginator(courses, 12)
    page = request.GET.get('page')
    courses = paginator.get_page(page)
    
    # Featured courses
    featured_courses = Course.objects.filter(
        is_active=True, 
        status='published', 
        is_featured=True
    ).annotate(
        enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True))
    )[:4]
    
    # Categories for sidebar
    categories = CourseCategory.objects.filter(is_active=True).annotate(
        course_count=Count('courses', filter=Q(
            courses__is_active=True, 
            courses__status='published'
        ))
    )
    
    context = {
        'courses': courses,
        'featured_courses': featured_courses,
        'categories': categories,
        'search_form': search_form,
    }
    
    return render(request, 'courses/catalog.html', context)


def course_preview(request, slug):
    """Course preview page for students (before enrollment)"""
    course = get_object_or_404(Course, slug=slug, is_active=True, status='published')
    
    # Check if user is already enrolled
    user_enrollment = None
    can_enroll = True
    enroll_message = ""
    
    if request.user.is_authenticated and request.user.role == 'student':
        user_enrollment = course.enrollments.filter(
            student=request.user, 
            is_active=True
        ).first()
        
        if not user_enrollment:
            can_enroll, enroll_message = course.can_user_enroll(request.user)
    
    # Get course modules (only titles for preview)
    modules = course.modules.filter(is_active=True).prefetch_related(
        'lessons'
    )
    
    # Get free preview lessons
    preview_lessons = CourseLesson.objects.filter(
        module__course=course,
        is_free_preview=True,
        is_active=True
    )
    
    # Get course reviews
    reviews = course.reviews.filter(is_approved=True).order_by('-created_at')
    
    # Calculate review statistics
    review_stats = reviews.aggregate(
        avg_rating=Avg('rating'),
        total_reviews=Count('id')
    )
    
    # ⭐ FIXED: Rating distribution as list
    rating_distribution = []
    for i in range(5, 0, -1):  # 5 to 1
        count = reviews.filter(rating=i).count()
        percentage = (count / review_stats['total_reviews'] * 100) if review_stats['total_reviews'] > 0 else 0
        rating_distribution.append({
            'rating': i,
            'count': count,
            'percentage': percentage
        })
    
    # Get FAQs
    faqs = course.faqs.filter(is_active=True)
    
    # Related courses
    related_courses = Course.objects.filter(
        category=course.category,
        is_active=True,
        status='published'
    ).exclude(id=course.id).annotate(
        enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True))
    )[:4]
    
    context = {
        'course': course,
        'user_enrollment': user_enrollment,
        'can_enroll': can_enroll,
        'enroll_message': enroll_message,
        'modules': modules,
        'preview_lessons': preview_lessons,
        'reviews': reviews[:10],
        'review_stats': review_stats,
        'rating_distribution': rating_distribution,  # ⭐ Now it's a list
        'faqs': faqs,
        'related_courses': related_courses,
    }
    
    return render(request, 'courses/course_preview.html', context)

@login_required
def enroll_course(request, course_id):
    """Enroll student in a course"""
    if request.user.role != 'student':
        messages.error(request, "Only students can enroll in courses!")
        return redirect('course_catalog')
    
    course = get_object_or_404(Course, id=course_id, is_active=True, status='published')
    
    # Check if can enroll
    can_enroll, message = course.can_user_enroll(request.user)
    
    if not can_enroll:
        messages.error(request, message)
        return redirect('course_preview', slug=course.slug)
    
    if request.method == 'POST':
        try:
            # Create enrollment
            enrollment = Enrollment.objects.create(
                student=request.user,
                course=course,
                amount_paid=course.get_effective_price(),
                payment_status='completed' if course.is_free else 'pending'
            )
            
            # Update course enrollment count
            course.total_enrollments = course.get_enrolled_count()
            course.save(update_fields=['total_enrollments'])
            
            messages.success(request, f'Successfully enrolled in "{course.title}"!')
            
            # Redirect based on payment status
            if course.is_free:
                return redirect('my_courses')
            else:
                # In a real app, redirect to payment gateway
                messages.info(request, 'Please complete payment to access course content.')
                return redirect('my_courses')
                
        except Exception as e:
            messages.error(request, f'Enrollment failed: {str(e)}')
            return redirect('course_preview', slug=course.slug)
    
    context = {
        'course': course,
    }
    
    return render(request, 'courses/enroll_course.html', context)


@login_required
def my_courses(request):
    """Student's enrolled courses"""
    if request.user.role != 'student':
        return redirect('user_login')
    
    enrollments = request.user.enrollments.filter(
        is_active=True
    ).select_related('course').order_by('-enrolled_at')
    
    # Categorize enrollments
    ongoing_courses = enrollments.filter(status='enrolled')
    completed_courses = enrollments.filter(status='completed')
    
    context = {
        'ongoing_courses': ongoing_courses,
        'completed_courses': completed_courses,
        'total_enrollments': enrollments.count(),
    }
    
    return render(request, 'courses/my_courses.html', context)


@login_required
def course_content(request, course_id):
    """Access course content (for enrolled students)"""
    if request.user.role != 'student':
        messages.error(request, "Only students can access course content!")
        return redirect('course_catalog')
    
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    # Check if student is enrolled
    enrollment = get_object_or_404(
        Enrollment, 
        student=request.user, 
        course=course, 
        is_active=True
    )
    
    # Get course content
    modules = course.modules.filter(is_active=True).prefetch_related(
        'lessons'
    )
    
    # Update last accessed
    enrollment.last_accessed = timezone.now()
    enrollment.save(update_fields=['last_accessed'])
    
    context = {
        'course': course,
        'enrollment': enrollment,
        'modules': modules,
    }
    
    return render(request, 'courses/course_content.html', context)


# batch management
# courses/views.py - Add these SIMPLE batch views

@login_required
def batch_list(request, course_id):
    """List all batches for a course"""
    if request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "You can only manage your own course batches!")
        return redirect('courses:manage_courses')
    
    batches = course.batches.all().order_by('-created_at')
    
    context = {
        'course': course,
        'batches': batches,
    }
    
    return render(request, 'courses/batch_list.html', context)



@login_required
def create_batch(request, course_id):
    """Create new batch"""
    if request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('courses:manage_courses')
    
    if request.method == 'POST':
        print("POST request received")
        print("POST data:", request.POST)
        
        form = BatchForm(request.POST, course=course)
        
        # Handle content_type manually if it's not in the form
        content_type = request.POST.get('content_type', 'copy')
        
        print(f"Form is valid: {form.is_valid()}")
        if not form.is_valid():
            print("Form errors:", form.errors)
            
        if form.is_valid():
            batch = form.save(commit=False)
            batch.course = course
            batch.created_by = request.user
            
            # Set content type from POST data
            batch.content_type = content_type
            
            # Set default status if not provided
            if not hasattr(batch, 'status') or not batch.status:
                batch.status = 'active'
            
            try:
                batch.save()
                messages.success(request, f'Batch "{batch.name}" created successfully!')
                
                # Handle content copying if selected
                if content_type == 'copy':
                    # Copy course content to batch here
                    # This depends on your content copying logic
                    pass
                    
                return redirect('courses:batch_list', course_id=course.id)
            except Exception as e:
                print(f"Error saving batch: {e}")
                messages.error(request, f"Error creating batch: {str(e)}")
        else:
            messages.error(request, "Please correct the form errors.")
    else:
        # Pre-fill instructor field with current user for new batches
        initial_data = {}
        if request.user.role == 'instructor':
            initial_data['instructor'] = request.user.id
            
        form = BatchForm(course=course, initial=initial_data)
    
    context = {
        'form': form,
        'course': course,
        'title': f'Create Batch for {course.title}',
    }
    
    return render(request, 'courses/batch_form.html', context)



@login_required
def batch_detail(request, course_id, batch_id):
    """Batch detail with modules and lessons"""
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('courses:manage_courses')
    elif request.user.role not in ['superadmin', 'instructor']:
        return redirect('user_login')
    
    modules = batch.batch_modules.all().prefetch_related('lessons')
    enrollments = batch.enrollments.all().select_related('student')
    
    # Add enrollment form support like batch_enrollments view
    enrollment_allowed = course.status == 'published'
    status_message = {
        'draft': 'Students cannot enroll in draft courses. Please publish the course first.',
        'archived': 'Students cannot enroll in archived courses. Please reactivate the course.',
        'suspended': 'Students cannot enroll in suspended courses. Please unsuspend the course.',
        'published': 'Course is ready for enrollment.'
    }
    
    # Handle POST request for enrollment
    if request.method == 'POST':
        if not enrollment_allowed:
            messages.error(request, status_message.get(course.status))
            return redirect('courses:batch_detail', course_id=course.id, batch_id=batch.id)
        
        form = BatchEnrollForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data['student']
            
            # Check if already enrolled
            if batch.enrollments.filter(student=student, is_active=True).exists():
                messages.error(request, f"{student.username} is already enrolled!")
            else:
                BatchEnrollment.objects.create(
                    student=student,
                    batch=batch
                )
                messages.success(request, f"{student.username} enrolled successfully!")
            
            return redirect('courses:batch_detail', course_id=course.id, batch_id=batch.id)
    else:
        form = BatchEnrollForm()
    
    context = {
        'course': course,
        'batch': batch,
        'modules': modules,
        'enrollments': enrollments,
        'form': form,  # Add this
        'enrollment_allowed': enrollment_allowed,  # Add this
        'status_message': status_message.get(course.status),  # Add this
        'course_status': course.status,  # Add this
    }
    
    return render(request, 'courses/batch_detail.html', context)

@login_required
def edit_batch(request, course_id, batch_id):
    """Edit batch"""
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    
    # Check permissions
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('courses:manage_courses')
    
    if request.method == 'POST':
        form = BatchForm(request.POST, instance=batch, course=course)
        if form.is_valid():
            batch = form.save()
            messages.success(request, f'Batch "{batch.name}" updated!')
            return redirect('courses:batch_detail', course_id=course.id, batch_id=batch.id)
    else:
        form = BatchForm(instance=batch, course=course)
    
    context = {
        'form': form,
        'course': course,
        'batch': batch,
        'title': f'Edit Batch: {batch.name}',
    }
    
    return render(request, 'courses/batch_form.html', context)


@login_required
def create_batch_module(request, course_id, batch_id):
    """Create module for batch with choice to add to course"""
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    
    if request.method == 'POST':
        form = SimpleBatchModuleForm(request.POST)
        add_to_course = request.POST.get('add_to_course')  # New choice field
        
        if form.is_valid():
            module = form.save(commit=False)
            module.batch = batch
            
            # Auto-set order
            last_module = batch.batch_modules.order_by('-order').first()
            module.order = (last_module.order + 1) if last_module else 1
            
            module.save()
            
            # User ka choice: Course mein bhi add karna hai ya nahi
            if add_to_course:
                # Course mein bhi add kar do
                course_module = CourseModule.objects.create(
                    course=course,
                    title=module.title,
                    description=module.description,
                    order=course.modules.count() + 1,
                    is_active=True
                )
                messages.success(request, f'Module "{module.title}" added to both batch and main course!')
            else:
                messages.success(request, f'Module "{module.title}" added to batch only!')
            
            return redirect('courses:batch_detail', course_id=course.id, batch_id=batch.id)
    else:
        form = SimpleBatchModuleForm()
    
    context = {
        'form': form,
        'course': course,
        'batch': batch,
        'title': f'Create Module for {batch.name}',
    }
    
    return render(request, 'courses/batch_module_form.html', context)

@login_required
def create_batch_lesson(request, course_id, batch_id, module_id):
    """Create lesson for batch module"""
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    module = get_object_or_404(BatchModule, id=module_id, batch=batch)
    
    if request.method == 'POST':
        form = SimpleBatchLessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.batch_module = module
            
            # Auto-set order
            last_lesson = module.lessons.order_by('-order').first()
            lesson.order = (last_lesson.order + 1) if last_lesson else 1
            
            lesson.save()
            messages.success(request, f'Lesson "{lesson.title}" created!')
            return redirect('courses:batch_detail', course_id=course.id, batch_id=batch.id)
    else:
        form = SimpleBatchLessonForm()
    
    context = {
        'form': form,
        'course': course,
        'batch': batch,
        'module': module,
        'title': f'Create Lesson for {module.title}',
    }
    
    return render(request, 'courses/batch_lesson_form.html', context)



from .forms import BulkBatchEnrollForm

@login_required
def batch_enrollments(request, course_id, batch_id):
    """Manage batch enrollments with status restrictions"""
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    
    enrollments = batch.enrollments.all().select_related('student')
    
    # Check if enrollment is allowed based on course status
    enrollment_allowed = course.status == 'published'
    status_message = {
        'draft': 'Students cannot enroll in draft courses. Please publish the course first.',
        'archived': 'Students cannot enroll in archived courses. Please reactivate the course.',
        'suspended': 'Students cannot enroll in suspended courses. Please unsuspend the course.',
        'published': 'Course is ready for enrollment.'
    }
    
    if request.method == 'POST':
        if not enrollment_allowed:
            messages.error(request, status_message.get(course.status))
            return redirect('courses:batch_enrollments', course_id=course.id, batch_id=batch.id)
        
        # Check which form was submitted
        if 'single_enroll' in request.POST:
            form = BatchEnrollForm(request.POST)
            if form.is_valid():
                enrollment = form.save(commit=False)
                student = enrollment.student
                
                # Check if already enrolled
                if batch.enrollments.filter(student=student, is_active=True).exists():
                    messages.error(request, f"{student.get_full_name() or student.username} is already enrolled!")
                else:
                    enrollment.batch = batch
                    enrollment.save()
                    messages.success(request, f"{student.get_full_name() or student.username} enrolled successfully!")
                
                return redirect('courses:batch_enrollments', course_id=course.id, batch_id=batch.id)
        
        elif 'bulk_enroll' in request.POST:
            bulk_form = BulkBatchEnrollForm(request.POST)
            if bulk_form.is_valid():
                students = bulk_form.cleaned_data['students']
                
                enrolled_count = 0
                already_enrolled = []
                
                for student in students:
                    if not batch.enrollments.filter(student=student, is_active=True).exists():
                        BatchEnrollment.objects.create(
                            student=student,
                            batch=batch
                        )
                        enrolled_count += 1
                    else:
                        already_enrolled.append(student.get_full_name() or student.username)
                
                if enrolled_count > 0:
                    messages.success(request, f"{enrolled_count} students enrolled successfully!")
                
                if already_enrolled:
                    messages.warning(request, f"Already enrolled: {', '.join(already_enrolled)}")
                
                return redirect('courses:batch_enrollments', course_id=course.id, batch_id=batch.id)
    else:
        form = BatchEnrollForm()
        bulk_form = BulkBatchEnrollForm()
    
    context = {
        'course': course,
        'batch': batch,
        'enrollments': enrollments,
        'form': form,
        'bulk_form': bulk_form,
        'enrollment_allowed': enrollment_allowed,
        'status_message': status_message.get(course.status),
        'course_status': course.status,
    }
    
    return render(request, 'courses/batch_enrollments.html', context)


from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required
@require_POST
def bulk_remove_batch_enrollments(request, course_id, batch_id):
    """Bulk remove students from batch"""
    try:
        import json
        data = json.loads(request.body)
        enrollment_ids = data.get('enrollment_ids', [])
        
        if not enrollment_ids:
            return JsonResponse({
                'success': False,
                'message': 'No students selected'
            })
        
        # Get the batch to verify access
        batch = get_object_or_404(Batch, id=batch_id, course_id=course_id)
        
        # Delete the enrollments
        deleted_count = BatchEnrollment.objects.filter(
            id__in=enrollment_ids,
            batch=batch
        ).delete()[0]
        
        return JsonResponse({
            'success': True,
            'message': f'{deleted_count} students removed successfully!',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)



@login_required  
def student_batch_list(request):
    """Student view of their batches"""
    if request.user.role != 'student':
        return redirect('user_login')
    
    enrollments = request.user.batch_enrollments.filter(
        is_active=True
    ).select_related('batch', 'batch__course').order_by('-enrolled_at')
    
    context = {
        'enrollments': enrollments,
    }
    
    return render(request, 'courses/student_batches.html', context)



@login_required
def student_batch_content(request, batch_id):
    """Student access to batch content"""
    if request.user.role != 'student':
        return redirect('user_login')
    
    # Check if student is enrolled
    enrollment = get_object_or_404(
        BatchEnrollment,
        student=request.user,
        batch_id=batch_id,
        is_active=True
    )
    
    batch = enrollment.batch
    modules = batch.batch_modules.filter(is_active=True).prefetch_related('lessons')
    
    context = {
        'batch': batch,
        'enrollment': enrollment,
        'modules': modules,
    }
    
    return render(request, 'courses/student_batch_content.html', context)




# courses/views.py में add करें:

@login_required
def course_specific_analytics(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Permission check
    if not request.user.is_superuser:
        if request.user.role == 'instructor' and course.instructor != request.user:
            return redirect('instructor_dashboard')
        elif request.user.role == 'student':
            return redirect('student_dashboard')
    
    # Get course statistics
    total_enrollments = course.enrollments.count()
    active_enrollments = course.enrollments.filter(status='enrolled').count()
    completed_enrollments = course.enrollments.filter(status='completed').count()
    
    context = {
        'course': course,
        'total_enrollments': total_enrollments,
        'active_enrollments': active_enrollments,
        'completed_enrollments': completed_enrollments,
        'completion_rate': (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0,
        'sidebar_courses': get_sidebar_courses(request.user),
    }
    return render(request, 'courses/course_analytics.html', context)



@login_required
def course_students(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Permission check
    if not request.user.is_superuser:
        if request.user.role == 'instructor' and course.instructor != request.user:
            return redirect('instructor_dashboard')
    
    enrollments = course.enrollments.all().select_related('student')
    
    context = {
        'course': course,
        'enrollments': enrollments,
        'sidebar_courses': get_sidebar_courses(request.user),
    }
    return render(request, 'courses/course_students.html', context)



@login_required
def course_enrollments(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Admin only view
    if not request.user.is_superuser:
        return redirect('instructor_dashboard')
    
    enrollments = course.enrollments.all().select_related('student')
    
    context = {
        'course': course,
        'enrollments': enrollments,
        'sidebar_courses': get_sidebar_courses(request.user),
    }
    return render(request, 'courses/course_enrollments.html', context)



# Helper function
def get_sidebar_courses(user):
    if user.is_superuser or getattr(user, 'role', None) == 'superadmin':
        return Course.objects.filter(is_active=True).order_by('course_code')[:15]
    elif getattr(user, 'role', None) == 'instructor':
        return Course.objects.filter(instructor=user, is_active=True).order_by('course_code')[:15]
    return []






# instructor panel batch management
# instructor panel batch management
# instructor panel batch management
# instructor panel batch management
# instructor panel batch management


# instructor/views.py - Instructor Batch Management Views

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from courses.models import Course, Batch, BatchModule, BatchLesson, BatchEnrollment, User
from courses.forms import BatchForm, SimpleBatchModuleForm, SimpleBatchLessonForm, BatchEnrollForm


@login_required
def instructor_batch_list(request, course_id):
    """Instructor: List all batches for their course"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    course = get_object_or_404(Course, id=course_id)
    
    # Check if instructor owns this course
    if course.instructor != request.user:
        messages.error(request, "You can only manage your own course batches!")
        return redirect('courses:manage_courses')  # Fixed namespace
    
    # Get batches with related data for efficiency
    batches = course.batches.all().select_related('course', 'instructor').prefetch_related(
        'batch_modules', 'enrollments'
    ).order_by('-created_at')
    
    # Calculate stats for the course header
    course_stats = {
        'total_batches': batches.count(),
        'active_batches': batches.filter(status='active').count(),
        'total_students': course.get_enrolled_count(),
        'total_modules': course.modules.count(),
    }
    
    # Add batch-specific enrollment data for each batch
    for batch in batches:
        # Pre-calculate to avoid multiple DB hits in template
        batch.enrolled_count = batch.get_enrolled_count()
        batch.available_seats = batch.get_available_seats()
        batch.modules_count = batch.batch_modules.count()
        
        # Get recent enrollments for this batch (for additional info if needed)
        batch.recent_enrollments = batch.enrollments.filter(
            is_active=True
        ).select_related('student').order_by('-enrolled_at')[:3]
    
    context = {
        'course': course,
        'batches': batches,
        'course_stats': course_stats,
        'page_title': f'Batches - {course.title}',
    }
    
    return render(request, 'batch_management_instructor/batch_list.html', context)
# Add this view to your instructor views.py file


@login_required
def instructor_view_all_batches(request):
    """Instructor: View all batches across all courses"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    # Get all batches for instructor's courses
    batches = Batch.objects.filter(
        instructor=request.user  # Course ke instructor ke bajaye batch ka instructor
    ).select_related('course').prefetch_related('enrollments').order_by('-created_at')
    
    
    # Filter by status if requested
    status_filter = request.GET.get('status', '')
    if status_filter:
        batches = batches.filter(status=status_filter)
    
    # Filter by course if requested
    course_filter = request.GET.get('course', '')
    if course_filter:
        batches = batches.filter(course_id=course_filter)
    
    # Get instructor's courses for filter dropdown
    courses = Course.objects.filter(instructor=request.user, is_active=True)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(batches, 12)  # 12 batches per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Stats for summary
    stats = {
        'total_batches': batches.count(),
        'active_batches': batches.filter(status='active').count(),
        'draft_batches': batches.filter(status='draft').count(),
        'completed_batches': batches.filter(status='completed').count(),
        'total_students': BatchEnrollment.objects.filter(
            batch__course__instructor=request.user,
            is_active=True
        ).count(),
    }
    
    context = {
        'page_obj': page_obj,
        'batches': page_obj,
        'courses': courses,
        'stats': stats,
        'status_filter': status_filter,
        'course_filter': course_filter,
        'page_title': 'All Batches',
    }
    
    return render(request, 'batch_management_instructor/all_batches.html', context)


# Replace your instructor_create_batch view with this COMPLETE fix:

# Debug your instructor_create_batch view - Add debugging:

# Fixed view - Instructor field auto-set karo:

# Replace your instructor_create_batch view with this:

# Replace your views with these COMPLETE fixed versions:

@login_required
def instructor_create_batch(request, course_id):
    """Instructor: Create new batch for their course"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('courses:manage_courses')  # FIXED
    
    if request.method == 'POST':
        form = BatchForm(request.POST, course=course)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.course = course
            batch.created_by = request.user
            batch.instructor = request.user
            batch.save()
            
            messages.success(request, f'Batch "{batch.name}" created successfully!')
            return redirect('courses:batch_list', course_id=course.id)  # FIXED
    else:
        form = BatchForm(course=course)
    
    context = {
        'form': form,
        'course': course,
        'courses': Course.objects.filter(instructor=request.user, is_active=True),
        'page_title': f'Create Batch - {course.title}',
        'submit_url': reverse('courses:create_batch', args=[course.id]),  # FIXED
    }
    
    return render(request, 'batch_management_instructor/batch_form.html', context)


@login_required
def instructor_batch_detail(request, course_id, batch_id):
    """Instructor: Batch detail with modules and lessons"""
    if request.user.role != 'instructor':
        return redirect('user_login')
        
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    
    # Check permissions
    if course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('courses:manage_courses')
    
    modules = batch.batch_modules.all().prefetch_related('lessons')
    
    # SAME QUERY as instructor_batch_enrollments
    enrollments = batch.enrollments.all().select_related('student').order_by('-enrolled_at')
    
    # Stats for dashboard
    stats = {
        'total_students': enrollments.count(),
        'active_students': enrollments.filter(is_active=True).count(),
        'inactive_students': enrollments.filter(is_active=False).count(),
        'available_seats': batch.get_available_seats(),
        'total_modules': modules.count(),
        'total_lessons': sum(module.lessons.count() for module in modules),
    }
    
    context = {
        'course': course,
        'batch': batch,
        'modules': modules,
        'enrollments': enrollments,
        'stats': stats,
        'page_title': f'{batch.name} - Overview',
    }
    
    return render(request, 'batch_management_instructor/batch_detail.html', context)


# views.py - DEBUGGED VERSION
from .forms import BatchEditForm  # Add this import

@login_required
def instructor_edit_batch(request, course_id, batch_id):
    """Instructor: Edit their batch"""
    if request.user.role != 'instructor':
        return redirect('user_login')
        
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    
    # Check permissions
    if course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('courses:manage_courses')
    
    if request.method == 'POST':
        # DEBUG: Print form data
        print("POST data:", request.POST)
        
        # Use BatchEditForm instead of BatchForm
        form = BatchEditForm(request.POST, instance=batch)
        
        # DEBUG: Print form errors
        print("Form is valid:", form.is_valid())
        if not form.is_valid():
            print("Form errors:", form.errors)
        
        if form.is_valid():
            # Store old status for comparison
            old_status = batch.status
            
            # Save the form (this only updates the editable fields)
            updated_batch = form.save()
            
            # DEBUG: Check if status actually changed
            print(f"Old status: {old_status}")
            print(f"New status: {updated_batch.status}")
            
            # Add specific message based on status change
            if old_status != updated_batch.status:
                status_messages = {
                    'draft': 'Content is now hidden from students.',
                    'active': 'Content is now visible to students.',
                    'completed': 'Batch marked as completed.'
                }
                status_msg = status_messages.get(updated_batch.status, '')
                messages.success(request, f'Batch "{updated_batch.name}" updated successfully! {status_msg}')
            else:
                messages.success(request, f'Batch "{updated_batch.name}" updated successfully!')
            
            return redirect('courses:batch_detail', course_id=course.id, batch_id=updated_batch.id)
        else:
            # DEBUG: Show form errors in messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # Use BatchEditForm for GET request too
        form = BatchEditForm(instance=batch)
    
    # DEBUG: Print current batch status
    print(f"Current batch status: {batch.status}")
    print(f"Form initial data: {form.initial}")
    
    context = {
        'form': form,
        'course': course,
        'batch': batch,
        'page_title': f'Edit Batch: {batch.name}',
        'submit_url': reverse('courses:edit_batch', args=[course.id, batch.id]),
    }
    
    return render(request, 'batch_management_instructor/batch_edit_form.html', context)




@login_required
def instructor_course_modules(request, course_id):
    """Instructor: View course modules and lessons"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('courses:instructor_batch_overview')
    
    # Get modules with lessons
    modules = course.modules.all().prefetch_related('lessons').order_by('order')
    
    # Get all lessons for additional processing if needed
    all_lessons = CourseLesson.objects.filter(
        module__course=course
    ).select_related('module').order_by('module__order', 'order')
    
    # Calculate stats
    total_modules = modules.count()
    total_lessons = sum(module.lessons.count() for module in modules)
    batches = course.batches.all().order_by('-created_at')  
    # Group lessons by type for stats
    lesson_stats = {
        'text': all_lessons.filter(lesson_type='text').count(),
        'video': all_lessons.filter(lesson_type='video').count(),
        'pdf': all_lessons.filter(lesson_type='pdf').count(),
        'mixed': all_lessons.filter(lesson_type='mixed').count(),
    }
    
    context = {
        'course': course,
        'modules': modules,
        'all_lessons': all_lessons,  # Yeh add kiya
        'total_modules': total_modules,
        'batches': batches,
        'total_lessons': total_lessons,
        'lesson_stats': lesson_stats,  # Bonus stats
        'page_title': f'{course.title} - Modules',
    }
    
    return render(request, 'batch_management_instructor/course_modules.html', context)


@login_required
def instructor_create_batch_module(request, course_id, batch_id):
    """Instructor: Create module for batch with choice to add to course"""
    if request.user.role != 'instructor':
        return redirect('user_login')
        
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    
    # Check permissions
    if course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('courses:manage_courses')

    
    if request.method == 'POST':
        form = SimpleBatchModuleForm(request.POST)
        add_to_course = request.POST.get('add_to_course')
        
        if form.is_valid():
            module = form.save(commit=False)
            module.batch = batch
            
            # Auto-set order
            last_module = batch.batch_modules.order_by('-order').first()
            module.order = (last_module.order + 1) if last_module else 1
            
            module.save()
            
            # Option to add to main course
            if add_to_course:
                from courses.models import CourseModule
                course_module = CourseModule.objects.create(
                    course=course,
                    title=module.title,
                    description=module.description,
                    order=course.modules.count() + 1,
                    is_active=True
                )
                messages.success(request, f'Module "{module.title}" added to both batch and main course!')
            else:
                messages.success(request, f'Module "{module.title}" added to batch!')
            
            return redirect('courses:instructor_batch_detail', course_id=course.id, batch_id=batch.id)  # FIXED
    else:
        form = SimpleBatchModuleForm()
    
    context = {
        'form': form,
        'course': course,
        'batch': batch,
        'page_title': f'Create Module - {batch.name}',
        'submit_url': reverse('courses:instructor_create_batch_module', args=[course.id, batch.id]),  # FIXED
    }
    
    return render(request, 'batch_management_instructor/batch_module_form.html', context)

@login_required
def instructor_create_batch_lesson(request, course_id, batch_id, module_id):
    """Instructor: Create lesson for batch module"""
    if request.user.role != 'instructor':
        return redirect('user_login')
        
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    module = get_object_or_404(BatchModule, id=module_id, batch=batch)
    
    # Check permissions
    if course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('instructor:manage_courses')
    
    if request.method == 'POST':
        form = SimpleBatchLessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.batch_module = module
            
            # Auto-set order
            last_lesson = module.lessons.order_by('-order').first()
            lesson.order = (last_lesson.order + 1) if last_lesson else 1
            
            lesson.save()
            messages.success(request, f'Lesson "{lesson.title}" created successfully!')
            return redirect('courses:instructor_batch_detail', course_id=course.id, batch_id=batch.id)  # FIXED
    else:
        form = SimpleBatchLessonForm()
    
    context = {
        'form': form,
        'course': course,
        'batch': batch,
        'module': module,
        'page_title': f'Create Lesson - {module.title}',
        'submit_url': reverse('courses:instructor_create_batch_lesson', args=[course.id, batch.id, module.id]),  # FIXED
    }
    
    return render(request, 'batch_management_instructor/batch_lesson_form.html', context)


@login_required
def instructor_batch_enrollments(request, course_id, batch_id):
    """Instructor: Manage batch enrollments"""
    if request.user.role != 'instructor':
        return redirect('user_login')
        
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    
    # Check permissions
    if course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('courses:manage_courses')
    
    # SAME QUERY as batch_detail
    enrollments = batch.enrollments.all().select_related('student').order_by('-enrolled_at')
    
    # Quick enroll form
    if request.method == 'POST':
        form = BatchEnrollForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data['student']
            
            # Check if already enrolled
            if batch.enrollments.filter(student=student, is_active=True).exists():
                messages.error(request, f"{student.get_full_name() or student.username} is already enrolled!")
            else:
                BatchEnrollment.objects.create(
                    student=student,
                    batch=batch
                )
                messages.success(request, f"{student.get_full_name() or student.username} enrolled successfully!")
            
            return redirect('courses:instructor_batch_enrollments', course_id=course.id, batch_id=batch.id)
    else:
        form = BatchEnrollForm()
    
    # Stats - SAME calculation
    stats = {
        'total_enrolled': enrollments.count(),
        'active_enrolled': enrollments.filter(is_active=True).count(),
        'inactive_enrolled': enrollments.filter(is_active=False).count(),
        'total_completed': enrollments.filter(status='completed').count(),
        'total_dropped': enrollments.filter(status='dropped').count(),
        'available_seats': batch.get_available_seats(),
    }
    
    context = {
        'course': course,
        'batch': batch,
        'enrollments': enrollments,
        'form': form,
        'stats': stats,
        'page_title': f'Students - {batch.name}',
    }
    
    return render(request, 'batch_management_instructor/batch_enrollments.html', context)



@login_required
def instructor_batch_enrollment_toggle(request, course_id, batch_id, enrollment_id):
    """Instructor: Toggle enrollment status (activate/deactivate)"""
    if request.user.role != 'instructor':
        return redirect('user_login')
        
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    enrollment = get_object_or_404(BatchEnrollment, id=enrollment_id, batch=batch)
    
    # Check permissions
    if course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('instructor:manage_courses')
    
    # Toggle active status
    enrollment.is_active = not enrollment.is_active
    enrollment.save()
    
    status = "activated" if enrollment.is_active else "deactivated"
    messages.success(request, f"Student {enrollment.student.username} {status}!")
    
    return redirect('instructor:batch_enrollments', course_id=course.id, batch_id=batch.id)


@login_required
def instructor_batch_overview(request):
    """Instructor: Overview of all their batches"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    # Get all courses taught by this instructor
    courses = Course.objects.filter(instructor=request.user, is_active=True)
    
    # Get all batches for these courses
    batches = Batch.objects.filter(
        course__instructor=request.user
    ).select_related('course').order_by('-created_at')
    
    # Stats
    total_batches = batches.count()
    active_batches = batches.filter(status='active').count()
    total_students = BatchEnrollment.objects.filter(
        batch__course__instructor=request.user,
        is_active=True
    ).count()
    
    stats = {
        'total_courses': courses.count(),
        'total_batches': total_batches,
        'active_batches': active_batches,
        'total_students': total_students,
    }
    
    context = {
        'courses': courses,
        'batches': batches[:10],  # Recent 10 batches
        'stats': stats,
        'page_title': 'Batch Overview',
    }
    
    return render(request, 'batch_management_instructor/batch_overview.html', context)


@login_required
def instructor_delete_batch_module(request, course_id, batch_id, module_id):
    """Instructor: Delete batch module"""
    if request.user.role != 'instructor':
        return redirect('user_login')
        
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    module = get_object_or_404(BatchModule, id=module_id, batch=batch)
    
    # Check permissions
    if course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('instructor:manage_courses')
    
    if request.method == 'POST':
        module_title = module.title
        module.delete()
        messages.success(request, f'Module "{module_title}" deleted successfully!')
        return redirect('instructor:batch_detail', course_id=course.id, batch_id=batch.id)
    
    context = {
        'course': course,
        'batch': batch,
        'module': module,
        'page_title': f'Delete Module: {module.title}',
    }
    
    return render(request, 'instructor/confirm_delete.html', context)


@login_required
def instructor_delete_batch_lesson(request, course_id, batch_id, module_id, lesson_id):
    """Instructor: Delete batch lesson"""
    if request.user.role != 'instructor':
        return redirect('user_login')
        
    course = get_object_or_404(Course, id=course_id)
    batch = get_object_or_404(Batch, id=batch_id, course=course)
    module = get_object_or_404(BatchModule, id=module_id, batch=batch)
    lesson = get_object_or_404(BatchLesson, id=lesson_id, batch_module=module)
    
    # Check permissions
    if course.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('instructor:manage_courses')
    
    if request.method == 'POST':
        lesson_title = lesson.title
        lesson.delete()
        messages.success(request, f'Lesson "{lesson_title}" deleted successfully!')
        return redirect('instructor:batch_detail', course_id=course.id, batch_id=batch.id)
    
    context = {
        'course': course,
        'batch': batch,
        'module': module,
        'lesson': lesson,
        'page_title': f'Delete Lesson: {lesson.title}',
    }
    
    return render(request, 'instructor/confirm_delete.html', context)



from .models import (
    Course, CourseCategory, CourseModule, CourseLesson,
    Enrollment, CourseReview, CourseFAQ,
    Batch, BatchModule, BatchLesson, BatchEnrollment,
    StudentSubscription, DeviceSession, StudentLoginLog  # <-- YEH ADD KARO
)
# courses/views.py - ADD AT THE END

# courses/views.py - ADD THESE AT THE VERY END

# ==================== SUBSCRIPTIONS ====================

@login_required
def subscription_list(request):
    """List all student subscriptions"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Only superadmin can access subscriptions.')
        return redirect('courses:course_dashboard')
    
    subscriptions = StudentSubscription.objects.all().select_related('student', 'course').order_by('-subscribed_at')
    
    # Filters
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    if search:
        subscriptions = subscriptions.filter(
            Q(student__username__icontains=search) |
            Q(student__email__icontains=search) |
            Q(course__title__icontains=search)
        )
    
    if status_filter == 'active':
        subscriptions = subscriptions.filter(is_active=True)
    elif status_filter == 'expired':
        subscriptions = subscriptions.filter(is_active=False)
    
    # Stats
    total_subs = StudentSubscription.objects.count()
    active_subs = StudentSubscription.objects.filter(is_active=True).count()
    expired_subs = total_subs - active_subs
    
    # Pagination
    paginator = Paginator(subscriptions, 20)
    page = request.GET.get('page')
    subscriptions = paginator.get_page(page)
    
    context = {
        'subscriptions': subscriptions,
        'search': search,
        'status_filter': status_filter,
        'total_subs': total_subs,
        'active_subs': active_subs,
        'expired_subs': expired_subs,
    }
    return render(request, 'courses/subscription_list.html', context)


@login_required
def remove_device_session(request, device_id):
    """Remove a device session"""
    
    if request.user.role != 'superadmin':
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    try:
        device = get_object_or_404(DeviceSession, id=device_id)
        subscription = device.subscription
        
        device.delete()
        
        # Update device count
        subscription.current_devices = subscription.devices.filter(is_active=True).count()
        subscription.save()
        
        return JsonResponse({'success': True, 'message': 'Device removed successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def create_subscription(request):
    """Create new subscription via form"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('courses:course_dashboard')
    
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student')
            course_id = request.POST.get('course')
            max_devices = int(request.POST.get('max_devices', 2))
            expires_days = request.POST.get('expires_days', '')
            
            student = get_object_or_404(User, id=student_id, role='student')
            course = get_object_or_404(Course, id=course_id)
            
            # Check if already exists
            if StudentSubscription.objects.filter(student=student, course=course).exists():
                messages.error(request, f'{student.username} already has subscription for {course.title}')
                return redirect('courses:create_subscription')
            
            # Calculate expiry
            expires_at = None
            if expires_days:
                from datetime import timedelta
                expires_at = timezone.now() + timedelta(days=int(expires_days))
            
            # Create subscription
            subscription = StudentSubscription.objects.create(
                student=student,
                course=course,
                max_devices=max_devices,
                current_devices=0,
                expires_at=expires_at,
                is_active=True
            )
            
            messages.success(request, f'Subscription created for {student.username} - {course.title}')
            return redirect('courses:subscription_list')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('courses:create_subscription')
    
    # GET request - show form
    students = User.objects.filter(role='student', is_active=True).order_by('first_name', 'last_name')
    courses = Course.objects.filter(is_active=True, status='published').order_by('title')
    
    context = {
        'students': students,
        'courses': courses,
    }
    return render(request, 'courses/create_subscription.html', context)


@login_required
def subscription_details(request, student_id):
    """Detailed subscription info for a student"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('courses:course_dashboard')
    
    student = get_object_or_404(User, id=student_id, role='student')
    subscriptions = student.course_subscriptions.all().select_related('course').order_by('-subscribed_at')
    
    # Get device sessions
    devices = DeviceSession.objects.filter(
        subscription__student=student
    ).select_related('subscription__course').order_by('-last_login')
    
    # Stats
    total_subs = subscriptions.count()
    active_subs = subscriptions.filter(is_active=True).count()
    total_devices = devices.filter(is_active=True).count()
    
    context = {
        'student': student,
        'subscriptions': subscriptions,
        'devices': devices,
        'total_subs': total_subs,
        'active_subs': active_subs,
        'total_devices': total_devices,
    }
    return render(request, 'courses/subscription_details.html', context)


@login_required
def edit_subscription(request, subscription_id):
    """Edit existing subscription"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('courses:course_dashboard')
    
    subscription = get_object_or_404(StudentSubscription, id=subscription_id)
    
    if request.method == 'POST':
        try:
            subscription.max_devices = int(request.POST.get('max_devices', 2))
            subscription.is_active = request.POST.get('is_active') == 'on'
            
            expires_days = request.POST.get('expires_days', '')
            if expires_days:
                from datetime import timedelta
                subscription.expires_at = timezone.now() + timedelta(days=int(expires_days))
            elif request.POST.get('remove_expiry'):
                subscription.expires_at = None
            
            subscription.save()
            
            messages.success(request, 'Subscription updated successfully!')
            return redirect('courses:subscription_details', student_id=subscription.student.id)
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    context = {
        'subscription': subscription,
    }
    return render(request, 'courses/edit_subscription.html', context)


@login_required
def delete_subscription(request, subscription_id):
    """Delete subscription"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('courses:course_dashboard')
    
    subscription = get_object_or_404(StudentSubscription, id=subscription_id)
    
    if request.method == 'POST':
        student_name = subscription.student.username
        course_name = subscription.course.title
        subscription.delete()
        
        messages.success(request, f'Subscription deleted: {student_name} - {course_name}')
        return redirect('courses:subscription_list')
    
    context = {
        'subscription': subscription,
    }
    return render(request, 'courses/delete_subscription.html', context)


@login_required
def device_restrictions(request):
    """Manage device restrictions"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('courses:course_dashboard')
    
    subscriptions = StudentSubscription.objects.all().select_related('student', 'course').order_by('-subscribed_at')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        subscriptions = subscriptions.filter(
            Q(student__username__icontains=search) |
            Q(student__email__icontains=search) |
            Q(course__title__icontains=search)
        )
    
    context = {
        'subscriptions': subscriptions,
        'search': search,
    }
    return render(request, 'courses/device_restrictions.html', context)


@login_required
def update_device_restriction(request, subscription_id):
    """Update device restriction for subscription"""
    if request.user.role != 'superadmin':
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    if request.method == 'POST':
        try:
            subscription = get_object_or_404(StudentSubscription, id=subscription_id)
            max_devices = int(request.POST.get('max_devices', 2))
            
            subscription.max_devices = max_devices
            subscription.save()
            
            messages.success(request, f'Device limit updated to {max_devices}')
            return redirect('courses:device_restrictions')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('courses:device_restrictions')
    
    return redirect('courses:device_restrictions')


# ==================== COURSE REVIEWS ====================

@login_required
def course_reviews(request):
    """View all course reviews"""
    if request.user.role not in ['superadmin', 'instructor']:
        messages.error(request, 'Access denied.')
        return redirect('courses:course_dashboard')
    
    if request.user.role == 'instructor':
        reviews = CourseReview.objects.filter(course__instructor=request.user)
    else:
        reviews = CourseReview.objects.all()
    
    reviews = reviews.select_related('course', 'student').order_by('-created_at')
    
    # Filters
    search = request.GET.get('search', '')
    rating_filter = request.GET.get('rating', '')
    approved_filter = request.GET.get('approved', '')
    
    if search:
        reviews = reviews.filter(
            Q(student__username__icontains=search) |
            Q(course__title__icontains=search) |
            Q(review_text__icontains=search)
        )
    
    if rating_filter:
        reviews = reviews.filter(rating=rating_filter)
    
    if approved_filter == 'yes':
        reviews = reviews.filter(is_approved=True)
    elif approved_filter == 'no':
        reviews = reviews.filter(is_approved=False)
    
    # Stats
    total_reviews = CourseReview.objects.count()
    avg_rating = CourseReview.objects.aggregate(Avg('rating'))['rating__avg'] or 0
    pending_reviews = CourseReview.objects.filter(is_approved=False).count()
    
    # Pagination
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews = paginator.get_page(page)
    
    context = {
        'reviews': reviews,
        'search': search,
        'rating_filter': rating_filter,
        'approved_filter': approved_filter,
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
        'pending_reviews': pending_reviews,
    }
    return render(request, 'courses/course_reviews.html', context)


@login_required
def course_review_detail(request, course_id):
    """Reviews for specific course"""
    if request.user.role not in ['superadmin', 'instructor']:
        messages.error(request, 'Access denied.')
        return redirect('courses:course_dashboard')
    
    course = get_object_or_404(Course, id=course_id)
    
    # Permission check for instructor
    if request.user.role == 'instructor' and course.instructor != request.user:
        messages.error(request, 'You can only view reviews for your courses.')
        return redirect('courses:course_reviews')
    
    reviews = course.reviews.all().select_related('student').order_by('-created_at')
    
    # Stats
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    rating_distribution = {
        5: reviews.filter(rating=5).count(),
        4: reviews.filter(rating=4).count(),
        3: reviews.filter(rating=3).count(),
        2: reviews.filter(rating=2).count(),
        1: reviews.filter(rating=1).count(),
    }
    
    context = {
        'course': course,
        'reviews': reviews,
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
        'rating_distribution': rating_distribution,
    }
    return render(request, 'courses/course_review_detail.html', context)


@login_required
def approve_review(request, review_id):
    """Approve/reject review"""
    if request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    review = get_object_or_404(CourseReview, id=review_id)
    
    # Permission check
    if request.user.role == 'instructor' and review.course.instructor != request.user:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            review.is_approved = True
            review.save()
            messages.success(request, 'Review approved.')
        elif action == 'reject':
            review.is_approved = False
            review.save()
            messages.success(request, 'Review rejected.')
        
        return redirect('courses:course_reviews')
    
    return redirect('courses:course_reviews')


# ==================== ATTENDANCE (LOGIN/LOGOUT) ====================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from courses.models import StudentLoginLog, Course
from userss.models import AbstractUser

# courses/views.py - REPLACE ATTENDANCE SECTION

# ==================== ATTENDANCE (AUTOMATIC TRACKING) ====================

@login_required
def attendance_dashboard(request):
    """Attendance dashboard with statistics"""
    
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('courses:course_dashboard')
    
    # Date range (default: last 30 days)
    from datetime import timedelta
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    date_from = request.GET.get('date_from', start_date)
    date_to = request.GET.get('date_to', end_date)
    
    # Get logs
    logs = StudentLoginLog.objects.filter(
        login_time__date__gte=date_from,
        login_time__date__lte=date_to
    ).select_related('student', 'course')
    
    # Stats
    total_sessions = logs.count()
    active_sessions = logs.filter(logout_time__isnull=True).count()
    unique_students = logs.values('student').distinct().count()
    
    # Total time
    completed_logs = logs.filter(logout_time__isnull=False)
    total_minutes = completed_logs.aggregate(Sum('session_duration'))['session_duration__sum'] or 0
    total_hours = round(total_minutes / 60, 1)
    
    # Average session
    avg_session = total_minutes / completed_logs.count() if completed_logs.count() > 0 else 0
    
    # Today's active
    today = timezone.now().date()
    today_active = logs.filter(
        login_time__date=today,
        logout_time__isnull=True
    ).count()
    
    # Daily trend (last 7 days)
    daily_stats = []
    for i in range(7):
        date = end_date - timedelta(days=i)
        count = StudentLoginLog.objects.filter(login_time__date=date).count()
        daily_stats.append({
            'date': date.strftime('%b %d'),
            'count': count
        })
    daily_stats.reverse()
    
    context = {
        'total_sessions': total_sessions,
        'active_sessions': active_sessions,
        'unique_students': unique_students,
        'total_hours': total_hours,
        'avg_session_minutes': round(avg_session),
        'today_active': today_active,
        'daily_stats': daily_stats,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'courses/attendance_dashboard.html', context)


@login_required
def attendance_status(request):
    """Detailed attendance logs with filters"""
    
    if request.user.role != 'superadmin':
        messages.error(request, 'Only superadmin can access attendance.')
        return redirect('courses:course_dashboard')
    
    logs = StudentLoginLog.objects.all().select_related('student', 'course').order_by('-login_time')
    
    # Filters
    date_filter = request.GET.get('date', '')
    course_filter = request.GET.get('course', '')
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    if date_filter:
        logs = logs.filter(login_time__date=date_filter)
    
    if course_filter:
        logs = logs.filter(course_id=course_filter)
    
    if search:
        logs = logs.filter(
            Q(student__username__icontains=search) |
            Q(student__email__icontains=search) |
            Q(student__first_name__icontains=search) |
            Q(student__last_name__icontains=search)
        )
    
    if status_filter == 'active':
        logs = logs.filter(logout_time__isnull=True)
    elif status_filter == 'completed':
        logs = logs.filter(logout_time__isnull=False)
    
    # Stats
    total_logs = logs.count()
    active_sessions = logs.filter(logout_time__isnull=True).count()
    total_students = logs.values('student').distinct().count()
    
    # Pagination
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    
    # Courses for filter
    courses = Course.objects.filter(is_active=True).order_by('title')
    
    context = {
        'logs': logs,
        'date_filter': date_filter,
        'course_filter': course_filter,
        'search': search,
        'status_filter': status_filter,
        'total_logs': total_logs,
        'active_sessions': active_sessions,
        'total_students': total_students,
        'courses': courses,
    }
    return render(request, 'courses/attendance_status.html', context)


@login_required
def student_attendance_detail(request, student_id):
    """Detailed attendance for specific student"""
    
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('courses:course_dashboard')
    
    student = get_object_or_404(User, id=student_id, role='student')
    logs = student.login_logs.all().select_related('course').order_by('-login_time')
    
    # Date filters
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if date_from:
        logs = logs.filter(login_time__date__gte=date_from)
    if date_to:
        logs = logs.filter(login_time__date__lte=date_to)
    
    # Stats
    total_logins = logs.count()
    total_minutes = logs.aggregate(Sum('session_duration'))['session_duration__sum'] or 0
    total_time_hours = round(total_minutes / 60, 1)
    active_sessions = logs.filter(logout_time__isnull=True).count()
    avg_session = total_minutes / total_logins if total_logins > 0 else 0
    
    # Course-wise breakdown
    course_stats = logs.values('course__title').annotate(
        total_sessions=Count('id'),
        total_time=Sum('session_duration')
    ).order_by('-total_sessions')[:5]
    
    # Pagination
    paginator = Paginator(logs, 30)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    
    context = {
        'student': student,
        'logs': logs,
        'total_logins': total_logins,
        'total_time_hours': total_time_hours,
        'active_sessions': active_sessions,
        'avg_session_minutes': round(avg_session),
        'course_stats': course_stats,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'courses/student_attendance_detail.html', context)


@login_required
def export_attendance(request):
    """Export attendance to CSV"""
    import csv
    from django.http import HttpResponse
    
    if request.user.role != 'superadmin':
        return redirect('courses:attendance_status')
    
    # Get filters
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    logs = StudentLoginLog.objects.all().select_related('student', 'course')
    
    if date_from:
        logs = logs.filter(login_time__date__gte=date_from)
    if date_to:
        logs = logs.filter(login_time__date__lte=date_to)
    
    # Create CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Student', 'Email', 'Course', 'Login Time', 'Logout Time', 
        'Duration (mins)', 'IP Address'
    ])
    
    for log in logs:
        writer.writerow([
            log.student.get_full_name() or log.student.username,
            log.student.email,
            log.course.title if log.course else 'General',
            log.login_time.strftime('%Y-%m-%d %H:%M:%S'),
            log.logout_time.strftime('%Y-%m-%d %H:%M:%S') if log.logout_time else 'Active',
            log.session_duration,
            log.ip_address or 'N/A'
        ])
    
    return response
# courses/views.py - ADD AT THE END

# ==================== STUDENT REVIEW SUBMISSION ====================


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import Course, CourseReview, Enrollment

@login_required
def submit_course_review(request, course_id):
    """Submit a review for a course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user is enrolled
    try:
        enrollment = Enrollment.objects.get(
            student=request.user,
            course=course,
            is_active=True
        )
    except Enrollment.DoesNotExist:
        messages.error(request, "You must be enrolled in this course to submit a review.")
        return redirect('courses:course_detail', course_id=course_id)
    
    # Check if user already reviewed
    existing_review = CourseReview.objects.filter(
        student=request.user,
        course=course
    ).first()
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review_text = request.POST.get('review')
        
        if not rating or not review_text:
            messages.error(request, "Please provide both rating and review text.")
            return render(request, 'courses/submit_review.html', {
                'course': course,
                'existing_review': existing_review
            })
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5")
        except (ValueError, TypeError):
            messages.error(request, "Invalid rating value.")
            return render(request, 'courses/submit_review.html', {
                'course': course,
                'existing_review': existing_review
            })
        
        # Create or update review
        if existing_review:
            existing_review.rating = rating
            existing_review.review = review_text
            existing_review.save()
            messages.success(request, "Your review has been updated successfully!")
        else:
            CourseReview.objects.create(
                student=request.user,
                course=course,
                rating=rating,
                review=review_text
            )
            messages.success(request, "Thank you for your review!")
        
        # Redirect to student courses page - FIXED NAMESPACE
        # Check which URL pattern exists in your project
        try:
            # Try common patterns
            return redirect('student_courses')  # Without namespace
        except:
            try:
                return redirect('userss:student_courses')  # With userss namespace
            except:
                # Fallback to course detail
                return redirect('courses:course_detail', course_id=course_id)
    
    # GET request - show review form
    context = {
        'course': course,
        'existing_review': existing_review,
        'enrollment': enrollment
    }
    
    return render(request, 'courses/submit_review.html', context)

def update_course_rating(course):
    """Update course average rating and total reviews"""
    reviews = course.reviews.filter(is_approved=True)
    total_reviews = reviews.count()
    
    if total_reviews > 0:
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        course.average_rating = round(avg_rating, 2)
        course.total_reviews = total_reviews
    else:
        course.average_rating = 0
        course.total_reviews = 0
    
    course.save(update_fields=['average_rating', 'total_reviews'])


@login_required
def my_reviews(request):
    """Student's submitted reviews"""
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    reviews = CourseReview.objects.filter(
        student=request.user
    ).select_related('course').order_by('-created_at')
    
    context = {
        'reviews': reviews,
    }
    
    return render(request, 'courses/my_reviews.html', context)


@login_required
def edit_my_review(request, review_id):
    """Edit student's own review"""
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    review = get_object_or_404(CourseReview, id=review_id, student=request.user)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text', '').strip()
        
        if not rating:
            messages.error(request, 'Please select a rating.')
            return redirect('courses:edit_my_review', review_id=review.id)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError("Invalid rating")
            
            review.rating = rating
            review.review_text = review_text
            review.save()
            
            # Update course rating
            update_course_rating(review.course)
            
            messages.success(request, 'Review updated successfully!')
            return redirect('courses:my_reviews')
            
        except ValueError:
            messages.error(request, 'Invalid rating value.')
    
    context = {
        'review': review,
    }
    
    return render(request, 'courses/edit_review.html', context)


@login_required
def delete_my_review(request, review_id):
    """Delete student's own review"""
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    review = get_object_or_404(CourseReview, id=review_id, student=request.user)
    
    if request.method == 'POST':
        course = review.course
        review.delete()
        
        # Update course rating
        update_course_rating(course)
        
        messages.success(request, 'Review deleted successfully!')
        return redirect('courses:my_reviews')
    
    context = {
        'review': review,
    }
    
    return render(request, 'courses/delete_review.html', context)




# courses/views.py - ADD THIS VIEW

@login_required
def category_profile(request, category_id):
    """Category profile with all courses and enrolled students"""
    if request.user.role not in ['superadmin', 'instructor']:
        messages.error(request, 'Access denied.')
        return redirect('courses:course_dashboard')
    
    category = get_object_or_404(CourseCategory, id=category_id)
    
    # Get all courses in this category
    courses = Course.objects.filter(
        category=category,
        is_active=True
    ).annotate(
        enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True)),
        total_revenue=Sum('enrollments__amount_paid', filter=Q(enrollments__is_active=True))
    ).order_by('-created_at')
    
    # Get all enrollments from these courses
    enrollments = Enrollment.objects.filter(
        course__category=category,
        is_active=True
    ).select_related('student', 'course').order_by('-enrolled_at')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        enrollments = enrollments.filter(
            Q(student__username__icontains=search) |
            Q(student__first_name__icontains=search) |
            Q(student__last_name__icontains=search) |
            Q(student__email__icontains=search)
        )
    
    # Filter by course
    course_filter = request.GET.get('course', '')
    if course_filter:
        enrollments = enrollments.filter(course_id=course_filter)
    
    # Stats
    total_courses = courses.count()
    total_students = enrollments.values('student').distinct().count()
    total_enrollments = enrollments.count()
    
    # Calculate total revenue
    total_revenue = courses.aggregate(Sum('enrollments__amount_paid'))['enrollments__amount_paid__sum'] or 0
    
    # Status breakdown
    status_breakdown = enrollments.values('status').annotate(count=Count('id'))
    
    # Course performance
    course_performance = []
    for course in courses:
        course_enrollments = course.enrollments.filter(is_active=True)
        course_performance.append({
            'course': course,
            'total_students': course_enrollments.count(),
            'completed': course_enrollments.filter(status='completed').count(),
            'active': course_enrollments.filter(status='enrolled').count(),
            'revenue': course_enrollments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        })
    
    # Top students in this category
    top_students = enrollments.values(
        'student__id', 'student__username', 'student__first_name', 'student__last_name'
    ).annotate(
        total_courses=Count('id'),
        completed_courses=Count('id', filter=Q(status='completed'))
    ).order_by('-total_courses')[:10]
    
    # Pagination for enrollments
    paginator = Paginator(enrollments, 20)
    page = request.GET.get('page')
    enrollments = paginator.get_page(page)
    
    context = {
        'category': category,
        'courses': courses,
        'enrollments': enrollments,
        'total_courses': total_courses,
        'total_students': total_students,
        'total_enrollments': total_enrollments,
        'total_revenue': total_revenue,
        'status_breakdown': status_breakdown,
        'course_performance': course_performance,
        'top_students': top_students,
        'search': search,
        'course_filter': course_filter,
    }
    
    return render(request, 'courses/category_profile.html', context)

# courses/views.py - ADD THIS NEW VIEW

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Enrollment, CourseLesson, LessonProgress

# courses/views.py - UPDATE THIS

# courses/views.py - continue_learning view FIX KARO

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Course, BatchEnrollment, LessonProgress, BatchModule, BatchLesson


@login_required
def course_detail_continue_learning_student(request, course_id):
    """View course details"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user can view this course
    can_view = False
    if request.user.role == 'superadmin':
        can_view = True
    elif request.user.role == 'instructor' and course.instructor == request.user:
        can_view = True
    elif request.user.role == 'student':
        # Students can view if enrolled or if course is published
        if course.status == 'published' or course.enrollments.filter(student=request.user, is_active=True).exists():
            can_view = True
    
    if not can_view:
        messages.error(request, "You don't have permission to view this course!")
        return redirect('courses:course_dashboard')
    
    # Get course modules and lessons
    modules = course.modules.filter(is_active=True).prefetch_related('lessons')
    
    # Get enrollment info for students
    user_enrollment = None
    if request.user.role == 'student':
        user_enrollment = course.enrollments.filter(student=request.user, is_active=True).first()
    
    # Get course reviews
    reviews = course.reviews.filter(is_approved=True).order_by('-created_at')[:5]
    
    # Get FAQs
    faqs = course.faqs.filter(is_active=True)
    
    context = {
        'course': course,
        'modules': modules,
        'user_enrollment': user_enrollment,
        'reviews': reviews,
        'faqs': faqs,
    }
    
    return render(request, 'courses/course_detail_continue_learning_student.html', context)


# courses/views.py - ADD THIS NEW VIEW

# views.py mein ye view UPDATE karo

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Course, BatchLesson, BatchModule, LessonProgress, LessonAttachment

# courses/views.py

# courses/views.py

# courses/views.py - BATCH-BASED Lesson Viewer

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Course, Batch, BatchModule, BatchLesson, LessonProgress, BatchEnrollment

# courses/views.py - Lesson Viewer WITHOUT enrollment check
# courses/views.py - COURSE DIRECT (NO BATCH)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Course, CourseModule, CourseLesson, LessonProgress

@login_required
def continue_learning(request, course_id):
    """Continue learning - SEEDHA COURSE SE"""
    
    course = get_object_or_404(Course, id=course_id)
    
    # ✅ Get last accessed lesson
    last_progress = LessonProgress.objects.filter(
        student=request.user,
        course_lesson__module__course=course  # Direct course relation
    ).order_by('-last_accessed').first()
    
    if last_progress and last_progress.course_lesson:
        # Continue from last lesson
        lesson = last_progress.course_lesson
        module = lesson.module
        
        return redirect(
            'courses:student_lesson_view',
            course_id=course.id,
            module_id=module.id,
            lesson_id=lesson.id
        )
    
    # ✅ No progress? Start from first lesson
    first_module = course.modules.filter(is_active=True).order_by('order').first()
    
    if not first_module:
        messages.warning(request, "No modules available yet!")
        return redirect('student_courses')
    
    first_lesson = first_module.lessons.filter(is_active=True).order_by('order').first()
    
    if not first_lesson:
        messages.warning(request, "No lessons available yet!")
        return redirect('student_courses')
    
    return redirect(
        'courses:student_lesson_view',
        course_id=course.id,
        module_id=first_module.id,
        lesson_id=first_lesson.id
    )


# courses/views.py - student_lesson_view

# courses/views.py - UPDATED VIEW

# courses/views.py - CROSS MODULE NAVIGATION

@login_required
def student_lesson_view(request, course_id, module_id, lesson_id):
    """Student lesson viewer - CROSS MODULE NAVIGATION"""
    
    course = get_object_or_404(Course, id=course_id)
    
    # ✅ Don't check module_id strict - lesson might be in different module
    lesson = get_object_or_404(CourseLesson, id=lesson_id)
    module = lesson.module  # Get actual module from lesson
    
    # Get or create lesson progress
    lesson_progress, created = LessonProgress.objects.get_or_create(
        student=request.user,
        course_lesson=lesson,
        defaults={'status': 'in_progress'}
    )
    
    if lesson_progress.status == 'not_started':
        lesson_progress.status = 'in_progress'
        lesson_progress.save()
    
    # Get attachments
    attachments = []
    if hasattr(lesson, 'attachments'):
        attachments = lesson.attachments.all()
    
    # ✅ GET ALL LESSONS FROM ALL MODULES (cross-module navigation)
    all_course_lessons = []
    all_modules = course.modules.filter(is_active=True).order_by('order')
    
    for mod in all_modules:
        for les in mod.lessons.filter(is_active=True).order_by('order'):
            all_course_lessons.append(les)
    
    print(f"\n=== LESSON NAVIGATION DEBUG ===")
    print(f"Course: {course.title} (ID: {course.id})")
    print(f"Total modules: {all_modules.count()}")
    print(f"Total lessons: {len(all_course_lessons)}")
    print(f"Current lesson: {lesson.title} (ID: {lesson.id}, Module: {module.title})")
    
    # Find current lesson index
    current_index = None
    for idx, l in enumerate(all_course_lessons):
        if l.id == lesson.id:
            current_index = idx
            break
    
    print(f"Current index: {current_index}")
    
    prev_lesson = None
    next_lesson = None
    
    if current_index is not None:
        if current_index > 0:
            prev_lesson = all_course_lessons[current_index - 1]
            print(f"✅ Prev: {prev_lesson.title} (Module: {prev_lesson.module.title})")
        
        if current_index < len(all_course_lessons) - 1:
            next_lesson = all_course_lessons[current_index + 1]
            print(f"✅ Next: {next_lesson.title} (Module: {next_lesson.module.title})")
    
    print(f"=== END DEBUG ===\n")
    
    context = {
        'course': course,
        'module': module,
        'lesson': lesson,
        'lesson_progress': lesson_progress,
        'attachments': attachments,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'all_modules': all_modules,
    }
    
    return render(request, 'courses/lesson_viewer.html', context)


@login_required
def mark_lesson_complete(request, course_id, module_id, lesson_id):
    """Mark course lesson as completed"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    lesson = get_object_or_404(CourseLesson, id=lesson_id)
    
    try:
        progress = LessonProgress.objects.get(
            student=request.user,
            course_lesson=lesson  # ✅ course_lesson field
        )
        progress.mark_as_completed()
        
        return JsonResponse({
            'success': True,
            'message': 'Lesson marked as complete!'
        })
    
    except LessonProgress.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Progress record not found'
        })
