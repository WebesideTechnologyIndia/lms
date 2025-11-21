# fees/urls.py - Complete URL Configuration

from django.urls import path
from . import views

app_name = "fees"

urlpatterns = [
    # ==================== ADMIN DASHBOARD ====================
    path("admin/", views.admin_fees_dashboard, name="admin_fees_dashboard"),
    path("admin/daily-tasks/", views.run_daily_fee_tasks, name="run_daily_fee_tasks"),
    # ==================== FEE STRUCTURE MANAGEMENT ====================
    path(
        "admin/structures/", views.manage_fee_structures, name="manage_fee_structures"
    ),
    path(
        "admin/structures/create/",
        views.create_fee_structure,
        name="create_fee_structure",
    ),
    path(
        "admin/structures/<int:structure_id>/edit/",
        views.edit_fee_structure,
        name="edit_fee_structure",
    ),
    path(
        "admin/structures/<int:structure_id>/delete/",
        views.delete_fee_structure,
        name="delete_fee_structure",
    ),
    # ==================== STUDENT FEE ASSIGNMENT ====================
    path("admin/student-fees/", views.manage_student_fees, name="manage_student_fees"),
    path(
        "admin/student-fees/<int:pk>/edit/",
        views.edit_student_fee_assignment,
        name="edit_student_fee_assignment",
    ),
    path(
        "admin/student-fees/assign/",
        views.assign_fee_to_student,
        name="assign_fee_to_student",
    ),
    path(
        "admin/student-fees/<int:assignment_id>/",
        views.student_fee_detail,
        name="student_fee_detail",
    ),
    # urls.py mein add karo
    path(
        "admin/student-fee-details/<int:student_id>/<int:course_id>/",
        views.student_fee_details,
        name="student_fee_details",
    ),
    path(
        "admin/student-fees/<int:assignment_id>/lock/",
        views.lock_course_for_student,
        name="lock_course_for_student",
    ),
    path(
        "admin/student-fees/<int:assignment_id>/unlock/",
        views.unlock_course_for_student,
        name="unlock_course_for_student",
    ),
    # ==================== PAYMENT MANAGEMENT ====================
    path("admin/payments/record/", views.record_payment, name="record_payment"),
    path(
        "admin/payments/quick/<int:assignment_id>/",
        views.quick_payment,
        name="quick_payment",
    ),
    path("admin/payments/history/", views.payment_history, name="payment_history"),
    path("admin/payments/overdue/", views.overdue_payments, name="overdue_payments"),
    # ==================== BATCH ACCESS CONTROL ====================
    path("admin/batch-access/", views.manage_batch_access, name="manage_batch_access"),
    path(
        "admin/batch-access/create/",
        views.create_batch_access_control,
        name="create_batch_access_control",
    ),
    # ==================== REPORTS ====================
    path("admin/reports/", views.fee_reports, name="fee_reports"),
    path(
        "admin/reports/export-payments/",
        views.export_payment_report,
        name="export_payment_report",
    ),
    path(
        "admin/reports/export-overdue/",
        views.export_overdue_report,
        name="export_overdue_report",
    ),
    # ==================== DISCOUNT MANAGEMENT ====================
    path("admin/discounts/", views.manage_discounts, name="manage_discounts"),
    path("admin/discounts/create/", views.create_discount, name="create_discount"),
    path(
        "admin/discounts/<int:discount_id>/edit/",
        views.edit_discount,
        name="edit_discount",
    ),
    path(
        "admin/discounts/<int:discount_id>/delete/",
        views.delete_discount,
        name="delete_discount",
    ),
    # ==================== AJAX ENDPOINTS ====================
    path(
        "ajax/emi-schedules/",
        views.get_emi_schedules_ajax,
        name="get_emi_schedules_ajax",
    ),
    path(
        "ajax/update-emi-status/",
        views.update_emi_status_ajax,
        name="update_emi_status_ajax",
    ),
    path(
        "ajax/send-reminder/",
        views.send_payment_reminder_ajax,
        name="send_payment_reminder_ajax",
    ),
    path(
        "ajax/student-fee-info/",
        views.get_student_fee_info_ajax,
        name="get_student_fee_info_ajax",
    ),
    path(
        "ajax/fee-structure-details/",
        views.get_fee_structure_details_ajax,
        name="get_fee_structure_details_ajax",
    ),
    path(
        "ajax/calculate-payment/",
        views.calculate_payment_amount_ajax,
        name="calculate_payment_amount_ajax",
    ),
    path("ajax/get-emi-schedules/", views.get_emi_schedules, name="get_emi_schedules"),
    path(
        "ajax/get-emi-schedules/",
        views.get_emi_schedules_ajax,
        name="get_emi_schedules",
    ),
    path(
        "ajax/calculate-payment/",
        views.calculate_payment_ajax,
        name="calculate_payment",
    ),
    # ==================== STUDENT PORTAL ====================
    path("student/", views.student_fee_dashboard, name="student_fee_dashboard"),
    path(
        "student/course/<int:assignment_id>/",
        views.student_course_fees,
        name="student_course_fees",
    ),
    path(
        "student/pay/<int:assignment_id>/",
        views.make_online_payment,
        name="make_online_payment",
    ),
    path(
        "admin/student-courses/",
        views.student_course_management,
        name="student_course_management",
    ),
    path(
        "admin/student-courses/action/",
        views.student_course_management_action,
        name="student_course_management_action",
    ),
    path(
        "admin/bulk-course-action/", views.bulk_course_action, name="bulk_course_action"
    ),
]
