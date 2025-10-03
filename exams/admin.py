from django.contrib import admin

# Register your models here.
# exams/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Exam, MCQQuestion, MCQOption, QAQuestion, AssignmentExam,
    ExamAssignment, ExamAttempt, MCQResponse, QAResponse,
    AssignmentSubmission, ExamFile
)


class MCQOptionInline(admin.TabularInline):
    """Inline for MCQ Options"""
    model = MCQOption
    extra = 4
    min_num = 2
    fields = ('option_text', 'option_image', 'is_correct', 'order')
    ordering = ['order']


@admin.register(MCQQuestion)
class MCQQuestionAdmin(admin.ModelAdmin):
    list_display = ('question_preview', 'exam', 'marks', 'order', 'is_active', 'correct_answer_preview')
    list_filter = ('exam', 'is_active', 'marks')
    search_fields = ('question_text', 'exam__title')
    list_editable = ('order', 'is_active', 'marks')
    ordering = ['exam', 'order']
    inlines = [MCQOptionInline]
    
    fieldsets = (
        ('Question Details', {
            'fields': ('exam', 'question_text', 'question_image', 'order')
        }),
        ('Scoring', {
            'fields': ('marks', 'is_active')
        }),
        ('Explanation', {
            'fields': ('explanation',),
            'classes': ('collapse',)
        })
    )
    
    def question_preview(self, obj):
        return obj.question_text[:50] + "..." if len(obj.question_text) > 50 else obj.question_text
    question_preview.short_description = 'Question'
    
    def correct_answer_preview(self, obj):
        correct = obj.get_correct_answer()
        if correct:
            return format_html('<span style="color: green;">✓ {}</span>', 
                             correct.option_text[:30] + "..." if len(correct.option_text) > 30 else correct.option_text)
        return format_html('<span style="color: red;">No correct answer set</span>')
    correct_answer_preview.short_description = 'Correct Answer'


@admin.register(QAQuestion)
class QAQuestionAdmin(admin.ModelAdmin):
    list_display = ('question_preview', 'exam', 'marks', 'order', 'is_active')
    list_filter = ('exam', 'is_active', 'marks')
    search_fields = ('question_text', 'exam__title')
    list_editable = ('order', 'is_active', 'marks')
    ordering = ['exam', 'order']
    
    fieldsets = (
        ('Question Details', {
            'fields': ('exam', 'question_text', 'question_image', 'order')
        }),
        ('Scoring', {
            'fields': ('marks', 'is_active')
        }),
        ('Answer Guidelines', {
            'fields': ('model_answer', 'keywords'),
            'classes': ('collapse',)
        })
    )
    
    def question_preview(self, obj):
        return obj.question_text[:50] + "..." if len(obj.question_text) > 50 else obj.question_text
    question_preview.short_description = 'Question'



@admin.register(AssignmentExam)
class AssignmentExamAdmin(admin.ModelAdmin):
    list_display = ('exam', 'max_file_size_mb', 'max_files_allowed', 'allowed_file_types')
    list_filter = ('max_file_size_mb', 'max_files_allowed')
    search_fields = ('exam__title', 'assignment_description')
    
    fieldsets = (
        ('Assignment Details', {
            'fields': ('exam', 'assignment_description', 'submission_guidelines')
        }),
        ('File Restrictions', {
            'fields': ('allowed_file_types', 'max_file_size_mb', 'max_files_allowed')
        }),
        ('Evaluation', {
            'fields': ('evaluation_criteria',),
            'classes': ('collapse',)
        })
    )


class MCQQuestionInline(admin.TabularInline):
    model = MCQQuestion
    extra = 0
    fields = ('question_text', 'marks', 'order', 'is_active')
    readonly_fields = ('question_text',)
    show_change_link = True


