# courses/admin.py - COMPLETE VERSION WITH ALL MODELS

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import (
    CourseCategory,
    Course,
    CourseModule,
    CourseLesson,
    LessonAttachment,
    LessonProgress,
    Enrollment,
    CourseReview,
    CourseFAQ,
    Batch,
    BatchModule,
    BatchLesson,
    BatchEnrollment,
)


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "course_count", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]

    def course_count(self, obj):
        return obj.courses.count()

    course_count.short_description = "Courses"


class CourseModuleInline(admin.TabularInline):
    model = CourseModule
    extra = 0
    fields = ["title", "order", "is_active"]


class CourseFAQInline(admin.TabularInline):
    model = CourseFAQ
    extra = 0
    fields = ["question", "answer", "order", "is_active"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        "course_code",
        "title",
        "category",
        "instructor",
        "status",
        "difficulty_level",
        "price",
        "enrollment_count",
        "is_featured",
        "created_at",
    ]
    list_filter = [
        "status",
        "difficulty_level",
        "course_type",
        "category",
        "is_featured",
        "is_free",
        "created_at",
    ]
    search_fields = ["title", "course_code", "description", "instructor__username"]
    prepopulated_fields = {"slug": ("course_code", "title")}
    readonly_fields = [
        "created_at",
        "updated_at",
        "total_enrollments",
        "average_rating",
        "total_reviews",
    ]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "title",
                    "slug",
                    "course_code",
                    "category",
                    "instructor",
                    "co_instructors",
                )
            },
        ),
        (
            "Content",
            {
                "fields": (
                    "short_description",
                    "description",
                    "thumbnail",
                    "intro_video",
                )
            },
        ),
        (
            "Course Configuration",
            {
                "fields": (
                    "difficulty_level",
                    "course_type",
                    "status",
                    "max_students",
                    "duration_weeks",
                    "hours_per_week",
                )
            },
        ),
        ("Pricing", {"fields": ("is_free", "price", "discounted_price")}),
        (
            "Dates",
            {
                "fields": (
                    "enrollment_start_date",
                    "enrollment_end_date",
                    "course_start_date",
                    "course_end_date",
                )
            },
        ),
        (
            "Requirements & Outcomes",
            {"fields": ("prerequisites", "learning_outcomes", "course_materials")},
        ),
        (
            "SEO & Marketing",
            {"fields": ("meta_keywords", "meta_description", "is_featured")},
        ),
        ("Settings", {"fields": ("is_active", "allow_enrollment")}),
        (
            "Statistics",
            {
                "fields": ("total_enrollments", "average_rating", "total_reviews"),
                "classes": ("collapse",),
            },
        ),
        (
            "System Info",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    filter_horizontal = ["co_instructors"]
    inlines = [CourseModuleInline, CourseFAQInline]

    def enrollment_count(self, obj):
        count = obj.get_enrolled_count()
        return format_html(
            '<span style="color: {};">{}</span>',
            "green" if count > 0 else "gray",
            count,
        )

    enrollment_count.short_description = "Enrollments"

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class CourseLessonInline(admin.TabularInline):
    model = CourseLesson
    extra = 0
    fields = ["title", "lesson_type", "order", "duration_minutes", "is_active"]
    readonly_fields = ["lesson_type"]


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "course",
        "order",
        "lesson_count",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "course__category", "created_at"]
    search_fields = ["title", "course__title", "course__course_code"]
    readonly_fields = ["created_at", "updated_at"]

    inlines = [CourseLessonInline]

    def lesson_count(self, obj):
        return obj.lessons.count()

    lesson_count.short_description = "Lessons"


class LessonAttachmentInline(admin.TabularInline):
    model = LessonAttachment
    extra = 0
    fields = ["title", "file", "is_active"]
    readonly_fields = ["file_size", "download_count"]


