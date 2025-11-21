# courses/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from PIL import Image
import os

User = get_user_model()

class CourseCategory(models.Model):
    """Course categories for organization"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        limit_choices_to={'role': 'superadmin'}
    )

    class Meta:
        verbose_name_plural = "Course Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_courses_count(self):
        return self.courses.filter(is_active=True).count()

class Course(models.Model):
    """Enhanced Course model with all necessary fields"""
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
        ('suspended', 'Suspended'),
    ]
    
    COURSE_TYPE_CHOICES = [
        ('live', 'Live Classes'),
        ('recorded', 'Recorded'),
        ('hybrid', 'Hybrid'),
        ('offline', 'Offline')
    ]

    # Basic Information
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    short_description = models.TextField(max_length=500, help_text="Brief description for course cards")
    
    # Course Details
    course_code = models.CharField(max_length=20, unique=True, help_text="e.g., CS101, PY001")
    category = models.ForeignKey(CourseCategory, on_delete=models.CASCADE, related_name='courses')
    instructor = models.ForeignKey(
        User, on_delete=models.CASCADE, 
        limit_choices_to={'role': 'instructor'},
        related_name='instructor_courses'
    )
    co_instructors = models.ManyToManyField(
        User, blank=True,
        limit_choices_to={'role': 'instructor'},
        related_name='co_instructor_courses'
    )
    
    # Course Configuration
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    course_type = models.CharField(max_length=20, choices=COURSE_TYPE_CHOICES, default='live')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Capacity and Duration
    max_students = models.PositiveIntegerField(default=30)
    duration_weeks = models.PositiveIntegerField(default=8, help_text="Course duration in weeks")
    hours_per_week = models.PositiveIntegerField(default=3, help_text="Expected study hours per week")
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_free = models.BooleanField(default=False)
    
    # Media
    thumbnail = models.ImageField(upload_to='course_thumbnails/', null=True, blank=True)
    intro_video = models.URLField(blank=True, help_text="YouTube/Vimeo URL for course intro")
    
    # Dates
    enrollment_start_date = models.DateTimeField(null=True, blank=True)
    enrollment_end_date = models.DateTimeField(null=True, blank=True)
    course_start_date = models.DateTimeField(null=True, blank=True)
    course_end_date = models.DateTimeField(null=True, blank=True)
    
    # Requirements and Learning Outcomes
    prerequisites = models.TextField(blank=True, help_text="What students need to know before taking this course")
    learning_outcomes = models.TextField(help_text="What students will learn after completing this course")
    course_materials = models.TextField(blank=True, help_text="Required books, software, materials")
    
    # SEO and Marketing
    meta_keywords = models.CharField(max_length=500, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    
    # System fields
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text="Show on homepage")
    allow_enrollment = models.BooleanField(default=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_courses'
    )
    
    # Statistics (computed fields)
    total_enrollments = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['category', 'difficulty_level']),
            models.Index(fields=['instructor']),
        ]

    def __str__(self):
        return f"{self.course_code} - {self.title}"

    def save(self, *args, **kwargs):
        # Auto-generate slug if not provided
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(f"{self.course_code}-{self.title}")
        
        # Resize thumbnail if uploaded
        super().save(*args, **kwargs)
        if self.thumbnail:
            self.resize_thumbnail()

    def resize_thumbnail(self):
        """Resize uploaded thumbnail to standard size"""
        if self.thumbnail:
            with Image.open(self.thumbnail.path) as img:
                if img.height > 300 or img.width > 400:
                    img.thumbnail((400, 300))
                    img.save(self.thumbnail.path)

    def get_absolute_url(self):
        return reverse('course_detail', kwargs={'slug': self.slug})

    def get_enrolled_count(self):
        """Get current enrollment count"""
        return self.enrollments.filter(is_active=True).count()

    def get_available_seats(self):
        """Get remaining seats"""
        return self.max_students - self.get_enrolled_count()

    def is_enrollment_open(self):
        """Check if enrollment is currently open"""
        if not self.allow_enrollment:
            return False
        
        now = timezone.now()
        if self.enrollment_start_date and now < self.enrollment_start_date:
            return False
        if self.enrollment_end_date and now > self.enrollment_end_date:
            return False
        
        return self.get_available_seats() > 0

    def get_effective_price(self):
        """Get the price to display (discounted if available)"""
        if self.is_free:
            return 0
        return self.discounted_price if self.discounted_price else self.price

    def get_discount_percentage(self):
        """Calculate discount percentage"""
        if self.discounted_price and self.price > 0:
            return round(((self.price - self.discounted_price) / self.price) * 100)
        return 0

    def can_user_enroll(self, user):
        """Check if user can enroll in this course"""
        if user.role != 'student':
            return False, "Only students can enroll in courses"
        
        if not self.is_enrollment_open():
            return False, "Enrollment is closed"
        
        # Check if already enrolled
        if self.enrollments.filter(student=user, is_active=True).exists():
            return False, "Already enrolled"
        
        return True, "Can enroll"

    def get_course_progress_for_user(self, user):
        """Get course progress percentage for a specific user"""
        # This will be implemented when we add content management
        return 0

    @property
    def is_published(self):
        return self.status == 'published'

    @property
    def total_duration_hours(self):
        return self.duration_weeks * self.hours_per_week




class CourseModule(models.Model):
    """Course modules for organizing content"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = ['course', 'order']

    def __str__(self):
        return f"{self.course.course_code} - Module {self.order}: {self.title}"

    def get_lessons_count(self):
        return self.lessons.filter(is_active=True).count()

