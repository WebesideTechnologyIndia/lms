# userss/admin.py - Clean version without Course and Enrollment

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, UserProfile, UserActivityLog,
    EmailLimitSet, EmailTemplate, EmailLog, DailyEmailSummary, EmailTemplateType
    # Removed Course and Enrollment from import
)

# Custom User Admin
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'date_joined', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone_number', 'profile_picture', 'bio', 'date_of_birth', 'address', 'created_by')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'first_name', 'last_name', 'role', 'phone_number')
        }),
    )
    
    inlines = (UserProfileInline,)

# User Profile Admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'employee_id', 'department', 'year_of_study')
    list_filter = ('department', 'year_of_study')
    search_fields = ('user__username', 'student_id', 'employee_id', 'department')

# User Activity Log Admin
@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'description', 'ip_address')
    ordering = ('-timestamp',)
    readonly_fields = ('user', 'action', 'description', 'ip_address', 'user_agent', 'timestamp')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

# Email Template Type Admin
@admin.register(EmailTemplateType)
class EmailTemplateTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'templates_count', 'created_by', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def templates_count(self, obj):
        return obj.templates.count()
    templates_count.short_description = 'Templates Count'
    templates_count.admin_order_field = 'templates__count'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

# Email Template Admin
@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'subject_preview', 'is_active', 'created_by', 'created_at')
    list_filter = ('template_type', 'is_active', 'created_at')
    search_fields = ('name', 'subject', 'template_type__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'template_type')
        }),
        ('Email Content', {
            'fields': ('subject', 'email_body')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def subject_preview(self, obj):
        return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
    subject_preview.short_description = 'Subject Preview'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

# Email Log Admin
@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'template_used', 'subject_preview', 'is_sent_successfully', 'sent_date', 'sent_by')
    list_filter = ('is_sent_successfully', 'sent_date', 'template_used__template_type')
    search_fields = ('recipient_email', 'subject', 'recipient_user__username')
    readonly_fields = ('sent_date', 'sent_time')
    date_hierarchy = 'sent_date'
    
    fieldsets = (
        ('Email Details', {
            'fields': ('recipient_email', 'recipient_user', 'template_used', 'template_type_used')
        }),
        ('Content', {
            'fields': ('subject', 'email_body'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_sent_successfully', 'error_message')
        }),
        ('Metadata', {
            'fields': ('sent_by', 'sent_date', 'sent_time'),
        }),
    )
    
    def subject_preview(self, obj):
        return obj.subject[:40] + '...' if len(obj.subject) > 40 else obj.subject
    subject_preview.short_description = 'Subject'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

# Daily Email Summary Admin
@admin.register(DailyEmailSummary)
class DailyEmailSummaryAdmin(admin.ModelAdmin):
    list_display = ('date', 'successful_emails', 'failed_emails', 'total_emails_sent', 'daily_limit', 'usage_percentage')
    list_filter = ('date',)
    readonly_fields = ('date', 'total_emails_sent', 'successful_emails', 'failed_emails')
    date_hierarchy = 'date'
    
    def usage_percentage(self, obj):
        if obj.daily_limit > 0:
            percentage = (obj.total_emails_sent / obj.daily_limit) * 100
            return f"{percentage:.1f}%"
        return "0%"
    usage_percentage.short_description = 'Usage %'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

# Email Limit Set Admin
@admin.register(EmailLimitSet)
class EmailLimitSetAdmin(admin.ModelAdmin):
    list_display = ('email_limit_per_day', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Email Limit Settings', {
            'fields': ('email_limit_per_day', 'is_active')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if obj.is_active:
            # Deactivate all other active settings
            EmailLimitSet.objects.filter(is_active=True).update(is_active=False)
        super().save_model(request, obj, form, change)
    
    def has_delete_permission(self, request, obj=None):
        return False

# Register CustomUser with custom admin - ONLY ONCE
admin.site.register(CustomUser, CustomUserAdmin)

# Admin site customization
admin.site.site_header = "LMS Administration"
admin.site.site_title = "LMS Admin Portal"
admin.site.index_title = "Welcome to LMS Administration Portal"