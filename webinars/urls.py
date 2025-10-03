# webinars/urls.py - COMPLETE UPDATED URLS

from django.urls import path
from . import views

app_name = 'webinars'

urlpatterns = [
    # Public URLs
    path('', views.webinar_landing, name='webinar_landing'),
    path('webinars/', views.webinar_list, name='webinar_list'),
    path('webinar/<slug:slug>/', views.webinar_detail, name='webinar_detail'),
    path('webinar/<slug:slug>/register/', views.webinar_register, name='webinar_register'),
    path('registration-success/<int:registration_id>/', views.registration_success, name='registration_success'),
    
    # User Dashboard
    path('my-webinars/', views.my_webinars, name='my_webinars'),
    path('feedback/<int:webinar_id>/', views.webinar_feedback, name='webinar_feedback'),
    
    # Registration URLs
    path('register/<slug:slug>/', views.webinar_register, name='webinar_register'),
    path('registration/success/<int:registration_id>/', views.registration_success, name='registration_success'),
    path('registration/<int:registration_id>/confirm-payment/', views.confirm_payment, name='confirm_payment'),
    
    # Admin URLs
    path('admin/dashboard/', views.admin_webinar_dashboard, name='admin_webinar_dashboard'),
    path('admin/webinars/', views.admin_manage_webinars, name='admin_manage_webinars'),
    path('admin/webinars/create/', views.admin_create_webinar, name='admin_create_webinar'),
    path('admin/webinars/<int:webinar_id>/edit/', views.admin_edit_webinar, name='admin_edit_webinar'),
    path('admin/webinars/<int:webinar_id>/registrations/', views.admin_webinar_registrations, name='admin_webinar_registrations'),
    path('admin/registrations/', views.admin_all_registrations, name='admin_all_registrations'),
    path('admin/webinars/<int:webinar_id>/analytics/', views.webinar_analytics, name='webinar_analytics'),
    
    # Admin Registration Management
    path('admin/registration/<int:registration_id>/mark-paid/', views.admin_mark_payment, name='admin_mark_payment'),
    path('admin/registration/<int:registration_id>/delete/', views.admin_delete_registration, name='admin_delete_registration'),
    path('admin/registration/<int:registration_id>/send-reminder/', views.admin_send_reminder, name='admin_send_reminder'),
    path('admin/registration/<int:registration_id>/update-status/', views.update_registration_status, name='update_registration_status'),
    
    # Admin Category Management
    path('admin/categories/', views.admin_manage_categories, name='admin_manage_categories'),
    path('admin/categories/create/', views.admin_create_category, name='admin_create_category'),
    path('admin/categories/<int:category_id>/edit/', views.admin_edit_category, name='admin_edit_category'),
    path('admin/categories/<int:category_id>/delete/', views.admin_delete_category, name='admin_delete_category'),
    
    # Bulk Actions
    path('admin/bulk-update-status/', views.admin_bulk_update_status, name='admin_bulk_update_status'),
    path('admin/bulk-send-reminders/', views.admin_bulk_send_reminders, name='admin_bulk_send_reminders'),
    
    # AJAX/API URLs
    path('api/update-registration/<int:registration_id>/', views.update_registration_status, name='update_registration_status'),
    path('api/upcoming-webinars/', views.api_upcoming_webinars, name='api_upcoming_webinars'),
    
    # Testing URLs
    path('test/', views.simple_landing, name='simple_landing'),
    path('ajax-register/', views.ajax_register, name='ajax_register'),
    path('api/register/', views.ajax_register, name='api_register'),
]