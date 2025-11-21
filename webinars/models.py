from django.db import models

# Create your models here.
# webinars/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
import random
import string

User = get_user_model()

class WebinarCategory(models.Model):
    """Categories for webinars"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Webinar Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Webinar(models.Model):
    """Main webinar model"""
    
    WEBINAR_TYPE_CHOICES = [
        ('free', 'Free Webinar'),
        ('paid', 'Paid Webinar'),
    ]
    
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('live', 'Live Now'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic Info
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, help_text="Brief description for cards")
    
    # Webinar Details
    category = models.ForeignKey(WebinarCategory, on_delete=models.CASCADE, related_name='webinars')
    webinar_type = models.CharField(max_length=10, choices=WEBINAR_TYPE_CHOICES, default='free')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    
    # Pricing (for paid webinars)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Schedule
    scheduled_date = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60, help_text="Duration in minutes")
    
    # Capacity
    max_attendees = models.PositiveIntegerField(default=100)
    
    # Content
    thumbnail = models.ImageField(upload_to='webinar_thumbnails/', blank=True, null=True)
    webinar_link = models.URLField(blank=True, help_text="Zoom/Meet/Teams link")
    meeting_id = models.CharField(max_length=50, blank=True)
    meeting_password = models.CharField(max_length=50, blank=True)
    
    # Instructor
    instructor = models.ForeignKey(
        User, on_delete=models.CASCADE,
        limit_choices_to={'role__in': ['instructor', 'superadmin']},
        related_name='hosted_webinars'
    )
    
    # Learning outcomes
    learning_outcomes = models.TextField(help_text="What attendees will learn")
    prerequisites = models.TextField(blank=True, help_text="What attendees should know")
    
    # Email settings
    send_reminder_emails = models.BooleanField(default=True)
    reminder_hours_before = models.PositiveIntegerField(default=24, help_text="Send reminder X hours before")
    
    # Tracking
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_webinars'
    )
    
    # Stats
    total_registrations = models.PositiveIntegerField(default=0)
    actual_attendees = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['status', 'webinar_type']),
            models.Index(fields=['scheduled_date']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_webinar_type_display()})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('webinars:webinar_detail', kwargs={'slug': self.slug})
    
    def get_registration_count(self):
        return self.registrations.filter(is_active=True).count()
    
    def get_available_spots(self):
        return max(0, self.max_attendees - self.get_registration_count())
    
    def is_registration_open(self):
        """Check if registration is still open"""
        if self.status in ['completed', 'cancelled']:
            return False
        if timezone.now() > self.scheduled_date:
            return False
        return self.get_available_spots() > 0
    
    def is_upcoming(self):
        return self.status == 'upcoming' and timezone.now() < self.scheduled_date
    
    def is_live_now(self):
        now = timezone.now()
        end_time = self.scheduled_date + timedelta(minutes=self.duration_minutes)
        return self.scheduled_date <= now <= end_time
    
    def get_end_time(self):
        return self.scheduled_date + timedelta(minutes=self.duration_minutes)


# webinars/models.py - WebinarRegistration class mein ye changes karo

# webinars/models.py - WebinarRegistration class COMPLETE

import random
import string
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class WebinarRegistration(models.Model):
    """Webinar registrations with automatic user creation"""
    
    STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('attended', 'Attended'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Payment Pending'),
        ('paid', 'Paid'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Registration Info
    webinar = models.ForeignKey(Webinar, on_delete=models.CASCADE, related_name='registrations')
    
    # User Info (will be created automatically)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='webinar_registrations')
    
    # Registration Details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')
    registered_at = models.DateTimeField(auto_now_add=True)
    
    # Contact Info (from registration form)
    email = models.EmailField()
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15, blank=True)
    company = models.CharField(max_length=100, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    
    # Payment Info
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Email notifications
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    join_link_sent = models.BooleanField(default=False)
    
    # Tracking
    is_active = models.BooleanField(default=True)
    attended_duration_minutes = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['webinar', 'email']
        ordering = ['-registered_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.webinar.title}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def is_payment_required(self):
        """Check if payment is required for this registration"""
        return self.webinar.webinar_type == 'paid' and self.payment_status != 'paid'
    
    # webinars/models.py - CORRECTED confirm_payment method

    
    # webinars/models.py - FINAL CORRECT confirm_payment method

    def confirm_payment(self):
        """Confirm payment and upgrade user - FIXED LOGIC"""
        self.payment_status = 'paid'
        self.payment_date = timezone.now()
        self.amount_paid = self.webinar.price if self.webinar.webinar_type == 'paid' else 0
        self.save()
        
        # DEBUG logging
        print(f"=== PAYMENT CONFIRMATION (FINAL CORRECT) ===")
        print(f"User: {self.user.email}")
        print(f"Current Role: {self.user.role}")
        print(f"Webinar Type: {self.webinar.webinar_type}")
        print(f"Webinar Price: {self.webinar.price}")
        
        # FINAL CORRECT LOGIC per your requirement
        if self.user:
            if self.webinar.webinar_type == 'paid':
                # PAID webinar → upgrade to STUDENT (for course access)
                if self.user.role != 'student':
                    print(f"PAID WEBINAR: Upgrading {self.user.role} -> STUDENT (course access)")
                    self.user.role = 'student'
                    self.user.save()
                    return True  # User upgraded to student for paid webinars
                else:
                    print(f"PAID WEBINAR: User already STUDENT")
                    return False
            else:
                # FREE webinar → upgrade to WEBINAR_USER (limited webinar access only)
                if self.user.role != 'webinar_user':
                    print(f"FREE WEBINAR: Upgrading {self.user.role} -> WEBINAR_USER (limited access)")
                    self.user.role = 'webinar_user'
                    self.user.save()
                    return True  # User upgraded to webinar_user for free webinars
                else:
                    print(f"FREE WEBINAR: User already WEBINAR_USER")
                    return False
        
        print(f"NO CHANGE: No user found")
        return False


    @classmethod
    def create_registration(cls, webinar, email, first_name, last_name, 
                          phone_number='', company='', designation=''):
        """Create a registration and auto-create user if needed"""
        from django.contrib.auth import get_user_model
        import random
        import string

        User = get_user_model()

        # Check if user exists
        user = User.objects.filter(email=email.lower()).first()
        generated_password = None

        if not user:
            print(f"Creating new user for: {email}")

            # Generate username from email
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # Generate random password
            generated_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

            # Create user with webinar_user role
            user = User.objects.create_user(
                username=username,
                email=email.lower(),
                password=generated_password,
                first_name=first_name,
                last_name=last_name,
                role='webinar_user',  # ✅ Set correct role
                is_active=True
            )

            print(f"✅ User created: {username} with role: {user.role}")

            # Send welcome email with password
            if generated_password:
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings

                    subject = "Your LMS Account Has Been Created"
                    message = f"""
    Dear {first_name},

    Your account has been created successfully!

    Login Credentials:
    Username: {username}
    Email: {email}
    Password: {generated_password}

    Login URL: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}/login/

    You can change your password after logging in.

    Best regards,
    Team
                    """

                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    print(f"✅ Welcome email sent to: {email}")
                except Exception as e:
                    print(f"❌ User creation email error: {e}")
        else:
            print(f"User already exists: {user.username} with role: {user.role}")

        # Create registration
        registration = cls.objects.create(
            webinar=webinar,
            user=user,
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            company=company,
            designation=designation,
            # registration_source='website'
        )

        print(f"✅ Registration created: {registration.id}")
        return registration
    
    @staticmethod
    def send_welcome_email(user, password, webinar):
        """Send welcome email with login details"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"Welcome! Your registration for {webinar.title}"
        
        webinar_type_message = (
            "This is a FREE webinar - you now have Student access!" 
            if webinar.webinar_type == 'free' 
            else f"This is a PAID webinar (₹{webinar.price}) - complete payment to upgrade to Webinar User."
        )
        
        message = f"""
Dear {user.get_full_name()},

Thank you for registering for "{webinar.title}"!

Your account details:
Email: {user.email}
Password: {password}

Webinar Details:
Date & Time: {webinar.scheduled_date.strftime('%B %d, %Y at %I:%M %p')}
Duration: {webinar.duration_minutes} minutes

{webinar_type_message}

Account Access:
- Free Webinars: Student Access (Basic)
- Paid Webinars: Webinar User Access (Premium) - after payment

We'll send you the webinar link closer to the event time.

Best regards,
LMS Team
"""
        
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send welcome email: {e}")
    
    def get_user_role_display(self):
        """Get user role with upgrade status"""
        if self.user:
            role_map = {
                'student': 'Student (Basic Access)',
                'webinar_user': 'Webinar User (Premium Access)',
                'instructor': 'Instructor',
                'superadmin': 'Super Admin'
            }
            return role_map.get(self.user.role, self.user.role.title())
        return 'No User'
    
    def can_access_webinar(self):
        """Check if user can access webinar based on payment status"""
        if self.webinar.webinar_type == 'free':
            return True  # Free webinars always accessible
        return self.payment_status == 'paid'  # Paid webinars need payment
    
    def get_access_level(self):
        """Get access level description"""
        if self.webinar.webinar_type == 'free':
            return "Basic Access (Student)"
        elif self.payment_status == 'paid':
            return "Premium Access (Webinar User)"
        else:
            return "Pending Payment"




class WebinarResource(models.Model):
    """Resources/materials for webinars"""
    
    webinar = models.ForeignKey(Webinar, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='webinar_resources/')
    is_available_before_webinar = models.BooleanField(
        default=False, 
        help_text="Make available to registered users before webinar"
    )
    is_available_after_webinar = models.BooleanField(
        default=True,
        help_text="Make available after webinar completion"
    )
    download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['title']
    
    def __str__(self):
        return f"{self.webinar.title} - {self.title}"


class WebinarFeedback(models.Model):
    """Feedback from webinar attendees"""
    
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]
    
    webinar = models.ForeignKey(Webinar, on_delete=models.CASCADE, related_name='feedback')
    attendee = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Ratings
    content_rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    instructor_rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    overall_rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    
    # Comments
    what_you_liked = models.TextField(blank=True)
    suggestions_for_improvement = models.TextField(blank=True)
    would_recommend = models.BooleanField(default=True)
    
    # Follow-up
    interested_in_similar_webinars = models.BooleanField(default=True)
    interested_in_paid_courses = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['webinar', 'attendee']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.attendee.get_full_name()} - {self.webinar.title} ({self.overall_rating}★)"


