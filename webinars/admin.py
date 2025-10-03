from django.contrib import admin

# Register your models here.
# ===========================================
# webinars/admin.py
# ===========================================

from django.contrib import admin
from .models import WebinarCategory, Webinar, WebinarRegistration, WebinarResource, WebinarFeedback

@admin.register(WebinarCategory)
class WebinarCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Webinar)
class WebinarAdmin(admin.ModelAdmin):
    list_display = ['title', 'webinar_type', 'status', 'scheduled_date', 'instructor', 'total_registrations']
    list_filter = ['webinar_type', 'status', 'category', 'scheduled_date', 'created_at']
    search_fields = ['title', 'description', 'instructor__first_name', 'instructor__last_name']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'scheduled_date'
    ordering = ['-scheduled_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'category', 'webinar_type', 'status')
        }),
        ('Content', {
            'fields': ('short_description', 'description', 'learning_outcomes', 'prerequisites', 'thumbnail')
        }),
        ('Schedule & Capacity', {
            'fields': ('scheduled_date', 'duration_minutes', 'max_attendees')
        }),
        ('Pricing', {
            'fields': ('price',)
        }),
        ('Instructor & Meeting', {
            'fields': ('instructor', 'webinar_link', 'meeting_id', 'meeting_password')
        }),
        ('Email Settings', {
            'fields': ('send_reminder_emails', 'reminder_hours_before')
        }),
        ('System', {
            'fields': ('is_active', 'created_by')
        })
    )


@admin.register(WebinarRegistration)
class WebinarRegistrationAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'webinar', 'status', 'registered_at']
    list_filter = ['status', 'webinar__webinar_type', 'payment_status', 'registered_at']
    search_fields = ['first_name', 'last_name', 'email', 'webinar__title']
    date_hierarchy = 'registered_at'
    ordering = ['-registered_at']
    
    readonly_fields = ['user', 'registered_at']


@admin.register(WebinarFeedback)
class WebinarFeedbackAdmin(admin.ModelAdmin):
    list_display = ['attendee', 'webinar', 'overall_rating', 'would_recommend', 'created_at']
    list_filter = ['overall_rating', 'would_recommend', 'created_at']
    search_fields = ['attendee__first_name', 'attendee__last_name', 'webinar__title']
    ordering = ['-created_at']


# ===========================================
# Update userss/models.py - Add webinar_user role
# ===========================================

# In your existing CustomUser model, update ROLE_CHOICES:
"""
ROLE_CHOICES = (
    ("superadmin", "Super Admin"),
    ("instructor", "Instructor"), 
    ("student", "Student"),
    ("webinar_user", "Webinar User"),  # Add this line
)
"""