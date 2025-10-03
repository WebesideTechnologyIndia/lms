# courses/forms.py

from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory
from .models import (
    Course, CourseCategory, CourseModule, CourseLesson, 
    Enrollment, CourseReview, CourseFAQ,
    Batch, BatchModule, BatchLesson, BatchEnrollment 
  
)

User = get_user_model()

class CourseForm(forms.ModelForm):
    """Form for creating and editing courses"""
    
    class Meta:
        model = Course
        fields = [
            'title', 'course_code', 'category', 'instructor', 'co_instructors',
            'short_description', 'description', 'difficulty_level', 'course_type',
            'max_students', 'duration_weeks', 'hours_per_week',
            'price', 'discounted_price', 'is_free',
            'thumbnail', 'intro_video',
            'enrollment_start_date', 'enrollment_end_date',
            'course_start_date', 'course_end_date',
            'prerequisites', 'learning_outcomes', 'course_materials',
            'meta_keywords', 'meta_description',
            'is_featured', 'allow_enrollment'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter course title'}),
            'course_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CS101'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'instructor': forms.Select(attrs={'class': 'form-select'}),
            'co_instructors': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '3'}),
            'short_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief description for course cards'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Detailed course description'}),
            'difficulty_level': forms.Select(attrs={'class': 'form-select'}),
            'course_type': forms.Select(attrs={'class': 'form-select'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'duration_weeks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'hours_per_week': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'discounted_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'is_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'intro_video': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'YouTube/Vimeo URL'}),
            'enrollment_start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'enrollment_end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'course_start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'course_end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'prerequisites': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'learning_outcomes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'course_materials': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'meta_keywords': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_description': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 160}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_enrollment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter instructors
        self.fields['instructor'].queryset = User.objects.filter(role='instructor', is_active=True)
        self.fields['co_instructors'].queryset = User.objects.filter(role='instructor', is_active=True)
        
        # Make some fields required
        self.fields['category'].required = True
        self.fields['instructor'].required = True
        
    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price', 0)
        discounted_price = cleaned_data.get('discounted_price')
        is_free = cleaned_data.get('is_free', False)
        
        # Validate pricing logic
        if is_free:
            cleaned_data['price'] = 0
            cleaned_data['discounted_price'] = None
        elif discounted_price and discounted_price >= price:
            raise forms.ValidationError("Discounted price must be less than the original price.")
        
        # Validate date logic
        enrollment_start = cleaned_data.get('enrollment_start_date')
        enrollment_end = cleaned_data.get('enrollment_end_date')
        course_start = cleaned_data.get('course_start_date')
        course_end = cleaned_data.get('course_end_date')
        
        if enrollment_start and enrollment_end and enrollment_start >= enrollment_end:
            raise forms.ValidationError("Enrollment end date must be after enrollment start date.")
        
        if course_start and course_end and course_start >= course_end:
            raise forms.ValidationError("Course end date must be after course start date.")
        
        return cleaned_data


class CourseCategoryForm(forms.ModelForm):
    """Form for creating and editing course categories"""
    
    class Meta:
        model = CourseCategory
        fields = ['name', 'description', 'slug', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'auto-generated if left empty'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if not slug:
            # Auto-generate slug from name
            from django.utils.text import slugify
            name = self.cleaned_data.get('name', '')
            slug = slugify(name)
        return slug


class CourseModuleForm(forms.ModelForm):
    """Form for creating course modules"""
    
    class Meta:
        model = CourseModule
        fields = ['title', 'description', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# courses/forms.py

# courses/forms.py - EKDUM SIMPLE VERSION

from django import forms
from .models import CourseLesson, CourseModule

class BasicLessonForm(forms.ModelForm):
    """Sirf title aur description - bas itna hi"""
    
    class Meta:
        model = CourseLesson
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lesson ka title likho'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Lesson ke bare mein kuch lines likho...'
            }),
        }
    
    def __init__(self, *args, module=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Required fields
        self.fields['title'].required = True
        self.fields['description'].required = True
        
        # Store module for saving
        self.module = module
        
class EnrollmentForm(forms.ModelForm):
    """Form for manual enrollment by admin"""
    
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'status', 'amount_paid', 'payment_status']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = User.objects.filter(role='student', is_active=True)
        self.fields['course'].queryset = Course.objects.filter(is_active=True)


