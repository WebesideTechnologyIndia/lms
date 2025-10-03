# exams/forms.py - Forms for Exam Management

from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory
from .models import (
    Exam, MCQQuestion, MCQOption, QAQuestion, AssignmentExam,
    ExamAssignment, MCQResponse, QAResponse, AssignmentSubmission
)
from courses.models import Course, Batch

User = get_user_model()

class ExamForm(forms.ModelForm):
    """Main form for creating/editing exams"""
    
    class Meta:
        model = Exam
        fields = [
            'title', 'description', 'instructions', 'exam_type',
            'total_marks', 'passing_marks', 'timing_type',
            'time_per_question_minutes', 'total_exam_time_minutes',
            'allow_retake', 'max_attempts', 'show_results_immediately',
            'randomize_questions', 'randomize_options',
            'start_datetime', 'end_datetime', 'status'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter exam title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the exam purpose and content'
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Special instructions for students (optional)'
            }),
            'exam_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'exam_type_select'
            }),
            'total_marks': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'passing_marks': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'timing_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'timing_type_select'
            }),
            'time_per_question_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 60
            }),
            'total_exam_time_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 5,
                'max': 600
            }),
            'allow_retake': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'max_attempts': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10
            }),
            'show_results_immediately': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'randomize_questions': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'randomize_options': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'start_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['timing_type'].help_text = "Choose how time limits will be applied"
        self.fields['time_per_question_minutes'].help_text = "Only applies if 'Time Per Question' is selected"
        self.fields['total_exam_time_minutes'].help_text = "Only applies if 'Total Exam Time' is selected"
        self.fields['randomize_options'].help_text = "Only for MCQ exams"
        
        # Make some fields required
        self.fields['title'].required = True
        self.fields['description'].required = True
        self.fields['exam_type'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        exam_type = cleaned_data.get('exam_type')
        timing_type = cleaned_data.get('timing_type')
        passing_marks = cleaned_data.get('passing_marks')
        total_marks = cleaned_data.get('total_marks')
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        
        # Validate passing marks
        if passing_marks and total_marks and passing_marks > total_marks:
            raise forms.ValidationError("Passing marks cannot be greater than total marks")
        
        # Validate date range
        if start_datetime and end_datetime and start_datetime >= end_datetime:
            raise forms.ValidationError("End date must be after start date")
        
        # Validate timing settings
        if timing_type == 'per_question':
            time_per_question = cleaned_data.get('time_per_question_minutes')
            if not time_per_question or time_per_question < 1:
                raise forms.ValidationError("Time per question must be at least 1 minute")
        
        elif timing_type == 'total_exam':
            total_time = cleaned_data.get('total_exam_time_minutes')
            if not total_time or total_time < 5:
                raise forms.ValidationError("Total exam time must be at least 5 minutes")
        
        return cleaned_data


class MCQQuestionForm(forms.ModelForm):
    """Form for MCQ Questions"""
    
    class Meta:
        model = MCQQuestion
        fields = ['question_text', 'question_image', 'marks', 'explanation']
        
        widgets = {
            'question_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter the question'
            }),
            'question_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'marks': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 1
            }),
            'explanation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Explanation for the correct answer (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['question_text'].required = True


class MCQOptionForm(forms.ModelForm):
    """Form for MCQ Options"""
    
    class Meta:
        model = MCQOption
        fields = ['option_text', 'option_image', 'is_correct']
        
        widgets = {
            'option_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter option text'
            }),
            'option_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'is_correct': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


# Inline formset for MCQ options
MCQOptionFormSet = inlineformset_factory(
    MCQQuestion, 
    MCQOption, 
    form=MCQOptionForm,
    extra=4,  # Default 4 options
    min_num=2,  # Minimum 2 options
    max_num=6,  # Maximum 6 options
    can_delete=True,
    fields=['option_text', 'option_image', 'is_correct']
)


class QAQuestionForm(forms.ModelForm):
    """Form for Q&A Questions"""
    
    class Meta:
        model = QAQuestion
        fields = ['question_text', 'question_image', 'marks', 'model_answer', 'keywords']
        
        widgets = {
            'question_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter the question'
            }),
            'question_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'marks': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 5
            }),
            'model_answer': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Model answer for reference during evaluation'
            }),
            'keywords': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Key points to look for in student answers'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['question_text'].required = True


class AssignmentExamForm(forms.ModelForm):
    """Form for Assignment Details"""
    
    class Meta:
        model = AssignmentExam
        fields = [
            'assignment_description', 'submission_guidelines',
            'allowed_file_types', 'max_file_size_mb', 'max_files_allowed',
            'evaluation_criteria'
        ]
        
        widgets = {
            'assignment_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Detailed assignment description and requirements'
            }),
            'submission_guidelines': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Guidelines for submission format, naming conventions, etc.'
            }),
            'allowed_file_types': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'pdf,doc,docx,txt (comma-separated)'
            }),
            'max_file_size_mb': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100,
                'value': 10
            }),
            'max_files_allowed': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10,
                'value': 1
            }),
            'evaluation_criteria': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Criteria for evaluating the assignment'
            }),
        }


