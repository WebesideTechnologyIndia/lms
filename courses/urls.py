from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    # ==================== COURSE MANAGEMENT ====================
    # Main Dashboard
    path("dashboard/", views.course_dashboard, name="course_dashboard"),
    path("analytics/", views.course_analytics, name="course_analytics"),
    # Course Management
    path("manage/", views.manage_courses, name="manage_courses"),
    path("create/", views.create_course, name="create_course"),
    path("<int:course_id>/edit/", views.edit_course, name="edit_course"),
    path("<int:course_id>/detail/", views.course_detail, name="course_detail"),
    path("<int:course_id>/delete/", views.delete_course, name="delete_course"),
    path(
        "<int:course_id>/toggle-status/",
        views.toggle_course_status,
        name="toggle_course_status",
    ),
    path(
        "<int:course_id>/change-status/",
        views.change_course_status,
        name="change_course_status",
    ),
    path(
        "<int:course_id>/analytics/",
        views.course_specific_analytics,
        name="course_specific_analytics",
    ),
    path("<int:course_id>/students/", views.course_students, name="course_students"),
    path(
        "<int:course_id>/enrollments/",
        views.course_enrollments,
        name="course_enrollments",
    ),
    # ==================== COURSE CATEGORIES ====================
    path("categories/", views.manage_categories, name="manage_categories"),
    path(
        "categories/<int:category_id>/profile/",
        views.category_profile,
        name="category_profile",
    ),
    path("categories/create/", views.create_category, name="create_category"),
    path(
        "categories/<int:category_id>/edit/", views.edit_category, name="edit_category"
    ),
    path(
        "categories/<int:category_id>/delete/",
        views.delete_category,
        name="delete_category",
    ),
    # ==================== COURSE MODULES ====================
    path("<int:course_id>/modules/", views.course_modules, name="course_modules"),
    path("<int:course_id>/modules/create/", views.create_module, name="create_module"),
    path(
        "<int:course_id>/modules/create/instructor",
        views.create_module_instructor,
        name="create_module_instructor",
    ),
    path(
        "<int:course_id>/modules/<int:module_id>/edit/",
        views.edit_module,
        name="edit_module",
    ),
    path(
        "<int:course_id>/modules/<int:module_id>/delete/",
        views.delete_module,
        name="delete_module",
    ),
    # ==================== COURSE LESSONS ====================
    path(
        "<int:course_id>/modules/<int:module_id>/lessons/",
        views.module_lessons,
        name="module_lessons",
    ),
    path(
        "<int:course_id>/modules/<int:module_id>/lessons/create/",
        views.create_lesson,
        name="create_lesson",
    ),
    path(
        "<int:course_id>/modules/<int:module_id>/lessons/create/instructor",
        views.create_lesson_instructor,
        name="create_lesson_instructor",
    ),
    path(
        "<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>/",
        views.lesson_detail,
        name="lesson_detail",
    ),
    path(
        "<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>/lesson_detail_instructor",
        views.lesson_detail_instructor,
        name="lesson_detail_instructor",
    ),
    path(
        "<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>/edit/",
        views.edit_lesson,
        name="edit_lesson",
    ),
    path(
        "<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>/delete/",
        views.delete_lesson,
        name="delete_lesson",
    ),
    path(
        "<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>/complete/",
        views.mark_lesson_complete,
        name="mark_lesson_complete",
    ),
    # Quick lesson creation
    path(
        "<int:course_id>/modules/<int:module_id>/lessons/quick-create/",
        views.quick_create_lesson,
        name="quick_create_lesson",
    ),
    # ==================== ENROLLMENT MANAGEMENT ====================
    path(
        "admin-manage-enrollments/",
        views.manage_enrollments,
        name="admin_manage_enrollments",
    ),
    # Add these URL patterns to your courses/urls.py

# ==================== ENROLLMENT MANAGEMENT ====================
path(
    "admin-manage-enrollments/",
    views.manage_enrollments,
    name="admin_manage_enrollments",
),

# API endpoints - note the trailing slashes!
path(
    "api/enrollment/<int:enrollment_id>/",
    views.get_enrollment_api,
    name="get_enrollment_api",
),
path(
    "api/enrollment/<int:enrollment_id>/update/",
    views.update_enrollment_api,
    name="update_enrollment_api",
),
path(
    "api/enrollment/<int:enrollment_id>/delete/",
    views.delete_enrollment_api,
    name="delete_enrollment_api",
),

