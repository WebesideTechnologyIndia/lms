# userss/apps.py

from django.apps import AppConfig
from django.conf import settings

class UserssConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'userss'
    
    def ready(self):
        """
        Yeh method tab run hoga jab Django completely load ho jayega
        Yahan database access safe hai! ✅
        """
        self.update_email_settings()
    
    def update_email_settings(self):
        """Update Django settings from database"""
        try:
            from userss.models import EmailSMTPConfiguration, EmailLimitSet
            
            # Database se fetch karo
            smtp = EmailSMTPConfiguration.objects.filter(is_active=True).first()
            if smtp:
                settings.EMAIL_HOST = smtp.email_host
                settings.EMAIL_PORT = smtp.email_port
                settings.EMAIL_USE_TLS = smtp.email_use_tls
                settings.EMAIL_HOST_USER = smtp.email_host_user
                settings.EMAIL_HOST_PASSWORD = smtp.email_host_password
                settings.DEFAULT_FROM_EMAIL = smtp.default_from_email
                print("✅ Email settings loaded from DATABASE")
            else:
                print("⚠️ No active SMTP config found, using defaults")
            
            # Email limit fetch karo
            limit = EmailLimitSet.objects.filter(is_active=True).first()
            if limit:
                settings.EMAIL_DAILY_LIMIT_DEFAULT = limit.email_limit_per_day
                
        except Exception as e:
            print(f"⚠️ Could not load email settings from DB: {e}")
            print("📌 Using default email settings")