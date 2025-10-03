from django.apps import AppConfig

class ZoomConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'zoom'
    verbose_name = 'Zoom Integration'
    
    def ready(self):
        # Import signals if you have any
        pass