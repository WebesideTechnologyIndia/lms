# attendance/apps.py

from django.apps import AppConfig
import sys

class AttendanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'attendance'

    def ready(self):
        # Start scheduler only when running server
        if 'runserver' in sys.argv:
            from .scheduler import start_scheduler
            try:
                start_scheduler()
                print("=" * 60)
                print("🚀 Attendance Auto-Absent Scheduler STARTED!")
                print("⏰ Running every 5 minutes")
                print("=" * 60)
            except Exception as e:
                print(f"⚠️ Scheduler error: {str(e)}")