class QAQuestionInline(admin.TabularInline):
    model = QAQuestion
    extra = 0
    fields = ('question_text', 'marks', 'order', 'is_active')
    readonly_fields = ('question_text',)
    show_change_link = True


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'exam_type', 'total_marks', 'status', 'total_questions', 'is_active', 'created_at')
    list_filter = ('exam_type', 'status', 'timing_type', 'is_active', 'created_at')
    search_fields = ('title', 'description', 'created_by__username')
    list_editable = ('status', 'is_active')
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'instructions', 'created_by')
        }),
        ('Exam Configuration', {
            'fields': ('exam_type', 'total_marks', 'passing_marks')
        }),
        ('Timing Settings', {
            'fields': ('timing_type', 'time_per_question_minutes', 'total_exam_time_minutes')
        }),
        ('Exam Settings', {
            'fields': ('allow_retake', 'max_attempts', 'show_results_immediately', 
                      'randomize_questions', 'randomize_options')
        }),
        ('Scheduling', {
            'fields': ('start_datetime', 'end_datetime'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'is_active')
        })
    )
    
    def get_inlines(self, request, obj):
        if obj and obj.exam_type == 'mcq':
            return [MCQQuestionInline]
        elif obj and obj.exam_type == 'qa':
            return [QAQuestionInline]
        return []
    
    def total_questions(self, obj):
        return obj.get_total_questions()
    total_questions.short_description = 'Questions'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ExamAssignment)