# courses/models.py - Enhanced Lesson Models

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
User = get_user_model()

# courses/models.py - SIMPLE LESSON MODEL

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# courses/models.py - Enhanced Lesson Models

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
import os

User = get_user_model()

class CourseLesson(models.Model):
    """Enhanced lesson with multiple content types"""
    
    LESSON_TYPE_CHOICES = [
        ('text', 'Text Content'),
        ('video', 'Video'),
        ('pdf', 'PDF Document'),
        ('mixed', 'Mixed Content'),
    ]
    
    module = models.ForeignKey('CourseModule', on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField()
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPE_CHOICES, default='text')
    order = models.IntegerField(default=1)
    
    # Duration
    duration_minutes = models.PositiveIntegerField(default=0, help_text="Lesson duration in minutes")
    
    # Content fields
    text_content = models.TextField(blank=True, help_text="Rich text content for the lesson")
    
    # Video content
    video_file = models.FileField(
        upload_to='lesson_videos/', 
        blank=True, null=True,
        validators=[FileExtensionValidator(['mp4', 'avi', 'mkv', 'mov'])],
        help_text="Upload video file (mp4, avi, mkv, mov)"
    )
    youtube_url = models.URLField(
        blank=True, 
        help_text="YouTube/Vimeo URL"
    )
    vimeo_url = models.URLField(blank=True, help_text="Vimeo URL")
    
    # Document content
    pdf_file = models.FileField(
        upload_to='lesson_pdfs/', 
        blank=True, null=True,
        validators=[FileExtensionValidator(['pdf'])],
        help_text="Upload PDF document"
    )
    
    # Additional resources
    additional_notes = models.TextField(blank=True, help_text="Additional notes or instructions")
    
    # Settings
    is_free_preview = models.BooleanField(default=False, help_text="Can be viewed without enrollment")
    is_active = models.BooleanField(default=True)
    is_mandatory = models.BooleanField(default=True, help_text="Required for course completion")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = ['module', 'order']

    def __str__(self):
        return f"{self.module.course.course_code} - {self.title}"
    
    def save(self, *args, **kwargs):
        # Auto-set order if not provided
        if not self.order:
            last_lesson = self.module.lessons.order_by('-order').first()
            self.order = (last_lesson.order + 1) if last_lesson else 1
        super().save(*args, **kwargs)

    def get_video_url(self):
        """Get the appropriate video URL"""
        if self.video_file:
            return self.video_file.url
        elif self.youtube_url:
            return self.youtube_url
        elif self.vimeo_url:
            return self.vimeo_url
        return None

    def has_video_content(self):
        """Check if lesson has any video content"""
        return bool(self.video_file or self.youtube_url or self.vimeo_url)

    def has_document_content(self):
        """Check if lesson has document content"""
        return bool(self.pdf_file)

    def get_content_types(self):
        """Get list of content types in this lesson"""
        types = []
        if self.text_content:
            types.append('Text')
        if self.has_video_content():
            types.append('Video')
        if self.has_document_content():
            types.append('PDF')
        return types


