from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils import timezone
import uuid

User = get_user_model()

class CertificateType(models.Model):
    """Types of certificates (Course Completion, Achievement, Participation)"""
    
    TYPE_CHOICES = [
        ('completion', 'Course Completion'),
        ('achievement', 'Achievement'),
        ('participation', 'Participation'),
        ('excellence', 'Excellence'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField(max_length=200)
    type_code = models.CharField(max_length=50, choices=TYPE_CHOICES, default='completion')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class CertificateTemplate(models.Model):
    """Certificate design templates"""
    
    ORIENTATION_CHOICES = [
        ('landscape', 'Landscape'),
        ('portrait', 'Portrait'),
    ]
    
    name = models.CharField(max_length=200)
    certificate_type = models.ForeignKey(CertificateType, on_delete=models.CASCADE, related_name='templates')
    
    # Design files
    template_file = models.FileField(
        upload_to='certificate_templates/',
        validators=[FileExtensionValidator(['html', 'pdf'])],
        help_text="Upload HTML template"
    )
    thumbnail = models.ImageField(upload_to='certificate_thumbnails/', blank=True, null=True)
    
    # Template configuration
    orientation = models.CharField(max_length=20, choices=ORIENTATION_CHOICES, default='landscape')
    width = models.IntegerField(default=297)  # mm (A4 landscape)
    height = models.IntegerField(default=210)  # mm
    
    # HTML/CSS content (for editing)
    html_content = models.TextField(help_text="HTML template with placeholders")
    css_content = models.TextField(blank=True, help_text="CSS styling")
    
    # Available placeholders
    available_placeholders = models.JSONField(
        default=dict,
        help_text="Available template variables like {student_name}, {course_name}"
    )
    
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.certificate_type.name})"
    
    def get_default_placeholders(self):
        """Default available placeholders"""
        return {
            '{student_name}': 'Student full name',
            '{course_name}': 'Course title',
            '{batch_name}': 'Batch name',
            '{completion_date}': 'Completion date',
            '{issue_date}': 'Certificate issue date',
            '{certificate_id}': 'Unique certificate ID',
            '{instructor_name}': 'Instructor name',
            '{grade}': 'Grade/Score',
            '{duration}': 'Course duration',
        }


class IssuedCertificate(models.Model):
    """Certificates issued to students"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ]
    
    # Unique identifier
    certificate_id = models.CharField(max_length=100, unique=True, editable=False)
    
    # Certificate details
    template = models.ForeignKey(CertificateTemplate, on_delete=models.PROTECT)
    certificate_type = models.ForeignKey(CertificateType, on_delete=models.PROTECT)
    
    # Recipient
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    
    # Context (what it's for)
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True)
    batch = models.ForeignKey('courses.Batch', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Certificate data
    student_name = models.CharField(max_length=200)  # Stored for consistency
    course_name = models.CharField(max_length=200, blank=True)
    batch_name = models.CharField(max_length=200, blank=True)
    
    # Metadata
    issue_date = models.DateField(default=timezone.now)
    completion_date = models.DateField(blank=True, null=True)
    
    # ✅ UPDATED FIELDS - Grade with help text
    grade = models.CharField(max_length=50, blank=True, help_text="Student grade (A+, 95%, etc.)")
    
    # ✅ NEW FIELD - Duration
    duration = models.CharField(max_length=100, blank=True, help_text="Course duration (3 Months, 12 Weeks)")
    
    remarks = models.TextField(blank=True)
    
    # Generated file
    generated_pdf = models.FileField(upload_to='certificates/issued/', blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True)
    
    # Tracking
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='certificates_issued')
    issued_at = models.DateTimeField(auto_now_add=True)
    
    # Verification
    verification_code = models.CharField(max_length=100, unique=True, editable=False)
    
    class Meta:
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['certificate_id']),
            models.Index(fields=['student', 'status']),
        ]
    
    def __str__(self):
        return f"Certificate #{self.certificate_id} - {self.student_name}"
    
    def save(self, *args, **kwargs):
        if not self.certificate_id:
            self.certificate_id = f"CERT-{uuid.uuid4().hex[:8].upper()}"
        
        if not self.verification_code:
            self.verification_code = uuid.uuid4().hex.upper()
        
        super().save(*args, **kwargs)
    
    def get_verification_url(self):
        """Get public verification URL"""
        from django.urls import reverse
        return reverse('certificates:verify', args=[self.verification_code])