class CourseReviewForm(forms.ModelForm):
    """Form for course reviews"""
    
    class Meta:
        model = CourseReview
        fields = ['rating', 'review_text']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f"{i} Star{'s' if i != 1 else ''}") for i in range(1, 6)],
                attrs={'class': 'form-select'}
            ),
            'review_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Share your experience...'}),
        }


class CourseFAQForm(forms.ModelForm):
    """Form for course FAQs"""
    
    class Meta:
        model = CourseFAQ
        fields = ['question', 'answer', 'order', 'is_active']
        widgets = {
            'question': forms.TextInput(attrs={'class': 'form-control'}),
            'answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CourseSearchForm(forms.Form):
    """Form for searching and filtering courses"""
    
    SORT_CHOICES = [
        ('title', 'Title A-Z'),
        ('-title', 'Title Z-A'),
        ('-created_at', 'Newest First'),
        ('created_at', 'Oldest First'),
        ('price', 'Price Low to High'),
        ('-price', 'Price High to Low'),
        ('-average_rating', 'Highest Rated'),
        ('-total_enrollments', 'Most Popular'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search courses...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=CourseCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    difficulty = forms.ChoiceField(
        choices=[('', 'All Levels')] + Course.DIFFICULTY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    course_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Course.COURSE_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    price_range = forms.ChoiceField(
        choices=[
            ('', 'All Prices'),
            ('free', 'Free'),
            ('0-50', '$0 - $50'),
            ('50-100', '$50 - $100'),
            ('100-200', '$100 - $200'),
            ('200+', '$200+'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-select'})
    )



# courses/forms.py - Enhanced Lesson Forms

from django import forms
from django.forms import inlineformset_factory
from .models import CourseLesson, LessonAttachment, CourseModule

class EnhancedLessonForm(forms.ModelForm):
    """Enhanced form for lesson with multiple content types"""
    
    class Meta:
        model = CourseLesson
        fields = [
            'title', 'description', 'lesson_type', 'duration_minutes',
            'text_content', 'video_file', 'youtube_url', 'vimeo_url',
            'pdf_file', 'additional_notes', 'is_free_preview', 
            'is_mandatory'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter lesson title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of this lesson'
            }),
            'lesson_type': forms.Select(attrs={'class': 'form-select'}),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Expected duration in minutes'
            }),
            'text_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Rich text content for the lesson (optional)'
            }),
            'video_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*'
            }),
            'youtube_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
            'vimeo_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://vimeo.com/...'
            }),
            'pdf_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'
            }),
            'additional_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Any additional notes or instructions (optional)'
            }),
            'is_free_preview': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_mandatory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, module=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.module = module
        
        # Required fields
        self.fields['title'].required = True
        self.fields['description'].required = True
        self.fields['lesson_type'].required = True
        
        # Add help text
        self.fields['lesson_type'].help_text = "Select the primary content type for this lesson"
        self.fields['is_free_preview'].help_text = "Allow non-enrolled students to view this lesson"
        self.fields['is_mandatory'].help_text = "Required for course completion"

    def clean(self):
        cleaned_data = super().clean()
        lesson_type = cleaned_data.get('lesson_type')
        
        # Validate based on lesson type
        if lesson_type == 'video':
            video_file = cleaned_data.get('video_file')
            youtube_url = cleaned_data.get('youtube_url')
            vimeo_url = cleaned_data.get('vimeo_url')
            
            if not any([video_file, youtube_url, vimeo_url]):
                raise forms.ValidationError(
                    "Video lessons must have either a video file or a video URL"
                )
        
        elif lesson_type == 'pdf':
            pdf_file = cleaned_data.get('pdf_file')
            if not pdf_file:
                raise forms.ValidationError(
                    "PDF lessons must have a PDF file uploaded"
                )
        
        elif lesson_type == 'text':
            text_content = cleaned_data.get('text_content')
            if not text_content:
                raise forms.ValidationError(
                    "Text lessons must have text content"
                )
        
        # Check video file size (max 500MB)
        video_file = cleaned_data.get('video_file')
        if video_file and video_file.size > 500 * 1024 * 1024:  # 500MB
            raise forms.ValidationError(
                "Video file size should not exceed 500MB"
            )
        
        # Check PDF file size (max 50MB)
        pdf_file = cleaned_data.get('pdf_file')
        if pdf_file and pdf_file.size > 50 * 1024 * 1024:  # 50MB
            raise forms.ValidationError(
                "PDF file size should not exceed 50MB"
            )
        
        return cleaned_data