class ExamAssignmentAdmin(admin.ModelAdmin):
    list_display = ('exam', 'assignment_type', 'get_assigned_to', 'assigned_by', 'assigned_at', 'is_active')
    list_filter = ('assignment_type', 'assigned_at', 'is_active')
    search_fields = ('exam__title', 'student__username', 'batch__name', 'course__title')
    date_hierarchy = 'assigned_at'
    
    fieldsets = (
        ('Assignment Details', {
            'fields': ('exam', 'assignment_type', 'assigned_by')
        }),
        ('Target', {
            'fields': ('student', 'batch', 'course'),
            'description': 'Select target based on assignment type'
        }),
        ('Custom Timing', {
            'fields': ('custom_start_datetime', 'custom_end_datetime'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    
    def get_assigned_to(self, obj):
        if obj.assignment_type == 'individual':
            return obj.student.username if obj.student else 'Not set'
        elif obj.assignment_type == 'batch':
            return obj.batch.name if obj.batch else 'Not set'
        else:
            return obj.course.title if obj.course else 'Not set'
    get_assigned_to.short_description = 'Assigned To'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)


class MCQResponseInline(admin.TabularInline):
    model = MCQResponse
    extra = 0
    readonly_fields = ('question', 'selected_option', 'is_correct', 'answered_at', 'time_spent_seconds')
    fields = ('question', 'selected_option', 'is_correct', 'time_spent_seconds')
    
    def is_correct(self, obj):
        if obj.is_correct():
            return format_html('<span style="color: green;">✓ Correct</span>')
        return format_html('<span style="color: red;">✗ Incorrect</span>')
    is_correct.short_description = 'Result'


class QAResponseInline(admin.TabularInline):
    model = QAResponse
    extra = 0
    readonly_fields = ('question', 'answered_at')
    fields = ('question', 'marks_obtained', 'is_graded', 'feedback')


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'attempt_number', 'status', 'total_marks_obtained', 
                   'percentage', 'is_passed', 'started_at', 'is_graded')
    list_filter = ('status', 'is_passed', 'is_graded', 'exam__exam_type', 'started_at')
    search_fields = ('student__username', 'exam__title')
    readonly_fields = ('started_at', 'exam_config', 'percentage')
    date_hierarchy = 'started_at'
    ordering = ['-started_at']
    
    fieldsets = (
        ('Attempt Information', {
            'fields': ('exam', 'student', 'attempt_number', 'status')
        }),
        ('Timing', {
            'fields': ('started_at', 'submitted_at', 'time_spent_minutes')
        }),
        ('Results', {
            'fields': ('total_marks_obtained', 'percentage', 'is_passed')
        }),
        ('Grading', {
            'fields': ('is_graded', 'graded_at', 'graded_by')
        }),
        ('Configuration Snapshot', {
            'fields': ('exam_config',),
            'classes': ('collapse',)
        })
    )
    
    def get_inlines(self, request, obj):
        if obj and obj.exam.exam_type == 'mcq':
            return [MCQResponseInline]
        elif obj and obj.exam.exam_type == 'qa':
            return [QAResponseInline]
        return []
    
    def save_model(self, request, obj, form, change):
        if obj.is_graded and not obj.graded_by:
            obj.graded_by = request.user
            if not obj.graded_at:
                from django.utils import timezone
                obj.graded_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(MCQResponse)
class MCQResponseAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'selected_option', 'is_correct_display', 'time_spent_seconds')
    list_filter = ('answered_at', 'attempt__exam')
    search_fields = ('attempt__student__username', 'question__question_text')
    readonly_fields = ('answered_at',)
    
    def is_correct_display(self, obj):
        if obj.is_correct():
            return format_html('<span style="color: green;">✓ Correct</span>')
        return format_html('<span style="color: red;">✗ Incorrect</span>')
    is_correct_display.short_description = 'Result'


@admin.register(QAResponse)
class QAResponseAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'marks_obtained', 'is_graded', 'answered_at')
    list_filter = ('is_graded', 'answered_at', 'attempt__exam')
    search_fields = ('attempt__student__username', 'question__question_text', 'answer_text')
    readonly_fields = ('answered_at', 'uploaded_files')
    
    fieldsets = (
        ('Response Information', {
            'fields': ('attempt', 'question', 'answered_at', 'time_spent_seconds')
        }),
        ('Answer', {
            'fields': ('answer_text', 'uploaded_files')
        }),
        ('Grading', {
            'fields': ('marks_obtained', 'feedback', 'is_graded', 'graded_at', 'graded_by')
        })
    )
    
    def save_model(self, request, obj, form, change):
        if obj.is_graded and not obj.graded_by:
            obj.graded_by = request.user
            if not obj.graded_at:
                from django.utils import timezone
                obj.graded_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'marks_obtained', 'is_graded', 'submitted_at')
    list_filter = ('is_graded', 'submitted_at')
    search_fields = ('attempt__student__username', 'attempt__exam__title', 'submission_text')
    readonly_fields = ('submitted_at', 'uploaded_files')
    
    fieldsets = (
        ('Submission Information', {
            'fields': ('attempt', 'submitted_at')
        }),
        ('Submission Content', {
            'fields': ('submission_text', 'uploaded_files')
        }),
        ('Grading', {
            'fields': ('marks_obtained', 'feedback', 'is_graded', 'graded_at', 'graded_by')
        })
    )
    
    def save_model(self, request, obj, form, change):
        if obj.is_graded and not obj.graded_by:
            obj.graded_by = request.user
            if not obj.graded_at:
                from django.utils import timezone
                obj.graded_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(ExamFile)
class ExamFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'file_type', 'get_file_size_mb', 'uploaded_at')
    list_filter = ('file_type', 'uploaded_at')
    search_fields = ('original_filename',)
    readonly_fields = ('uploaded_at', 'file_size')
    
    fieldsets = (
        ('File Information', {
            'fields': ('file_type', 'file', 'original_filename', 'file_size', 'uploaded_at')
        }),
        ('Linked Response', {
            'fields': ('qa_response', 'assignment_submission')
        })
    )


# Optional: Register MCQOption separately if you need direct access
@admin.register(MCQOption)
class MCQOptionAdmin(admin.ModelAdmin):
    list_display = ('question', 'option_text', 'is_correct', 'order')
    list_filter = ('is_correct', 'question__exam')
    search_fields = ('option_text', 'question__question_text')
    list_editable = ('is_correct', 'order')


# Admin site customization
admin.site.site_header = "Exam Management System"
admin.site.site_title = "Exam Admin"
admin.site.index_title = "Welcome to Exam Management System"


