# signals.py - Fixed version

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import date
from .models import CustomUser, UserProfile, UserActivityLog, EmailLimitSet, EmailLog, DailyEmailSummary, EmailTemplate, EmailTemplateType

def check_daily_email_limit():
    """Check if daily email limit is reached"""
    try:
        email_limit_setting = EmailLimitSet.objects.filter(is_active=True).first()
        if not email_limit_setting:
            return False  # No limit set, can send
        
        today = date.today()
        daily_summary, created = DailyEmailSummary.objects.get_or_create(
            date=today,
            defaults={'daily_limit': email_limit_setting.email_limit_per_day}
        )
        
        return daily_summary.total_emails_sent >= daily_summary.daily_limit
    except Exception:
        return False

def send_user_welcome_email(user):
    """Send welcome email to newly created user"""
    if check_daily_email_limit():
        print(f"Daily email limit reached. Cannot send email to {user.email}")
        return False
    
    template = None
    template_type_used = None
    
    try:
        # Direct approach - get any active welcome email template
        # You can create template in admin with any name you want
        template = EmailTemplate.objects.filter(
            name__icontains='welcome',  # Find any template with 'welcome' in name
            is_active=True
        ).first()
        
        if template:
            template_type_used = template.template_type
        
        # Alternative: Filter by template type code if you have created the EmailTemplateType
        if not template:
            template_type_used = EmailTemplateType.objects.filter(
                code='user_welcome',
                is_active=True
            ).first()
            
            if template_type_used:
                template = EmailTemplate.objects.filter(
                    template_type=template_type_used,
                    is_active=True
                ).first()
        
        if template:
            # Use database template
            print(f"Using template: {template.name}")
            subject = template.subject
            message = template.email_body
            
            # Replace dynamic placeholders
            subject = subject.replace('{{username}}', user.username or '')
            subject = subject.replace('{{email}}', user.email or '')
            subject = subject.replace('{{first_name}}', user.first_name or user.username)
            subject = subject.replace('{{last_name}}', user.last_name or '')
            
            message = message.replace('{{username}}', user.username or '')
            message = message.replace('{{email}}', user.email or '')
            message = message.replace('{{first_name}}', user.first_name or user.username)
            message = message.replace('{{last_name}}', user.last_name or '')
            
        else:
            # Fallback if no template found
            print("No welcome template found in database, using default")
            subject = "Welcome to LMS - Your Account Has Been Created"
            message = f"""Dear {user.get_full_name() or user.username},

Welcome to our Learning Management System!

Your account has been successfully created:
- Username: {user.username}
- Email: {user.email}
- Role: {user.get_role_display()}

Please contact your administrator for login credentials.

Best regards,
LMS Team"""
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        # Log successful email
        EmailLog.objects.create(
            recipient_email=user.email,
            recipient_user=user,
            template_used=template,
            template_type_used=template_type_used,  # Now properly defined
            subject=subject,
            email_body=message,
            is_sent_successfully=True
        )
        
        # Update daily summary
        today = date.today()
        email_limit = 50  # Default
        if EmailLimitSet.objects.filter(is_active=True).exists():
            email_limit = EmailLimitSet.objects.filter(is_active=True).first().email_limit_per_day
            
        daily_summary, created = DailyEmailSummary.objects.get_or_create(
            date=today,
            defaults={'daily_limit': email_limit}
        )
        daily_summary.total_emails_sent += 1
        daily_summary.successful_emails += 1
        daily_summary.save()
        
        print(f"Welcome email sent successfully to {user.email}")
        return True
        
    except Exception as e:
        # Log failed email
        EmailLog.objects.create(
            recipient_email=user.email,
            recipient_user=user,
            template_used=template if template else None,
            template_type_used=template_type_used if template_type_used else None,
            subject=subject if 'subject' in locals() else "Welcome to LMS",
            email_body=message if 'message' in locals() else "",
            is_sent_successfully=False,
            error_message=str(e)
        )
        
        # Update daily summary for failed email
        today = date.today()
        email_limit = 50  # Default
        if EmailLimitSet.objects.filter(is_active=True).exists():
            email_limit = EmailLimitSet.objects.filter(is_active=True).first().email_limit_per_day
            
        daily_summary, created = DailyEmailSummary.objects.get_or_create(
            date=today,
            defaults={'daily_limit': email_limit}
        )
        daily_summary.total_emails_sent += 1
        daily_summary.failed_emails += 1
        daily_summary.save()
        
        print(f"Failed to send email to {user.email}: {str(e)}")
        return False

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create a UserProfile when a new CustomUser is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    """Save the user profile whenever the user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def log_user_creation_and_send_email(sender, instance, created, **kwargs):
    """Log user creation and send welcome email"""
    if created:
        # Log user creation
        UserActivityLog.objects.create(
            user=instance,
            action='create_user',
            description=f'New {instance.get_role_display()} account created'
        )
        
        # Send welcome email
        if instance.email:
            send_user_welcome_email(instance)