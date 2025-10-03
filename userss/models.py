from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils import timezone
from datetime import date


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
    ("superadmin", "Super Admin"),
    ("instructor", "Instructor"), 
    ("student", "Student"),
    ("webinar_user", "Webinar User"),  # Add this line
)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="profile_pics/", blank=True, null=True
    )
    bio = models.TextField(max_length=500, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_users",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_absolute_url(self):
        return reverse("user_details", kwargs={"user_id": self.pk})
    
    def has_instructor_permission(self, permission_code):
        """Check if instructor has specific permission"""
        if self.role == 'superadmin':
            return True
        if self.role != 'instructor':
            return False
        
        try:
            instructor_profile = self.instructor_profile
            return instructor_profile.permissions.filter(
                permission__code=permission_code,
                is_active=True
            ).exists()
        except:
            return False
    
    def get_instructor_permissions(self):
        """Get all active permissions for instructor"""
        if self.role != 'instructor':
            return []
        
        try:
            return self.instructor_profile.permissions.filter(
                is_active=True
            ).select_related('permission')
        except:
            return []

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "User"
        verbose_name_plural = "Users"

class UserProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="profile"
    )
    student_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True)
    year_of_study = models.IntegerField(blank=True, null=True)  # For students
    specialization = models.CharField(max_length=100, blank=True)  # For instructors
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class InstructorPermission(models.Model):
    """Define available permissions for instructors"""
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True, help_text="Unique code like 'content_management'")
    description = models.TextField(help_text="What this permission allows")
    category = models.CharField(max_length=50, help_text="Category like 'Course Management', 'Email Marketing'")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True,
        limit_choices_to={'role': 'superadmin'}
    )
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = "Instructor Permission"
        verbose_name_plural = "Instructor Permissions"
    
    def __str__(self):
        return f"{self.category} - {self.name}"


class InstructorProfile(models.Model):
    """Extended profile for instructors with permissions"""
    
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='instructor_profile',
        limit_choices_to={'role': 'instructor'}
    )
    
    # Basic Info
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    qualification = models.TextField(blank=True, help_text="Educational qualifications")
    experience_years = models.PositiveIntegerField(default=0)
    
    # Contact Info
    office_location = models.CharField(max_length=100, blank=True)
    office_phone = models.CharField(max_length=15, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    
    # Professional Info
    joining_date = models.DateField(blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False, help_text="Admin approval for teaching")
    
    # Permissions assigned by admin
    # This will be handled through InstructorPermissionAssignment model
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_instructor_profiles',
        limit_choices_to={'role': 'superadmin'}
    )
    
    class Meta:
        verbose_name = "Instructor Profile"
        verbose_name_plural = "Instructor Profiles"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Instructor Profile"
    
    def get_assigned_permissions(self):
        """Get all assigned permissions"""
        return self.permissions.filter(is_active=True).select_related('permission')
    
    def has_permission(self, permission_code):
        """Check if instructor has specific permission"""
        return self.permissions.filter(
            permission__code=permission_code,
            is_active=True
        ).exists()
    

class InstructorPermissionAssignment(models.Model):
    """Assign permissions to instructors"""
    
    instructor = models.ForeignKey(
        InstructorProfile, 
        on_delete=models.CASCADE,
        related_name='permissions'
    )
    permission = models.ForeignKey(
        InstructorPermission, 
        on_delete=models.CASCADE
    )
    
    # Assignment details
    assigned_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True,
        limit_choices_to={'role': 'superadmin'}
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Admin notes about this permission")
    
    # Expiry (optional)
    expires_at = models.DateTimeField(blank=True, null=True, help_text="Permission expiry date")
    
    class Meta:
        unique_together = ['instructor', 'permission']
        ordering = ['-assigned_at']
        verbose_name = "Instructor Permission Assignment"
        verbose_name_plural = "Instructor Permission Assignments"
    
    def __str__(self):
        return f"{self.instructor.user.get_full_name()} - {self.permission.name}"
    
    def is_expired(self):
        """Check if permission is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def is_valid(self):
        """Check if permission is valid (active and not expired)"""
        return self.is_active and not self.is_expired()



class UserActivityLog(models.Model):
    ACTION_CHOICES = (
        ("login", "Login"),
        ("logout", "Logout"),
        ("create_user", "Created User"),
        ("update_user", "Updated User"),
        ("delete_user", "Deleted User"),
        ("create_course", "Created Course"),
        ("update_course", "Updated Course"),
        ("enroll_course", "Enrolled in Course"),
        ("permission_granted", "Permission Granted"),
        ("permission_revoked", "Permission Revoked"),
    )

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="activity_logs"
    )
    action = models.CharField(max_length=25, choices=ACTION_CHOICES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"
    
class EmailLimitSet(models.Model):
    email_limit_per_day = models.IntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Daily Email Limit: {self.email_limit_per_day}"

    class Meta:
        verbose_name = "Email Limit Setting"
        verbose_name_plural = "Email Limit Settings"


class EmailTemplateType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'role': 'superadmin'}
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class EmailTemplate(models.Model):
    name = models.CharField(max_length=100)
    template_type = models.ForeignKey(
        EmailTemplateType, 
        on_delete=models.CASCADE, 
        related_name='templates'
    )
    subject = models.CharField(max_length=200)
    email_body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'role__in': ['superadmin', 'instructor']}
    )

    def __str__(self):
        return f"{self.name} - {self.template_type.name}"


class EmailLog(models.Model):
    recipient_email = models.EmailField()
    recipient_user = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True
    )
    template_used = models.ForeignKey(
        EmailTemplate, on_delete=models.SET_NULL, null=True
    )
    template_type_used = models.ForeignKey(
        EmailTemplateType, on_delete=models.SET_NULL, null=True
    )
    subject = models.CharField(max_length=200)
    email_body = models.TextField()
    sent_date = models.DateField(auto_now_add=True)
    sent_time = models.DateTimeField(auto_now_add=True)
    is_sent_successfully = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    sent_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, related_name="sent_emails"
    )

    def __str__(self):
        status = "✅" if self.is_sent_successfully else "❌"
        return f"{status} {self.recipient_email} - {self.sent_date}"

    class Meta:
        ordering = ["-sent_time"]


class DailyEmailSummary(models.Model):
    date = models.DateField(unique=True, default=date.today)
    total_emails_sent = models.IntegerField(default=0)
    successful_emails = models.IntegerField(default=0)
    failed_emails = models.IntegerField(default=0)
    daily_limit = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.date} - {self.successful_emails}/{self.daily_limit} emails"

    class Meta:
        ordering = ["-date"]
        


# Add this model to your existing models.py

import random
from django.utils import timezone
from datetime import timedelta

class PasswordResetOTP(models.Model):
    """Model to store OTP for password reset"""
    
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='password_reset_otps'
    )
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Only set expiry on creation
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_otp(cls, user):
        """Generate a 6-digit OTP for user"""
        # Invalidate previous unused OTPs
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Generate new OTP
        otp_code = str(random.randint(100000, 999999))
        otp_instance = cls.objects.create(user=user, otp=otp_code)
        return otp_instance
    
    def is_valid(self):
        """Check if OTP is valid (not used and not expired)"""
        return not self.is_used and timezone.now() <= self.expires_at
    
    def __str__(self):
        return f"{self.user.email} - {self.otp} - {'Valid' if self.is_valid() else 'Invalid'}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Password Reset OTP"
        verbose_name_plural = "Password Reset OTPs"