@admin.register(CourseLesson)
class CourseLessonAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "module",
        "lesson_type",
        "order",
        "duration_minutes",
        "content_types",
        "is_free_preview",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "lesson_type",
        "is_free_preview",
        "is_active",
        "is_mandatory",
        "module__course__category",
        "created_at",
    ]
    search_fields = [
        "title",
        "description",
        "module__title",
        "module__course__title",
        "module__course__course_code",
    ]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Basic Info",
            {"fields": ("module", "title", "description", "lesson_type", "order")},
        ),
        (
            "Duration & Settings",
            {
                "fields": (
                    "duration_minutes",
                    "is_free_preview",
                    "is_mandatory",
                    "is_active",
                )
            },
        ),
        ("Text Content", {"fields": ("text_content",), "classes": ("collapse",)}),
        (
            "Video Content",
            {
                "fields": ("video_file", "youtube_url", "vimeo_url"),
                "classes": ("collapse",),
            },
        ),
        ("Document Content", {"fields": ("pdf_file",), "classes": ("collapse",)}),
        (
            "Additional Resources",
            {"fields": ("additional_notes",), "classes": ("collapse",)},
        ),
        (
            "System Info",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    inlines = [LessonAttachmentInline]

    def content_types(self, obj):
        types = obj.get_content_types()
        if not types:
            return format_html('<span style="color: orange;">No Content</span>')

        colors = {"Text": "blue", "Video": "green", "PDF": "red"}
        badges = []
        for content_type in types:
            color = colors.get(content_type, "gray")
            badges.append(
                f'<span style="background: {color}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; margin-right: 3px;">{content_type}</span>'
            )

        return format_html("".join(badges))

    content_types.short_description = "Content Types"


@admin.register(LessonAttachment)
class LessonAttachmentAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "lesson",
        "file_extension",
        "file_size_display",
        "download_count",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "created_at", "lesson__module__course__category"]
    search_fields = [
        "title",
        "description",
        "lesson__title",
        "lesson__module__title",
        "lesson__module__course__title",
    ]
    readonly_fields = ["file_size", "download_count", "created_at"]

    fieldsets = (
        ("Basic Info", {"fields": ("lesson", "title", "description", "file")}),
        ("File Info", {"fields": ("file_size", "download_count", "is_active")}),
        ("System Info", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def file_extension(self, obj):
        ext = obj.get_file_extension()
        return ext.upper()[1:] if ext else "Unknown"

    file_extension.short_description = "Type"

    def file_size_display(self, obj):
        return f"{obj.get_file_size_mb()} MB"

    file_size_display.short_description = "Size"


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "lesson_title",
        "status",
        "completion_percentage",
        "time_spent_display",
        "started_at",
        "completed_at",
        "last_accessed",
    ]
    list_filter = [
        "status",
        "lesson__module__course__category",
        "started_at",
        "completed_at",
        "last_accessed",
    ]
    search_fields = [
        "student__username",
        "student__first_name",
        "student__last_name",
        "lesson__title",
        "lesson__module__title",
        "lesson__module__course__title",
    ]
    readonly_fields = ["started_at", "completed_at", "last_accessed"]

    fieldsets = (
        (
            "Progress Info",
            {"fields": ("student", "lesson", "status", "completion_percentage")},
        ),
        (
            "Time Tracking",
            {
                "fields": (
                    "time_spent_minutes",
                    "started_at",
                    "completed_at",
                    "last_accessed",
                )
            },
        ),
    )

    actions = ["mark_as_completed", "reset_progress"]

    def lesson_title(self, obj):
        return f"{obj.lesson.module.course.course_code} - {obj.lesson.title}"

    lesson_title.short_description = "Lesson"

    def time_spent_display(self, obj):
        hours = obj.time_spent_minutes / 60
        return f"{hours:.1f}h" if hours >= 1 else f"{obj.time_spent_minutes}m"

    time_spent_display.short_description = "Time Spent"

    def mark_as_completed(self, request, queryset):
        updated = 0
        for progress in queryset:
            if progress.status != "completed":
                progress.mark_as_completed()
                updated += 1
        self.message_user(request, f"{updated} lessons marked as completed.")

    mark_as_completed.short_description = "Mark selected as completed"

    def reset_progress(self, request, queryset):
        queryset.update(
            status="not_started",
            completion_percentage=0.00,
            time_spent_minutes=0,
            started_at=None,
            completed_at=None,
        )
        self.message_user(request, f"{queryset.count()} progress records reset.")

    reset_progress.short_description = "Reset selected progress"


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "course",
        "status",
        "progress_percentage",
        "amount_paid",
        "payment_status",
        "enrolled_at",
    ]
    list_filter = [
        "status",
        "payment_status",
        "course__category",
        "enrolled_at",
        "completed_at",
    ]
    search_fields = [
        "student__username",
        "student__first_name",
        "student__last_name",
        "course__title",
        "course__course_code",
    ]
    readonly_fields = ["enrolled_at", "last_accessed", "total_time_spent_minutes"]

    fieldsets = (
        ("Enrollment Info", {"fields": ("student", "course", "status", "enrolled_at")}),
        (
            "Academic Progress",
            {"fields": ("progress_percentage", "grade", "completed_at")},
        ),
        ("Payment Info", {"fields": ("amount_paid", "payment_status", "payment_date")}),
        (
            "Activity Tracking",
            {"fields": ("last_accessed", "total_time_spent_minutes", "is_active")},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("student", "course")


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = [
        "course",
        "student",
        "rating",
        "review_preview",
        "is_approved",
        "created_at",
    ]
    list_filter = ["rating", "is_approved", "created_at", "course__category"]
    search_fields = ["course__title", "student__username", "review_text"]
    readonly_fields = ["created_at", "updated_at"]

    actions = ["approve_reviews", "reject_reviews"]

    def review_preview(self, obj):
        return (
            obj.review_text[:50] + "..."
            if len(obj.review_text) > 50
            else obj.review_text
        )

    review_preview.short_description = "Review Preview"

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} reviews approved.")

    approve_reviews.short_description = "Approve selected reviews"

    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f"{queryset.count()} reviews rejected.")

    reject_reviews.short_description = "Reject selected reviews"


