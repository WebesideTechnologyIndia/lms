# attendance/urls.py - COMPLETE & WORKING

from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # ==================== INSTRUCTOR URLS ====================
    
    # Session Management
    path('instructor/sessions/', views.instructor_sessions, name='instructor_sessions'),
    path('instructor/create-session/', views.create_session, name='create_session'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    
    # Manual Attendance
    path('session/<int:session_id>/student/<int:student_id>/mark/', 
         views.manual_mark_attendance, name='manual_mark'),
    path('session/<int:session_id>/mark-attendance/', 
         views.mark_attendance, name='mark_attendance'),
    path('session/<int:session_id>/mark-attendance/instructor', 
         views.mark_attendance_instructor, name='mark_attendance_instructor'),
    path('session/<int:session_id>/mark-selected/', 
         views.mark_selected_attendance, name='mark_selected_attendance'),
    path('session/<int:session_id>/bulk-mark/', 
         views.bulk_mark_attendance, name='bulk_mark_attendance'),
    path('session/<int:session_id>/request-manual/', views.request_manual_attendance, name='request_manual_attendance'),
path('request-manual/<int:session_id>/', 
     views.request_manual_attendance, 
     name='request_manual_attendance_alt'),

    # Manual Requests
    path('instructor/pending-requests/', views.pending_requests, name='pending_requests'),
    path('request/<int:request_id>/approve/', views.approve_manual_request, name='approve_manual_request'),
    path('request/<int:request_id>/reject/', views.reject_manual_request, name='reject_manual_request'),
    
    # ==================== STUDENT URLS ====================
    
    # QR Scanner
    path('student/scanner/', views.student_scanner, name='student_scanner'),
    path('student/mark-qr/', views.mark_attendance_qr, name='mark_attendance_qr'),
    
    # Manual Request
    path('session/<int:session_id>/request-manual/', 
         views.request_manual_attendance, name='request_manual_attendance'),
    
    # Student Dashboard
    path('student/my-attendance/', views.student_my_attendance, name='student_my_attendance'),
    path('student/attendance-history/', views.student_attendance_history, name='student_attendance_history'),
    
    # ==================== COMMON/SHARED URLS ====================
    
    # Session List (for both instructor and student)
    path('sessions/', views.session_list, name='session_list'),
    
    # Analytics & Reports
    path('reports/', views.attendance_reports, name='attendance_reports'),
    path('analytics/', views.attendance_analytics, name='attendance_analytics'),
]

# ==================== URL SUMMARY ====================
# 
# INSTRUCTOR VIEWS:
# - instructor_sessions: List all sessions
# - create_session: Create new attendance session
# - session_detail: View session with student list
# - manual_mark_attendance: Mark individual student
# - mark_attendance: Mark multiple students page
# - mark_selected_attendance: AJAX bulk mark selected
# - bulk_mark_attendance: Mark all unmarked students
# - pending_requests: View pending manual requests
# - approve_manual_request: Approve student request
# - reject_manual_request: Reject student request
#
# STUDENT VIEWS:
# - student_scanner: QR code scanner page
# - mark_attendance_qr: AJAX QR scan endpoint
# - request_manual_attendance: Request manual attendance
# - student_my_attendance: View own attendance summary
# - student_attendance_history: Complete attendance history
#
# COMMON VIEWS:
# - session_list: All sessions (role-based)
# - attendance_reports: Generate reports
# - attendance_analytics: View analytics dashboard