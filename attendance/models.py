# attendance/models.py - QR + Location Based

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files import File
import uuid
from math import radians, cos, sin, asin, sqrt
from courses.models import *
from django.db.models import Q  # ✅ Add this import

User = get_user_model()

from django.conf import settings
from datetime import timedelta
# attendance/models.py - ADD QR CODE GENERATION

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files import File
import uuid
from math import radians, cos, sin, asin, sqrt
from courses.models import *
from django.db.models import Q
from django.conf import settings
from datetime import timedelta

User = get_user_model()

class AttendanceSession(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    
    start_time = models.DateTimeField(
        default=timezone.now,
        help_text="Session start time (with date and timezone)"
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Session end time (with date and timezone)"
    )
    
    classroom_location = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    qr_secret = models.CharField(max_length=255, unique=True)
    
    # ✅ ADD THIS - QR Code Image Field
    qr_code = models.ImageField(
        upload_to='attendance_qr_codes/',
        blank=True,
        null=True,
        help_text="Generated QR code image"
    )
    
    is_active = models.BooleanField(default=True)
    allowed_radius_meters = models.IntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_sessions',
        limit_choices_to=Q(role='instructor')
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        # Set end_time to 1 hour after start_time if not provided
        if not self.end_time and self.start_time:
            self.end_time = self.start_time + timedelta(hours=1)
        
        # ✅ Generate QR secret if not exists
        if not self.qr_secret:
            self.qr_secret = str(uuid.uuid4())
        
        # ✅ Generate QR code ONLY if it doesn't exist yet
        if not self.qr_code:
            # Save first to get ID
            is_new = self.pk is None
            if is_new:
                super().save(*args, **kwargs)
            
            # Generate QR code data
            qr_data = f"ATTENDANCE:{self.id}:{self.qr_secret}"
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to BytesIO
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Save to model
            file_name = f'qr_session_{self.id}_{self.qr_secret[:8]}.png'
            self.qr_code.save(file_name, File(buffer), save=False)
            
            # If already saved (is_new=True), update only qr_code field
            if is_new:
                super().save(update_fields=['qr_code'])
                return
        
        super().save(*args, **kwargs)
    
    def is_open_now(self):
        """Check if session is currently open"""
        current_time = timezone.now()
        
        if not self.start_time or not self.end_time:
            return False
        
        return self.start_time <= current_time <= self.end_time
    
    def get_stats(self):
        """Calculate and return attendance statistics for this session"""
        from django.db.models import Count, Q
        
        total_students = BatchEnrollment.objects.filter(
            batch=self.batch,
            is_active=True
        ).count()
        
        attendances = self.attendances.aggregate(
            total_marked=Count('id'),
            present_count=Count('id', filter=Q(is_present=True)),
            absent_count=Count('id', filter=Q(is_present=False)),
            late_count=Count('id', filter=Q(is_late=True)),
            qr_count=Count('id', filter=Q(marking_method='qr_scan')),
            manual_count=Count('id', filter=Q(marking_method='manual')),
        )
        
        attendance_percentage = (
            (attendances['present_count'] / total_students * 100) 
            if total_students > 0 else 0
        )
        
        return {
            'total_students': total_students,
            'total_marked': attendances['total_marked'],
            'present_count': attendances['present_count'],
            'absent_count': attendances['absent_count'],
            'late_count': attendances['late_count'],
            'not_marked': total_students - attendances['total_marked'],
            'attendance_percentage': round(attendance_percentage, 2),
            'qr_count': attendances['qr_count'],
            'manual_count': attendances['manual_count'],
        }
    
    def __str__(self):
        return f"{self.batch.name} - {self.start_time.strftime('%d/%m/%Y %I:%M %p')}"

# ... rest of your models remain the same ...

class Attendance(models.Model):
    """Student attendance record"""
    
    MARKING_METHOD_CHOICES = [
        ('qr_scan', 'QR Code Scan'),
        ('manual', 'Manual by Instructor'),
    ]
    
    session = models.ForeignKey(
        AttendanceSession, 
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    # ✅ FIXED: Use Q object instead of lambda
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to=Q(role='student')  # Changed from lambda to Q object
    )
    
    # How was attendance marked
    marking_method = models.CharField(max_length=20, choices=MARKING_METHOD_CHOICES, default='qr_scan')
    
    # Student's location when scanning QR
    student_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    student_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Calculated distance from classroom
    distance_from_classroom = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Distance in meters from classroom"
    )
    
    # Status
    is_present = models.BooleanField(default=True)
    is_late = models.BooleanField(default=False)
    is_within_radius = models.BooleanField(default=False, help_text="Was student within allowed radius?")
    
    # Manual marking
    marked_by_instructor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manually_marked_attendances'
    )
    
    notes = models.TextField(blank=True)
    marked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['session', 'student']
        ordering = ['-marked_at']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.session.start_time.date()} - {'Present' if self.is_present else 'Absent'}"
    
    def calculate_distance(self):
        """Calculate distance between student and classroom using Haversine formula"""
        if not self.student_latitude or not self.student_longitude:
            return None
        
        # Convert to radians
        lon1 = radians(float(self.session.longitude))
        lat1 = radians(float(self.session.latitude))
        lon2 = radians(float(self.student_longitude))
        lat2 = radians(float(self.student_latitude))
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Earth radius in meters
        radius_earth = 6371000
        distance = c * radius_earth
        
        return int(distance)
    
    def verify_location(self):
        """Check if student is within allowed radius"""
        distance = self.calculate_distance()
        
        if distance is None:
            self.is_within_radius = False
            self.distance_from_classroom = None
            return False
        
        self.distance_from_classroom = distance
        self.is_within_radius = distance <= self.session.allowed_radius_meters
        self.save(update_fields=['distance_from_classroom', 'is_within_radius'])
        
        return self.is_within_radius


class ManualAttendanceRequest(models.Model):
    """Student requests manual attendance if scan failed"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name='manual_requests'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attendance_requests'
    )
    
    reason = models.TextField(help_text="Why couldn't you scan QR?")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requests'
    )
    
    class Meta:
        unique_together = ['session', 'student']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.session.start_time.date()} - {self.status}"