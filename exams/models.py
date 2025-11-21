from django.db import models

# Create your models here.
# exams/models.py - Complete Exam Management System

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
import json

User = get_user_model()


class Exam(models.Model):
    """Main Exam Model"""
    
    EXAM_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice Questions'),
        ('qa', 'Question & Answer'),
        ('assignment', 'Assignment Upload'),
    ]
    
    TIMING_TYPE_CHOICES = [
        ('no_timing', 'No Time Limit'),
        ('per_question', 'Time Per Question'),
        ('total_exam', 'Total Exam Time'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    # Basic Info
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructions = models.TextField(blank=True, help_text="Special instructions for students")
    
    # Exam Configuration
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES)
    total_marks = models.PositiveIntegerField(default=100)
    passing_marks = models.PositiveIntegerField(default=40)
    
    # Timing Configuration
    timing_type = models.CharField(max_length=20, choices=TIMING_TYPE_CHOICES, default='no_timing')
    time_per_question_minutes = models.PositiveIntegerField(
        null=True,  # ✅ Allow NULL
        blank=True,  # ✅ Allow blank
        help_text="Minutes per question (only for per_question timing)"
    )
    total_exam_time_minutes = models.PositiveIntegerField(
        null=True,  # ✅ Allow NULL
        blank=True,  # ✅ Allow blank
        help_text="Total exam duration in minutes"
    )
    
    # Settings
    allow_retake = models.BooleanField(default=False)
    max_attempts = models.PositiveIntegerField(default=1)
    show_results_immediately = models.BooleanField(default=True)
    randomize_questions = models.BooleanField(default=False)
    randomize_options = models.BooleanField(default=False, help_text="For MCQ only")
    
    # Scheduling
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    
    # Status and Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        limit_choices_to={'role__in': ['superadmin', 'instructor']}
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['exam_type', 'status']),
            models.Index(fields=['start_datetime', 'end_datetime']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_exam_type_display()})"
    
    def get_total_questions(self):
        """Get total number of questions in exam"""
        if self.exam_type == 'mcq':
            return self.mcq_questions.filter(is_active=True).count()
        elif self.exam_type == 'qa':
            return self.qa_questions.filter(is_active=True).count()
        else:  # assignment
            return 1  # Assignment has 1 submission
    
    def calculate_exam_duration(self):
        """Calculate total exam duration based on timing type"""
        if self.timing_type == 'no_timing':
            return None  # ✅ No time limit
        elif self.timing_type == 'per_question':
            if self.time_per_question_minutes:
                return self.get_total_questions() * self.time_per_question_minutes
            return None
        else:  # total_exam
            return self.total_exam_time_minutes  # ✅ Can be None
    
    def is_available_now(self):
        """Check if exam is currently available"""
        now = timezone.now()
        if self.start_datetime and now < self.start_datetime:
            return False
        if self.end_datetime and now > self.end_datetime:
            return False
        return self.status == 'published' and self.is_active

    def can_student_attempt(self, student):
        """
        Check if student can attempt this exam
        Logic: Student can attempt multiple times WITHIN the exam window
        """
        from django.utils import timezone
        
        # Check if exam is active and published
        if not self.is_active or self.status != 'published':
            return False, 'Exam is not available'
        
        # Check exam window timing
        now = timezone.now()
        
        # If start_datetime is set, check if exam window has started
        if self.start_datetime and now < self.start_datetime:
            return False, f'Exam window starts at {self.start_datetime.strftime("%Y-%m-%d %H:%M")}'
        
        # If end_datetime is set, check if exam window has ended
        if self.end_datetime and now > self.end_datetime:
            return False, 'Exam window has closed'
        
        # Get student's attempts for this exam
        from .models import ExamAttempt
        attempts = ExamAttempt.objects.filter(
            exam=self,
            student=student
        ).order_by('-started_at')
        
        attempt_count = attempts.count()
        
        # Check if there's an ongoing attempt
        ongoing_attempt = attempts.filter(status='in_progress').first()
        if ongoing_attempt:
            return False, 'You have an ongoing attempt. Complete it first.'
        
        # If no attempts yet, allow first attempt (within window)
        if attempt_count == 0:
            return True, 'First attempt allowed'
        
        # Check if max attempts reached
        if attempt_count >= self.max_attempts:
            return False, f'Maximum attempts ({self.max_attempts}) reached'
        
        # If retakes are not allowed and student has attempted
        if not self.allow_retake and attempt_count > 0:
            return False, 'Retakes not allowed for this exam'
        
        # If retakes are allowed and haven't reached max attempts AND within window
        if self.allow_retake and attempt_count < self.max_attempts:
            return True, f'Retake allowed (Attempt {attempt_count + 1}/{self.max_attempts})'
        
        # Default fallback
        return False, 'Cannot attempt exam'
    
    def get_time_limit_display(self):
        """Get human-readable time limit"""
        if self.timing_type == 'no_timing':
            return 'No Time Limit'
        elif self.timing_type == 'per_question':
            if self.time_per_question_minutes:
                return f'{self.time_per_question_minutes} min per question'
            return 'Not set'
        else:  # total_exam
            if self.total_exam_time_minutes:
                return f'{self.total_exam_time_minutes} minutes total'
            return 'Not set'
        
        