# Bulk operations
path(
    "api/bulk-update-status/",
    views.bulk_update_status,
    name="bulk_update_status",
),
path(
    "api/bulk-delete-enrollments/",
    views.bulk_delete_enrollments,
    name="bulk_delete_enrollments",
),

# Email
path(
    "api/send-student-email/",
    views.send_student_email,
    name="send_student_email",
),
    path(
        "admin-manual-enrollment/",
        views.manual_enrollment,
        name="admin_manual_enrollment",
    ),
    path(
        "api/enrollment/<int:enrollment_id>/",
        views.get_enrollment_api,
        name="get_enrollment_api",
    ),
    path(
        "api/enrollment/<int:enrollment_id>/update/",
        views.update_enrollment_api,
        name="update_enrollment_api",
    ),
    path(
        "api/enrollment/<int:enrollment_id>/delete/",
        views.delete_enrollment_api,
        name="delete_enrollment_api",
    ),
    path("send-student-email/", views.send_student_email, name="send_student_email"),
    path("bulk-update-status/", views.bulk_update_status, name="bulk_update_status"),
    path(
        "bulk-delete-enrollments/",
        views.bulk_delete_enrollments,
        name="bulk_delete_enrollments",
    ),
    # ==================== PUBLIC COURSE VIEWS ====================
    path("catalog/", views.course_catalog, name="course_catalog"),
    path("preview/<slug:slug>/", views.course_preview, name="course_preview"),
    # ==================== STUDENT ENROLLMENT ====================
    path("<int:course_id>/enroll/", views.enroll_course, name="enroll_course"),
    path("my-courses/", views.my_courses, name="my_courses"),
    path("<int:course_id>/content/", views.course_content, name="course_content"),
    # ==================== AJAX ENDPOINTS ====================
    path("api/<int:course_id>/stats/", views.get_course_stats, name="get_course_stats"),
    # ==================== BATCH MANAGEMENT (ORIGINAL) ====================
    path("<int:course_id>/batches/", views.batch_list, name="batch_list"),
    path("<int:course_id>/batches/create/", views.create_batch, name="create_batch"),
    path(
        "<int:course_id>/batches/<int:batch_id>/",
        views.batch_detail,
        name="batch_detail",
    ),
    path(
        "<int:course_id>/batches/<int:batch_id>/edit/",
        views.edit_batch,
        name="edit_batch",
    ),
    # Batch modules and lessons
    path(
        "<int:course_id>/batches/<int:batch_id>/modules/create/",
        views.create_batch_module,
        name="create_batch_module",
    ),
    path(
        "<int:course_id>/batches/<int:batch_id>/modules/<int:module_id>/lessons/create/",
        views.create_batch_lesson,
        name="create_batch_lesson",
    ),
    # Batch enrollments - ORIGINAL PATTERN
    path(
        "<int:course_id>/batches/<int:batch_id>/enrollments/",
        views.batch_enrollments,
        name="batch_enrollments",
    ),
    # Student batch views
    path("my-batches/", views.student_batch_list, name="student_batch_list"),
    path(
        "batches/<int:batch_id>/content/",
        views.student_batch_content,
        name="student_batch_content",
    ),
    # ==================== INSTRUCTOR PANEL BATCH MANAGEMENT ====================
    # Overview
    path(
        "batch-overview/",
        views.instructor_batch_overview,
        name="instructor_batch_overview",
    ),
    path(
        "batches/all/",
        views.instructor_view_all_batches,
        name="instructor_view_all_batches",
    ),
    # Course specific batch management (DIFFERENT NAMES!)
    path(
        "instructor/course/<int:course_id>/batches/",
        views.instructor_batch_list,
        name="instructor_batch_list",
    ),
    path(
        "instructor/course/<int:course_id>/batch/create/",
        views.instructor_create_batch,
        name="instructor_create_batch",
    ),
    # Individual batch management
    path(
        "instructor/course/<int:course_id>/batch/<int:batch_id>/",
        views.instructor_batch_detail,
        name="instructor_batch_detail",
    ),
    path(
        "instructor/course/<int:course_id>/batch/<int:batch_id>/edit/",
        views.instructor_edit_batch,
        name="instructor_edit_batch",
    ),
    # Batch content management
    # courses/urls.py mein add karo
    path(
        "instructor/course/<int:course_id>/modules/",
        views.instructor_course_modules,
        name="instructor_course_modules",
    ),
    path(
        "instructor/course/<int:course_id>/batch/<int:batch_id>/module/create/",
        views.instructor_create_batch_module,
        name="instructor_create_batch_module",
    ),
    path(
        "instructor/course/<int:course_id>/batch/<int:batch_id>/module/<int:module_id>/lesson/create/",
        views.instructor_create_batch_lesson,
        name="instructor_create_batch_lesson",
    ),
    # Delete operations
    path(
        "instructor/course/<int:course_id>/batch/<int:batch_id>/module/<int:module_id>/delete/",
        views.instructor_delete_batch_module,
        name="instructor_delete_batch_module",
    ),
    path(
        "instructor/course/<int:course_id>/batch/<int:batch_id>/module/<int:module_id>/lesson/<int:lesson_id>/delete/",
        views.instructor_delete_batch_lesson,
        name="instructor_delete_batch_lesson",
    ),
    # Enrollment management (DIFFERENT NAME!)
    path(
        "instructor/course/<int:course_id>/batch/<int:batch_id>/enrollments/",
        views.instructor_batch_enrollments,
        name="instructor_batch_enrollments",
    ),
    path(
        "instructor/course/<int:course_id>/batch/<int:batch_id>/enrollment/<int:enrollment_id>/toggle/",
        views.instructor_batch_enrollment_toggle,
        name="instructor_batch_enrollment_toggle",
    ),
    path("subscriptions/", views.subscription_list, name="subscription_list"),
    path(
        "subscriptions/create/", views.create_subscription, name="create_subscription"
    ),
    path(
        "subscriptions/<int:student_id>/",
        views.subscription_details,
        name="subscription_details",
    ),
    path(
        "subscriptions/<int:subscription_id>/edit/",
        views.edit_subscription,
        name="edit_subscription",
    ),
    path(
        "subscriptions/<int:subscription_id>/delete/",
        views.delete_subscription,
        name="delete_subscription",
    ),
    path(
        "subscriptions/device-restrictions/",
        views.device_restrictions,
        name="device_restrictions",
    ),
    path(
        "subscriptions/<int:subscription_id>/update-devices/",
        views.update_device_restriction,
        name="update_device_restriction",
    ),
    # ==================== COURSE REVIEWS ====================
    path("reviews/", views.course_reviews, name="course_reviews"),
    path(
        "reviews/<int:course_id>/",
        views.course_review_detail,
        name="course_review_detail",
    ),
    path(
        "reviews/<int:review_id>/approve/", views.approve_review, name="approve_review"
    ),
    # ==================== ATTENDANCE ====================
    path(
        "attendance/dashboard/", views.attendance_dashboard, name="attendance_dashboard"
    ),
    path("attendance/status/", views.attendance_status, name="attendance_status"),
    path(
        "attendance/student/<int:student_id>/",
        views.student_attendance_detail,
        name="student_attendance_detail",
    ),
    path("attendance/export/", views.export_attendance, name="export_attendance"),
    path(
        "course/<int:course_id>/submit-review/",
        views.submit_course_review,
        name="submit_course_review",
    ),
    path("my-reviews/", views.my_reviews, name="my_reviews"),
    path(
        "my-reviews/<int:review_id>/edit/", views.edit_my_review, name="edit_my_review"
    ),
    path(
        "my-reviews/<int:review_id>/delete/",
        views.delete_my_review,
        name="delete_my_review",
    ),
    path(
        "devices/<int:device_id>/remove/",
        views.remove_device_session,
        name="remove_device_session",
    ),
    path(
        "<int:course_id>/continue/", views.continue_learning, name="continue_learning"
    ),
    path(
        "<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>/view/",
        views.student_lesson_view,
        name="student_lesson_view",
    ),
    path(
        "<int:course_id>/details/",
        views.course_detail_continue_learning_student,
        name="course_detail_continue_learning_student",
    ),
]
