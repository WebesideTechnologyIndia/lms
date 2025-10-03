from django.shortcuts import render

# Create your views here.
# exams/views.py - Views for Exam Management System

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Avg, Sum, Prefetch
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
from datetime import timedelta
import random

from .models import (
    Exam, MCQQuestion, MCQOption, QAQuestion, AssignmentExam,
    ExamAssignment, ExamAttempt, MCQResponse, QAResponse, 
    AssignmentSubmission, ExamFile
)
from .forms import (
    ExamForm, MCQQuestionForm, MCQOptionFormSet, QAQuestionForm,
    AssignmentExamForm, ExamAssignmentForm, QuickMCQForm,
    MCQResponseForm, QAResponseForm, AssignmentSubmissionForm,
    QAGradingForm, AssignmentGradingForm
)
from courses.models import Course, Batch
from userss.models import CustomUser


# ==================== ADMIN EXAM MANAGEMENT VIEWS ====================

@login_required
def exam_dashboard(request):
    """Main exam dashboard for admin"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    # Get exam statistics
    total_exams = Exam.objects.count()
    published_exams = Exam.objects.filter(status='published').count()
    draft_exams = Exam.objects.filter(status='draft').count()
    total_attempts = ExamAttempt.objects.count()
    pending_grading = ExamAttempt.objects.filter(
        is_graded=False,
        status__in=['submitted', 'auto_submitted']
    ).count()
    
    # Recent exams
    recent_exams = Exam.objects.order_by('-created_at')[:5]
    
    # Recent attempts
    recent_attempts = ExamAttempt.objects.select_related(
        'exam', 'student'
    ).order_by('-started_at')[:10]
    
    # Exam type distribution
    exam_types = Exam.objects.values('exam_type').annotate(
        count=Count('id')
    ).order_by('exam_type')
    
    context = {
        'total_exams': total_exams,
        'published_exams': published_exams,
        'draft_exams': draft_exams,
        'total_attempts': total_attempts,
        'pending_grading': pending_grading,
        'recent_exams': recent_exams,
        'recent_attempts': recent_attempts,
        'exam_types': exam_types,
    }
    
    return render(request, 'exam/dashboard.html', context)


@login_required
def create_exam(request):
    """Create new exam - Step 1: Basic details"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.save()
            
            messages.success(request, f'Exam "{exam.title}" created successfully!')
            
            # Redirect based on exam type
            if exam.exam_type == 'mcq':
                return redirect('add_mcq_questions', exam_id=exam.id)
            elif exam.exam_type == 'qa':
                return redirect('add_qa_questions', exam_id=exam.id)
            else:  # assignment
                return redirect('setup_assignment', exam_id=exam.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ExamForm()
    
    context = {
        'form': form,
        'page_title': 'Create New Exam',
    }
    
    return render(request, 'exam/create_exam.html', context)


@login_required
def add_mcq_questions(request, exam_id):
    """Add MCQ questions to exam"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    exam = get_object_or_404(Exam, id=exam_id, exam_type='mcq')
    
    if request.method == 'POST':
        if 'quick_add' in request.POST:
            # Quick add form
            quick_form = QuickMCQForm(request.POST)
            if quick_form.is_valid():
                # Create question
                question = MCQQuestion.objects.create(
                    exam=exam,
                    question_text=quick_form.cleaned_data['question_text'],
                    marks=quick_form.cleaned_data['marks'],
                    explanation=quick_form.cleaned_data.get('explanation', ''),
                    order=exam.mcq_questions.count() + 1
                )
                
                # Create options
                options_data = [
                    (quick_form.cleaned_data['option_1'], quick_form.cleaned_data['correct_option'] == '1'),
                    (quick_form.cleaned_data['option_2'], quick_form.cleaned_data['correct_option'] == '2'),
                ]
                
                if quick_form.cleaned_data.get('option_3'):
                    options_data.append((
                        quick_form.cleaned_data['option_3'], 
                        quick_form.cleaned_data['correct_option'] == '3'
                    ))
                
                if quick_form.cleaned_data.get('option_4'):
                    options_data.append((
                        quick_form.cleaned_data['option_4'], 
                        quick_form.cleaned_data['correct_option'] == '4'
                    ))
                
                for i, (option_text, is_correct) in enumerate(options_data, 1):
                    MCQOption.objects.create(
                        question=question,
                        option_text=option_text,
                        is_correct=is_correct,
                        order=i
                    )
                
                messages.success(request, 'Question added successfully!')
                return redirect('add_mcq_questions', exam_id=exam.id)
        
        elif 'finish_exam' in request.POST:
            if exam.mcq_questions.count() > 0:
                exam.status = 'published'
                exam.save()
                messages.success(request, f'Exam "{exam.title}" published successfully!')
                return redirect('exam_dashboard')
            else:
                messages.error(request, 'Please add at least one question before publishing.')
    
    # Get existing questions
    questions = exam.mcq_questions.filter(is_active=True).prefetch_related('options').order_by('order')
    quick_form = QuickMCQForm()
    
    context = {
        'exam': exam,
        'questions': questions,
        'quick_form': quick_form,
        'total_questions': questions.count(),
    }
    
    return render(request, 'exam/add_mcq_questions.html', context)


@login_required
def add_qa_questions(request, exam_id):
    """Add Q&A questions to exam"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    exam = get_object_or_404(Exam, id=exam_id, exam_type='qa')
    
    if request.method == 'POST':
        if 'add_question' in request.POST:
            form = QAQuestionForm(request.POST, request.FILES)
            if form.is_valid():
                question = form.save(commit=False)
                question.exam = exam
                question.order = exam.qa_questions.count() + 1
                question.save()
                
                messages.success(request, 'Question added successfully!')
                return redirect('add_qa_questions', exam_id=exam.id)
        
        elif 'finish_exam' in request.POST:
            if exam.qa_questions.count() > 0:
                exam.status = 'published'
                exam.save()
                messages.success(request, f'Exam "{exam.title}" published successfully!')
                return redirect('exam_dashboard')
            else:
                messages.error(request, 'Please add at least one question before publishing.')
    
    # Get existing questions
    questions = exam.qa_questions.filter(is_active=True).order_by('order')
    form = QAQuestionForm()
    
    context = {
        'exam': exam,
        'questions': questions,
        'form': form,
        'total_questions': questions.count(),
    }
    
    return render(request, 'exam/add_qa_questions.html', context)


@login_required
def setup_assignment(request, exam_id):
    """Setup assignment exam details"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    exam = get_object_or_404(Exam, id=exam_id, exam_type='assignment')
    
    try:
        assignment = exam.assignment_details
    except AssignmentExam.DoesNotExist:
        assignment = None
    
    if request.method == 'POST':
        form = AssignmentExamForm(request.POST, instance=assignment)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.exam = exam
            assignment.save()
            
            exam.status = 'published'
            exam.save()
            
            messages.success(request, f'Assignment exam "{exam.title}" published successfully!')
            return redirect('exam_dashboard')
    else:
        form = AssignmentExamForm(instance=assignment)
    
    context = {
        'exam': exam,
        'form': form,
        'assignment': assignment,
    }
    
    return render(request, 'exams/setup_assignment.html', context)


# exams/views.py - Add these views to your existing views.py

@login_required
def load_exam_details(request, exam_id):
    """AJAX endpoint to load detailed exam information"""
    if request.user.role != 'superadmin':
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    try:
        exam = get_object_or_404(Exam, id=exam_id)
        
        # Format datetime for display
        start_datetime = exam.start_datetime.strftime('%b %d, %Y %I:%M %p') if exam.start_datetime else None
        end_datetime = exam.end_datetime.strftime('%b %d, %Y %I:%M %p') if exam.end_datetime else None
        
        exam_data = {
            'id': exam.id,
            'title': exam.title,
            'exam_type': exam.exam_type,
            'exam_type_display': exam.get_exam_type_display(),
            'total_marks': exam.total_marks,
            'passing_marks': exam.passing_marks,
            'timing_type': exam.timing_type,
            'timing_type_display': exam.get_timing_type_display(),
            'status': exam.status,
            'status_display': exam.get_status_display(),
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
            'created_at': exam.created_at.strftime('%b %d, %Y'),
            'allow_retake': exam.allow_retake,
            'max_attempts': exam.max_attempts,
            'total_questions': exam.get_total_questions(),
        }
        
        # Add timing details based on type
        if exam.timing_type == 'per_question':
            exam_data['time_per_question'] = exam.time_per_question_minutes
        elif exam.timing_type == 'total_exam':
            exam_data['total_exam_time'] = exam.total_exam_time_minutes
        
        return JsonResponse({
            'success': True,
            'exam': exam_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


# Add this view to your main exams/views.py

@login_required
def admin_exam_detail(request, exam_id):
    """Admin view for detailed exam information"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Get exam statistics
    total_attempts = ExamAttempt.objects.filter(exam=exam).count()
    submitted_attempts = ExamAttempt.objects.filter(
        exam=exam, 
        status__in=['submitted', 'auto_submitted']
    ).count()
    pending_grading = ExamAttempt.objects.filter(
        exam=exam,
        is_graded=False,
        status__in=['submitted', 'auto_submitted']
    ).count()
    
    # Get recent attempts
    recent_attempts = ExamAttempt.objects.filter(exam=exam).select_related(
        'student'
    ).order_by('-started_at')[:10]
    
    # Get exam questions based on type
    questions = []
    if exam.exam_type == 'mcq':
        questions = exam.mcq_questions.filter(is_active=True).prefetch_related('options').order_by('order')
    elif exam.exam_type == 'qa':
        questions = exam.qa_questions.filter(is_active=True).order_by('order')
    elif exam.exam_type == 'assignment':
        try:
            assignment_details = exam.assignment_details
        except:
            assignment_details = None
    
    # Get assignments for this exam
    exam_assignments = ExamAssignment.objects.filter(
        exam=exam,
        is_active=True
    ).select_related('student', 'batch', 'course', 'assigned_by')
    
    # Calculate pass/fail statistics
    graded_attempts = ExamAttempt.objects.filter(exam=exam, is_graded=True)
    passed_attempts = graded_attempts.filter(is_passed=True).count()
    failed_attempts = graded_attempts.filter(is_passed=False).count()
    
    # Average score
    if graded_attempts.exists():
        avg_score = graded_attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0
        avg_score = round(avg_score, 2)
    else:
        avg_score = 0
    
    context = {
        'exam': exam,
        'questions': questions,
        'total_attempts': total_attempts,
        'submitted_attempts': submitted_attempts,
        'pending_grading': pending_grading,
        'recent_attempts': recent_attempts,
        'exam_assignments': exam_assignments,
        'passed_attempts': passed_attempts,
        'failed_attempts': failed_attempts,
        'avg_score': avg_score,
    }
    
    if exam.exam_type == 'assignment':
        context['assignment_details'] = assignment_details if 'assignment_details' in locals() else None
    
    return render(request, 'exam/admin_exam_detail.html', context)


# Update your existing assign_exam view to handle the form properly
# views.py - Fixed version


# views.py - Fixed version
from django.contrib.auth import get_user_model

# Get the custom User model
User = get_user_model()

@login_required 
def assign_exam(request):
    """Enhanced assign exam view with better data loading"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    if request.method == 'POST':
        exam_id = request.POST.get('exam_id')
        assignment_type = request.POST.get('assignment_type')
        custom_start = request.POST.get('custom_start_datetime')
        custom_end = request.POST.get('custom_end_datetime')
        
        if not exam_id or not assignment_type:
            messages.error(request, 'Please select an exam and assignment type!')
            return redirect('assign_exam')
        
        exam = get_object_or_404(Exam, id=exam_id)
        
        # Parse custom datetime if provided
        custom_start_datetime = None
        custom_end_datetime = None
        
        if custom_start:
            try:
                from datetime import datetime
                custom_start_datetime = datetime.fromisoformat(custom_start.replace('T', ' '))
            except ValueError:
                messages.error(request, 'Invalid start date format!')
                return redirect('assign_exam')
        
        if custom_end:
            try:
                from datetime import datetime  
                custom_end_datetime = datetime.fromisoformat(custom_end.replace('T', ' '))
            except ValueError:
                messages.error(request, 'Invalid end date format!')
                return redirect('assign_exam')
        
        assigned_count = 0
        
        if assignment_type == 'individual':
            selected_students = request.POST.getlist('selected_students')
            
            for student_id in selected_students:
                try:
                    student = User.objects.get(id=student_id, role='student')
                    
                    assignment, created = ExamAssignment.objects.get_or_create(
                        exam=exam,
                        assignment_type='individual',
                        student=student,
                        defaults={
                            'assigned_by': request.user,
                            'custom_start_datetime': custom_start_datetime,
                            'custom_end_datetime': custom_end_datetime,
                        }
                    )
                    
                    if created:
                        assigned_count += 1
                    elif not assignment.is_active:
                        # Reactivate if it was previously deactivated
                        assignment.is_active = True
                        assignment.custom_start_datetime = custom_start_datetime
                        assignment.custom_end_datetime = custom_end_datetime
                        assignment.save()
                        assigned_count += 1
                        
                except User.DoesNotExist:
                    continue
            
            messages.success(request, f'Exam assigned to {assigned_count} students!')
        
        elif assignment_type == 'batch' and Batch is not None:
            selected_batches = request.POST.getlist('selected_batches')
            
            for batch_id in selected_batches:
                try:
                    batch = Batch.objects.get(id=batch_id)
                    
                    assignment, created = ExamAssignment.objects.get_or_create(
                        exam=exam,
                        assignment_type='batch',
                        batch=batch,
                        defaults={
                            'assigned_by': request.user,
                            'custom_start_datetime': custom_start_datetime,
                            'custom_end_datetime': custom_end_datetime,
                        }
                    )
                    
                    if created:
                        assigned_count += 1
                    elif not assignment.is_active:
                        assignment.is_active = True
                        assignment.custom_start_datetime = custom_start_datetime
                        assignment.custom_end_datetime = custom_end_datetime
                        assignment.save()
                        assigned_count += 1
                        
                except:
                    continue
            
            messages.success(request, f'Exam assigned to {assigned_count} batches!')
        
        elif assignment_type == 'course' and Course is not None:
            selected_courses = request.POST.getlist('selected_courses')
            
            for course_id in selected_courses:
                try:
                    course = Course.objects.get(id=course_id)
                    
                    assignment, created = ExamAssignment.objects.get_or_create(
                        exam=exam,
                        assignment_type='course',
                        course=course,
                        defaults={
                            'assigned_by': request.user,
                            'custom_start_datetime': custom_start_datetime,
                            'custom_end_datetime': custom_end_datetime,
                        }
                    )
                    
                    if created:
                        assigned_count += 1
                    elif not assignment.is_active:
                        assignment.is_active = True
                        assignment.custom_start_datetime = custom_start_datetime
                        assignment.custom_end_datetime = custom_end_datetime
                        assignment.save()
                        assigned_count += 1
                        
                except:
                    continue
            
            messages.success(request, f'Exam assigned to {assigned_count} courses!')
        
        return redirect('assign_exam')
    
    # GET request - show assignment form with all data
    try:
        # Get all published exams
        exams = Exam.objects.filter(
            status='published', 
            is_active=True
        ).select_related('created_by').order_by('-created_at')
        
        print(f"Found {exams.count()} exams")  # Debug
        
        # Get all active students with their profiles
        students = User.objects.filter(
            role='student', 
            is_active=True
        ).order_by('first_name', 'last_name', 'username')
        
        print(f"Found {students.count()} students")  # Debug
        
        # Handle courses models with fallback
        if Batch is not None and Course is not None:
            # Get all active batches with course and instructor info
            batches = Batch.objects.filter(
                is_active=True
            ).select_related('course', 'instructor').order_by('course__title', 'name')
            
            print(f"Found {batches.count()} batches")  # Debug
            
            # Get all active courses
            courses = Course.objects.filter(
                is_active=True
            ).select_related('instructor').order_by('title')
            
            # If courses have status field
            try:
                courses = courses.filter(status='published')
            except:
                pass  # Status field might not exist
            
            print(f"Found {courses.count()} courses")  # Debug
        else:
            print("Courses app not available - using empty querysets")
            batches = []
            courses = []
        
        # Recent assignments
        recent_assignments = ExamAssignment.objects.select_related(
            'exam', 'student', 'batch', 'course', 'assigned_by'
        ).order_by('-assigned_at')[:10]
        
        print(f"Found {recent_assignments.count()} recent assignments")  # Debug
        
    except Exception as e:
        print(f"Error loading data: {e}")
        import traceback
        traceback.print_exc()
        
        # Provide empty querysets as fallback
        exams = Exam.objects.none()
        students = User.objects.none()
        batches = []
        courses = []
        recent_assignments = ExamAssignment.objects.none()
        
        messages.error(request, f'Error loading data: {str(e)}')
    
    context = {
        'exams': exams,
        'students': students,
        'batches': batches,
        'courses': courses,
        'recent_assignments': recent_assignments,
    }
    
    # Debug context
    print("Context data:")
    for key, value in context.items():
        if hasattr(value, 'count'):
            print(f"  {key}: {value.count()} items")
        elif isinstance(value, list):
            print(f"  {key}: {len(value)} items")
        else:
            print(f"  {key}: {type(value)}")
    
    return render(request, 'exam/assign_exam.html', context)


@login_required
def exam_submissions(request):
    """View all exam submissions and results"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    # Get filter parameters
    exam_filter = request.GET.get('exam')
    status_filter = request.GET.get('status')
    grading_filter = request.GET.get('grading')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    attempts = ExamAttempt.objects.select_related(
        'exam', 'student', 'graded_by'
    ).order_by('-started_at')
    
    # Apply filters
    if exam_filter:
        attempts = attempts.filter(exam_id=exam_filter)
    
    if status_filter:
        attempts = attempts.filter(status=status_filter)
    
    if grading_filter == 'graded':
        attempts = attempts.filter(is_graded=True)
    elif grading_filter == 'ungraded':
        attempts = attempts.filter(is_graded=False)
    
    if search_query:
        attempts = attempts.filter(
            Q(student__username__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(exam__title__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(attempts, 20)
    page = request.GET.get('page')
    attempts = paginator.get_page(page)
    
    # For dropdowns
    exams = Exam.objects.filter(status='published').order_by('title')
    
    # Statistics
    total_attempts = ExamAttempt.objects.count()
    pending_grading = ExamAttempt.objects.filter(
        is_graded=False,
        status__in=['submitted', 'auto_submitted']
    ).count()
    
    context = {
        'attempts': attempts,
        'exams': exams,
        'exam_filter': exam_filter,
        'status_filter': status_filter,
        'grading_filter': grading_filter,
        'search_query': search_query,
        'total_attempts': total_attempts,
        'pending_grading': pending_grading,
    }
    
    return render(request, 'exam/exam_submissions.html', context)


@login_required
def view_exam_attempt(request, attempt_id):
    """View detailed exam attempt"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    attempt = get_object_or_404(ExamAttempt, id=attempt_id)
    
    context = {
        'attempt': attempt,
    }
    
    if attempt.exam.exam_type == 'mcq':
        # Get MCQ responses
        mcq_responses = attempt.mcq_responses.select_related(
            'question', 'selected_option'
        ).order_by('question__order')
        context['mcq_responses'] = mcq_responses
        
    elif attempt.exam.exam_type == 'qa':
        # Get Q&A responses
        qa_responses = attempt.qa_responses.select_related(
            'question', 'graded_by'
        ).order_by('question__order')
        context['qa_responses'] = qa_responses
        
    else:  # assignment
        # Get assignment submission
        try:
            assignment_submission = attempt.assignment_submission
            context['assignment_submission'] = assignment_submission
        except AssignmentSubmission.DoesNotExist:
            context['assignment_submission'] = None
    
    return render(request, 'exams/view_exam_attempt.html', context)


# ==================== STUDENT EXAM VIEWS ====================
@login_required
def student_exams(request):
    """Student dashboard for assigned exams with debugging"""
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    print(f"\n=== DEBUG: Student Exams View for {request.user.username} ===")
    
    # Get assigned exams for this student
    assigned_exams = []
    
    # Individual assignments
    individual_assignments = ExamAssignment.objects.filter(
        assignment_type='individual',
        student=request.user,
        is_active=True
    ).select_related('exam')
    
    print(f"Individual assignments found: {individual_assignments.count()}")
    
    for assignment in individual_assignments:
        can_attempt_result = assignment.exam.can_student_attempt(request.user)
        print(f"  - Exam: {assignment.exam.title}")
        print(f"    Can attempt: {can_attempt_result}")
        print(f"    Allow retake: {assignment.exam.allow_retake}")
        print(f"    Max attempts: {assignment.exam.max_attempts}")
        
        assigned_exams.append({
            'exam': assignment.exam,
            'assignment': assignment,
            'can_attempt': can_attempt_result
        })
    
    # Batch assignments
    try:
        from courses.models import BatchEnrollment
        student_batches = BatchEnrollment.objects.filter(
            student=request.user,
            is_active=True
        ).values_list('batch_id', flat=True)
        
        print(f"Student batches: {list(student_batches)}")
        
        batch_assignments = ExamAssignment.objects.filter(
            assignment_type='batch',
            batch_id__in=student_batches,
            is_active=True
        ).select_related('exam')
        
        print(f"Batch assignments found: {batch_assignments.count()}")
        
        for assignment in batch_assignments:
            can_attempt_result = assignment.exam.can_student_attempt(request.user)
            print(f"  - Exam: {assignment.exam.title}")
            print(f"    Can attempt: {can_attempt_result}")
            print(f"    Allow retake: {assignment.exam.allow_retake}")
            print(f"    Max attempts: {assignment.exam.max_attempts}")
            
            assigned_exams.append({
                'exam': assignment.exam,
                'assignment': assignment,
                'can_attempt': can_attempt_result
            })
    except ImportError:
        print("BatchEnrollment model not available")
    
    # Course assignments
    try:
        from courses.models import Enrollment
        student_courses = Enrollment.objects.filter(
            student=request.user,
            is_active=True
        ).values_list('course_id', flat=True)
        
        print(f"Student courses: {list(student_courses)}")
        
        course_assignments = ExamAssignment.objects.filter(
            assignment_type='course',
            course_id__in=student_courses,
            is_active=True
        ).select_related('exam')
        
        print(f"Course assignments found: {course_assignments.count()}")
        
        for assignment in course_assignments:
            can_attempt_result = assignment.exam.can_student_attempt(request.user)
            print(f"  - Exam: {assignment.exam.title}")
            print(f"    Can attempt: {can_attempt_result}")
            print(f"    Allow retake: {assignment.exam.allow_retake}")
            print(f"    Max attempts: {assignment.exam.max_attempts}")
            
            assigned_exams.append({
                'exam': assignment.exam,
                'assignment': assignment,
                'can_attempt': can_attempt_result
            })
    except ImportError:
        print("Enrollment model not available")
    
    # Remove duplicates
    unique_exams = {}
    for item in assigned_exams:
        exam_id = item['exam'].id
        if exam_id not in unique_exams:
            unique_exams[exam_id] = item
    
    assigned_exams = list(unique_exams.values())
    print(f"Total unique exams after deduplication: {len(assigned_exams)}")
    
    # Get student's attempts
    student_attempts = ExamAttempt.objects.filter(
        student=request.user
    ).select_related('exam').order_by('-started_at')
    
    print(f"Total student attempts: {student_attempts.count()}")
    
    # Debug each attempt
    for attempt in student_attempts:
        print(f"  - Attempt: {attempt.exam.title} (Attempt #{attempt.attempt_number}, Status: {attempt.status})")
    
    # Separate into categories
    upcoming_exams = []
    available_exams = []
    completed_exams = []
    
    print(f"\n=== CATEGORIZING EXAMS ===")
    
    for item in assigned_exams:
        exam = item['exam']
        attempts = student_attempts.filter(exam=exam)
        
        print(f"\nExam: {exam.title}")
        print(f"  - Attempts count: {attempts.count()}")
        print(f"  - Allow retake: {exam.allow_retake}")
        print(f"  - Max attempts: {exam.max_attempts}")
        print(f"  - Status: {exam.status}")
        print(f"  - Is active: {exam.is_active}")
        print(f"  - Start datetime: {exam.start_datetime}")
        print(f"  - End datetime: {exam.end_datetime}")
        
        if attempts.exists():
            # Has attempts
            latest_attempt = attempts.first()
            item['latest_attempt'] = latest_attempt
            item['attempt_count'] = attempts.count()
            item['max_attempts'] = exam.max_attempts
            
            print(f"  - Latest attempt: #{latest_attempt.attempt_number}, Status: {latest_attempt.status}")
            
            # Check if student can still attempt (retakes allowed)
            can_attempt, message = item['can_attempt']
            print(f"  - Can attempt result: {can_attempt}, Message: {message}")
            
            # NEW LOGIC: Check retake eligibility separately
            can_retake = (
                exam.allow_retake and 
                attempts.count() < exam.max_attempts and
                not attempts.filter(status='in_progress').exists() and
                exam.is_active and
                exam.status == 'published'
            )
            
            # Check timing constraints for retake
            from django.utils import timezone
            now = timezone.now()
            timing_ok = True
            timing_message = ""
            
            if exam.start_datetime and now < exam.start_datetime:
                timing_ok = False
                timing_message = f'Exam starts at {exam.start_datetime.strftime("%Y-%m-%d %H:%M")}'
            elif exam.end_datetime and now > exam.end_datetime:
                timing_ok = False
                timing_message = 'Exam period has ended'
            
            print(f"  - Can retake (rules): {can_retake}")
            print(f"  - Timing OK: {timing_ok}")
            
            if can_retake and timing_ok:
                # Can retake - show in available
                item['is_retake'] = True
                available_exams.append(item)
                print(f"  -> Added to AVAILABLE (retake)")
            elif can_attempt and timing_ok:
                # Can attempt based on original logic
                item['is_retake'] = attempts.count() > 0
                available_exams.append(item)
                print(f"  -> Added to AVAILABLE (original logic)")
            else:
                # Cannot retake - show in completed
                item['is_retake'] = False
                if not timing_ok:
                    item['availability_message'] = timing_message
                completed_exams.append(item)
                print(f"  -> Added to COMPLETED (no retake - {timing_message if not timing_ok else 'rules'})")
        else:
            # No attempts yet
            can_attempt, message = item['can_attempt']
            print(f"  - Can attempt result: {can_attempt}, Message: {message}")
            
            item['attempt_count'] = 0
            item['max_attempts'] = exam.max_attempts
            
            if can_attempt:
                # First time attempt
                item['is_retake'] = False
                available_exams.append(item)
                print(f"  -> Added to AVAILABLE (first time)")
            else:
                # Not yet available (timing restrictions)
                item['is_retake'] = False
                item['availability_message'] = message
                upcoming_exams.append(item)
                print(f"  -> Added to UPCOMING ({message})")
    
    # NEW: Get ALL completed attempts for history section (individual rows per attempt)
    completed_attempts = []
    assigned_exam_ids = [item['exam'].id for item in assigned_exams]
    
    # Get all attempts for assigned exams, ordered by exam and then by attempt number
    all_student_attempts = ExamAttempt.objects.filter(
        student=request.user,
        exam_id__in=assigned_exam_ids
    ).select_related('exam').order_by('exam__title', 'attempt_number')
    
    for attempt in all_student_attempts:
        completed_attempts.append({
            'exam': attempt.exam,
            'attempt': attempt,
            'attempt_number': attempt.attempt_number,
            'status': attempt.status,
            'submitted_at': attempt.submitted_at,
            'started_at': attempt.started_at,
            'total_marks_obtained': attempt.total_marks_obtained,
            'percentage': attempt.percentage,
            'is_graded': attempt.is_graded,
            'is_passed': attempt.is_passed,
        })
    
    print(f"\n=== FINAL COUNTS ===")
    print(f"Available exams: {len(available_exams)}")
    print(f"Completed exams: {len(completed_exams)}")
    print(f"Upcoming exams: {len(upcoming_exams)}")
    print(f"Completed attempts: {len(completed_attempts)}")
    
    # Print details for available exams
    print(f"\n=== AVAILABLE EXAMS DETAILS ===")
    for item in available_exams:
        print(f"- {item['exam'].title} (Retake: {item.get('is_retake', False)}, Attempts: {item.get('attempt_count', 0)}/{item.get('max_attempts', 1)})")
    
    # Print completed attempts
    print(f"\n=== ALL COMPLETED ATTEMPTS DETAILS ===")
    for item in completed_attempts:
        print(f"- {item['exam'].title} - Attempt #{item['attempt_number']} - Status: {item['status']} - Score: {item.get('total_marks_obtained', 'N/A')}")
    
    context = {
        'upcoming_exams': upcoming_exams,
        'available_exams': available_exams,
        'completed_exams': completed_exams,
        'completed_attempts': completed_attempts,  # NEW: All previous attempts history
        'student_attempts': student_attempts,
        'total_assigned': len(assigned_exams),
        'total_completed': len([item for item in completed_exams if item.get('attempt_count', 0) > 0]),
        'total_available': len(available_exams),
        'total_upcoming': len(upcoming_exams),
    }
    
    return render(request, 'exam/student_exams.html', context)


@login_required
def take_exam(request, exam_id):
    """Start taking an exam"""
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Check if student can attempt this exam
    can_attempt, message = exam.can_student_attempt(request.user)
    if not can_attempt:
        messages.error(request, message)
        return redirect('student_exams')
    
    # Check if student has an ongoing attempt
    ongoing_attempt = ExamAttempt.objects.filter(
        exam=exam,
        student=request.user,
        status__in=['started', 'in_progress']
    ).first()
    
    if ongoing_attempt:
        # Resume existing attempt
        return redirect('exam_interface', attempt_id=ongoing_attempt.id)
    
    # Create new attempt
    attempt_number = ExamAttempt.objects.filter(
        exam=exam,
        student=request.user
    ).count() + 1
    
    attempt = ExamAttempt.objects.create(
        exam=exam,
        student=request.user,
        attempt_number=attempt_number,
        status='started',
        exam_config={
            'title': exam.title,
            'total_marks': exam.total_marks,
            'timing_type': exam.timing_type,
            'time_per_question_minutes': exam.time_per_question_minutes,
            'total_exam_time_minutes': exam.total_exam_time_minutes,
        }
    )
    
    return redirect('exam_interface', attempt_id=attempt.id)


@login_required
def exam_interface(request, attempt_id):
    """Main exam taking interface"""
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)
    
    # Check if attempt is still active
    if attempt.status not in ['started', 'in_progress']:
        messages.error(request, 'This exam attempt has been completed.')
        return redirect('student_exams')
    
    exam = attempt.exam
    
    # Update status to in_progress if just started
    if attempt.status == 'started':
        attempt.status = 'in_progress'
        attempt.save()
    
    context = {
        'attempt': attempt,
        'exam': exam,
    }
    
    if exam.exam_type == 'mcq':
        # Get MCQ questions
        if exam.randomize_questions:
            # If randomization is enabled, use random ordering
            questions = exam.mcq_questions.filter(is_active=True).prefetch_related('options').order_by('?')
        else:
            # Use original order
            questions = exam.mcq_questions.filter(is_active=True).prefetch_related('options').order_by('order')
        
        # Convert to list for easier manipulation
        questions_list = list(questions)
        
        # Randomize options if enabled
        if exam.randomize_options:
            import random
            for question in questions_list:
                # Get all options for this question
                options = list(question.options.all())
                # Shuffle the options
                random.shuffle(options)
                # Assign shuffled options back to question
                question.shuffled_options = options
        else:
            # Keep original order
            for question in questions_list:
                question.shuffled_options = question.options.all().order_by('order')
        
        # Get existing responses
        responses = {}
        for response in attempt.mcq_responses.all():
            responses[response.question.id] = response.selected_option.id if response.selected_option else None
        
        context.update({
            'questions': questions_list,
            'responses': responses,
            'total_questions': len(questions_list),
        })
        
        return render(request, 'exam/mcq_interface.html', context)
    
    elif exam.exam_type == 'qa':
        # Get Q&A questions
        if exam.randomize_questions:
            questions = exam.qa_questions.filter(is_active=True).order_by('?')
        else:
            questions = exam.qa_questions.filter(is_active=True).order_by('order')
        
        # Convert to list
        questions_list = list(questions)
        
        # Get existing responses
        responses = {}
        for response in attempt.qa_responses.all():
            responses[response.question.id] = response.answer_text
        
        context.update({
            'questions': questions_list,
            'responses': responses,
            'total_questions': len(questions_list),
        })
        
        return render(request, 'exam/qa_interface.html', context)
    
    else:  # assignment
        # Get assignment details
        assignment_details = exam.assignment_details
        
        # Get existing submission
        try:
            submission = attempt.assignment_submission
        except AssignmentSubmission.DoesNotExist:
            submission = None
        
        context.update({
            'assignment_details': assignment_details,
            'submission': submission,
        })
        
        return render(request, 'exam/assignment_interface.html', context)

@login_required
@require_http_methods(["POST"])
def save_mcq_response(request, attempt_id):
    """Save MCQ response via AJAX"""
    if request.user.role != 'student':
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)
    
    if attempt.status not in ['started', 'in_progress']:
        return JsonResponse({'success': False, 'message': 'Exam attempt not active'})
    
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        option_id = data.get('option_id')
        
        question = get_object_or_404(MCQQuestion, id=question_id, exam=attempt.exam)
        option = get_object_or_404(MCQOption, id=option_id, question=question) if option_id else None
        
        # Save or update response
        response, created = MCQResponse.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={'selected_option': option}
        )
        
        return JsonResponse({'success': True, 'message': 'Response saved'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_http_methods(["POST"])
def save_qa_response(request, attempt_id):
    """Save Q&A response via AJAX"""
    if request.user.role != 'student':
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)
    
    if attempt.status not in ['started', 'in_progress']:
        return JsonResponse({'success': False, 'message': 'Exam attempt not active'})
    
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        answer_text = data.get('answer_text', '')
        
        question = get_object_or_404(QAQuestion, id=question_id, exam=attempt.exam)
        
        # Save or update response
        response, created = QAResponse.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={'answer_text': answer_text}
        )
        
        return JsonResponse({'success': True, 'message': 'Response saved'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def submit_exam(request, attempt_id):
    """Submit exam attempt"""
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)
    
    if attempt.status not in ['started', 'in_progress']:
        messages.error(request, 'This exam attempt has already been submitted.')
        return redirect('student_exams')
    
    if request.method == 'POST':
        # Submit the exam
        attempt.status = 'submitted'
        attempt.submitted_at = timezone.now()
        attempt.save()
        
        # Calculate marks for MCQ exams
        if attempt.exam.exam_type == 'mcq':
            attempt.calculate_mcq_marks()
        
        messages.success(request, 'Exam submitted successfully!')
        
        if attempt.exam.show_results_immediately and attempt.exam.exam_type == 'mcq':
            return redirect('exam_result', attempt_id=attempt.id)
        else:
            return redirect('student_exams')
    
    # GET request - show confirmation page
    context = {
        'attempt': attempt,
    }
    
    return render(request, 'exam/submit_exam.html', context)


@login_required
def exam_result(request, attempt_id):
    """View exam result"""
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)
    
    if attempt.status not in ['submitted', 'auto_submitted']:
        messages.error(request, 'Exam not completed yet.')
        return redirect('student_exams')
    
    context = {
        'attempt': attempt,
    }
    
    if attempt.exam.exam_type == 'mcq':
        # Get MCQ responses with correct answers
        mcq_responses = attempt.mcq_responses.select_related(
            'question', 'selected_option'
        ).order_by('question__order')
        
        # Add correct answer info
        for response in mcq_responses:
            response.correct_option = response.question.get_correct_answer()
            response.is_correct_answer = response.is_correct()
        
        context['mcq_responses'] = mcq_responses
    
    return render(request, 'exam/exam_result.html', context)


# ==================== GRADING VIEWS ====================

@login_required
def pending_grading(request):
    """View exams pending manual grading"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    # Get Q&A and Assignment attempts that need grading
    qa_attempts = ExamAttempt.objects.filter(
        exam__exam_type='qa',
        status__in=['submitted', 'auto_submitted'],
        is_graded=False
    ).select_related('exam', 'student').order_by('-submitted_at')
    
    assignment_attempts = ExamAttempt.objects.filter(
        exam__exam_type='assignment',
        status__in=['submitted', 'auto_submitted'],
        is_graded=False
    ).select_related('exam', 'student').order_by('-submitted_at')
    
    context = {
        'qa_attempts': qa_attempts,
        'assignment_attempts': assignment_attempts,
        'total_pending': qa_attempts.count() + assignment_attempts.count(),
    }
    
    return render(request, 'exam/pending_grading.html', context)


@login_required
def grade_qa_attempt(request, attempt_id):
    """Grade Q&A exam attempt"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, exam__exam_type='qa')
    
    if request.method == 'POST':
        total_marks = 0
        all_graded = True
        
        # Process each Q&A response
        for response in attempt.qa_responses.all():
            form_data = {
                'marks_obtained': request.POST.get(f'marks_{response.id}'),
                'feedback': request.POST.get(f'feedback_{response.id}', '')
            }
            
            form = QAGradingForm(form_data, instance=response)
            if form.is_valid():
                graded_response = form.save(commit=False)
                graded_response.is_graded = True
                graded_response.graded_at = timezone.now()
                graded_response.graded_by = request.user
                graded_response.save()
                
                total_marks += float(graded_response.marks_obtained)
            else:
                all_graded = False
        
        if all_graded:
            # Update attempt
            attempt.total_marks_obtained = total_marks
            attempt.calculate_percentage()
            attempt.is_graded = True
            attempt.graded_at = timezone.now()
            attempt.graded_by = request.user
            attempt.save()
            
            messages.success(request, 'Exam graded successfully!')
            return redirect('pending_grading')
        else:
            messages.error(request, 'Please complete grading for all questions.')
    
    # Get Q&A responses
    qa_responses = attempt.qa_responses.select_related('question').order_by('question__order')
    
    # Create forms for each response
    response_forms = []
    for response in qa_responses:
        form = QAGradingForm(instance=response)
        response_forms.append({
            'response': response,
            'form': form
        })
    
    context = {
        'attempt': attempt,
        'response_forms': response_forms,
    }
    
    return render(request, 'exam/grade_qa_attempt.html', context)


@login_required
def grade_assignment_attempt(request, attempt_id):
    """Grade assignment attempt"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, exam__exam_type='assignment')
    
    try:
        submission = attempt.assignment_submission
    except AssignmentSubmission.DoesNotExist:
        messages.error(request, 'No submission found for this attempt.')
        return redirect('pending_grading')
    
    if request.method == 'POST':
        form = AssignmentGradingForm(request.POST, instance=submission)
        if form.is_valid():
            graded_submission = form.save(commit=False)
            graded_submission.is_graded = True
            graded_submission.graded_at = timezone.now()
            graded_submission.graded_by = request.user
            graded_submission.save()
            
            # Update attempt
            attempt.total_marks_obtained = float(graded_submission.marks_obtained)
            attempt.calculate_percentage()
            attempt.is_graded = True
            attempt.graded_at = timezone.now()
            attempt.graded_by = request.user
            attempt.save()
            
            messages.success(request, 'Assignment graded successfully!')
            return redirect('pending_grading')
    else:
        form = AssignmentGradingForm(instance=submission)
    
    context = {
        'attempt': attempt,
        'submission': submission,
        'form': form,
    }
    
    return render(request, 'exam/grade_assignment_attempt.html', context)


# ==================== UTILITY VIEWS ====================



@login_required
def delete_exam(request, exam_id):
    """Delete exam"""
    if request.user.role != 'superadmin':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        exam_title = exam.title
        exam.delete()
        messages.success(request, f'Exam "{exam_title}" deleted successfully!')
        return redirect('exam_dashboard')
    
    context = {
        'exam': exam,
        'total_attempts': exam.attempts.count(),
    }
    
    return render(request, 'exam/delete_exam.html', context)


@login_required
def get_batch_students_for_exam(request, batch_id):
    """AJAX endpoint to get students in a batch for exam assignment"""
    if request.user.role != 'superadmin':
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    try:
        batch = get_object_or_404(Batch, id=batch_id)
        
        from courses.models import BatchEnrollment
        students = CustomUser.objects.filter(
            role='student',
            batch_enrollments__batch=batch,
            batch_enrollments__is_active=True,
            is_active=True
        ).distinct().values('id', 'username', 'first_name', 'last_name', 'email')
        
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
            'total_count': len(students_list)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def get_course_students_for_exam(request, course_id):
    """AJAX endpoint to get students in a course for exam assignment"""
    if request.user.role != 'superadmin':
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    try:
        course = get_object_or_404(Course, id=course_id)
        
        from courses.models import Enrollment
        students = CustomUser.objects.filter(
            role='student',
            enrollments__course=course,
            enrollments__is_active=True,
            is_active=True
        ).distinct().values('id', 'username', 'first_name', 'last_name', 'email')
        
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
            'total_count': len(students_list)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
    



# instructor view 
# instructor view 
# instructor view 
# instructor view 
# instructor view 
# instructor view 
# instructor view 
# instructor view 
# instructor view 
# instructor view 


# exams/instructor_views.py - Instructor-specific exam management views

 # exams/instructor_views.py - Instructor-specific exam management views

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from datetime import timedelta

from .models import (
    Exam, MCQQuestion, MCQOption, QAQuestion, AssignmentExam,
    ExamAssignment, ExamAttempt, MCQResponse, QAResponse, 
    AssignmentSubmission
)
from .forms import (
    ExamForm, MCQQuestionForm, QAQuestionForm,
    AssignmentExamForm, ExamAssignmentForm, QuickMCQForm
)

# Import course models safely
try:
    from courses.models import Course, Batch, Enrollment, BatchEnrollment
except ImportError:
    Course = None
    Batch = None
    Enrollment = None
    BatchEnrollment = None

User = get_user_model()

@login_required
def instructor_exam_dashboard(request):
    """Instructor exam dashboard showing overview of their exams"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    # Get instructor's exams
    instructor_exams = Exam.objects.filter(created_by=request.user)
    
    # Statistics for instructor
    total_exams = instructor_exams.count()
    published_exams = instructor_exams.filter(status='published').count()
    draft_exams = instructor_exams.filter(status='draft').count()
    
    # Get total attempts on instructor's exams
    total_attempts = ExamAttempt.objects.filter(exam__created_by=request.user).count()
    
    # Pending grading for instructor's exams
    pending_grading = ExamAttempt.objects.filter(
        exam__created_by=request.user,
        is_graded=False,
        status__in=['submitted', 'auto_submitted']
    ).count()
    
    # Recent exams created by instructor
    recent_exams = instructor_exams.order_by('-created_at')[:5]
    
    # Recent attempts on instructor's exams
    recent_attempts = ExamAttempt.objects.filter(
        exam__created_by=request.user
    ).select_related('exam', 'student').order_by('-started_at')[:10]
    
    # Exam type distribution for instructor
    exam_types = instructor_exams.values('exam_type').annotate(
        count=Count('id')
    ).order_by('exam_type')
    
    context = {
        'total_exams': total_exams,
        'published_exams': published_exams,
        'draft_exams': draft_exams,
        'total_attempts': total_attempts,
        'pending_grading': pending_grading,
        'recent_exams': recent_exams,
        'recent_attempts': recent_attempts,
        'exam_types': exam_types,
    }
    
    return render(request, 'exam/instructor/dashboard.html', context)


@login_required
def instructor_create_exam(request):
    """Create new exam for instructor"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.save()
            
            messages.success(request, f'Exam "{exam.title}" created successfully!')
            
            # Redirect based on exam type
            if exam.exam_type == 'mcq':
                return redirect('instructor_add_mcq_questions', exam_id=exam.id)
            elif exam.exam_type == 'qa':
                return redirect('instructor_add_qa_questions', exam_id=exam.id)
            else:  # assignment
                return redirect('instructor_setup_assignment', exam_id=exam.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ExamForm()
    
    context = {
        'form': form,
        'page_title': 'Create New Exam',
    }
    
    return render(request, 'exam/instructor/create_exam.html', context)


@login_required
def instructor_add_mcq_questions(request, exam_id):
    """Add MCQ questions to instructor's exam"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    exam = get_object_or_404(Exam, id=exam_id, exam_type='mcq', created_by=request.user)
    
    if request.method == 'POST':
        if 'quick_add' in request.POST:
            # Quick add form
            quick_form = QuickMCQForm(request.POST)
            if quick_form.is_valid():
                # Create question
                question = MCQQuestion.objects.create(
                    exam=exam,
                    question_text=quick_form.cleaned_data['question_text'],
                    marks=quick_form.cleaned_data['marks'],
                    explanation=quick_form.cleaned_data.get('explanation', ''),
                    order=exam.mcq_questions.count() + 1
                )
                
                # Create options
                options_data = [
                    (quick_form.cleaned_data['option_1'], quick_form.cleaned_data['correct_option'] == '1'),
                    (quick_form.cleaned_data['option_2'], quick_form.cleaned_data['correct_option'] == '2'),
                ]
                
                if quick_form.cleaned_data.get('option_3'):
                    options_data.append((
                        quick_form.cleaned_data['option_3'], 
                        quick_form.cleaned_data['correct_option'] == '3'
                    ))
                
                if quick_form.cleaned_data.get('option_4'):
                    options_data.append((
                        quick_form.cleaned_data['option_4'], 
                        quick_form.cleaned_data['correct_option'] == '4'
                    ))
                
                for i, (option_text, is_correct) in enumerate(options_data, 1):
                    MCQOption.objects.create(
                        question=question,
                        option_text=option_text,
                        is_correct=is_correct,
                        order=i
                    )
                
                messages.success(request, 'Question added successfully!')
                return redirect('instructor_add_mcq_questions', exam_id=exam.id)
        
        elif 'finish_exam' in request.POST:
            if exam.mcq_questions.count() > 0:
                exam.status = 'published'
                exam.save()
                messages.success(request, f'Exam "{exam.title}" published successfully!')
                return redirect('instructor_exam_dashboard')
            else:
                messages.error(request, 'Please add at least one question before publishing.')
    
    # Get existing questions
    questions = exam.mcq_questions.filter(is_active=True).prefetch_related('options').order_by('order')
    quick_form = QuickMCQForm()
    
    context = {
        'exam': exam,
        'questions': questions,
        'quick_form': quick_form,
        'total_questions': questions.count(),
    }
    
    return render(request, 'exam/instructor/add_mcq_questions.html', context)


@login_required
def instructor_add_qa_questions(request, exam_id):
    """Add Q&A questions to instructor's exam"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    exam = get_object_or_404(Exam, id=exam_id, exam_type='qa', created_by=request.user)
    
    if request.method == 'POST':
        if 'add_question' in request.POST:
            form = QAQuestionForm(request.POST, request.FILES)
            if form.is_valid():
                question = form.save(commit=False)
                question.exam = exam
                question.order = exam.qa_questions.count() + 1
                question.save()
                
                messages.success(request, 'Question added successfully!')
                return redirect('instructor_add_qa_questions', exam_id=exam.id)
        
        elif 'finish_exam' in request.POST:
            if exam.qa_questions.count() > 0:
                exam.status = 'published'
                exam.save()
                messages.success(request, f'Exam "{exam.title}" published successfully!')
                return redirect('instructor_exam_dashboard')
            else:
                messages.error(request, 'Please add at least one question before publishing.')
    
    # Get existing questions
    questions = exam.qa_questions.filter(is_active=True).order_by('order')
    form = QAQuestionForm()
    
    context = {
        'exam': exam,
        'questions': questions,
        'form': form,
        'total_questions': questions.count(),
    }
    
    return render(request, 'exam/instructor/add_qa_questions.html', context)


@login_required
def instructor_setup_assignment(request, exam_id):
    """Setup assignment exam details for instructor"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    exam = get_object_or_404(Exam, id=exam_id, exam_type='assignment', created_by=request.user)
    
    try:
        assignment = exam.assignment_details
    except AssignmentExam.DoesNotExist:
        assignment = None
    
    if request.method == 'POST':
        form = AssignmentExamForm(request.POST, instance=assignment)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.exam = exam
            assignment.save()
            
            exam.status = 'published'
            exam.save()
            
            messages.success(request, f'Assignment exam "{exam.title}" published successfully!')
            return redirect('instructor_exam_dashboard')
    else:
        form = AssignmentExamForm(instance=assignment)
    
    context = {
        'exam': exam,
        'form': form,
        'assignment': assignment,
    }
    
    return render(request, 'exam/instructor/setup_assignment.html', context)


@login_required
def instructor_my_exams(request):
    """View all exams - created by instructor + assigned to instructor's students/batches/courses"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    # Get filter parameters
    exam_type_filter = request.GET.get('exam_type')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search', '')
    exam_source_filter = request.GET.get('source', 'all')  # all, created, assigned
    
    # Get instructor's created exams
    created_exams = Exam.objects.filter(created_by=request.user)
    
    # Get exams assigned to instructor's students/batches/courses
    assigned_exam_ids = set()
    
    if Batch and Course and BatchEnrollment and Enrollment:
        # Get exams assigned to instructor's batches
        instructor_batches = Batch.objects.filter(instructor=request.user)
        batch_assignments = ExamAssignment.objects.filter(
            assignment_type='batch',
            batch__in=instructor_batches,
            is_active=True
        ).values_list('exam_id', flat=True)
        assigned_exam_ids.update(batch_assignments)
        
        # Get exams assigned to instructor's courses
        instructor_courses = Course.objects.filter(instructor=request.user)
        course_assignments = ExamAssignment.objects.filter(
            assignment_type='course',
            course__in=instructor_courses,
            is_active=True
        ).values_list('exam_id', flat=True)
        assigned_exam_ids.update(course_assignments)
        
        # Get exams assigned to instructor's individual students
        instructor_students = get_instructor_students(request.user)
        individual_assignments = ExamAssignment.objects.filter(
            assignment_type='individual',
            student__in=instructor_students,
            is_active=True
        ).values_list('exam_id', flat=True)
        assigned_exam_ids.update(individual_assignments)
    
    # Combine exams based on filter
    if exam_source_filter == 'created':
        # Only created by instructor
        exams = created_exams
    elif exam_source_filter == 'assigned':
        # Only assigned to instructor
        exams = Exam.objects.filter(id__in=assigned_exam_ids).exclude(created_by=request.user)
    else:
        # All exams (created + assigned)
        all_exam_ids = set(created_exams.values_list('id', flat=True))
        all_exam_ids.update(assigned_exam_ids)
        exams = Exam.objects.filter(id__in=all_exam_ids)
    
    exams = exams.order_by('-created_at')
    
    # Apply filters
    if exam_type_filter:
        exams = exams.filter(exam_type=exam_type_filter)
    
    if status_filter:
        exams = exams.filter(status=status_filter)
    
    if search_query:
        exams = exams.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Add attempt counts and metadata
    exams_with_metadata = []
    for exam in exams:
        # Check if instructor created this exam
        is_creator = exam.created_by == request.user
        
        # Get attempt counts
        total_attempts = ExamAttempt.objects.filter(exam=exam).count()
        pending_grading = ExamAttempt.objects.filter(
            exam=exam,
            is_graded=False,
            status__in=['submitted', 'auto_submitted']
        ).count()
        
        # Get assignment info if not creator
        assignment_info = None
        if not is_creator:
            assignments = ExamAssignment.objects.filter(
                exam=exam,
                is_active=True
            ).select_related('batch', 'course', 'student')
            
            # Find which assignment relates to this instructor
            for assignment in assignments:
                if assignment.assignment_type == 'batch' and assignment.batch and assignment.batch.instructor == request.user:
                    assignment_info = f"Assigned to your batch: {assignment.batch.name}"
                    break
                elif assignment.assignment_type == 'course' and assignment.course and assignment.course.instructor == request.user:
                    assignment_info = f"Assigned to your course: {assignment.course.title}"
                    break
                elif assignment.assignment_type == 'individual' and assignment.student:
                    # Check if student is in instructor's batches/courses
                    if instructor_can_assign_to_student(request.user, assignment.student):
                        assignment_info = f"Assigned to your student: {assignment.student.get_full_name() or assignment.student.username}"
                        break
        
        exams_with_metadata.append({
            'exam': exam,
            'is_creator': is_creator,
            'total_attempts': total_attempts,
            'pending_grading': pending_grading,
            'assignment_info': assignment_info,
        })
    
    # Pagination
    paginator = Paginator(exams_with_metadata, 10)
    page = request.GET.get('page')
    exams_with_metadata = paginator.get_page(page)
    
    # Statistics
    total_created = created_exams.count()
    total_assigned = len(assigned_exam_ids) - created_exams.filter(id__in=assigned_exam_ids).count()
    
    context = {
        'exams': exams_with_metadata,
        'exam_type_filter': exam_type_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        'exam_source_filter': exam_source_filter,
        'exam_type_choices': Exam.EXAM_TYPE_CHOICES,
        'status_choices': Exam.STATUS_CHOICES,
        'total_created': total_created,
        'total_assigned': total_assigned,
    }
    
    return render(request, 'exam/instructor/my_exams.html', context)


@login_required
def instructor_assign_exam(request):
    """Assign instructor's exams to students/batches/courses"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    if request.method == 'POST':
        exam_id = request.POST.get('exam_id')
        assignment_type = request.POST.get('assignment_type')
        custom_start = request.POST.get('custom_start_datetime')
        custom_end = request.POST.get('custom_end_datetime')
        
        if not exam_id or not assignment_type:
            messages.error(request, 'Please select an exam and assignment type!')
            return redirect('instructor_assign_exam')
        
        # Ensure exam belongs to instructor
        exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
        
        # Parse custom datetime if provided
        custom_start_datetime = None
        custom_end_datetime = None
        
        if custom_start:
            try:
                from datetime import datetime
                custom_start_datetime = datetime.fromisoformat(custom_start.replace('T', ' '))
            except ValueError:
                messages.error(request, 'Invalid start date format!')
                return redirect('instructor_assign_exam')
        
        if custom_end:
            try:
                from datetime import datetime  
                custom_end_datetime = datetime.fromisoformat(custom_end.replace('T', ' '))
            except ValueError:
                messages.error(request, 'Invalid end date format!')
                return redirect('instructor_assign_exam')
        
        assigned_count = 0
        
        if assignment_type == 'individual':
            selected_students = request.POST.getlist('selected_students')
            
            for student_id in selected_students:
                try:
                    student = User.objects.get(id=student_id, role='student')
                    
                    # Check if student is in instructor's batches/courses
                    if not instructor_can_assign_to_student(request.user, student):
                        continue
                    
                    assignment, created = ExamAssignment.objects.get_or_create(
                        exam=exam,
                        assignment_type='individual',
                        student=student,
                        defaults={
                            'assigned_by': request.user,
                            'custom_start_datetime': custom_start_datetime,
                            'custom_end_datetime': custom_end_datetime,
                        }
                    )
                    
                    if created:
                        assigned_count += 1
                    elif not assignment.is_active:
                        assignment.is_active = True
                        assignment.custom_start_datetime = custom_start_datetime
                        assignment.custom_end_datetime = custom_end_datetime
                        assignment.save()
                        assigned_count += 1
                        
                except User.DoesNotExist:
                    continue
            
            messages.success(request, f'Exam assigned to {assigned_count} students!')
        
        elif assignment_type == 'batch' and Batch is not None:
            selected_batches = request.POST.getlist('selected_batches')
            
            for batch_id in selected_batches:
                try:
                    batch = Batch.objects.get(id=batch_id)
                    
                    # Check if batch belongs to instructor
                    if batch.instructor != request.user:
                        continue
                    
                    assignment, created = ExamAssignment.objects.get_or_create(
                        exam=exam,
                        assignment_type='batch',
                        batch=batch,
                        defaults={
                            'assigned_by': request.user,
                            'custom_start_datetime': custom_start_datetime,
                            'custom_end_datetime': custom_end_datetime,
                        }
                    )
                    
                    if created:
                        assigned_count += 1
                    elif not assignment.is_active:
                        assignment.is_active = True
                        assignment.custom_start_datetime = custom_start_datetime
                        assignment.custom_end_datetime = custom_end_datetime
                        assignment.save()
                        assigned_count += 1
                        
                except:
                    continue
            
            messages.success(request, f'Exam assigned to {assigned_count} batches!')
        
        elif assignment_type == 'course' and Course is not None:
            selected_courses = request.POST.getlist('selected_courses')
            
            for course_id in selected_courses:
                try:
                    course = Course.objects.get(id=course_id)
                    
                    # Check if course belongs to instructor
                    if course.instructor != request.user:
                        continue
                    
                    assignment, created = ExamAssignment.objects.get_or_create(
                        exam=exam,
                        assignment_type='course',
                        course=course,
                        defaults={
                            'assigned_by': request.user,
                            'custom_start_datetime': custom_start_datetime,
                            'custom_end_datetime': custom_end_datetime,
                        }
                    )
                    
                    if created:
                        assigned_count += 1
                    elif not assignment.is_active:
                        assignment.is_active = True
                        assignment.custom_start_datetime = custom_start_datetime
                        assignment.custom_end_datetime = custom_end_datetime
                        assignment.save()
                        assigned_count += 1
                        
                except:
                    continue
            
            messages.success(request, f'Exam assigned to {assigned_count} courses!')
        
        return redirect('instructor_assign_exam')
    
    # GET request - show assignment form with instructor's data only
    try:
        # Get only instructor's published exams
        exams = Exam.objects.filter(
            created_by=request.user,
            status='published', 
            is_active=True
        ).order_by('-created_at')
        
        # Get students from instructor's batches/courses
        students = get_instructor_students(request.user)
        
        # Get instructor's batches and courses
        if Batch is not None and Course is not None:
            batches = Batch.objects.filter(
                instructor=request.user,
                is_active=True
            ).select_related('course').order_by('course__title', 'name')
            
            courses = Course.objects.filter(
                instructor=request.user,
                is_active=True
            ).order_by('title')
        else:
            batches = []
            courses = []
        
        # Recent assignments by instructor
        recent_assignments = ExamAssignment.objects.filter(
            assigned_by=request.user
        ).select_related(
            'exam', 'student', 'batch', 'course'
        ).order_by('-assigned_at')[:10]
        
    except Exception as e:
        print(f"Error loading instructor data: {e}")
        exams = Exam.objects.none()
        students = User.objects.none()
        batches = []
        courses = []
        recent_assignments = ExamAssignment.objects.none()
        messages.error(request, f'Error loading data: {str(e)}')
    
    context = {
        'exams': exams,
        'students': students,
        'batches': batches,
        'courses': courses,
        'recent_assignments': recent_assignments,
    }
    
    return render(request, 'exam/instructor/assign_exam.html', context)


@login_required
def instructor_exam_submissions(request):
    """View submissions for instructor's exams"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    # Get filter parameters
    exam_filter = request.GET.get('exam')
    status_filter = request.GET.get('status')
    grading_filter = request.GET.get('grading')
    search_query = request.GET.get('search', '')
    
    # Base queryset - only instructor's exam attempts
    attempts = ExamAttempt.objects.filter(
        exam__created_by=request.user
    ).select_related('exam', 'student', 'graded_by').order_by('-started_at')
    
    # Apply filters
    if exam_filter:
        attempts = attempts.filter(exam_id=exam_filter)
    
    if status_filter:
        attempts = attempts.filter(status=status_filter)
    
    if grading_filter == 'graded':
        attempts = attempts.filter(is_graded=True)
    elif grading_filter == 'ungraded':
        attempts = attempts.filter(is_graded=False)
    
    if search_query:
        attempts = attempts.filter(
            Q(student__username__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(exam__title__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(attempts, 20)
    page = request.GET.get('page')
    attempts = paginator.get_page(page)
    
    # For dropdowns - only instructor's exams
    exams = Exam.objects.filter(
        created_by=request.user,
        status='published'
    ).order_by('title')
    
    # Statistics for instructor
    total_attempts = ExamAttempt.objects.filter(exam__created_by=request.user).count()
    pending_grading = ExamAttempt.objects.filter(
        exam__created_by=request.user,
        is_graded=False,
        status__in=['submitted', 'auto_submitted']
    ).count()
    
    context = {
        'attempts': attempts,
        'exams': exams,
        'exam_filter': exam_filter,
        'status_filter': status_filter,
        'grading_filter': grading_filter,
        'search_query': search_query,
        'total_attempts': total_attempts,
        'pending_grading': pending_grading,
    }
    
    return render(request, 'exam/instructor/exam_submissions.html', context)


@login_required
def instructor_view_exam_attempt(request, attempt_id):
    """View detailed exam attempt for instructor's exam"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    attempt = get_object_or_404(
        ExamAttempt, 
        id=attempt_id, 
        exam__created_by=request.user
    )
    
    context = {
        'attempt': attempt,
    }
    
    if attempt.exam.exam_type == 'mcq':
        # Get MCQ responses
        mcq_responses = attempt.mcq_responses.select_related(
            'question', 'selected_option'
        ).order_by('question__order')
        context['mcq_responses'] = mcq_responses
        
    elif attempt.exam.exam_type == 'qa':
        # Get Q&A responses
        qa_responses = attempt.qa_responses.select_related(
            'question', 'graded_by'
        ).order_by('question__order')
        context['qa_responses'] = qa_responses
        
    else:  # assignment
        # Get assignment submission
        try:
            assignment_submission = attempt.assignment_submission
            context['assignment_submission'] = assignment_submission
        except AssignmentSubmission.DoesNotExist:
            context['assignment_submission'] = None
    
    return render(request, 'exam/instructor/view_exam_attempt.html', context)


@login_required
def instructor_delete_exam(request, exam_id):
    """Delete instructor's exam"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
    
    if request.method == 'POST':
        exam_title = exam.title
        exam.delete()
        messages.success(request, f'Exam "{exam_title}" deleted successfully!')
        return redirect('instructor_my_exams')
    
    context = {
        'exam': exam,
        'total_attempts': exam.attempts.count(),
    }
    
    return render(request, 'exam/instructor/delete_exam.html', context)


# Helper functions
def instructor_can_assign_to_student(instructor, student):
    """Check if instructor can assign exam to student"""
    if not Batch or not Course or not BatchEnrollment or not Enrollment:
        return False
    
    # Check if student is in instructor's batches
    instructor_batches = Batch.objects.filter(instructor=instructor)
    student_in_batch = BatchEnrollment.objects.filter(
        student=student,
        batch__in=instructor_batches,
        is_active=True
    ).exists()
    
    # Check if student is enrolled in instructor's courses
    instructor_courses = Course.objects.filter(instructor=instructor)
    student_in_course = Enrollment.objects.filter(
        student=student,
        course__in=instructor_courses,
        is_active=True
    ).exists()
    
    return student_in_batch or student_in_course


def get_instructor_students(instructor):
    """Get all students assigned to instructor"""
    if not Batch or not Course or not BatchEnrollment or not Enrollment:
        return User.objects.none()
    
    # Get students from instructor's batches
    batch_students = User.objects.filter(
        role='student',
        batch_enrollments__batch__instructor=instructor,
        batch_enrollments__is_active=True,
        is_active=True
    ).distinct()
    
    # Get students from instructor's courses
    course_students = User.objects.filter(
        role='student',
        enrollments__course__instructor=instructor,
        enrollments__is_active=True,
        is_active=True
    ).distinct()
    
    # Combine and return unique students
    student_ids = set()
    for student in batch_students:
        student_ids.add(student.id)
    for student in course_students:
        student_ids.add(student.id)
    
    return User.objects.filter(
        id__in=student_ids,
        role='student',
        is_active=True
    ).order_by('first_name', 'last_name', 'username')



# Add this view to your instructor_views.py
# Add this view to your instructor_views.py

@login_required
def instructor_exam_detail(request, exam_id):
    """View detailed exam information for instructor"""
    if request.user.role != 'instructor':
        messages.error(request, 'Access denied.')
        return redirect('user_login')
    
    # Get exam - either created by instructor or assigned to instructor's students/batches/courses
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Check if instructor has access to this exam
    has_access = False
    is_creator = exam.created_by == request.user
    assignment_info = None
    
    if is_creator:
        has_access = True
    else:
        # Check if exam is assigned to instructor's students/batches/courses
        if Batch and Course and BatchEnrollment and Enrollment:
            # Check batch assignments
            instructor_batches = Batch.objects.filter(instructor=request.user)
            batch_assignments = ExamAssignment.objects.filter(
                exam=exam,
                assignment_type='batch',
                batch__in=instructor_batches,
                is_active=True
            ).first()
            
            if batch_assignments:
                has_access = True
                assignment_info = f"Assigned to your batch: {batch_assignments.batch.name}"
            
            # Check course assignments
            if not has_access:
                instructor_courses = Course.objects.filter(instructor=request.user)
                course_assignments = ExamAssignment.objects.filter(
                    exam=exam,
                    assignment_type='course',
                    course__in=instructor_courses,
                    is_active=True
                ).first()
                
                if course_assignments:
                    has_access = True
                    assignment_info = f"Assigned to your course: {course_assignments.course.title}"
            
            # Check individual student assignments
            if not has_access:
                instructor_students = get_instructor_students(request.user)
                individual_assignments = ExamAssignment.objects.filter(
                    exam=exam,
                    assignment_type='individual',
                    student__in=instructor_students,
                    is_active=True
                ).first()
                
                if individual_assignments:
                    has_access = True
                    assignment_info = f"Assigned to your student: {individual_assignments.student.get_full_name() or individual_assignments.student.username}"
    
    if not has_access:
        messages.error(request, 'You do not have access to this exam.')
        return redirect('instructor_my_exams')
    
    # Get exam statistics
    total_attempts = ExamAttempt.objects.filter(exam=exam).count()
    submitted_attempts = ExamAttempt.objects.filter(
        exam=exam, 
        status__in=['submitted', 'auto_submitted']
    ).count()
    pending_grading = ExamAttempt.objects.filter(
        exam=exam,
        is_graded=False,
        status__in=['submitted', 'auto_submitted']
    ).count()
    
    # Get recent attempts - ONLY from relevant students
    relevant_student_ids = set()
    
    if is_creator:
        # If creator, show all attempts
        recent_attempts = ExamAttempt.objects.filter(exam=exam).select_related(
            'student'
        ).order_by('-started_at')[:10]
        
        # All students for statistics
        total_attempts = ExamAttempt.objects.filter(exam=exam).count()
        submitted_attempts = ExamAttempt.objects.filter(
            exam=exam, 
            status__in=['submitted', 'auto_submitted']
        ).count()
        pending_grading = ExamAttempt.objects.filter(
            exam=exam,
            is_graded=False,
            status__in=['submitted', 'auto_submitted']
        ).count()
        
        # Pass/fail stats for all students
        graded_attempts = ExamAttempt.objects.filter(exam=exam, is_graded=True)
        
    else:
        # If assigned exam, only show instructor's students
        if Batch and Course and BatchEnrollment and Enrollment:
            # Get students from instructor's batches
            instructor_batches = Batch.objects.filter(instructor=request.user)
            batch_students = User.objects.filter(
                role='student',
                batch_enrollments__batch__in=instructor_batches,
                batch_enrollments__is_active=True,
                is_active=True
            ).distinct().values_list('id', flat=True)
            relevant_student_ids.update(batch_students)
            
            # Get students from instructor's courses
            instructor_courses = Course.objects.filter(instructor=request.user)
            course_students = User.objects.filter(
                role='student',
                enrollments__course__in=instructor_courses,
                enrollments__is_active=True,
                is_active=True
            ).distinct().values_list('id', flat=True)
            relevant_student_ids.update(course_students)
        
        # Filter attempts to only relevant students
        recent_attempts = ExamAttempt.objects.filter(
            exam=exam,
            student_id__in=relevant_student_ids
        ).select_related('student').order_by('-started_at')[:10]
        
        # Statistics only for relevant students
        total_attempts = ExamAttempt.objects.filter(
            exam=exam,
            student_id__in=relevant_student_ids
        ).count()
        submitted_attempts = ExamAttempt.objects.filter(
            exam=exam,
            student_id__in=relevant_student_ids,
            status__in=['submitted', 'auto_submitted']
        ).count()
        pending_grading = ExamAttempt.objects.filter(
            exam=exam,
            student_id__in=relevant_student_ids,
            is_graded=False,
            status__in=['submitted', 'auto_submitted']
        ).count()
        
        # Pass/fail stats only for relevant students
        graded_attempts = ExamAttempt.objects.filter(
            exam=exam,
            student_id__in=relevant_student_ids,
            is_graded=True
        )
    
    # Get exam questions based on type
    questions = []
    if exam.exam_type == 'mcq':
        questions = exam.mcq_questions.filter(is_active=True).prefetch_related('options').order_by('order')
    elif exam.exam_type == 'qa':
        questions = exam.qa_questions.filter(is_active=True).order_by('order')
    elif exam.exam_type == 'assignment':
        try:
            assignment_details = exam.assignment_details
        except:
            assignment_details = None
    
    # Get assignments for this exam
    exam_assignments = ExamAssignment.objects.filter(
        exam=exam,
        is_active=True
    ).select_related('student', 'batch', 'course', 'assigned_by')
    
    # Calculate pass/fail statistics
    passed_attempts = graded_attempts.filter(is_passed=True).count()
    failed_attempts = graded_attempts.filter(is_passed=False).count()
    
    # Average score
    if graded_attempts.exists():
        avg_score = graded_attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0
        avg_score = round(avg_score, 2)
    else:
        avg_score = 0
    
    # Get assignments for this exam - only relevant ones
    if is_creator:
        # Creator can see all assignments
        exam_assignments = ExamAssignment.objects.filter(
            exam=exam,
            is_active=True
        ).select_related('student', 'batch', 'course', 'assigned_by')
    else:
        # Assigned instructor only sees assignments related to them
        exam_assignments = ExamAssignment.objects.filter(
            exam=exam,
            is_active=True
        ).select_related('student', 'batch', 'course', 'assigned_by')
        
        # Filter to only assignments relevant to this instructor
        relevant_assignments = []
        for assignment in exam_assignments:
            if assignment.assignment_type == 'batch' and assignment.batch and assignment.batch.instructor == request.user:
                relevant_assignments.append(assignment)
            elif assignment.assignment_type == 'course' and assignment.course and assignment.course.instructor == request.user:
                relevant_assignments.append(assignment)
            elif assignment.assignment_type == 'individual' and assignment.student and assignment.student.id in relevant_student_ids:
                relevant_assignments.append(assignment)
        
        exam_assignments = relevant_assignments
    
    context = {
        'exam': exam,
        'is_creator': is_creator,
        'assignment_info': assignment_info,
        'questions': questions,
        'total_attempts': total_attempts,
        'submitted_attempts': submitted_attempts,
        'pending_grading': pending_grading,
        'recent_attempts': recent_attempts,
        'exam_assignments': exam_assignments,
        'passed_attempts': passed_attempts,
        'failed_attempts': failed_attempts,
        'avg_score': avg_score,
    }
    
    if exam.exam_type == 'assignment':
        context['assignment_details'] = assignment_details if 'assignment_details' in locals() else None
    
    return render(request, 'exam/instructor/exam_detail.html', context)