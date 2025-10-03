# urls.py - Updated with user management URLs

from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path("", views.user_login, name="user_login"),
    path("login/", views.user_login, name="login"),
    # Dashboards
    path("admin_dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("instructor_dashboard/", views.instructor_dashboard, name="instructor_dashboard"),
    # student
    path("student_dashboard/", views.student_dashboard, name="student_dashboard"),
    # Profile
    path("student-profile/", views.student_profile, name="student_profile"),
    # Courses
    path("student-courses/", views.student_courses, name="student_courses"),
    path("student-browse-courses/", views.browse_courses, name="browse_courses"),
    # Batches
    path("student-batches/", views.student_batches, name="student_batches"),
    # Progress & Learning
    path("student-progress/", views.student_progress, name="student_progress"),
    path("student-assignments/", views.student_assignments, name="student_assignments"),
    path(
        "student-certificates/", views.student_certificates, name="student_certificates"
    ),
    # Settings
    path("student-settings/", views.student_settings, name="student_settings"),
    # User Management (Admin only)
    path("manage_users/", views.manage_users, name="manage_users"),
    path("create_user/", views.create_user, name="create_user"),
    path("edit_user/<int:user_id>/", views.edit_user, name="edit_user"),
    path("delete_user/<int:user_id>/", views.delete_user, name="delete_user"),
    path("user_details/<int:user_id>/", views.user_details, name="user_details"),
    # Email Management URLs
    path("email-dashboard/", views.email_dashboard, name="email_dashboard"),
    path(
        "email-templates/", views.manage_email_templates, name="manage_email_templates"
    ),
    path(
        "email-templates/<int:template_id>/edit/",
        views.edit_email_template,
        name="edit_email_template",
    ),
    path("email-settings/", views.email_limit_settings, name="email_limit_settings"),
    path("email-logs/", views.email_logs, name="email_logs"),
    path("bulk-email/", views.bulk_email, name="bulk_email"),
    path(
        "email-templates/create/",
        views.create_email_template,
        name="create_email_template",
    ),
    path(
        "email-templates/<int:template_id>/delete/",
        views.delete_email_template,
        name="delete_email_template",
    ),
    path(
        "email-templates/<int:template_id>/test/",
        views.test_email_template,
        name="test_email_template",
    ),
    path("email-analytics/", views.email_analytics, name="email_analytics"),
    path(
        "email-management/template-types/",
        views.manage_template_types,
        name="manage_template_types",
    ),
    path(
        "email-management/template-types/create/",
        views.create_template_type,
        name="create_template_type",
    ),
    path(
        "email-management/template-types/update/<int:template_type_id>/",
        views.update_template_type,
        name="update_template_type",
    ),
    path(
        "email-management/template-types/delete/<int:template_type_id>/",
        views.delete_template_type,
        name="delete_template_type",
    ),
    path(
        "email-management/template-types/toggle/<int:template_type_id>/",
        views.toggle_template_type_status,
        name="toggle_template_type_status",
    ),
    # AJAX endpoints
    path(
        "api/template-types/<int:template_type_id>/templates/",
        views.get_templates_by_type,
        name="get_templates_by_type",
    ),
    # Updated email template URLs
    path(
        "email-management/templates/create/",
        views.create_email_template,
        name="create_email_template",
    ),
    path(
        "password-reset/", views.password_reset_request, name="password_reset_request"
    ),
    path(
        "password-reset/verify/",
        views.password_reset_verify,
        name="password_reset_verify",
    ),
    path(
        "password-reset/confirm/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    path("dashboard/", views.instructor_dashboard, name="instructor_dashboard"),
    # Course Management (requires course_management permission)
    path("courses/", views.instructor_courses, name="instructor_courses"),
    # Content Management (requires content_management permission)
    path("content/", views.content_management, name="content_management"),
    # Batch Management (requires batch_management permission)
    path("batches/", views.batch_management, name="batch_management"),
    # Student Management (requires student_management permission)
    path("students/", views.student_management, name="student_management"),
    # Email Marketing (requires email_marketing permission)
    path("email/", views.email_marketing, name="email_marketing"),
    # Analytics (requires analytics_view permission)
    path("analytics/", views.course_analytics, name="course_analytics"),
    # AJAX endpoints
    path("api/check-permission/", views.check_permission, name="check_permission"),
    path(
        "instructors/permissions/",
        views.manage_instructor_permissions,
        name="manage_instructor_permissions",
    ),
    path(
        "instructors/<int:instructor_id>/permissions/",
        views.instructor_permission_detail,
        name="instructor_permission_detail",
    ),
    path(
        "instructors/<int:instructor_id>/permissions/update/",
        views.update_instructor_permissions,
        name="update_instructor_permissions",
    ),
    path(
        "instructors/permissions/bulk-update/",
        views.bulk_permission_update,
        name="bulk_permission_update",
    ),
    path(
        "instructors/permissions/create/",
        views.create_instructor_permission,
        name="create_instructor_permission",
    ),
    path(
        "instructor_course_management/",
        views.instructor_course_management,
        name="instructor_course_management",
    ),
    path(
        "instructor_content_management/",
        views.instructor_content_management,
        name="instructor_content_management",
    ),
    path(
        "instructor_batch_management/",
        views.instructor_batch_management,
        name="instructor_batch_management",
    ),
    path(
        "instructor_student_management/",
        views.instructor_student_management,
        name="instructor_student_management",
    ),
    path(
        "instructor/email/",
        views.instructor_email_management,
        name="instructor_email_management",
    ),
    path(
        "instructor/email/send/",
        views.instructor_send_batch_email,
        name="instructor_send_batch_email",
    ),
    path(
        "instructor/email/history/",
        views.instructor_email_history,
        name="instructor_email_history",
    ),
    # AJAX endpoints
    path(
        "instructor/batch/<int:batch_id>/students/",
        views.get_batch_students,
        name="get_batch_students",
    ),
    path(
        "instructor/email-template/<int:template_id>/preview/",
        views.get_email_template_preview,
        name="get_email_template_preview",
    ),
    path(
        "instructor_profile_management/",
        views.instructor_profile_management,
        name="instructor_profile_management",
    ),
    path(
        "instructor-students/",
        views.instructor_view_students,
        name="instructor_view_students",
    ),
    path(
        "instructor-course-detail/<int:course_id>/",
        views.instructor_course_detail,
        name="instructor_course_detail",
    ),
    # Student Management URLs
    path(
        "instructor/students/",
        views.instructor_student_management,
        name="instructor_student_management",
    ),
    path(
        "api/course/<int:course_id>/batches/",
        views.get_course_batches_api,
        name="get_course_batches_api",
    ),
    path(
        "instructor/enrollment/<int:enrollment_id>/toggle-status/",
        views.toggle_enrollment_status,
        name="toggle_enrollment_status",
    ),
    path(
        "instructor/enrollment/<int:enrollment_id>/change-status/",
        views.change_enrollment_status,
        name="change_enrollment_status",
    ),
    path(
        "instructor/enrollment/bulk-change-status/",
        views.bulk_change_enrollment_status,
        name="bulk_change_enrollment_status",
    ),
    path(
        "instructor/enrollment/<int:enrollment_id>/remove/",
        views.remove_student_enrollment,
        name="remove_student_enrollment",
    ),
    path("send-email-to-user/<int:user_id>/", views.send_email_to_user, name="send_email_to_user"),

    # Exam Management
    # Exam Management
    # Exam Management
    # Exam Management
    # Exam Management
    path("exam-create", views.createExam, name="create_exam"),
    path("assign-create", views.assignExam, name="assign_exam"),
    path("exam-submission", views.exam_submission, name="exam_submission"),
]