class MCQQuestion(models.Model):
    """Multiple Choice Questions"""
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='mcq_questions')
    question_text = models.TextField()
    question_image = models.ImageField(upload_to='exam_questions/', blank=True, null=True)
    marks = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    # Explanation for correct answer
    explanation = models.TextField(blank=True, help_text="Explanation for the correct answer")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'id']
        unique_together = ['exam', 'order']
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."
    
    def get_correct_answer(self):
        """Get the correct answer option"""
        return self.options.filter(is_correct=True).first()


class MCQOption(models.Model):
    """Options for MCQ Questions"""
    
    question = models.ForeignKey(MCQQuestion, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=500)
    option_image = models.ImageField(upload_to='exam_options/', blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['order']
        unique_together = ['question', 'order']
    
    def __str__(self):
        return f"{self.option_text} {'✓' if self.is_correct else ''}"


class QAQuestion(models.Model):
    """Question & Answer Type Questions"""
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='qa_questions')
    question_text = models.TextField()
    question_image = models.ImageField(upload_to='exam_questions/', blank=True, null=True)
    marks = models.PositiveIntegerField(default=5)
    order = models.PositiveIntegerField(default=1)
    
    # Answer guidelines for manual checking
    model_answer = models.TextField(blank=True, help_text="Model answer for reference")
    keywords = models.TextField(blank=True, help_text="Key points to look for in answers")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'id']
        unique_together = ['exam', 'order']
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."


class AssignmentExam(models.Model):
    """Assignment Type Exam"""
    
    exam = models.OneToOneField(Exam, on_delete=models.CASCADE, related_name='assignment_details')
    assignment_description = models.TextField()
    submission_guidelines = models.TextField(blank=True)
    
    # File restrictions
    allowed_file_types = models.CharField(
        max_length=200, 
        default='pdf,doc,docx,txt',
        help_text="Comma-separated file extensions"
    )
    max_file_size_mb = models.PositiveIntegerField(default=10)
    max_files_allowed = models.PositiveIntegerField(default=1)
    
    # Evaluation criteria
    evaluation_criteria = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Assignment: {self.exam.title}"
    
    def get_allowed_extensions(self):
        """Get list of allowed file extensions"""
        return [ext.strip() for ext in self.allowed_file_types.split(',')]


class ExamAssignment(models.Model):
    """Assign Exam to Students or Batches"""
    
    ASSIGNMENT_TYPE_CHOICES = [
        ('individual', 'Individual Student'),
        ('batch', 'Entire Batch'),
        ('course', 'Entire Course'),
    ]
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='assignments')
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPE_CHOICES)
    
    # For individual assignment
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        limit_choices_to={'role': 'student'},
        related_name='assigned_exams'
    )
    
    # For batch assignment
    batch = models.ForeignKey(
        'courses.Batch', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='assigned_exams'
    )
    
    # For course assignment
    course = models.ForeignKey(
        'courses.Course', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='assigned_exams'
    )
    
    # Assignment details
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        limit_choices_to={'role__in': ['superadmin', 'instructor']},
        related_name='exam_assignments_made'
    )
    
    # Override exam timing if needed
    custom_start_datetime = models.DateTimeField(null=True, blank=True)
    custom_end_datetime = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = [
            ['exam', 'student'],
            ['exam', 'batch'],
            ['exam', 'course'],
        ]
    
    def __str__(self):
        if self.assignment_type == 'individual':
            return f"{self.exam.title} → {self.student.username}"
        elif self.assignment_type == 'batch':
            return f"{self.exam.title} → Batch: {self.batch.name}"
        else:
            return f"{self.exam.title} → Course: {self.course.title}"
    
    def get_assigned_students(self):
        """Get all students assigned to this exam"""
        if self.assignment_type == 'individual':
            return [self.student] if self.student else []
        elif self.assignment_type == 'batch':
            from courses.models import BatchEnrollment
            return User.objects.filter(
                batch_enrollments__batch=self.batch,
                batch_enrollments__is_active=True,
                role='student'
            ).distinct()
        else:  # course
            from courses.models import Enrollment
            return User.objects.filter(
                enrollments__course=self.course,
                enrollments__is_active=True,
                role='student'
            ).distinct()


