from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime
from .models import CertificateType, CertificateTemplate, IssuedCertificate
from courses.models import Course, Batch, BatchEnrollment
from userss.models import CustomUser as User

# ==================== ADMIN PANEL ====================

@login_required
def admin_certificate_dashboard(request):
    """Admin certificate dashboard"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    # Stats
    total_templates = CertificateTemplate.objects.filter(is_active=True).count()
    total_issued = IssuedCertificate.objects.filter(status='active').count()
    total_types = CertificateType.objects.filter(is_active=True).count()
    
    # Recent issued certificates
    recent_issued = IssuedCertificate.objects.select_related(
        'student', 'course', 'batch', 'issued_by'
    ).order_by('-issued_at')[:10]
    
    # Certificate types with counts
    types_with_counts = CertificateType.objects.annotate(
        issued_count=Count('issuedcertificate', filter=Q(issuedcertificate__status='active'))
    ).filter(is_active=True)
    
    context = {
        'total_templates': total_templates,
        'total_issued': total_issued,
        'total_types': total_types,
        'recent_issued': recent_issued,
        'types_with_counts': types_with_counts,
    }
    
    return render(request, 'admin/dashboard.html', context)

@login_required
def admin_certificate_types(request):
    """Manage certificate types"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    types = CertificateType.objects.annotate(
        template_count=Count('templates', distinct=True),
        issued_count=Count('templates__issuedcertificate', distinct=True)
    ).order_by('-created_at')
    
    context = {
        'types': types,
    }
    
    return render(request, 'admin/types.html', context)

@login_required
def admin_create_type(request):
    """Create certificate type"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        type_code = request.POST.get('type_code')
        description = request.POST.get('description', '')
        
        if not name or not type_code:
            messages.error(request, 'Name and type are required!')
            return redirect('certificates:admin_create_type')
        
        CertificateType.objects.create(
            name=name,
            type_code=type_code,
            description=description,
            created_by=request.user
        )
        
        messages.success(request, f'Certificate type "{name}" created successfully!')
        return redirect('certificates:admin_types')
    
    context = {
        'type_choices': CertificateType.TYPE_CHOICES,
    }
    
    return render(request, 'admin/create_type.html', context)


@login_required
def admin_certificate_templates(request):
    """Manage certificate templates"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    templates = CertificateTemplate.objects.select_related(
        'certificate_type', 'created_by'
    ).annotate(
        issued_count=Count('issuedcertificate')
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(templates, 12)
    page = request.GET.get('page')
    templates = paginator.get_page(page)
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'admin/templates.html', context)


