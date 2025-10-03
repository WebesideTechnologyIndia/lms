# apps.py

from django.apps import AppConfig

class LmsConfig(AppConfig):  # Replace 'Lms' with your actual app name
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'userss'  # Your app name
    
    def ready(self):
        import userss.signals  # Import your signals