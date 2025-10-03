# exams/urls.py - Complete URL Configuration for Exam Management

from django.urls import path
from . import views

urlpatterns = [
    # ==================== ADMIN EXAM MANAGEMENT URLs ====================
    
    # Dashboard
    path('dashboard/', views.exam_dashboard, name='exam_dashboard'),
    
    # Exam Creation
    path('create/', views.create_exam, name='create_exam'),
    # path('edit/<int:exam_id>/', views.edit_exam, name='edit_exam'),
    path('delete/<int:exam_id>/', views.delete_exam, name='delete_exam'),
    
    # Admin Exam Detail View (ADDED THIS)
    path('exam/<int:exam_id>/detail/', views.admin_exam_detail, name='admin_exam_detail'),
    
    # Question Management
    path('<int:exam_id>/add-mcq-questions/', views.add_mcq_questions, name='add_mcq_questions'),
    path('<int:exam_id>/add-qa-questions/', views.add_qa_questions, name='add_qa_questions'),
    path('<int:exam_id>/setup-assignment/', views.setup_assignment, name='setup_assignment'),
    
    # Individual Question Operations
    # path('mcq-question/<int:question_id>/edit/', views.edit_mcq_question, name='edit_mcq_question'),
    # path('mcq-question/<int:question_id>/delete/', views.delete_mcq_question, name='delete_mcq_question'),
    # path('qa-question/<int:question_id>/edit/', views.edit_qa_question, name='edit_qa_question'),
    # path('qa-question/<int:question_id>/delete/', views.delete_qa_question, name='delete_qa_question'),
    
    # Exam Assignment
    path('assign/', views.assign_exam, name='assign_exam'),
    # path('bulk-assign/', views.bulk_assign_exam, name='bulk_assign_exam'),
    # path('assignment/<int:assignment_id>/toggle/', views.toggle_assignment_status, name='toggle_assignment_status'),
    
    # Submissions and Results
    path('submissions/', views.exam_submissions, name='exam_submissions'),
    path('attempt/<int:attempt_id>/view/', views.view_exam_attempt, name='view_exam_attempt'),
    # path('attempt/<int:attempt_id>/delete/', views.delete_exam_attempt, name='delete_exam_attempt'),
    
    # Grading
    path('pending-grading/', views.pending_grading, name='pending_grading'),
    path('attempt/<int:attempt_id>/grade-qa/', views.grade_qa_attempt, name='grade_qa_attempt'),
    path('attempt/<int:attempt_id>/grade-assignment/', views.grade_assignment_attempt, name='grade_assignment_attempt'),
    # path('bulk-grade/', views.bulk_grade_attempts, name='bulk_grade_attempts'),
    
    # Reports and Export
    # path('attempt/<int:attempt_id>/report/', views.download_attempt_report, name='download_attempt_report'),
    # path('submissions/export/', views.export_submissions, name='export_submissions'),
    # path('exam/<int:exam_id>/analytics/', views.exam_analytics, name='exam_analytics'),
    
    # ==================== STUDENT EXAM URLs ====================
    
    # Student Dashboard
    path('student/', views.student_exams, name='student_exams'),
    # path('student/available/', views.available_exams, name='available_exams'),
    # path('student/completed/', views.completed_exams, name='completed_exams'),
    
    # Taking Exams
    path('take/<int:exam_id>/', views.take_exam, name='take_exam'),
    path('attempt/<int:attempt_id>/interface/', views.exam_interface, name='exam_interface'),
    path('attempt/<int:attempt_id>/submit/', views.submit_exam, name='submit_exam'),
    path('attempt/<int:attempt_id>/result/', views.exam_result, name='exam_result'),
    
    # ==================== AJAX/API URLs ====================
    
    # Question Management AJAX
    path('ajax/save-mcq-response/<int:attempt_id>/', views.save_mcq_response, name='save_mcq_response'),
    path('ajax/save-qa-response/<int:attempt_id>/', views.save_qa_response, name='save_qa_response'),
    # path('ajax/save-assignment/<int:attempt_id>/', views.save_assignment_submission, name='save_assignment_submission'),
    
    # Timing and Progress AJAX
    # path('ajax/attempt/<int:attempt_id>/time-left/', views.get_time_left, name='get_time_left'),
    # path('ajax/attempt/<int:attempt_id>/auto-submit/', views.auto_submit_exam, name='auto_submit_exam'),
    # path('ajax/attempt/<int:attempt_id>/save-progress/', views.save_exam_progress, name='save_exam_progress'),
    
    # Assignment Helper AJAX
    path('api/batch/<int:batch_id>/students/', views.get_batch_students_for_exam, name='get_batch_students_for_exam'),
    path('api/course/<int:course_id>/students/', views.get_course_students_for_exam, name='get_course_students_for_exam'),
    # path('ajax/exam/<int:exam_id>/preview/', views.exam_preview, name='exam_preview'),
    
    # Template and Content AJAX
    path('ajax/load-exam-details/<int:exam_id>/', views.load_exam_details, name='load_exam_details'),
    # path('ajax/validate-exam/<int:exam_id>/', views.validate_exam, name='validate_exam'),
    
    # Quick Actions AJAX
    # path('ajax/quick-grade/<int:attempt_id>/', views.quick_grade_modal, name='quick_grade_modal'),
    # path('ajax/bulk-operations/', views.bulk_operations, name='bulk_operations'),
    
    # File Uploads
    # path('upload/question-image/', views.upload_question_image, name='upload_question_image'),
    # path('upload/assignment-file/<int:attempt_id>/', views.upload_assignment_file, name='upload_assignment_file'),
    # path('download/assignment-file/<int:file_id>/', views.download_assignment_file, name='download_assignment_file'),
    
    # ==================== ADVANCED FEATURES URLs ====================
    
    # Exam Templates
    # path('templates/', views.exam_templates, name='exam_templates'),
    # path('template/<int:template_id>/use/', views.use_exam_template, name='use_exam_template'),
    # path('exam/<int:exam_id>/save-as-template/', views.save_as_template, name='save_as_template'),
    
    # Exam Settings
    # path('exam/<int:exam_id>/settings/', views.exam_settings, name='exam_settings'),
    # path('exam/<int:exam_id>/duplicate/', views.duplicate_exam, name='duplicate_exam'),
    # path('exam/<int:exam_id>/publish/', views.publish_exam, name='publish_exam'),
    # path('exam/<int:exam_id>/unpublish/', views.unpublish_exam, name='unpublish_exam'),
    
    # Proctoring and Security
    # path('attempt/<int:attempt_id>/violations/', views.exam_violations, name='exam_violations'),
    # path('ajax/attempt/<int:attempt_id>/log-violation/', views.log_exam_violation, name='log_exam_violation'),
    
    # Statistics and Analytics
    # path('analytics/', views.exam_analytics_dashboard, name='exam_analytics_dashboard'),
    # path('exam/<int:exam_id>/statistics/', views.exam_statistics, name='exam_statistics'),
    # path('student/<int:student_id>/exam-history/', views.student_exam_history, name='student_exam_history'),
    
    # Notifications
    # path('ajax/send-exam-notification/', views.send_exam_notification, name='send_exam_notification'),
    # path('ajax/reminder/<int:exam_id>/', views.send_exam_reminder, name='send_exam_reminder'),

    # ==================== INSTRUCTOR EXAM MANAGEMENT URLs ====================
    
    # Instructor Exam Dashboard
    path('instructor/dashboard/', views.instructor_exam_dashboard, name='instructor_exam_dashboard'),
    
    # Exam Creation
    path('instructor/create/', views.instructor_create_exam, name='instructor_create_exam'),
    path('instructor/<int:exam_id>/add-mcq-questions/', views.instructor_add_mcq_questions, name='instructor_add_mcq_questions'),
    path('instructor/<int:exam_id>/add-qa-questions/', views.instructor_add_qa_questions, name='instructor_add_qa_questions'),
    path('instructor/<int:exam_id>/setup-assignment/', views.instructor_setup_assignment, name='instructor_setup_assignment'),
    
    # Exam Management
    path('instructor/my-exams/', views.instructor_my_exams, name='instructor_my_exams'),
    path('instructor/exam/<int:exam_id>/detail/', views.instructor_exam_detail, name='instructor_exam_detail'),
    path('instructor/assign/', views.instructor_assign_exam, name='instructor_assign_exam'),
    path('instructor/<int:exam_id>/delete/', views.instructor_delete_exam, name='instructor_delete_exam'),
    
    # Submissions and Results
    path('instructor/submissions/', views.instructor_exam_submissions, name='instructor_exam_submissions'),
    path('instructor/attempt/<int:attempt_id>/view/', views.instructor_view_exam_attempt, name='instructor_view_exam_attempt'),
]