@admin.register(CourseFAQ)
class CourseFAQAdmin(admin.ModelAdmin):
    list_display = ["question_short", "course", "order", "is_active", "created_at"]
    list_filter = ["is_active", "course__category", "created_at"]
    search_fields = ["question", "answer", "course__title"]
    readonly_fields = ["created_at"]

    def question_short(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question

    question_short.short_description = "Question"


# ============================
# BATCH MANAGEMENT ADMIN
# ============================


class BatchModuleInline(admin.TabularInline):
    model = BatchModule
    extra = 0
    fields = ["title", "order", "is_active"]


class BatchEnrollmentInline(admin.TabularInline):
    model = BatchEnrollment
    extra = 0
    fields = ["student", "status", "enrolled_at", "is_active"]
    readonly_fields = ["enrolled_at"]


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "course",
        "instructor",
        "status",
        "enrollment_count",
        "available_seats",
        "start_date",
        "end_date",
    ]
    list_filter = [
        "status",
        "content_type",
        "is_active",
        "start_date",
        "course__category",
        "created_at",
    ]
    search_fields = [
        "name",
        "code",
        "course__title",
        "course__course_code",
        "instructor__username",
    ]
    readonly_fields = ["code", "created_at", "created_by"]

    fieldsets = (
        ("Basic Information", {"fields": ("course", "name", "code", "instructor")}),
        ("Content & Configuration", {"fields": ("content_type", "max_students")}),
        ("Schedule", {"fields": ("start_date", "end_date")}),
        ("Status", {"fields": ("status", "is_active")}),
        (
            "System Info",
            {"fields": ("created_by", "created_at"), "classes": ("collapse",)},
        ),
    )

    inlines = [BatchModuleInline, BatchEnrollmentInline]

    def enrollment_count(self, obj):
        count = obj.get_enrolled_count()
        max_students = obj.max_students
        color = (
            "green"
            if count < max_students * 0.8
            else "orange" if count < max_students else "red"
        )
        return format_html(
            '<span style="color: {};">{}/{}</span>', color, count, max_students
        )

    enrollment_count.short_description = "Enrollments"

    def available_seats(self, obj):
        available = obj.get_available_seats()
        color = "green" if available > 5 else "orange" if available > 0 else "red"
        return format_html('<span style="color: {};">{}</span>', color, available)

    available_seats.short_description = "Available"

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class BatchLessonInline(admin.TabularInline):
    model = BatchLesson
    extra = 0
    fields = ["title", "lesson_type", "order", "is_active"]


@admin.register(BatchModule)
class BatchModuleAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "batch",
        "order",
        "lesson_count",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "batch__course__category",
        "batch__status",
        "created_at",
    ]
    search_fields = [
        "title",
        "batch__name",
        "batch__code",
        "batch__course__title",
        "batch__course__course_code",
    ]
    readonly_fields = ["created_at"]

    inlines = [BatchLessonInline]

    def lesson_count(self, obj):
        return obj.lessons.count()

    lesson_count.short_description = "Lessons"


@admin.register(BatchLesson)
class BatchLessonAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "batch_module",
        "lesson_type",
        "order",
        "has_content",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "lesson_type",
        "is_active",
        "batch_module__batch__course__category",
        "created_at",
    ]
    search_fields = [
        "title",
        "description",
        "batch_module__title",
        "batch_module__batch__name",
        "batch_module__batch__code",
    ]
    readonly_fields = ["created_at"]

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "batch_module",
                    "title",
                    "description",
                    "lesson_type",
                    "order",
                )
            },
        ),
        ("Content", {"fields": ("text_content", "youtube_url")}),
        ("Settings", {"fields": ("is_active",)}),
        ("System Info", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def has_content(self, obj):
        has_text = bool(obj.text_content)
        has_video = bool(obj.youtube_url)

        if has_text and has_video:
            return format_html('<span style="color: green;">✓ Text + Video</span>')
        elif has_text:
            return format_html('<span style="color: blue;">✓ Text Only</span>')
        elif has_video:
            return format_html('<span style="color: purple;">✓ Video Only</span>')
        else:
            return format_html('<span style="color: red;">✗ No Content</span>')

    has_content.short_description = "Content"


@admin.register(BatchEnrollment)
class BatchEnrollmentAdmin(admin.ModelAdmin):
    list_display = ["student", "batch_info", "status", "enrolled_at", "is_active"]
    list_filter = [
        "status",
        "is_active",
        "batch__status",
        "batch__course__category",
        "enrolled_at",
    ]
    search_fields = [
        "student__username",
        "student__first_name",
        "student__last_name",
        "batch__name",
        "batch__code",
        "batch__course__title",
    ]
    readonly_fields = ["enrolled_at"]

    fieldsets = (
        ("Enrollment Info", {"fields": ("student", "batch", "status", "enrolled_at")}),
        ("Settings", {"fields": ("is_active",)}),
    )

    def batch_info(self, obj):
        return format_html(
            "<strong>{}</strong><br><small>{}</small>",
            obj.batch.name,
            obj.batch.course.title,
        )

    batch_info.short_description = "Batch"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("student", "batch", "batch__course")
        )


# ============================
# ADMIN SITE CUSTOMIZATION
# ============================

# Customize admin site header
admin.site.site_header = "Course Management System"
admin.site.site_title = "CMS Admin"
admin.site.index_title = "Welcome to Course Management System"