class LessonAttachment(models.Model):
    """Additional files attached to lessons"""
    
    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, related_name='attachments')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(
        upload_to='lesson_attachments/',
        validators=[FileExtensionValidator([
            'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 
            'zip', 'rar', 'txt', 'jpg', 'png', 'gif'
        ])]
    )
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    download_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def get_file_extension(self):
        return os.path.splitext(self.file.name)[1].lower()

    def get_file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2)

# courses/models.py - UPDATE LessonProgress

class LessonProgress(models.Model):
    """Track student progress on BOTH CourseLesson AND BatchLesson"""
    
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    student = models.ForeignKey(
        User, on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )
    
    # ✅ OPTION 1: Separate fields for both types
    course_lesson = models.ForeignKey(
        'CourseLesson', 
        on_delete=models.CASCADE, 
        related_name='progress_records',
        null=True, blank=True  # Allow null
    )
    
    batch_lesson = models.ForeignKey(
        'BatchLesson',
        on_delete=models.CASCADE,
        related_name='progress_records',
        null=True, blank=True  # Allow null
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    # Progress tracking
    time_spent_minutes = models.PositiveIntegerField(default=0)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        # ✅ Remove old unique_together
        ordering = ['-last_accessed']
        indexes = [
            models.Index(fields=['student', 'course_lesson']),
            models.Index(fields=['student', 'batch_lesson']),
        ]
    
    def __str__(self):
        lesson_title = self.batch_lesson.title if self.batch_lesson else self.course_lesson.title
        return f"{self.student.username} - {lesson_title} ({self.status})"
    
    def mark_as_completed(self):
        from django.utils import timezone
        self.status = 'completed'
        self.completion_percentage = 100.00
        if not self.completed_at:
            self.completed_at = timezone.now()
        self.save()
    
    def mark_as_started(self):
        from django.utils import timezone
        if self.status == 'not_started':
            self.status = 'in_progress'
            self.started_at = timezone.now()
            self.save()
# Enhanced Enrollment Model (update your existing one)

class Enrollment(models.Model):
    """Enhanced enrollment model"""
    
    STATUS_CHOICES = [
        ('enrolled', 'Enrolled'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
        ('suspended', 'Suspended'),
    ]
    
    GRADE_CHOICES = [
        ('A+', 'A+ (90-100)'),
        ('A', 'A (85-89)'),
        ('B+', 'B+ (80-84)'),
        ('B', 'B (75-79)'),
        ('C+', 'C+ (70-74)'),
        ('C', 'C (65-69)'),
        ('D', 'D (60-64)'),
        ('F', 'F (Below 60)'),
        ('I', 'Incomplete'),
        ('W', 'Withdrawn'),
    ]

    student = models.ForeignKey(
        User, on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name='enrollments'
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Academic Information
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_time_spent_minutes = models.PositiveIntegerField(default=0)
    
    # Payment Information
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=20, default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    is_active = models.BooleanField(default=True)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-enrolled_at']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['course', 'is_active']),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.course.title} ({self.status})"

    def update_progress(self):
        """Update progress based on completed lessons"""
        # This will be implemented with content management
        pass

    def get_time_spent_hours(self):
        return round(self.total_time_spent_minutes / 60, 1)

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if new enrollment
        super().save(*args, **kwargs)
        
        # Auto-create subscription for new enrollment
        if is_new and self.is_active:
            self.create_subscription()
    
    def create_subscription(self):
        """Auto-create subscription when enrolled"""
        from datetime import timedelta
        
        # Check if subscription already exists
        existing = StudentSubscription.objects.filter(
            student=self.student,
            course=self.course
        ).first()
        
        if not existing:
            # Create new subscription
            StudentSubscription.objects.create(
                student=self.student,
                course=self.course,
                max_devices=2,  # Default: 2 devices
                current_devices=0,
                is_active=True,
                expires_at=None  # Lifetime access (or set expiry date)
                # expires_at=timezone.now() + timedelta(days=365)  # 1 year
            )
        
class CourseReview(models.Model):
    """Course reviews and ratings"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    student = models.ForeignKey(
        User, on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review_text = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['course', 'student']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} - {self.course.title} ({self.rating}★)"


class CourseFAQ(models.Model):
    """Frequently Asked Questions for courses"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.course.title} - FAQ: {self.question[:50]}..."
    
# batch management

# courses/models.py - Add these SIMPLE models to your existing file

class Batch(models.Model):
    """Simple batch model - zyada complex nahi"""
    
    CONTENT_CHOICES = [
        ('fresh', 'Fresh Content (Empty)'),
        ('copy', 'Copy Course Content'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]
    
    # Basic info
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='batches')
    name = models.CharField(max_length=200)  # "Spring 2025", "Weekend Batch"
    code = models.CharField(max_length=50, unique=True, blank=True)  # Auto-generated
    
    # Content type
    content_type = models.CharField(max_length=10, choices=CONTENT_CHOICES, default='copy')
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Capacity
    max_students = models.PositiveIntegerField(default=30)
    
    # Instructor
    instructor = models.ForeignKey(
        User, on_delete=models.CASCADE,
        limit_choices_to={'role': 'instructor'}
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_batches'  # <-- Yeh add karo
    )
    DELIVERY_MODE_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('hybrid', 'Hybrid'),
    ]
    
    delivery_mode = models.CharField(
        max_length=20, 
        choices=DELIVERY_MODE_CHOICES, 
        default='online'
    )
    
    # Offline-specific fields
    classroom_location = models.CharField(max_length=200, blank=True)
    building_name = models.CharField(max_length=100, blank=True)
    floor_number = models.CharField(max_length=10, blank=True)
    classroom_capacity = models.IntegerField(default=30)
    
    # Geolocation for attendance
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    attendance_radius_meters = models.IntegerField(
        default=50, 
        help_text="Allowed distance for marking attendance"
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def is_offline(self):
        return self.delivery_mode == 'offline'
    
    def is_hybrid(self):
        return self.delivery_mode == 'hybrid'
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.course.title} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate code
        if not self.code:
            import random
            import string
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            self.code = f"{self.course.course_code}-{suffix}"
        super().save(*args, **kwargs)
        
        # Copy course content if needed
        if self.content_type == 'copy' and not self.batch_modules.exists():
            self.copy_course_content()
    
    def copy_course_content(self):
        """Copy modules and lessons from course"""
        for course_module in self.course.modules.filter(is_active=True):
            # Create batch module
            batch_module = BatchModule.objects.create(
                batch=self,
                title=course_module.title,
                description=course_module.description,
                order=course_module.order
            )
            
            # Copy lessons
            for course_lesson in course_module.lessons.filter(is_active=True):
                BatchLesson.objects.create(
                    batch_module=batch_module,
                    title=course_lesson.title,
                    description=course_lesson.description,
                    lesson_type=course_lesson.lesson_type,
                    text_content=course_lesson.text_content,
                    youtube_url=course_lesson.youtube_url,
                    order=course_lesson.order
                )
    
    def get_enrolled_count(self):
        return self.enrollments.filter(is_active=True).count()
    
    def get_available_seats(self):
        return self.max_students - self.get_enrolled_count()


class BatchModule(models.Model):
    """Simple batch module"""
    
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='batch_modules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ['batch', 'order']

    def __str__(self):
        return f"{self.batch.name} - {self.title}"


class BatchLesson(models.Model):
    """Simple batch lesson"""
    
    batch_module = models.ForeignKey(BatchModule, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField()
    lesson_type = models.CharField(max_length=20, choices=CourseLesson.LESSON_TYPE_CHOICES, default='text')
    order = models.PositiveIntegerField(default=1)
    
    # Simple content fields
    text_content = models.TextField(blank=True)
    youtube_url = models.URLField(blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ['batch_module', 'order']

    def __str__(self):
        return f"{self.batch_module.batch.name} - {self.title}"

# courses/models.py - Replace your existing BatchEnrollment model with this:
# courses/models.py - BatchEnrollment with DEBUGGING

class BatchEnrollment(models.Model):
    """Batch enrollment with independent batch-level lock"""
    
    STATUS_CHOICES = [
        ('enrolled', 'Enrolled'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    ]
    
    student = models.ForeignKey(
        User, on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name='batch_enrollments'
    )
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['student', 'batch']

    def __str__(self):
        return f"{self.student.username} - {self.batch.name}"
    
    
    @property
    def is_locked(self):
        """Check if THIS specific batch is locked - WITH DEBUGGING"""
        
        print(f"\n=== CHECKING LOCK for Enrollment {self.id} ===")
        print(f"Student: {self.student.username}")
        print(f"Batch: {self.batch.name}")
        print(f"Batch Status: {self.batch.status}")
        print(f"Enrollment is_active: {self.is_active}")
        
        # Check 1: Batch inactive ho to NOT LOCKED (just unavailable)
        if not self.is_active:
            print(f"✓ Enrollment INACTIVE - Returning TRUE (locked)")
            return True
        
        # Check 2: Batch completed/draft
        if self.batch.status == 'completed':
            print(f"✓ Batch COMPLETED - Returning FALSE (not locked, just completed)")
            return False
            
        if self.batch.status != 'active':
            print(f"✓ Batch NOT ACTIVE ({self.batch.status}) - Returning FALSE")
            return False
        
        # Check 3: Admin batch-specific lock (HIGHEST PRIORITY)
        try:
            from fees.models import BatchAccessControl
            batch_control = BatchAccessControl.objects.get(
                student=self.student,
                batch=self.batch
            )
            if not batch_control.is_access_allowed():
                print(f"✓ ADMIN LOCK found - Returning TRUE")
                return True
            else:
                print(f"✓ Admin control exists but access allowed")
        except BatchAccessControl.DoesNotExist:
            print(f"✓ No admin lock found")
        
        # Check 4: Fee-based lock (ONLY if admin not locked)
        try:
            from fees.models import StudentFeeAssignment
            fee_assignment = StudentFeeAssignment.objects.get(
                student=self.student,
                course=self.batch.course
            )
            is_batch_locked = fee_assignment.is_batch_locked(self.batch)
            print(f"✓ Fee assignment found - is_batch_locked: {is_batch_locked}")
            return is_batch_locked
        except StudentFeeAssignment.DoesNotExist:
            print(f"✓ No fee assignment found")
        
        print(f"✓ FINAL: Returning FALSE (unlocked)")
        return False
    
    def get_lock_reason(self):
        """Get lock reason - WITH DEBUGGING"""
        
        print(f"\n=== GETTING LOCK REASON for Enrollment {self.id} ===")
        
        if not self.is_locked:
            print(f"✓ Not locked - Returning None")
            return None
        
        # Check inactive
        if not self.is_active:
            print(f"✓ Enrollment INACTIVE - Reason: 'inactive'")
            return 'inactive'
        
        # Check admin lock
        try:
            from fees.models import BatchAccessControl
            batch_control = BatchAccessControl.objects.get(
                student=self.student,
                batch=self.batch
            )
            if not batch_control.is_access_allowed():
                print(f"✓ Admin lock found - Reason: 'admin'")
                return 'admin'
        except:
            print(f"✓ No admin lock")
            pass
        
        # Check fee lock
        try:
            from fees.models import StudentFeeAssignment
            fee_assignment = StudentFeeAssignment.objects.get(
                student=self.student,
                course=self.batch.course
            )
            if fee_assignment.is_batch_locked(self.batch):
                print(f"✓ Fee lock found - Reason: 'payment'")
                return 'payment'
        except:
            print(f"✓ No fee lock")
            pass
        
        print(f"✓ Unknown reason - Returning None")
        return None



# courses/models.py - ADD AT THE END (after BatchEnrollment)

# courses/models.py

# courses/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class StudentDeviceLimit(models.Model):
    """Global device limit per student"""
    
    student = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name='device_limit'
    )
    
    max_devices = models.PositiveIntegerField(default=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.student.username} - Max: {self.max_devices}"
    
    def current_device_count(self):
        return self.devices.filter(is_active=True).count()
    
    def can_add_device(self):
        return self.current_device_count() < self.max_devices


class DeviceSession(models.Model):
    """Track devices using fingerprint"""
    
    student_limit = models.ForeignKey(
        StudentDeviceLimit, 
        on_delete=models.CASCADE, 
        related_name='devices'
    )
    
    device_id = models.CharField(max_length=200,  help_text="SHA256 fingerprint")
    device_name = models.CharField(max_length=200, blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    
    first_login = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.student_limit.student.username} - {self.device_name}"


class StudentLoginLog(models.Model):
    """Attendance tracking"""
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_logs')
    device_session = models.ForeignKey(DeviceSession, on_delete=models.SET_NULL, null=True, blank=True)
    
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    session_duration = models.PositiveIntegerField(default=0)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.TextField(blank=True)
    
    def calculate_duration(self):
        if self.logout_time:
            delta = self.logout_time - self.login_time
            self.session_duration = int(delta.total_seconds() / 60)
            self.save()




