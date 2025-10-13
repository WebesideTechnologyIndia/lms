"""
URL configuration for lms project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('userss.urls')),
    path('courses/', include('courses.urls')),
    path('exams/', include('exams.urls')),
    path('webinars/', include('webinars.urls')),
    path('fees/', include('fees.urls')),
    path('zoom/', include('zoom.urls')),
    path('attendance/', include('attendance.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
]

# ✅ SERVE MEDIA FILES IN DEVELOPMENT (QR CODES)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)