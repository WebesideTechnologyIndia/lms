# certificates/urls.py

from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    # ========== ADMIN PANEL ==========
    path('admin/dashboard/', views.admin_certificate_dashboard, name='admin_dashboard'),
    
    # Certificate Types
    path('admin/types/', views.admin_certificate_types, name='admin_types'),
    path('admin/types/create/', views.admin_create_type, name='admin_create_type'),
    
    # Certificate Templates
    path('admin/templates/', views.admin_certificate_templates, name='admin_templates'),
    path('admin/templates/create/', views.admin_create_template, name='admin_create_template'),
    path('admin/templates/<int:template_id>/edit/', views.admin_edit_template, name='admin_edit_template'),
    path('admin/templates/<int:template_id>/preview/', views.admin_preview_template, name='admin_preview_template'),
    
    # Issue Certificates (Admin)
    path('admin/issue/', views.admin_issue_certificate, name='admin_issue'),
    path('admin/issued/', views.admin_issued_certificates, name='admin_issued'),
    path('admin/issued/<int:cert_id>/revoke/', views.admin_revoke_certificate, name='admin_revoke'),
    
    # ========== INSTRUCTOR PANEL ==========
    path('instructor/dashboard/', views.instructor_certificate_dashboard, name='instructor_dashboard'),
    path('instructor/issue/', views.instructor_issue_certificate, name='instructor_issue'),
    path('instructor/issued/', views.instructor_issued_certificates, name='instructor_issued'),
    
    # ========== STUDENT PANEL ==========
    path('my-certificates/', views.student_certificates, name='student_certificates'),
    path('my-certificates/<int:cert_id>/download/', views.download_certificate, name='download'),
    path('my-certificates/<int:cert_id>/view/', views.view_certificate, name='view'),
    
    # ========== PUBLIC ==========
    path('verify/<str:code>/', views.verify_certificate, name='verify'),
]