@login_required
def admin_create_template(request):
    """Create certificate template with pre-made library"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        certificate_type_id = request.POST.get('certificate_type')
        orientation = request.POST.get('orientation', 'landscape')
        html_content = request.POST.get('html_content', '')
        css_content = request.POST.get('css_content', '')
        
        # Check if using pre-made template
        use_template = request.POST.get('use_template')
        
        if not name or not certificate_type_id:
            messages.error(request, 'Name and certificate type are required!')
            return redirect('certificates:admin_create_template')
        
        cert_type = get_object_or_404(CertificateType, id=certificate_type_id)
        
        # Load template library
        from .template_library import get_template_library
        library = get_template_library()
        
        # Use pre-made template if selected
        if use_template and use_template in library:
            html_content = library[use_template]['html']
            css_content = library[use_template]['css']
        
        template = CertificateTemplate.objects.create(
            name=name,
            certificate_type=cert_type,
            orientation=orientation,
            html_content=html_content or get_default_template_html(),
            css_content=css_content or get_default_template_css(),
            created_by=request.user
        )
        
        messages.success(request, f'Template "{name}" created successfully!')
        return redirect('certificates:admin_edit_template', template_id=template.id)
    
    types = CertificateType.objects.filter(is_active=True)
    
    # Load template library
    from .template_library import get_template_library
    template_library = get_template_library()
    
    context = {
        'types': types,
        'template_library': template_library,
        'default_html': get_default_template_html(),
        'default_css': get_default_template_css(),
    }
    
    return render(request, 'admin/create_template.html', context)


@login_required
def admin_preview_template(request, template_id):
    """Preview template with sample data"""
    template = get_object_or_404(CertificateTemplate, id=template_id)
    
    # Sample data for preview
    sample_data = {
        '{student_name}': 'John Doe',
        '{course_name}': 'Advanced Python Programming',
        '{batch_name}': 'Batch 2024-A',
        '{completion_date}': datetime.now().strftime('%B %d, %Y'),
        '{issue_date}': datetime.now().strftime('%B %d, %Y'),
        '{certificate_id}': 'CERT-SAMPLE123',
        '{instructor_name}': 'Prof. Jane Smith',
        '{grade}': 'A+',
        '{duration}': '12 Weeks',
    }
    
    # Replace placeholders
    html = template.html_content
    for placeholder, value in sample_data.items():
        html = html.replace(placeholder, value)
    
    context = {
        'template': template,
        'html_content': html,
        'css_content': template.css_content,
    }
    
    return render(request, 'admin/preview_template.html', context)


# certificates/views.py

# certificates/views.py

from django.db.models import Count, Q
from courses.models import Course, Batch
from userss.models import AbstractUser

# certificates/views.py

# certificates/views.py


# Add this view after admin_revoke_certificate


@login_required
def admin_issued_certificates(request):
    """View all issued certificates with filters"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    # Filters
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    
    # Base query
    certificates = IssuedCertificate.objects.select_related(
        'student', 'course', 'batch', 'template', 'issued_by', 'certificate_type'
    ).order_by('-issued_at')
    
    # Apply search
    if search:
        certificates = certificates.filter(
            Q(student_name__icontains=search) |
            Q(certificate_id__icontains=search) |
            Q(student__email__icontains=search)
        )
    
    # Apply status filter
    if status_filter:
        certificates = certificates.filter(status=status_filter)
    
    # Apply type filter
    if type_filter:
        certificates = certificates.filter(certificate_type_id=type_filter)
    
    # Pagination
    paginator = Paginator(certificates, 20)
    page = request.GET.get('page')
    certificates = paginator.get_page(page)
    
    # Get certificate types for filter dropdown
    types = CertificateType.objects.filter(is_active=True)
    
    context = {
        'certificates': certificates,
        'search': search,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'types': types,
    }
    
    return render(request, 'admin/issued_certificates.html', context)


@login_required
def admin_revoke_certificate(request, cert_id):
    """Revoke a certificate"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    cert = get_object_or_404(IssuedCertificate, id=cert_id)
    
    if request.method == 'POST':
        cert.status = 'revoked'
        cert.is_active = False
        cert.save()
        
        messages.success(request, f'Certificate #{cert.certificate_id} revoked successfully!')
        return redirect('certificates:admin_issued')
    
    context = {
        'certificate': cert,
    }
    
    return render(request, 'admin/revoke_certificate.html', context)


# ==================== INSTRUCTOR PANEL ====================

@login_required
def instructor_certificate_dashboard(request):
    """Instructor certificate dashboard"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    # Get instructor's issued certificates
    total_issued = IssuedCertificate.objects.filter(
        issued_by=request.user,
        status='active'
    ).count()
    
    # Instructor's courses and batches
    my_courses = Course.objects.filter(instructor=request.user, is_active=True).count()
    my_batches = Batch.objects.filter(instructor=request.user, is_active=True).count()
    
    # Recent issued
    recent_issued = IssuedCertificate.objects.filter(
        issued_by=request.user
    ).select_related('student', 'course', 'batch').order_by('-issued_at')[:10]
    
    context = {
        'total_issued': total_issued,
        'my_courses': my_courses,
        'my_batches': my_batches,
        'recent_issued': recent_issued,
    }
    
    return render(request, 'instructor/dashboard.html', context)


