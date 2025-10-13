# admin.py

from django.contrib import admin
from .models import AttendanceSession, Attendance

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    # ✅ Updated - use start_time instead of date
    list_display = [
        'id',
        'batch',
        'get_session_date',  # Custom method
        'start_time',
        'end_time',
        'is_active',
        'created_at'
    ]
    
    # ✅ Updated - use start_time for filtering
    list_filter = [
        'is_active',
        'start_time',
        'created_at',
        'batch'
    ]
    
    # ✅ Updated - use start_time for hierarchy
    date_hierarchy = 'start_time'
    
    search_fields = ['batch__name', 'classroom_location']
    readonly_fields = ['qr_secret', 'created_at', 'get_session_info']
    
    fieldsets = (
        ('Session Details', {
            'fields': ('batch', 'start_time', 'end_time', 'get_session_info')
        }),
        ('Location Settings', {
            'fields': ('classroom_location', 'latitude', 'longitude', 'allowed_radius_meters')
        }),
        ('QR Code', {
            'fields': ('qr_secret',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
    )
    
    def get_session_date(self, obj):
        """Display session date from start_time"""
        return obj.start_time.strftime('%d-%m-%Y') if obj.start_time else '-'
    get_session_date.short_description = 'Date'
    
    def get_session_info(self, obj):
        """Display session duration info"""
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            return f"{obj.start_time.strftime('%I:%M %p')} to {obj.end_time.strftime('%I:%M %p')} ({duration})"
        return "No timing set"
    get_session_info.short_description = 'Session Duration'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'student',
        'session',
        'get_marked_date',  # Custom method
        'is_present',
        'is_late',
        'marking_method',
        'marked_at'
    ]
    
    # ✅ Updated - use session__start_time instead of session__date
    list_filter = [
        'is_present',
        'is_late',
        'marking_method',
        'session__start_time',
        'marked_at'
    ]
    
    # ✅ Updated - use marked_at for hierarchy
    date_hierarchy = 'marked_at'
    
    search_fields = ['student__username', 'session__batch__name']
    readonly_fields = ['marked_at', 'distance_from_classroom', 'get_location_info']
    
    fieldsets = (
        ('Attendance Info', {
            'fields': ('student', 'session', 'marking_method', 'marked_at')
        }),
        ('Status', {
            'fields': ('is_present', 'is_late')
        }),
        ('Location', {
            'fields': ('student_latitude', 'student_longitude', 'distance_from_classroom', 'get_location_info')
        }),
    )
    
    def get_marked_date(self, obj):
        """Display marked date"""
        return obj.marked_at.strftime('%d-%m-%Y %I:%M %p') if obj.marked_at else '-'
    get_marked_date.short_description = 'Marked At'
    
    def get_location_info(self, obj):
        """Display location details"""
        if obj.distance_from_classroom:
            allowed = obj.session.allowed_radius_meters if obj.session else 'N/A'
            return f"Distance: {obj.distance_from_classroom}m | Allowed: {allowed}m"
        return "Location not verified"
    get_location_info.short_description = 'Location Details'


# BatchEnrollment is already registered in courses.admin
# So we don't register it here