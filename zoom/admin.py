from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import *

@admin.register(ZoomConfiguration)
class ZoomConfigurationAdmin(admin.ModelAdmin):
    list_display = ['account_id', 'client_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('API Configuration', {
            'fields': ('account_id', 'client_id', 'client_secret', 'secret_token')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(BatchSession)
class BatchSessionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'batch', 'scheduled_date', 'start_time', 
        'status_badge', 'zoom_status', 'recording_status', 'created_by'
    ]
    list_filter = [
        'status', 'session_type', 'scheduled_date', 'is_recorded', 
        'batch__course', 'batch__instructor'
    ]
    search_fields = ['title', 'batch__name', 'batch__course__title', 'description']
    readonly_fields = [
        'zoom_meeting_id', 'zoom_meeting_password', 'zoom_join_url', 
        'zoom_start_url', 'created_at', 'duration_minutes'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('batch', 'title', 'description', 'session_type', 'status')
        }),
        ('Schedule', {
            'fields': ('scheduled_date', 'start_time', 'end_time', 'duration_minutes')
        }),
        ('Zoom Settings', {
            'fields': ('max_participants', 'is_recorded')
        }),
        ('Zoom Details', {
            'fields': (
                'zoom_meeting_id', 'zoom_meeting_password', 
                'zoom_join_url', 'zoom_start_url'
            ),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'scheduled': 'blue',
            'live': 'green',
            'completed': 'purple',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def zoom_status(self, obj):
        if obj.zoom_meeting_id:
            return format_html(
                '<span style="color: green;">✓ Created</span><br>'
                '<small>ID: {}</small>',
                obj.zoom_meeting_id
            )
        return format_html('<span style="color: red;">✗ Not Created</span>')
    zoom_status.short_description = 'Zoom Meeting'
    
    def recording_status(self, obj):
        recording_count = obj.recordings.count()
        if recording_count > 0:
            return format_html(
                '<span style="color: green;">{} Recording(s)</span>',
                recording_count
            )
        elif obj.is_recorded and obj.status == 'completed':
            return format_html('<span style="color: orange;">Processing...</span>')
        elif obj.is_recorded:
            return format_html('<span style="color: blue;">Enabled</span>')
        else:
            return format_html('<span style="color: gray;">Disabled</span>')
    recording_status.short_description = 'Recording'
    
    actions = ['create_zoom_meetings', 'sync_recordings']
    
    def create_zoom_meetings(self, request, queryset):
        """Bulk create Zoom meetings"""
        from .services import ZoomAPIService
        zoom_service = ZoomAPIService()
        
        created_count = 0
        for session in queryset.filter(zoom_meeting_id__isnull=True):
            try:
                success, result = zoom_service.create_meeting(session)
                if success:
                    created_count += 1
            except Exception as e:
                continue
        
        self.message_user(request, f'Created {created_count} Zoom meetings.')
    create_zoom_meetings.short_description = "Create Zoom meetings for selected sessions"
    
    def sync_recordings(self, request, queryset):
        """Sync recordings for completed sessions"""
        from .services import ZoomAPIService
        zoom_service = ZoomAPIService()
        
        synced_count = 0
        for session in queryset.filter(status='completed', zoom_meeting_id__isnull=False):
            try:
                success, result = zoom_service.get_meeting_recordings(session)
                if success:
                    synced_count += 1
            except Exception as e:
                continue
        
        self.message_user(request, f'Synced recordings for {synced_count} sessions.')
    sync_recordings.short_description = "Sync recordings for selected sessions"

@admin.register(SessionAttendance)
class SessionAttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'session_title', 'session_date', 'attendance_status', 
        'duration_minutes', 'attendance_percentage'
    ]
    list_filter = [
        'is_present', 'session__scheduled_date', 'session__batch__course',
        'session__batch__instructor'
    ]
    search_fields = [
        'student__username', 'student__first_name', 'student__last_name',
        'session__title', 'session__batch__name'
    ]
    readonly_fields = ['created_at', 'zoom_participant_id', 'zoom_user_name']
    
    def session_title(self, obj):
        return obj.session.title
    session_title.short_description = 'Session'
    
    def session_date(self, obj):
        return obj.session.scheduled_date
    session_date.short_description = 'Date'
    
    def attendance_status(self, obj):
        if obj.is_present:
            return format_html('<span style="color: green;">✓ Present</span>')
        else:
            return format_html('<span style="color: red;">✗ Absent</span>')
    attendance_status.short_description = 'Status'

@admin.register(ZoomRecording)
class ZoomRecordingAdmin(admin.ModelAdmin):
    list_display = [
        'session_title', 'session_date', 'file_size_display', 
        'duration_formatted', 'status', 'view_count', 'download_count'
    ]
    list_filter = [
        'status', 'recording_type', 'file_type', 
        'session__batch__course', 'recording_start'
    ]
    search_fields = [
        'session__title', 'session__batch__name', 
        'zoom_recording_id'
    ]
    readonly_fields = [
        'zoom_recording_id', 'download_url', 'play_url', 
        'recording_start', 'recording_end', 'created_at'
    ]
    
    fieldsets = (
        ('Recording Details', {
            'fields': ('session', 'zoom_recording_id', 'recording_type', 'file_type')
        }),
        ('File Information', {
            'fields': ('file_size', 'duration_minutes', 'status')
        }),
        ('URLs', {
            'fields': ('download_url', 'play_url'),
            'classes': ('collapse',)
        }),
        ('Access Control', {
            'fields': ('is_public', 'password_required', 'recording_password')
        }),
        ('Statistics', {
            'fields': ('view_count', 'download_count')
        }),
        ('Timestamps', {
            'fields': ('recording_start', 'recording_end', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def session_title(self, obj):
        return obj.session.title
    session_title.short_description = 'Session'
    
    def session_date(self, obj):
        return obj.session.scheduled_date
    session_date.short_description = 'Date'
    
    def file_size_display(self, obj):
        return f"{obj.get_file_size_mb()} MB"
    file_size_display.short_description = 'File Size'
    
    def duration_formatted(self, obj):
        return obj.get_duration_formatted()
    duration_formatted.short_description = 'Duration'

@admin.register(SessionFeedback)
class SessionFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'session_title', 'overall_rating', 
        'content_rating', 'instructor_rating', 'created_at'
    ]
    list_filter = [
        'overall_rating', 'content_rating', 'instructor_rating', 
        'technical_rating', 'is_anonymous', 'created_at'
    ]
    search_fields = [
        'student__username', 'student__first_name', 'student__last_name',
        'session__title', 'feedback_text'
    ]
    readonly_fields = ['created_at']
    
    def session_title(self, obj):
        return obj.session.title
    session_title.short_description = 'Session'

@admin.register(ZoomWebhookLog)
class ZoomWebhookLogAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'zoom_meeting_id', 'processed', 'created_at']
    list_filter = ['event_type', 'processed', 'created_at']
    search_fields = ['zoom_meeting_id', 'event_type']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation