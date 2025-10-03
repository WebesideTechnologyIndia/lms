# zoom/urls.py
from django.urls import path
from . import views

app_name = 'zoom'

urlpatterns = [
    # Dashboard
    path('', views.zoom_dashboard, name='dashboard'),
    
    # Configuration Management
    path('config/', views.zoom_config_setup, name='config_setup'),
    path('config/status/', views.zoom_config_status_page, name='config_status'),
    path('config/test/', views.test_zoom_connection, name='test_connection'),
    
    # Session Management
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/create/', views.create_session, name='create_session'),
    path('sessions/<int:session_id>/', views.session_detail, name='session_detail'),
    path('sessions/<int:session_id>/start/', views.start_meeting, name='start_meeting'),
    path('sessions/<int:session_id>/join/', views.join_meeting, name='join_meeting'),
    path('session/<int:session_id>/end/', views.end_session, name='end_session'),

    # Recordings
    path('recordings/', views.recording_list, name='recording_list'),
    path('recordings/<int:recording_id>/play/', views.play_recording, name='play_recording'),
    
    # AJAX Endpoints
    path('api/batch/<int:batch_id>/details/', views.get_batch_details, name='batch_details'),
    path('api/config/status/', views.zoom_config_status, name='api_config_status'),
    
    # Webhooks
    path('webhook/', views.zoom_webhook, name='webhook'),

    path('test-zoom/', views.test_zoom_config, name='test_zoom'),

     path('student/sessions/', views.student_sessions_browse, name='student_sessions_browse'),
    path('student/sessions/<int:session_id>/', views.student_session_detail, name='student_session_detail'),
    path('student/recordings/', views.student_recordings, name='student_recordings'),
    path('student/attendance/', views.student_attendance_history, name='student_attendance'),

]