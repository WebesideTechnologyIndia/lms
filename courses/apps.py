from django.apps import AppConfig

class CoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courses'
    
    def ready(self):
        """Import signals when app is ready"""
        import courses.signals  # This connects the signals
        print("📡 Courses app ready - Signals imported")