class ExamAttempt(models.Model):
    """Track student exam attempts"""
    
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('auto_submitted', 'Auto Submitted (Time Up)'),
        ('abandoned', 'Abandoned'),
    ]
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name='exam_attempts'
    )
    
    # Attempt details
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_spent_minutes = models.PositiveIntegerField(default=0)
    
    # Exam configuration at time of attempt (frozen)
    exam_config = models.JSONField(default=dict, help_text="Exam settings when attempt was made")
    
    # Results
    total_marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_passed = models.BooleanField(default=False)
    
    # Grading
    is_graded = models.BooleanField(default=False)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='graded_attempts'
    )
    
    class Meta:
        unique_together = ['exam', 'student', 'attempt_number']
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.exam.title} (Attempt {self.attempt_number})"
    
    def calculate_percentage(self):
        """Calculate percentage based on total marks"""
        if self.exam.total_marks > 0:
            self.percentage = (self.total_marks_obtained / self.exam.total_marks) * 100
            self.is_passed = self.percentage >= self.exam.passing_marks
        else:
            self.percentage = 0
            self.is_passed = False
    
    def auto_submit(self):
        """Auto submit when time is up"""
        self.status = 'auto_submitted'
        self.submitted_at = timezone.now()
        self.save()
        
        # Calculate final marks for MCQ exams
        if self.exam.exam_type == 'mcq':
            self.calculate_mcq_marks()
    
    def calculate_mcq_marks(self):
        """Calculate marks for MCQ exam"""
        correct_answers = 0
        total_questions = self.exam.mcq_questions.filter(is_active=True).count()
        
        for response in self.mcq_responses.all():
            if response.selected_option and response.selected_option.is_correct:
                correct_answers += 1
        
        # Calculate marks based on correct answers
        if total_questions > 0:
            marks_per_question = self.exam.total_marks / total_questions
            self.total_marks_obtained = correct_answers * marks_per_question
            self.calculate_percentage()
            self.is_graded = True
            self.graded_at = timezone.now()
            self.save()


class MCQResponse(models.Model):
    """Student responses to MCQ questions"""
    
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='mcq_responses')
    question = models.ForeignKey(MCQQuestion, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(MCQOption, on_delete=models.CASCADE, null=True, blank=True)
    
    # Timing for this question
    time_spent_seconds = models.PositiveIntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"{self.attempt.student.username} - Q{self.question.order}"
    
    def is_correct(self):
        """Check if the selected answer is correct"""
        return self.selected_option and self.selected_option.is_correct


class QAResponse(models.Model):
    """Student responses to Q&A questions"""
    
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='qa_responses')
    question = models.ForeignKey(QAQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField()
    
    # Files uploaded as part of answer
    uploaded_files = models.JSONField(default=list, blank=True)
    
    # Timing for this question
    time_spent_seconds = models.PositiveIntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    # Manual grading
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    feedback = models.TextField(blank=True)
    is_graded = models.BooleanField(default=False)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    class Meta:
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"{self.attempt.student.username} - Q{self.question.order}"


class AssignmentSubmission(models.Model):
    """Assignment submissions"""
    
    attempt = models.OneToOneField(ExamAttempt, on_delete=models.CASCADE, related_name='assignment_submission')
    submission_text = models.TextField(blank=True)
    
    # File uploads
    uploaded_files = models.JSONField(default=list)
    
    # Submission timing
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    # Manual grading
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    feedback = models.TextField(blank=True)
    is_graded = models.BooleanField(default=False)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    def __str__(self):
        return f"Assignment: {self.attempt.student.username} - {self.attempt.exam.title}"


class ExamFile(models.Model):
    """Handle file uploads for Q&A and Assignment exams"""
    
    FILE_TYPE_CHOICES = [
        ('qa_response', 'Q&A Response File'),
        ('assignment', 'Assignment File'),
    ]
    
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file = models.FileField(upload_to='exam_submissions/')
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    
    # Link to specific response
    qa_response = models.ForeignKey(QAResponse, on_delete=models.CASCADE, null=True, blank=True)
    assignment_submission = models.ForeignKey(AssignmentSubmission, on_delete=models.CASCADE, null=True, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.file_type}: {self.original_filename}"
    
    def get_file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)