class ExamAssignmentForm(forms.ModelForm):
    """Form for assigning exams to students/batches/courses"""
    
    class Meta:
        model = ExamAssignment
        fields = [
            'assignment_type', 'student', 'batch', 'course',
            'custom_start_datetime', 'custom_end_datetime'
        ]
        
        widgets = {
            'assignment_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'assignment_type_select'
            }),
            'student': forms.Select(attrs={
                'class': 'form-select',
                'id': 'student_select'
            }),
            'batch': forms.Select(attrs={
                'class': 'form-select',
                'id': 'batch_select'
            }),
            'course': forms.Select(attrs={
                'class': 'form-select',
                'id': 'course_select'
            }),
            'custom_start_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'custom_end_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter choices based on role
        self.fields['student'].queryset = User.objects.filter(role='student', is_active=True)
        self.fields['batch'].queryset = Batch.objects.filter(is_active=True)
        self.fields['course'].queryset = Course.objects.filter(is_active=True)
        
        # Make fields optional initially
        self.fields['student'].required = False
        self.fields['batch'].required = False
        self.fields['course'].required = False
        
        # Add help text
        self.fields['custom_start_datetime'].help_text = "Override exam start time (optional)"
        self.fields['custom_end_datetime'].help_text = "Override exam end time (optional)"
    
    def clean(self):
        cleaned_data = super().clean()
        assignment_type = cleaned_data.get('assignment_type')
        student = cleaned_data.get('student')
        batch = cleaned_data.get('batch')
        course = cleaned_data.get('course')
        custom_start = cleaned_data.get('custom_start_datetime')
        custom_end = cleaned_data.get('custom_end_datetime')
        
        # Validate based on assignment type
        if assignment_type == 'individual' and not student:
            raise forms.ValidationError("Student is required for individual assignment")
        elif assignment_type == 'batch' and not batch:
            raise forms.ValidationError("Batch is required for batch assignment")
        elif assignment_type == 'course' and not course:
            raise forms.ValidationError("Course is required for course assignment")
        
        # Validate custom date range
        if custom_start and custom_end and custom_start >= custom_end:
            raise forms.ValidationError("Custom end date must be after start date")
        
        return cleaned_data


class QuickMCQForm(forms.Form):
    """Quick form for adding MCQ questions with options"""
    
    question_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter the question'
        })
    )
    
    marks = forms.IntegerField(
        initial=1,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1
        })
    )
    
    option_1 = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Option A'
        })
    )
    
    option_2 = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Option B'
        })
    )
    
    option_3 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Option C (optional)'
        })
    )
    
    option_4 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Option D (optional)'
        })
    )
    
    correct_option = forms.ChoiceField(
        choices=[
            ('1', 'Option A'),
            ('2', 'Option B'),
            ('3', 'Option C'),
            ('4', 'Option D'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    explanation = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Explanation for correct answer (optional)'
        })
    )


class BulkAssignmentForm(forms.Form):
    """Form for bulk assignment of exams"""
    
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.filter(status='published', is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    assignment_type = forms.ChoiceField(
        choices=ExamAssignment.ASSIGNMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    selected_students = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role='student', is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    
    selected_batches = forms.ModelMultipleChoiceField(
        queryset=Batch.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    
    selected_courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    
    custom_start_datetime = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
    
    custom_end_datetime = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )


# Student Exam Forms

class MCQResponseForm(forms.ModelForm):
    """Form for student MCQ responses"""
    
    class Meta:
        model = MCQResponse
        fields = ['selected_option']
        
        widgets = {
            'selected_option': forms.RadioSelect()
        }


class QAResponseForm(forms.ModelForm):
    """Form for student Q&A responses"""
    
    class Meta:
        model = QAResponse
        fields = ['answer_text']
        
        widgets = {
            'answer_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Write your answer here...'
            })
        }


class AssignmentSubmissionForm(forms.ModelForm):
    """Form for assignment submissions"""
    
    files = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        }),
        required=False
    )
    
    class Meta:
        model = AssignmentSubmission
        fields = ['submission_text']
        
        widgets = {
            'submission_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Additional comments or explanation (optional)'
            })
        }


# Grading Forms

class QAGradingForm(forms.ModelForm):
    """Form for grading Q&A responses"""
    
    class Meta:
        model = QAResponse
        fields = ['marks_obtained', 'feedback']
        
        widgets = {
            'marks_obtained': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.5
            }),
            'feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Feedback for the student'
            })
        }


class AssignmentGradingForm(forms.ModelForm):
    """Form for grading assignment submissions"""
    
    class Meta:
        model = AssignmentSubmission
        fields = ['marks_obtained', 'feedback']
        
        widgets = {
            'marks_obtained': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.5
            }),
            'feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Detailed feedback for the assignment'
            })
        }


class ExamSearchForm(forms.Form):
    """Form for searching and filtering exams"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search exams by title...'
        })
    )
    
    exam_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Exam.EXAM_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Exam.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    created_by = forms.ModelChoiceField(
        queryset=User.objects.filter(role__in=['superadmin', 'instructor']),
        required=False,
        empty_label="All Creators",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class ExamFilterForm(forms.Form):
    """Advanced filtering form for exams"""
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    min_marks = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0
        })
    )
    
    max_marks = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0
        })
    )
    
    timing_type = forms.ChoiceField(
        choices=[('', 'All Timing Types')] + Exam.TIMING_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )