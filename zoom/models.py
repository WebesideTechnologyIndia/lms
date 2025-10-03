from django.db import models

# Create your models here.
# zoom/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid



# zoom/models.py - Updated Configuration Model

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class ZoomConfiguration(models.Model):
    """Dynamic Zoom API Configuration - Admin can change anytime"""
    
    # Admin Details
    organization_name = models.CharField(max_length=200, default="My LMS Organization")
    admin_email = models.EmailField(help_text="Admin email for this Zoom configuration")
    
    # Zoom API Credentials (Admin will fill these)
    account_id = models.CharField(
        max_length=100, 
        blank=True,  # Remove default, admin must fill
        help_text="Your Zoom Account ID from marketplace.zoom.us"
    )
    client_id = models.CharField(
        max_length=100, 
        blank=True,  # Remove default, admin must fill
        help_text="Your Zoom App Client ID"
    )
    client_secret = models.CharField(
        max_length=100, 
        blank=True,  # Remove default, admin must fill
        help_text="Your Zoom App Client Secret"
    )
    secret_token = models.CharField(
        max_length=100, 
        blank=True,  # Remove default, admin must fill
        help_text="Your Zoom App Secret Token for webhooks"
    )
    
    # Default Meeting Settings (Admin can customize)
    default_host_video = models.BooleanField(default=True)
    default_participant_video = models.BooleanField(default=True)
    default_join_before_host = models.BooleanField(default=False)
    default_mute_upon_entry = models.BooleanField(default=True)
    default_waiting_room = models.BooleanField(default=True)
    default_auto_recording = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Recording'),
            ('local', 'Local Recording'),
            ('cloud', 'Cloud Recording'),
        ],
        default='cloud'
    )
    
    # Webhook URL (Auto-generated)
    webhook_url = models.URLField(blank=True, help_text="Auto-generated webhook URL")
    
    # Status
    is_active = models.BooleanField(default=False)  # Default False until admin configures
    is_configured = models.BooleanField(default=False)  # Auto-set when all fields filled
    
    # Connection Test
    last_test_date = models.DateTimeField(null=True, blank=True)
    test_status = models.CharField(
        max_length=20,
        choices=[
            ('not_tested', 'Not Tested'),
            ('success', 'Success'),
            ('failed', 'Failed'),
        ],
        default='not_tested'
    )
    test_error_message = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'role': 'superadmin'}
    )
    
    class Meta:
        verbose_name = "Zoom Configuration"
        verbose_name_plural = "Zoom Configurations"
    
    def __str__(self):
        return f"Zoom Config - {self.organization_name} ({'Active' if self.is_active else 'Inactive'})"
    
    def clean(self):
        """Validate that all required fields are filled for activation"""
        if self.is_active:
            required_fields = ['account_id', 'client_id', 'client_secret']
            missing_fields = [field for field in required_fields if not getattr(self, field)]
            
            if missing_fields:
                raise ValidationError(
                    f"Cannot activate without these fields: {', '.join(missing_fields)}"
                )
    
    def save(self, *args, **kwargs):
        # Auto-generate webhook URL
        if not self.webhook_url:
            # This will be set by admin or auto-detected
            self.webhook_url = f"https://yourdomain.com/zoom/webhook/"
        
        # Check if configuration is complete
        required_fields = ['account_id', 'client_id', 'client_secret']
        self.is_configured = all(getattr(self, field) for field in required_fields)
        
        # Only allow one active configuration
        if self.is_active:
            ZoomConfiguration.objects.filter(is_active=True).exclude(id=self.id).update(is_active=False)
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_config(cls):
        """Get the currently active configuration"""
        return cls.objects.filter(is_active=True, is_configured=True).first()
    
    def test_connection(self):
        """Test Zoom API connection"""
        try:
            from .services import ZoomAPIService
            service = ZoomAPIService(config=self)
            token = service.get_access_token()
            
            if token:
                self.test_status = 'success'
                self.test_error_message = ''
                self.last_test_date = timezone.now()
                self.save()
                return True, "Connection successful!"
            else:
                self.test_status = 'failed'
                self.test_error_message = 'Failed to generate access token'
                self.save()
                return False, "Failed to generate access token"
                
        except Exception as e:
            self.test_status = 'failed'
            self.test_error_message = str(e)
            self.save()
            return False, str(e)
        

# courses/models.py - Updated BatchSession Model

class BatchSession(models.Model):
    """Batch Sessions with Zoom Integration and Recurring Support"""
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    SESSION_TYPE_CHOICES = [
        ('live_class', 'Live Class'),
        ('doubt_session', 'Doubt Session'),
        ('workshop', 'Workshop'),
        ('exam', 'Online Exam'),
    ]
    
    RECURRING_TYPE_CHOICES = [
        ('none', 'Single Session'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('custom', 'Custom Days'),
    ]
    
    # Basic Info
    batch = models.ForeignKey(
        'courses.Batch', 
        on_delete=models.CASCADE, 
        related_name='sessions'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, default='live_class')
    
    # Schedule
    scheduled_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.IntegerField(default=60)
    
    # Recurring Session Fields
    is_recurring = models.BooleanField(default=False)
    recurring_type = models.CharField(
        max_length=20, 
        choices=RECURRING_TYPE_CHOICES,
        default='none'
    )
    recurring_end_date = models.DateField(null=True, blank=True)
    recurring_days = models.CharField(
        max_length=20, 
        blank=True,
        help_text="For weekly: 1,2,3,4,5,6,7 (Mon-Sun)"
    )
    parent_session = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='recurring_sessions'
    )
    session_sequence = models.IntegerField(default=1, help_text="Session number in recurring series")
    
    # Zoom Details
    zoom_meeting_id = models.CharField(max_length=100, blank=True, null=True)
    zoom_meeting_password = models.CharField(max_length=50, blank=True, null=True)
    zoom_join_url = models.URLField(blank=True, null=True)
    zoom_start_url = models.URLField(blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    is_recorded = models.BooleanField(default=True)
    max_participants = models.IntegerField(default=100)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_sessions'
    )
    
    class Meta:
        ordering = ['-scheduled_date', '-start_time']
        verbose_name = "Batch Session"
        verbose_name_plural = "Batch Sessions"
        indexes = [
            models.Index(fields=['batch', 'scheduled_date']),
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['parent_session']),
        ]
    
    def __str__(self):
        return f"{self.batch.name} - {self.title}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate duration
        if self.start_time and self.end_time:
            from datetime import datetime, timedelta
            start = datetime.combine(self.scheduled_date, self.start_time)
            end = datetime.combine(self.scheduled_date, self.end_time)
            if end < start:  # Next day
                end += timedelta(days=1)
            self.duration_minutes = int((end - start).total_seconds() / 60)
        
        super().save(*args, **kwargs)
    
    def get_zoom_meeting_time(self):
        """Get meeting time in Zoom format"""
        from datetime import datetime
        if self.scheduled_date and self.start_time:
            meeting_datetime = datetime.combine(self.scheduled_date, self.start_time)
            return meeting_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        return None
    
    # zoom/models.py - BatchSession model mein is_live_now method fix karo:

    def is_live_now(self):
        """Check if session is currently live"""
        from django.utils import timezone
        from datetime import datetime

        now = timezone.now()

        # Make sure we're using timezone-aware datetimes
        meeting_start = timezone.make_aware(
            datetime.combine(self.scheduled_date, self.start_time)
        )
        meeting_end = timezone.make_aware(
            datetime.combine(self.scheduled_date, self.end_time)
        )

        return meeting_start <= now <= meeting_end
    
    def can_start_meeting(self, user):
        """Check if user can start the meeting"""
        return user == self.batch.instructor or user.role == 'superadmin'
    
    def can_join_meeting(self, user):
        """Check if user can join the meeting"""
        # Students enrolled in batch or instructor or superadmin can join
        if user.role == 'superadmin':
            return True
        if user.role == 'instructor' and user == self.batch.instructor:
            return True
        if user.role == 'student':
            return self.batch.enrollments.filter(student=user, is_active=True).exists()
        return False
    
    def get_recurring_info(self):
        """Get information about recurring sessions"""
        if not self.is_recurring:
            return None
        
        info = {
            'type': self.get_recurring_type_display(),
            'total_sessions': 0,
            'completed_sessions': 0,
            'upcoming_sessions': 0,
        }
        
        if self.parent_session:
            # This is a child session
            parent = self.parent_session
            all_sessions = parent.recurring_sessions.all()
            info['total_sessions'] = all_sessions.count() + 1  # +1 for parent
            info['completed_sessions'] = all_sessions.filter(status='completed').count()
            if parent.status == 'completed':
                info['completed_sessions'] += 1
            info['upcoming_sessions'] = info['total_sessions'] - info['completed_sessions']
        else:
            # This is the parent session
            all_sessions = self.recurring_sessions.all()
            info['total_sessions'] = all_sessions.count() + 1  # +1 for self
            info['completed_sessions'] = all_sessions.filter(status='completed').count()
            if self.status == 'completed':
                info['completed_sessions'] += 1
            info['upcoming_sessions'] = info['total_sessions'] - info['completed_sessions']
        
        return info
    
    def get_all_recurring_sessions(self):
        """Get all sessions in the recurring series"""
        if self.parent_session:
            parent = self.parent_session
            return [parent] + list(parent.recurring_sessions.all().order_by('scheduled_date'))
        elif self.is_recurring:
            return [self] + list(self.recurring_sessions.all().order_by('scheduled_date'))
        else:
            return [self]



# zoom/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class SessionAttendance(models.Model):
    """Track session attendance with detailed metrics"""
    
    session = models.ForeignKey(
        'BatchSession', 
        on_delete=models.CASCADE, 
        related_name='attendances'
    )
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name='session_attendances'
    )
    
    # Attendance Details
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)
    
    # Zoom Integration
    zoom_participant_id = models.CharField(max_length=100, blank=True)
    zoom_user_name = models.CharField(max_length=100, blank=True)
    
    # Status
    is_present = models.BooleanField(default=False)
    attendance_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Percentage of session attended"
    )
    
    # Manual override by instructor
    manually_marked = models.BooleanField(default=False)
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendances'
    )
    
    # Notes
    notes = models.TextField(blank=True, help_text="Optional attendance notes")
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['session', 'student']
        ordering = ['-created_at']
        verbose_name = 'Session Attendance'
        verbose_name_plural = 'Session Attendances'
    
    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.student.get_full_name()} - {self.session.title} ({status})"
    
    def calculate_attendance_percentage(self):
        """Calculate attendance percentage based on duration"""
        if self.joined_at and self.left_at:
            # Calculate actual duration attended
            total_duration = (self.left_at - self.joined_at).total_seconds() / 60
            session_duration = self.session.duration_minutes
            
            if session_duration > 0:
                percentage = min(100, (total_duration / session_duration) * 100)
                self.attendance_percentage = round(percentage, 2)
                self.duration_minutes = int(total_duration)
                
                # Mark present if attended >= 75% of session
                self.is_present = self.attendance_percentage >= 75
                self.save(update_fields=[
                    'attendance_percentage', 
                    'duration_minutes', 
                    'is_present'
                ])
    
    def mark_present(self, marked_by=None):
        """Manually mark student as present"""
        self.is_present = True
        self.manually_marked = True
        self.marked_by = marked_by
        if not self.joined_at:
            self.joined_at = timezone.now()
        self.save()
    
    def mark_absent(self):
        """Mark student as absent"""
        self.is_present = False
        self.joined_at = None
        self.left_at = None
        self.duration_minutes = 0
        self.attendance_percentage = 0
        self.save()

class ZoomRecording(models.Model):
    """Zoom Recordings Management"""
    
    RECORDING_TYPE_CHOICES = [
        ('cloud', 'Cloud Recording'),
        ('local', 'Local Recording'),
    ]
    
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    # Session Link
    session = models.ForeignKey(
        BatchSession, 
        on_delete=models.CASCADE, 
        related_name='recordings'
    )
    
    # Recording Details
    zoom_recording_id = models.CharField(max_length=100, unique=True)
    recording_type = models.CharField(max_length=20, choices=RECORDING_TYPE_CHOICES, default='cloud')
    file_type = models.CharField(max_length=10, default='mp4')  # mp4, m4a, txt, etc.
    
    # File Info
    download_url = models.URLField()
    play_url = models.URLField(blank=True)
    file_size = models.BigIntegerField(default=0)  # in bytes
    duration_minutes = models.IntegerField(default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    recording_start = models.DateTimeField()
    recording_end = models.DateTimeField()
    
    # Access Control
    is_public = models.BooleanField(default=False)
    password_required = models.BooleanField(default=True)
    recording_password = models.CharField(max_length=50, blank=True)
    
    # Tracking
    download_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recording_start']
        verbose_name = "Zoom Recording"
        verbose_name_plural = "Zoom Recordings"
    
    def __str__(self):
        return f"{self.session.title} - Recording ({self.get_file_size_mb()}MB)"
    
    def get_file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    def get_duration_formatted(self):
        """Get formatted duration"""
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

class SessionFeedback(models.Model):
    """Session Feedback from Students"""
    
    RATING_CHOICES = [
        (1, 'Very Poor'),
        (2, 'Poor'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]
    
    session = models.ForeignKey(
        BatchSession, 
        on_delete=models.CASCADE, 
        related_name='feedbacks'
    )
    student = models.ForeignKey(
        User, on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )
    
    # Ratings
    content_rating = models.IntegerField(choices=RATING_CHOICES)
    instructor_rating = models.IntegerField(choices=RATING_CHOICES)
    technical_rating = models.IntegerField(choices=RATING_CHOICES)
    overall_rating = models.IntegerField(choices=RATING_CHOICES)
    
    # Feedback
    feedback_text = models.TextField(blank=True)
    suggestions = models.TextField(blank=True)
    
    # Status
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['session', 'student']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.session.title} - {self.student.get_full_name()} ({self.overall_rating}★)"

class ZoomWebhookLog(models.Model):
    """Log Zoom webhook events"""
    
    EVENT_TYPE_CHOICES = [
        ('meeting.started', 'Meeting Started'),
        ('meeting.ended', 'Meeting Ended'),
        ('meeting.participant_joined', 'Participant Joined'),
        ('meeting.participant_left', 'Participant Left'),
        ('recording.completed', 'Recording Completed'),
    ]
    
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    zoom_meeting_id = models.CharField(max_length=100)
    event_data = models.JSONField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.zoom_meeting_id}"