class LessonAttachmentForm(forms.ModelForm):
    """Form for lesson attachments"""
    
    class Meta:
        model = LessonAttachment
        fields = ['title', 'description', 'file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Attachment title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Brief description (optional)'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.zip,.rar,.txt,.jpg,.png,.gif'
            })
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 100MB)
            if file.size > 100 * 1024 * 1024:  # 100MB
                raise forms.ValidationError(
                    "File size should not exceed 100MB"
                )
        return file


# Inline formset for lesson attachments
LessonAttachmentFormSet = inlineformset_factory(
    CourseLesson, 
    LessonAttachment, 
    form=LessonAttachmentForm,
    extra=1,
    can_delete=True,
    fields=['title', 'description', 'file']
)


class QuickLessonForm(forms.ModelForm):
    """Quick form for basic lesson creation"""
    
    class Meta:
        model = CourseLesson
        fields = ['title', 'description', 'lesson_type']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Quick lesson title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description'
            }),
            'lesson_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, module=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.module = module
        self.fields['title'].required = True
        self.fields['description'].required = True


class LessonSearchForm(forms.Form):
    """Form for searching lessons within a course"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search lessons...'
        })
    )
    
    lesson_type = forms.ChoiceField(
        choices=[('', 'All Types')] + CourseLesson.LESSON_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    module = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Modules",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course:
            self.fields['module'].queryset = course.modules.filter(is_active=True)



# courses/forms.py - Add these SIMPLE forms

# courses/forms.py - Updated BatchForm with status field

class BatchForm(forms.ModelForm):
    """Simple batch creation form with status"""
    
    class Meta:
        model = Batch
        fields = ['name', 'content_type', 'start_date', 'end_date', 'max_students', 'instructor', 'status']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Spring 2025, Weekend Batch'
            }),
            'content_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control', 'value': 30}),
            'instructor': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.course = course
        
        # Filter instructors
        self.fields['instructor'].queryset = User.objects.filter(role='instructor', is_active=True)
        
        # Set default instructor from course
        if course and course.instructor:
            self.fields['instructor'].initial = course.instructor
        
        # Add help text for status
        self.fields['status'].help_text = "Change batch status to control student access"
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError("End date must be after start date.")
        
        return cleaned_data
    

# Add this to your forms.py

class BatchEditForm(forms.ModelForm):
    """Form specifically for editing existing batches"""
    
    class Meta:
        model = Batch
        # Only include fields that can actually be edited
        fields = ['name', 'start_date', 'end_date', 'max_students', 'status']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Spring 2025, Weekend Batch'
            }),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        max_students = cleaned_data.get('max_students')
        
        # Validate dates
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError("End date must be after start date.")
        
        # Validate max_students against current enrollment
        if self.instance and max_students:
            current_enrolled = self.instance.get_enrolled_count()
            if max_students < current_enrolled:
                raise forms.ValidationError(
                    f"Cannot set max students below current enrolled students ({current_enrolled})"
                )
        
        return cleaned_data
    
class SimpleBatchModuleForm(forms.ModelForm):
    """Simple module form for batch"""
    
    class Meta:
        model = BatchModule
        fields = ['title', 'description', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }


class SimpleBatchLessonForm(forms.ModelForm):
    """Simple lesson form for batch"""
    
    class Meta:
        model = BatchLesson
        fields = ['title', 'description', 'lesson_type', 'text_content', 'youtube_url', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'lesson_type': forms.Select(attrs={'class': 'form-select'}),
            'text_content': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'youtube_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'YouTube URL (optional)'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }


class BatchEnrollForm(forms.ModelForm):
    """Simple enrollment form"""
    
    class Meta:
        model = BatchEnrollment
        fields = ['student']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = User.objects.filter(role='student', is_active=True)


# courses/forms.py - Create this file or add to existing forms

from django import forms
from django.contrib.auth import get_user_model
from courses.models import Course, Enrollment

User = get_user_model()


class EnrollmentForm(forms.ModelForm):
    """Form for manual student enrollment"""
    
    class Meta:
        model = Enrollment
        fields = [
            'student', 'course', 'status', 'payment_status', 
            'amount_paid', 'progress_percentage'
        ]
        widgets = {
            'student': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'course': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payment_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount_paid': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'progress_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter students - only active students
        self.fields['student'].queryset = User.objects.filter(
            role='student',
            is_active=True
        ).select_related('profile')
        
        # Filter courses based on user role
        if user and user.role == 'instructor':
            self.fields['course'].queryset = Course.objects.filter(
                instructor=user,
                is_active=True,
                status='published'
            )
        else:
            self.fields['course'].queryset = Course.objects.filter(
                is_active=True,
                status='published'
            )
        
        # Set default values
        self.fields['status'].initial = 'enrolled'
        self.fields['payment_status'].initial = 'pending'
        self.fields['amount_paid'].initial = 0.00
        self.fields['progress_percentage'].initial = 0
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        course = cleaned_data.get('course')
        
        if student and course:
            # Check if student is already enrolled
            if Enrollment.objects.filter(
                student=student,
                course=course,
                is_active=True
            ).exists():
                raise forms.ValidationError(
                    f"Student {student.get_full_name()} is already enrolled in {course.title}"
                )
        
        return cleaned_data


class BulkEnrollmentForm(forms.Form):
    """Form for bulk enrollment operations"""
    
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role='student', is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label="Select Students"
    )
    
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_active=True, status='published'),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Course"
    )
    
    status = forms.ChoiceField(
        choices=Enrollment.STATUS_CHOICES,
        initial='enrolled',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    payment_status = forms.ChoiceField(
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('waived', 'Waived')
        ],
        initial='pending',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    send_welcome_emails = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Send welcome emails to students"
    )


class EnrollmentFilterForm(forms.Form):
    """Form for filtering enrollments"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search students or courses...'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + list(Enrollment.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_active=True),
        required=False,
        empty_label="All Courses",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    payment_status = forms.ChoiceField(
        choices=[
            ('', 'All Payment Status'),
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('waived', 'Waived')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Enrolled From"
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Enrolled To"
    )


class EmailStudentForm(forms.Form):
    """Form for sending emails to students"""
    
    EMAIL_TEMPLATE_CHOICES = [
        ('', 'Custom Email'),
        ('welcome', 'Welcome to Course'),
        ('reminder', 'Course Reminder'),
        ('completion', 'Course Completion'),
        ('payment_reminder', 'Payment Reminder'),
        ('assignment_reminder', 'Assignment Reminder'),
    ]
    
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role='student', is_active=True),
        widget=forms.CheckboxSelectMultiple(),
        label="Recipients"
    )
    
    template = forms.ChoiceField(
        choices=EMAIL_TEMPLATE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Email Template"
    )
    
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email subject...'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Email message...'
        })
    )
    
    send_copy_to_self = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Send a copy to myself"
    )


class EnrollmentUpdateForm(forms.ModelForm):
    """Form for updating enrollment details"""
    
    class Meta:
        model = Enrollment
        fields = [
            'status', 'progress_percentage', 'grade', 
            'payment_status', 'amount_paid'
        ]
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'progress_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.1'
            }),
            'grade': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payment_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount_paid': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add empty choice for grade
        grade_choices = [('', 'No Grade')] + list(Enrollment.GRADE_CHOICES)
        self.fields['grade'].choices = grade_choices
        
        # Payment status choices
        payment_choices = [
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('waived', 'Waived')
        ]
        self.fields['payment_status'].choices = payment_choices