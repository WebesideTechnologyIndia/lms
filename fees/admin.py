from django.contrib import admin

# Register your models here.
# fees/admin.py

from django.contrib import admin
from .models import (
    FeeStructure, StudentFeeAssignment, PaymentRecord, 
    EMISchedule, BatchAccessControl, FeeDiscount,
    PaymentReminder, DiscountUsage
)

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'total_amount', 'payment_type', 'is_active', 'is_default', 'created_at']
    list_filter = ['payment_type', 'is_active', 'is_default', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'total_amount', 'payment_type')
        }),
        ('EMI Settings', {
            'fields': ('emi_duration_months', 'emi_amount', 'down_payment'),
            'classes': ('collapse',)
        }),
        ('Fees & Penalties', {
            'fields': ('grace_period_days', 'late_fee_amount', 'late_fee_percentage')
        }),
        ('Discounts', {
            'fields': ('early_payment_discount', 'bulk_discount')
        }),
        ('Status', {
            'fields': ('is_active', 'is_default')
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(StudentFeeAssignment)
class StudentFeeAssignmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'fee_structure', 'total_amount', 'amount_paid', 'amount_pending', 'status', 'is_course_locked']
    list_filter = ['status', 'is_course_locked', 'fee_structure', 'assigned_date']
    search_fields = ['student__username', 'student__email', 'course__title', 'course__course_code']
    readonly_fields = ['assigned_date', 'created_at', 'updated_at']
    raw_id_fields = ['student', 'course', 'fee_structure']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'course', 'fee_structure')

@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'get_student_name', 'get_course_name', 'amount', 'payment_method', 'payment_date', 'status']
    list_filter = ['payment_method', 'status', 'payment_date']
    search_fields = ['payment_id', 'fee_assignment__student__username', 'transaction_id']
    readonly_fields = ['payment_id', 'payment_time', 'created_at', 'updated_at']
    raw_id_fields = ['fee_assignment', 'emi_schedule']
    
    def get_student_name(self, obj):
        return obj.fee_assignment.student.get_full_name()
    get_student_name.short_description = 'Student'
    
    def get_course_name(self, obj):
        return obj.fee_assignment.course.title
    get_course_name.short_description = 'Course'

@admin.register(EMISchedule)
class EMIScheduleAdmin(admin.ModelAdmin):
    list_display = ['get_student_name', 'get_course_name', 'installment_number', 'amount', 'due_date', 'status', 'days_overdue']
    list_filter = ['status', 'installment_type', 'due_date']
    search_fields = ['fee_assignment__student__username', 'fee_assignment__course__title']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['fee_assignment']
    
    def get_student_name(self, obj):
        return obj.fee_assignment.student.get_full_name()
    get_student_name.short_description = 'Student'
    
    def get_course_name(self, obj):
        return obj.fee_assignment.course.title
    get_course_name.short_description = 'Course'

@admin.register(BatchAccessControl)
class BatchAccessControlAdmin(admin.ModelAdmin):
    list_display = ['student', 'batch', 'access_type', 'effective_from', 'effective_until', 'created_at']
    list_filter = ['access_type', 'effective_from', 'batch__course']
    search_fields = ['student__username', 'batch__name', 'batch__course__title']
    raw_id_fields = ['student', 'batch']

@admin.register(FeeDiscount)
class FeeDiscountAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'discount_type', 'discount_value', 'valid_from', 'valid_until', 'used_count', 'is_active']
    list_filter = ['discount_type', 'is_active', 'valid_from']
    search_fields = ['name', 'code']
    readonly_fields = ['used_count', 'created_at']

@admin.register(PaymentReminder)
class PaymentReminderAdmin(admin.ModelAdmin):
    list_display = ['get_student_name', 'reminder_type', 'scheduled_date', 'sent_date', 'status']
    list_filter = ['reminder_type', 'status', 'scheduled_date']
    search_fields = ['emi_schedule__fee_assignment__student__username']
    
    def get_student_name(self, obj):
        return obj.emi_schedule.fee_assignment.student.get_full_name()
    get_student_name.short_description = 'Student'

@admin.register(DiscountUsage)
class DiscountUsageAdmin(admin.ModelAdmin):
    list_display = ['discount', 'get_student_name', 'discount_amount', 'applied_date']
    list_filter = ['applied_date', 'discount']
    search_fields = ['fee_assignment__student__username', 'discount__name']
    
    def get_student_name(self, obj):
        return obj.fee_assignment.student.get_full_name()
    get_student_name.short_description = 'Student'