@login_required
def instructor_issue_certificate(request):
    """Instructor issue certificates (only their students)"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    if request.method == 'POST':
        template_id = request.POST.get('template_id')
        issue_type = request.POST.get('issue_type')
        
        template = get_object_or_404(CertificateTemplate, id=template_id)
        
        issued_count = 0
        
        if issue_type == 'individual':
            student_ids = request.POST.getlist('selected_students')
            course_id = request.POST.get('course_id')
            batch_id = request.POST.get('batch_id')
            
            course = Course.objects.get(id=course_id, instructor=request.user) if course_id else None
            batch = Batch.objects.get(id=batch_id, instructor=request.user) if batch_id else None
            
            for student_id in student_ids:
                student = User.objects.get(id=student_id)
                
                # Verify student is in instructor's batch/course
                if not is_instructor_student(request.user, student):
                    continue
                
                cert = IssuedCertificate.objects.create(
                    template=template,
                    certificate_type=template.certificate_type,
                    student=student,
                    course=course,
                    batch=batch,
                    student_name=student.get_full_name() or student.username,
                    course_name=course.title if course else '',
                    batch_name=batch.name if batch else '',
                    issue_date=timezone.now().date(),
                    issued_by=request.user
                )
                
                generate_certificate_pdf(cert)
                issued_count += 1
            
            messages.success(request, f'✅ Issued {issued_count} certificates!')
        
        elif issue_type == 'batch':
            batch_id = request.POST.get('batch_id')
            batch = get_object_or_404(Batch, id=batch_id, instructor=request.user)
            
            enrollments = BatchEnrollment.objects.filter(batch=batch, is_active=True)
            
            for enrollment in enrollments:
                cert = IssuedCertificate.objects.create(
                    template=template,
                    certificate_type=template.certificate_type,
                    student=enrollment.student,
                    course=batch.course,
                    batch=batch,
                    student_name=enrollment.student.get_full_name() or enrollment.student.username,
                    course_name=batch.course.title,
                    batch_name=batch.name,
                    issue_date=timezone.now().date(),
                    issued_by=request.user
                )
                
                generate_certificate_pdf(cert)
                issued_count += 1
            
            messages.success(request, f'✅ Issued {issued_count} certificates to batch!')
        
        elif issue_type == 'course':
            course_id = request.POST.get('course_id')
            course = get_object_or_404(Course, id=course_id, instructor=request.user)
            
            from courses.models import Enrollment
            enrollments = Enrollment.objects.filter(course=course, is_active=True)
            
            for enrollment in enrollments:
                cert = IssuedCertificate.objects.create(
                    template=template,
                    certificate_type=template.certificate_type,
                    student=enrollment.student,
                    course=course,
                    student_name=enrollment.student.get_full_name() or enrollment.student.username,
                    course_name=course.title,
                    issue_date=timezone.now().date(),
                    issued_by=request.user
                )
                
                generate_certificate_pdf(cert)
                issued_count += 1
            
            messages.success(request, f'✅ Issued {issued_count} certificates!')
        
        return redirect('certificates:instructor_issued')
    
    # GET - only instructor's data
    templates = CertificateTemplate.objects.filter(is_active=True)
    
    # Only students from instructor's batches/courses
    my_students = get_instructor_students(request.user)
    my_batches = Batch.objects.filter(instructor=request.user, is_active=True)
    my_courses = Course.objects.filter(instructor=request.user, is_active=True)
    
    context = {
        'templates': templates,
        'students': my_students,
        'batches': my_batches,
        'courses': my_courses,
    }
    
    return render(request, 'instructor/issue_certificate.html', context)


@login_required
def instructor_issued_certificates(request):
    """View instructor's issued certificates"""
    if request.user.role != 'instructor':
        return redirect('user_login')
    
    certificates = IssuedCertificate.objects.filter(
        issued_by=request.user
    ).select_related('student', 'course', 'batch', 'template').order_by('-issued_at')
    
    # Filters
    search = request.GET.get('search', '')
    if search:
        certificates = certificates.filter(
            Q(student_name__icontains=search) |
            Q(certificate_id__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(certificates, 20)
    page = request.GET.get('page')
    certificates = paginator.get_page(page)
    
    context = {
        'certificates': certificates,
        'search': search,
    }
    
    return render(request, 'instructor/issued_certificates.html', context)


# ==================== STUDENT PANEL ====================

@login_required
def student_certificates(request):
    """Student's certificates"""
    if request.user.role != 'student':
        return redirect('user_login')
    
    certificates = IssuedCertificate.objects.filter(
        student=request.user,
        status='active'
    ).select_related('course', 'batch', 'template').order_by('-issued_at')
    
    context = {
        'certificates': certificates,
    }
    
    return render(request, 'student/my_certificates.html', context)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from .models import CertificateTemplate, CertificateType, IssuedCertificate
from userss.models import AbstractUser
from courses.models import Course, Batch, Enrollment


def get_certificate_context_data(certificate):
    """
    Generate complete context data for certificate rendering
    Replaces all placeholders with actual data
    """
    context = {
        # Student Information
        'student_name': certificate.student_name or 'N/A',
        '{student_name}': certificate.student_name or 'N/A',
        
        # Course Information
        'course_name': certificate.course_name or 'N/A',
        '{course_name}': certificate.course_name or 'N/A',
        
        # Batch Information
        'batch_name': certificate.batch_name or 'N/A',
        '{batch_name}': certificate.batch_name or 'N/A',
        
        # Dates
        'completion_date': certificate.completion_date.strftime('%B %d, %Y') if certificate.completion_date else certificate.issue_date.strftime('%B %d, %Y'),
        '{completion_date}': certificate.completion_date.strftime('%B %d, %Y') if certificate.completion_date else certificate.issue_date.strftime('%B %d, %Y'),
        
        'issue_date': certificate.issue_date.strftime('%B %d, %Y') if certificate.issue_date else 'N/A',
        '{issue_date}': certificate.issue_date.strftime('%B %d, %Y') if certificate.issue_date else 'N/A',
        
        # Certificate ID
        'certificate_id': certificate.certificate_id or f"CERT-{certificate.id}",
        '{certificate_id}': certificate.certificate_id or f"CERT-{certificate.id}",
        
        # Instructor/Issuer Information
        'instructor_name': certificate.issued_by.get_full_name() if certificate.issued_by else 'Admin',
        '{instructor_name}': certificate.issued_by.get_full_name() if certificate.issued_by else 'Admin',
        
        # Grade Information
        'grade': certificate.grade if certificate.grade else 'N/A',
        '{grade}': certificate.grade if certificate.grade else 'N/A',
        
        # Duration Information
        'duration': certificate.duration if certificate.duration else 'N/A',
        '{duration}': certificate.duration if certificate.duration else 'N/A',
    }
    
    return context


def render_certificate_html(certificate):
    """
    Render certificate HTML by replacing all placeholders
    """
    html_content = certificate.template.html_content
    css_content = certificate.template.css_content
    
    # Get context data
    context = get_certificate_context_data(certificate)
    
    # Replace all placeholders in HTML
    for placeholder, value in context.items():
        if placeholder.startswith('{'):
            html_content = html_content.replace(placeholder, str(value))
    
    # Combine HTML with CSS
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Certificate - {certificate.student_name}</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&family=Georgia:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Georgia', serif;
            }}
            @page {{
                size: {'A4 landscape' if certificate.template.orientation == 'landscape' else 'A4 portrait'};
                margin: 0;
            }}
            @media print {{
                body {{
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }}
            }}
            {css_content}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    return full_html


