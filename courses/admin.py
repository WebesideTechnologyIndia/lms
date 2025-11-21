# courses/admin.py

from django.contrib import admin
from .models import (
    Course, CourseCategory, CourseModule, CourseLesson, 
    Batch, BatchModule, BatchLesson,
    Enrollment, BatchEnrollment, LessonProgress,
    LessonAttachment, CourseReview, CourseFAQ,
     DeviceSession, StudentLoginLog
)

# ==================== COURSE CATEGORY ADMIN ====================
@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'get_courses_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

# ==================== COURSE ADMIN ====================
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'title', 'instructor', 'status', 'is_active', 'price', 'total_enrollments']
    list_filter = ['status', 'is_active', 'difficulty_level', 'course_type', 'category']
    search_fields = ['title', 'course_code', 'description']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['co_instructors']

# ==================== BATCH ADMIN ====================
@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'course', 'instructor', 'status', 'start_date', 'end_date']
    list_filter = ['status', 'is_active', 'delivery_mode', 'start_date']
    search_fields = ['name', 'code', 'course__title']
    date_hierarchy = 'start_date'

# ==================== MODULE ADMINS ====================
@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'course']
    search_fields = ['title', 'description']

@admin.register(BatchModule)
class BatchModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'batch', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'batch__course']
    search_fields = ['title', 'description']

# ==================== LESSON ADMINS ====================
@admin.register(CourseLesson)
class CourseLessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'lesson_type', 'order', 'is_active']
    list_filter = ['lesson_type', 'is_active', 'module__course']
    search_fields = ['title', 'description']

@admin.register(BatchLesson)
class BatchLessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'batch_module', 'lesson_type', 'order', 'is_active']
    list_filter = ['lesson_type', 'is_active', 'batch_module__batch__course']
    search_fields = ['title', 'description']

# ==================== LESSON PROGRESS ADMIN (FIXED) ====================
@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'get_lesson_title', 'status', 'completion_percentage', 'last_accessed']
    list_filter = [
        'status',
        'started_at',
        'completed_at',
    ]
    search_fields = [
        'student__username',
        'student__email',
        'course_lesson__title',
        'batch_lesson__title'
    ]
    date_hierarchy = 'last_accessed'
    readonly_fields = ['started_at', 'completed_at', 'last_accessed']
    
    def get_lesson_title(self, obj):
        """Get lesson title from either course_lesson or batch_lesson"""
        if obj.batch_lesson:
            return f"[Batch] {obj.batch_lesson.title}"
        elif obj.course_lesson:
            return f"[Course] {obj.course_lesson.title}"
        return "N/A"
    get_lesson_title.short_description = 'Lesson'

# ==================== ENROLLMENT ADMINS ====================
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'status', 'progress_percentage', 'enrolled_at']
    list_filter = ['status', 'is_active', 'payment_status', 'course']
    search_fields = ['student__username', 'student__email', 'course__title']
    date_hierarchy = 'enrolled_at'

@admin.register(BatchEnrollment)
class BatchEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'batch', 'status', 'enrolled_at', 'is_active']
    list_filter = ['status', 'is_active', 'batch__course']
    search_fields = ['student__username', 'student__email', 'batch__name']
    date_hierarchy = 'enrolled_at'

# ==================== OTHER ADMINS ====================
@admin.register(LessonAttachment)
class LessonAttachmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'get_file_size_mb', 'download_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']

@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ['course', 'student', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating', 'created_at']
    search_fields = ['course__title', 'student__username', 'review_text']

@admin.register(CourseFAQ)
class CourseFAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'course', 'order', 'is_active']
    list_filter = ['is_active', 'course']
    search_fields = ['question', 'answer']

# ==================== SUBSCRIPTION ADMINS ====================
# courses/admin.py

from django.contrib import admin
from .models import StudentDeviceLimit, DeviceSession, StudentLoginLog

@admin.register(StudentDeviceLimit)
class StudentDeviceLimitAdmin(admin.ModelAdmin):
    list_display = ['student', 'max_devices', 'current_device_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'max_devices']
    search_fields = ['student__username', 'student__email']
    
    def current_device_count(self, obj):
        return obj.current_device_count()
    current_device_count.short_description = 'Active Devices'


@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'device_name', 'device_id_short', 'first_login', 'last_login', 'is_active']
    list_filter = ['is_active', 'first_login']
    search_fields = ['student_limit__student__username', 'device_name', 'device_id']
    readonly_fields = ['device_id', 'first_login', 'device_info']
    
    def student_name(self, obj):
        return obj.student_limit.student.username
    student_name.short_description = 'Student'
    
    def device_id_short(self, obj):
        return obj.device_id[:20] + '...' if len(obj.device_id) > 20 else obj.device_id
    device_id_short.short_description = 'Device ID'


@admin.register(StudentLoginLog)
class StudentLoginLogAdmin(admin.ModelAdmin):
    list_display = ['student', 'login_time', 'logout_time', 'session_duration', 'ip_address']
    list_filter = ['login_time']
    search_fields = ['student__username']
    readonly_fields = ['login_time', 'session_duration']