@login_required
def admin_issue_certificate(request):
    """Issue certificates with smart context selection"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    if request.method == 'POST':
        template_id = request.POST.get('template_id')
        issue_type = request.POST.get('issue_type')
        
        template = get_object_or_404(CertificateTemplate, id=template_id)
        
        issued_count = 0
        
        if issue_type == 'individual':
            student_ids = request.POST.getlist('selected_students')
            
            # ✅ User ne kya select kiya
            certificate_for = request.POST.get('certificate_for')  # 'course' or 'batch'
            course_id = request.POST.get('selected_course_id')
            batch_id = request.POST.get('selected_batch_id')
            
            for student_id in student_ids:
                student = User.objects.get(id=student_id)
                
                course = None
                batch = None
                course_name = ''
                batch_name = ''
                grade = ''
                duration = ''
                completion_date = timezone.now().date()
                
                # ✅ Context determine karo
                if certificate_for == 'batch' and batch_id:
                    # Batch certificate
                    batch = Batch.objects.get(id=batch_id)
                    course = batch.course
                    course_name = course.title
                    batch_name = batch.name
                    
                    # Get student's grade and duration from batch enrollment
                    try:
                        from courses.models import BatchEnrollment
                        enrollment = BatchEnrollment.objects.get(batch=batch, student=student)
                        grade = enrollment.grade if hasattr(enrollment, 'grade') else ''
                        
                        # Calculate duration
                        if batch.start_date and batch.end_date:
                            duration_days = (batch.end_date - batch.start_date).days
                            if duration_days > 30:
                                months = duration_days // 30
                                duration = f"{months} Month{'s' if months > 1 else ''}"
                            else:
                                weeks = duration_days // 7
                                duration = f"{weeks} Week{'s' if weeks > 1 else ''}"
                        
                        completion_date = batch.end_date if batch.end_date else timezone.now().date()
                    except Exception as e:
                        print(f"Batch enrollment error: {e}")
                    
                elif certificate_for == 'course' and course_id:
                    # Course certificate (without batch)
                    course = Course.objects.get(id=course_id)
                    course_name = course.title
                    batch_name = ''  # No batch for course certificate
                    
                    # Get course duration
                    try:
                        if hasattr(course, 'duration_weeks') and course.duration_weeks:
                            duration = f"{course.duration_weeks} Week{'s' if course.duration_weeks > 1 else ''}"
                        elif hasattr(course, 'duration_months') and course.duration_months:
                            duration = f"{course.duration_months} Month{'s' if course.duration_months > 1 else ''}"
                    except:
                        pass
                    
                    # Get student's grade from course enrollment
                    try:
                        enrollment = Enrollment.objects.get(course=course, student=student)
                        grade = enrollment.grade if hasattr(enrollment, 'grade') else ''
                        
                        if hasattr(enrollment, 'completion_date') and enrollment.completion_date:
                            completion_date = enrollment.completion_date
                    except Exception as e:
                        print(f"Course enrollment error: {e}")
                
                # Create certificate
                cert = IssuedCertificate.objects.create(
                    template=template,
                    certificate_type=template.certificate_type,
                    student=student,
                    course=course,
                    batch=batch,
                    student_name=student.get_full_name() or student.username,
                    course_name=course_name,
                    batch_name=batch_name,
                    grade=grade,
                    duration=duration,
                    issue_date=timezone.now().date(),
                    completion_date=completion_date,
                    issued_by=request.user
                )
                
                # Generate PDF
                try:
                    generate_certificate_pdf(cert)
                except Exception as e:
                    print(f"PDF Generation Error: {e}")
                
                issued_count += 1
            
            cert_type = "Batch" if certificate_for == 'batch' else "Course"
            messages.success(request, f'✅ Issued {issued_count} {cert_type} certificates!')
        
        elif issue_type == 'batch':
            batch_id = request.POST.get('batch_id')
            batch = get_object_or_404(Batch, id=batch_id)
            
            # Get batch enrollments
            try:
                from courses.models import BatchEnrollment
                enrollments = BatchEnrollment.objects.filter(batch=batch, is_active=True).select_related('student')
            except:
                enrollments = []
            
            # Calculate batch duration
            duration = ''
            completion_date = timezone.now().date()
            
            if batch.start_date and batch.end_date:
                duration_days = (batch.end_date - batch.start_date).days
                if duration_days > 30:
                    months = duration_days // 30
                    duration = f"{months} Month{'s' if months > 1 else ''}"
                else:
                    weeks = duration_days // 7
                    duration = f"{weeks} Week{'s' if weeks > 1 else ''}"
                
                completion_date = batch.end_date
            
            for enrollment in enrollments:
                grade = enrollment.grade if hasattr(enrollment, 'grade') else ''
                
                cert = IssuedCertificate.objects.create(
                    template=template,
                    certificate_type=template.certificate_type,
                    student=enrollment.student,
                    course=batch.course,
                    batch=batch,
                    student_name=enrollment.student.get_full_name() or enrollment.student.username,
                    course_name=batch.course.title,
                    batch_name=batch.name,
                    grade=grade,
                    duration=duration,
                    issue_date=timezone.now().date(),
                    completion_date=completion_date,
                    issued_by=request.user
                )
                
                try:
                    generate_certificate_pdf(cert)
                except Exception as e:
                    print(f"PDF Generation Error: {e}")
                
                issued_count += 1
            
            messages.success(request, f'✅ Issued {issued_count} certificates to {batch.name}!')
        
        elif issue_type == 'course':
            course_id = request.POST.get('course_id')
            course = get_object_or_404(Course, id=course_id)
            
            # Get course duration
            duration = ''
            try:
                if hasattr(course, 'duration_weeks') and course.duration_weeks:
                    duration = f"{course.duration_weeks} Week{'s' if course.duration_weeks > 1 else ''}"
                elif hasattr(course, 'duration_months') and course.duration_months:
                    duration = f"{course.duration_months} Month{'s' if course.duration_months > 1 else ''}"
            except:
                pass
            
            # Get direct course enrollments
            enrollments = Enrollment.objects.filter(
                course=course,
                is_active=True
            ).select_related('student')
            
            for enrollment in enrollments:
                grade = enrollment.grade if hasattr(enrollment, 'grade') else ''
                completion_date = enrollment.completion_date if hasattr(enrollment, 'completion_date') and enrollment.completion_date else timezone.now().date()
                
                cert = IssuedCertificate.objects.create(
                    template=template,
                    certificate_type=template.certificate_type,
                    student=enrollment.student,
                    course=course,
                    student_name=enrollment.student.get_full_name() or enrollment.student.username,
                    course_name=course.title,
                    batch_name='',  # No batch
                    grade=grade,
                    duration=duration,
                    issue_date=timezone.now().date(),
                    completion_date=completion_date,
                    issued_by=request.user
                )
                
                try:
                    generate_certificate_pdf(cert)
                except Exception as e:
                    print(f"PDF Generation Error: {e}")
                
                issued_count += 1
            
            messages.success(request, f'✅ Issued {issued_count} certificates for {course.title}!')
        
        return redirect('certificates:admin_issued')
    
    # GET request
    templates = CertificateTemplate.objects.filter(is_active=True)
    students = User.objects.filter(role='student', is_active=True).order_by('first_name', 'last_name')
    
    batches = Batch.objects.filter(is_active=True).select_related('course').order_by('-created_at')
    courses = Course.objects.filter(is_active=True).order_by('title')
    
    context = {
        'templates': templates,
        'students': students,
        'batches': batches,
        'courses': courses,
    }
    
    return render(request, 'admin/issue_certificate.html', context)


@login_required
def view_certificate(request, certificate_id):
    """View certificate with all data rendered"""
    certificate = get_object_or_404(IssuedCertificate, id=certificate_id)
    
    # Check permissions
    if request.user.role == 'student' and certificate.student != request.user:
        messages.error(request, '❌ Access denied!')
        return redirect('user_login')
    
    # Render complete HTML
    html_content = render_certificate_html(certificate)
    
    return HttpResponse(html_content)


def generate_certificate_pdf(certificate):
    """
    Generate PDF from certificate HTML
    Uses WeasyPrint for HTML to PDF conversion
    """
    try:
        from weasyprint import HTML
        from django.conf import settings
        import os
        
        # Get rendered HTML
        html_content = render_certificate_html(certificate)
        
        # Generate PDF filename
        filename = f"certificate_{certificate.student.username}_{certificate.certificate_id}.pdf"
        pdf_path = os.path.join(settings.MEDIA_ROOT, 'certificates', 'issued', filename)
        
        # Create directory if not exists
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        # Generate PDF
        HTML(string=html_content).write_pdf(pdf_path)
        
        # Save PDF path to certificate
        certificate.generated_pdf = f'certificates/issued/{filename}'
        certificate.save()
        
        return True
        
    except Exception as e:
        print(f"PDF Generation Error: {e}")
        return False


@login_required
def download_certificate(request, certificate_id):
    """Download certificate PDF"""
    certificate = get_object_or_404(IssuedCertificate, id=certificate_id)
    
    # Check permissions
    if request.user.role == 'student' and certificate.student != request.user:
        messages.error(request, '❌ Access denied!')
        return redirect('user_login')
    
    # Generate PDF if not exists
    if not certificate.generated_pdf:
        generate_certificate_pdf(certificate)
    
    if certificate.generated_pdf:
        from django.conf import settings
        import os
        
        pdf_path = os.path.join(settings.MEDIA_ROOT, str(certificate.generated_pdf))
        
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pdf:
                response = HttpResponse(pdf.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="certificate_{certificate.student.username}.pdf"'
                return response
    
    messages.error(request, '❌ Certificate PDF not found!')
    return redirect('certificates:admin_issued')


@login_required
def admin_edit_template(request, template_id):
    """Edit certificate template with GrapeJS page builder"""
    if request.user.role != 'superadmin':
        return redirect('user_login')
    
    template = get_object_or_404(CertificateTemplate, id=template_id)
    
    if request.method == 'POST':
        template.name = request.POST.get('name', template.name)
        template.orientation = request.POST.get('orientation', template.orientation)
        template.html_content = request.POST.get('html_content', template.html_content)
        template.css_content = request.POST.get('css_content', template.css_content)
        
        # Handle thumbnail upload
        if 'thumbnail' in request.FILES:
            template.thumbnail = request.FILES['thumbnail']
        
        template.save()
        messages.success(request, f'✅ Template "{template.name}" updated successfully!')
        return redirect('certificates:admin_edit_template', template_id=template.id)
    
    context = {
        'template': template,
        'placeholders': template.get_default_placeholders(),
    }
    
    return render(request, 'admin/edit_template.html', context)



# ==================== PUBLIC ====================

def verify_certificate(request, code):
    """Public certificate verification"""
    try:
        cert = IssuedCertificate.objects.get(verification_code=code, status='active')
        
        context = {
            'certificate': cert,
            'is_valid': True,
        }
    except IssuedCertificate.DoesNotExist:
        context = {
            'is_valid': False,
        }
    
    return render(request, 'public/verify.html', context)


# ==================== HELPER FUNCTIONS ====================

def get_default_template_html():
    """Default certificate HTML template"""
    return """
    <div class="certificate">
        <h1>Certificate of Completion</h1>
        <p class="subtitle">This is to certify that</p>
        <h2 class="student-name">{student_name}</h2>
        <p class="description">has successfully completed</p>
        <h3 class="course-name">{course_name}</h3>
        <div class="details">
            <p>Batch: {batch_name}</p>
            <p>Completion Date: {completion_date}</p>
            <p>Certificate ID: {certificate_id}</p>
        </div>
        <div class="signature">
            <div class="sign-line"></div>
            <p>{instructor_name}</p>
            <p class="title">Instructor</p>
        </div>
    </div>
    """


def get_default_template_css():
    """Default certificate CSS"""
    return """
    body {
        font-family: 'Georgia', serif;
        margin: 0;
        padding: 50px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .certificate {
        background: white;
        border: 15px solid #667eea;
        padding: 60px;
        text-align: center;
        max-width: 800px;
        margin: 0 auto;
    }
    h1 {
        color: #667eea;
        font-size: 48px;
        margin-bottom: 20px;
    }
    .student-name {
        color: #333;
        font-size: 36px;
        margin: 30px 0;
        text-decoration: underline;
    }
    .course-name {
        color: #764ba2;
        font-size: 28px;
        margin: 20px 0;
    }
    .details {
        margin: 40px 0;
    }
    .signature {
        margin-top: 60px;
    }
    .sign-line {
        border-top: 2px solid #333;
        width: 300px;
        margin: 0 auto 10px;
    }
    """


def get_instructor_students(instructor):
    """Get all students from instructor's batches/courses"""
    from courses.models import Enrollment
    
    # Students from batches
    batch_students = User.objects.filter(
        batch_enrollments__batch__instructor=instructor,
        batch_enrollments__is_active=True,
        role='student'
    ).distinct()
    
    # Students from direct course enrollments
    course_students = User.objects.filter(
        enrollments__course__instructor=instructor,
        enrollments__is_active=True,
        role='student'
    ).distinct()
    
    # Combine
    all_students = (batch_students | course_students).order_by('first_name', 'last_name')
    
    return all_students


def is_instructor_student(instructor, student):
    """Check if student belongs to instructor"""
    # Check batch enrollment
    batch_enrolled = BatchEnrollment.objects.filter(
        student=student,
        batch__instructor=instructor,
        is_active=True
    ).exists()
    
    if batch_enrolled:
        return True
    
    # Check course enrollment
    from courses.models import Enrollment
    course_enrolled = Enrollment.objects.filter(
        student=student,
        course__instructor=instructor,
        is_active=True
    ).exists()
    
    return course_enrolled



